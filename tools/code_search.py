#!/usr/bin/env python3
"""
code_search.py - FTS5-powered code search indexer for Python projects

PURPOSE: Index Python codebases by function/class using AST parsing, store in
         SQLite FTS5 for fast ranked search via BM25.
WHEN TO USE:
    python3 framework/tools/code_search.py index <dir1> [dir2 ...]
    python3 framework/tools/code_search.py search "query terms"
    python3 framework/tools/code_search.py reindex <dir1> [dir2 ...]
WHEN TO DELETE: Never — core framework tool
OWNER: CTO
CREATED: 2026-02-21
"""

from __future__ import annotations

import argparse
import ast
import logging
import sqlite3
import sys
import textwrap
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / ".code_search.db"

logger = logging.getLogger("code_search")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            chunk_type TEXT NOT NULL,
            name TEXT NOT NULL,
            source TEXT NOT NULL,
            docstring TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            file_path,
            name,
            chunk_type,
            docstring,
            source,
            content='chunks',
            content_rowid='id',
            tokenize='porter unicode61'
        )
    """)
    # Triggers to keep FTS in sync
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, file_path, name, chunk_type, docstring, source)
            VALUES (new.id, new.file_path, new.name, new.chunk_type, new.docstring, new.source);
        END;
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, file_path, name, chunk_type, docstring, source)
            VALUES ('delete', old.id, old.file_path, old.name, old.chunk_type, old.docstring, old.source);
        END;
        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, file_path, name, chunk_type, docstring, source)
            VALUES ('delete', old.id, old.file_path, old.name, old.chunk_type, old.docstring, old.source);
            INSERT INTO chunks_fts(rowid, file_path, name, chunk_type, docstring, source)
            VALUES (new.id, new.file_path, new.name, new.chunk_type, new.docstring, new.source);
        END;
    """)
    conn.commit()
    return conn


def clear_db(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM chunks")
    conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
    conn.commit()

# ---------------------------------------------------------------------------
# AST Chunking
# ---------------------------------------------------------------------------

def _get_source_segment(lines: list[str], node: ast.AST) -> str:
    """Extract source lines for an AST node (1-indexed start_line)."""
    start = node.lineno - 1
    end = getattr(node, "end_lineno", node.lineno)
    return "\n".join(lines[start:end])


def _get_decorator_start(node: ast.AST) -> int:
    """Get the earliest line including decorators."""
    if hasattr(node, "decorator_list") and node.decorator_list:
        return node.decorator_list[0].lineno
    return node.lineno


def extract_chunks(file_path: Path, source: str) -> list[dict]:
    """Parse a Python file and extract searchable chunks."""
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        logger.warning("Syntax error in %s: %s", file_path, e)
        return []

    lines = source.splitlines()
    chunks: list[dict] = []
    top_level_ranges: list[tuple[int, int]] = []  # track covered lines

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            start = _get_decorator_start(node)
            end = node.end_lineno or node.lineno
            body_lines = end - start + 1
            docstring = ast.get_docstring(node) or ""
            if body_lines < 3 and not docstring:
                continue
            src = "\n".join(lines[start - 1 : end])
            chunks.append({
                "file_path": str(file_path),
                "start_line": start,
                "end_line": end,
                "chunk_type": "function",
                "name": node.name,
                "source": src,
                "docstring": docstring,
            })
            top_level_ranges.append((start, end))

        elif isinstance(node, ast.ClassDef):
            start = _get_decorator_start(node)
            end = node.end_lineno or node.lineno
            class_docstring = ast.get_docstring(node) or ""

            # Class-level chunk: docstring + __init__ (if present)
            init_node = None
            method_nodes = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    if item.name == "__init__":
                        init_node = item
                    else:
                        method_nodes.append(item)

            # Build class overview chunk
            if init_node:
                init_end = init_node.end_lineno or init_node.lineno
                class_src = "\n".join(lines[start - 1 : init_end])
            else:
                # Just the class def line + docstring area
                first_method_line = None
                for item in node.body:
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) and item.name != "__init__":
                        first_method_line = _get_decorator_start(item)
                        break
                if first_method_line and first_method_line > start + 1:
                    class_src = "\n".join(lines[start - 1 : first_method_line - 1])
                else:
                    class_src = "\n".join(lines[start - 1 : end])

            chunks.append({
                "file_path": str(file_path),
                "start_line": start,
                "end_line": end,
                "chunk_type": "class",
                "name": node.name,
                "source": class_src,
                "docstring": class_docstring,
            })

            # Each method as separate chunk
            for method in method_nodes:
                m_start = _get_decorator_start(method)
                m_end = method.end_lineno or method.lineno
                body_lines = m_end - m_start + 1
                m_docstring = ast.get_docstring(method) or ""
                if body_lines < 3 and not m_docstring:
                    continue
                m_src = "\n".join(lines[m_start - 1 : m_end])
                chunks.append({
                    "file_path": str(file_path),
                    "start_line": m_start,
                    "end_line": m_end,
                    "chunk_type": "method",
                    "name": f"{node.name}.{method.name}",
                    "source": m_src,
                    "docstring": m_docstring,
                })

            top_level_ranges.append((start, end))

    # Module-level chunk: everything NOT in functions/classes
    module_docstring = ast.get_docstring(tree) or ""
    module_lines = []
    for i, line in enumerate(lines, 1):
        if not any(s <= i <= e for s, e in top_level_ranges):
            module_lines.append(line)
    module_src = "\n".join(module_lines).strip()
    if module_src or module_docstring:
        chunks.append({
            "file_path": str(file_path),
            "start_line": 1,
            "end_line": len(lines),
            "chunk_type": "module",
            "name": file_path.stem,
            "source": module_src[:2000] if len(module_src) > 2000 else module_src,
            "docstring": module_docstring,
        })

    return chunks

# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def index_directories(conn: sqlite3.Connection, dirs: list[str], verbose: bool = False) -> int:
    """Walk directories, parse Python files, insert chunks. Returns chunk count."""
    total = 0
    file_count = 0
    for dir_path in dirs:
        root = Path(dir_path)
        if not root.exists():
            logger.warning("Directory not found: %s", root)
            continue
        for py_file in sorted(root.rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                logger.warning("Cannot read %s: %s", py_file, e)
                continue
            chunks = extract_chunks(py_file, source)
            if verbose:
                logger.info("  %s → %d chunks", py_file, len(chunks))
            for c in chunks:
                conn.execute(
                    "INSERT INTO chunks (file_path, start_line, end_line, chunk_type, name, source, docstring) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (c["file_path"], c["start_line"], c["end_line"],
                     c["chunk_type"], c["name"], c["source"], c["docstring"]),
                )
            total += len(chunks)
            file_count += 1
    conn.commit()
    if verbose:
        logger.info("Indexed %d files → %d chunks", file_count, total)
    return total

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    """Search indexed chunks using FTS5 BM25 ranking."""
    # Escape special FTS5 characters in query
    safe_query = query.replace('"', '""')
    # Use OR between words for broader matching, with original phrase boosted
    words = safe_query.split()
    if len(words) > 1:
        # phrase match OR individual words
        fts_query = f'"{safe_query}" OR {" OR ".join(words)}'
    else:
        fts_query = safe_query

    try:
        rows = conn.execute(
            """
            SELECT c.file_path, c.start_line, c.end_line, c.chunk_type, c.name,
                   c.docstring, c.source, rank
            FROM chunks_fts fts
            JOIN chunks c ON c.id = fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
    except sqlite3.OperationalError as e:
        logger.error("Search error: %s", e)
        return []

    results = []
    for row in rows:
        results.append({
            "file_path": row[0],
            "start_line": row[1],
            "end_line": row[2],
            "chunk_type": row[3],
            "name": row[4],
            "docstring": row[5],
            "source": row[6],
            "rank": row[7],
        })
    return results


def format_results(results: list[dict]) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        # Build snippet from docstring or first lines of source
        snippet = r["docstring"] or ""
        if not snippet:
            src_lines = r["source"].splitlines()
            snippet = "\n".join(src_lines[:3])
        # Truncate and wrap
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        wrapped = textwrap.fill(snippet, width=80, initial_indent="    ", subsequent_indent="    ")

        lines.append(
            f"[{i}] {r['file_path']}:{r['start_line']}-{r['end_line']} "
            f"({r['chunk_type']}: {r['name']})"
        )
        lines.append(wrapped)
        lines.append("")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="FTS5-powered code search indexer for Python projects"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max search results (default: 10)")
    sub = parser.add_subparsers(dest="command")

    idx = sub.add_parser("index", help="Index directories (additive)")
    idx.add_argument("dirs", nargs="+", help="Directories to index")

    ridx = sub.add_parser("reindex", help="Clear and rebuild index")
    ridx.add_argument("dirs", nargs="+", help="Directories to index")

    srch = sub.add_parser("search", help="Search indexed code")
    srch.add_argument("query", help="Search query")
    srch.add_argument("--limit", "-n", type=int, default=None, help="Max results (default: 10)")

    sub.add_parser("stats", help="Show index statistics")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    if not args.command:
        parser.print_help()
        sys.exit(1)

    conn = get_db()

    if args.command == "index":
        t0 = time.monotonic()
        n = index_directories(conn, args.dirs, verbose=args.verbose)
        elapsed = time.monotonic() - t0
        print(f"Indexed {n} chunks in {elapsed:.2f}s")

    elif args.command == "reindex":
        clear_db(conn)
        t0 = time.monotonic()
        n = index_directories(conn, args.dirs, verbose=args.verbose)
        elapsed = time.monotonic() - t0
        print(f"Re-indexed {n} chunks in {elapsed:.2f}s")

    elif args.command == "search":
        limit = getattr(args, "limit", None) or 10
        # subcommand-level --limit overrides global
        results = search(conn, args.query, limit=limit)
        print(format_results(results))

    elif args.command == "stats":
        row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
        files = conn.execute("SELECT COUNT(DISTINCT file_path) FROM chunks").fetchone()
        print(f"Chunks: {row[0]}")
        print(f"Files:  {files[0]}")
        by_type = conn.execute(
            "SELECT chunk_type, COUNT(*) FROM chunks GROUP BY chunk_type ORDER BY chunk_type"
        ).fetchall()
        for t, c in by_type:
            print(f"  {t}: {c}")

    conn.close()


if __name__ == "__main__":
    main()

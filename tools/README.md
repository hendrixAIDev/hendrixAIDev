# Framework Tools

Shared developer tools for the workspace.

## code_search.py — FTS5 Code Search Indexer

Fast, ranked code search across Python projects using SQLite FTS5 (BM25 ranking) and AST-based chunking.

### Quick Start

```bash
# Index a project (additive — can index multiple dirs)
python3 framework/tools/code_search.py index projects/churn_copilot/app/src projects/churn_copilot/app/tests

# Search
python3 framework/tools/code_search.py search "optimistic locking"

# Re-index (clears DB first, then indexes)
python3 framework/tools/code_search.py reindex projects/churn_copilot/app/src

# Stats
python3 framework/tools/code_search.py stats
```

### Options

| Flag | Description |
|------|-------------|
| `--limit N` / `-n N` | Max results (default: 10) |
| `--verbose` / `-v` | Show per-file indexing details |

### How It Works

1. **Walks** directories for `*.py` files (skips `__pycache__`)
2. **Parses** each file with Python's `ast` module
3. **Chunks** into searchable units:
   - Functions/async functions (with decorators, docstring, full body)
   - Classes (docstring + `__init__`)
   - Methods (each method separately)
   - Module-level code (imports, constants, module docstring)
4. **Stores** in SQLite FTS5 with porter stemming
5. **Searches** with BM25 ranking; supports phrase and keyword queries

### Database

Stored at `framework/tools/.code_search.db` (gitignored). Pure stdlib — no external dependencies.

---

## Other Tools

- **generate_dependency_graph.py** — Generate project dependency graphs
- **smoke_test.py** — Run smoke tests across projects

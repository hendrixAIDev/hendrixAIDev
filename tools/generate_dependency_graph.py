#!/usr/bin/env python3
"""
generate_dependency_graph.py - Python Project Dependency Graph Generator

PURPOSE:
    Generates a DEPENDENCY_GRAPH.json for any Python project using AST static
    analysis. Gives sub-agents full visibility into cross-file dependencies
    before making code changes, preventing missed import/reference updates.

PROBLEM SOLVED:
    Sub-agents frequently miss cross-file implications when modifying code.
    Issue #62: moved go_to_add_card() but 3 test files still imported from old
    location causing 16 test failures and wasted QA cycles.

WHEN TO USE:
    - BEFORE starting any code-modifying work (see current state)
    - AFTER completing code changes (update graph for next agent)
    - To find all callers of a function before moving/renaming it

USAGE:
    # Generate for ChurnPilot
    python framework/tools/generate_dependency_graph.py \\
        --root projects/churn_copilot/app \\
        --output projects/churn_copilot/app/DEPENDENCY_GRAPH.json

    # Generate for StatusPulse
    python framework/tools/generate_dependency_graph.py \\
        --root projects/statuspulse \\
        --output projects/statuspulse/DEPENDENCY_GRAPH.json

    # Generate for current directory
    python framework/tools/generate_dependency_graph.py --root .

    # Quick scan (print summary, no file output)
    python framework/tools/generate_dependency_graph.py --root . --summary

OUTPUT SCHEMA:
    {
      "generated_at": "2026-02-18T12:00:00Z",
      "project_root": "projects/churn_copilot/app",
      "total_files": 42,
      "files": {
        "src/ui/app.py": {
          "functions": ["main", "render_dashboard"],
          "classes": ["App"],
          "imports_from": ["src.ui.pages.auth_page", "src.ui.styles"],
          "imported_by": ["tests/test_app.py"]
        }
      },
      "functions": {
        "go_to_add_card": {
          "defined_in": "src/ui/pages/dashboard/main_dashboard.py",
          "called_by": ["src/ui/components/empty_state.py"],
          "calls": ["st.session_state"]
        }
      },
      "classes": {
        "App": {
          "defined_in": "src/ui/app.py",
          "bases": ["object"],
          "methods": ["__init__", "run"],
          "used_in": ["tests/test_app.py"]
        }
      }
    }

OWNER: DevOps/Infrastructure (shared utility, workspace-level)
CREATED: 2026-02-18
RELATED: Issue #68
"""

import ast
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────
# AST Visitors
# ─────────────────────────────────────────────

class FileAnalyzer(ast.NodeVisitor):
    """Extracts definitions, calls, and imports from a single Python file."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.functions: list[dict[str, Any]] = []   # {name, class, line, calls}
        self.classes: list[dict[str, Any]] = []     # {name, bases, methods, line}
        self.imports: list[str] = []                 # module paths imported from/as
        self.current_class: str | None = None
        self._class_stack: list[str] = []

    # ── Imports ──────────────────────────────

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    # ── Classes ──────────────────────────────

    def visit_ClassDef(self, node: ast.ClassDef):
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(_attr_to_str(b))

        methods = [
            n.name for n in ast.walk(node)
            if isinstance(n, ast.FunctionDef) and n in node.body
        ]

        self.classes.append({
            "name": node.name,
            "bases": bases,
            "methods": methods,
            "line": node.lineno,
        })

        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    # ── Functions ─────────────────────────────

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_function(node)

    def _process_function(self, node):
        parent_class = self._class_stack[-1] if self._class_stack else None

        # Collect calls made inside this function
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = _call_to_str(child.func)
                if call_name and call_name not in calls:
                    calls.append(call_name)

        self.functions.append({
            "name": node.name,
            "class": parent_class,
            "line": node.lineno,
            "calls": calls,
        })

        # If inside a class, push class context for nested functions
        if not self._class_stack:
            self.generic_visit(node)
        else:
            # Already handled via class visit; don't double-recurse
            self.generic_visit(node)


def _attr_to_str(node) -> str:
    """Convert ast.Attribute chain to dotted string (e.g. st.session_state)."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _call_to_str(node) -> str | None:
    """Convert ast.Call func node to string representation."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return _attr_to_str(node)
    return None


# ─────────────────────────────────────────────
# Core Graph Builder
# ─────────────────────────────────────────────

def find_python_files(root: Path) -> list[Path]:
    """Recursively find all .py files, skipping hidden dirs and __pycache__."""
    skip_dirs = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules", ".tox"}
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]
        for fname in filenames:
            if fname.endswith(".py"):
                results.append(Path(dirpath) / fname)
    return sorted(results)


def build_dependency_graph(project_root: str) -> dict[str, Any]:
    """Build the full dependency graph for the given project root."""
    root = Path(project_root).resolve()
    python_files = find_python_files(root)

    # ── Pass 1: Analyze each file ─────────────
    file_analyses: dict[str, FileAnalyzer] = {}
    parse_errors: list[str] = []

    for filepath in python_files:
        rel_path = str(filepath.relative_to(root))
        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(filepath))
            analyzer = FileAnalyzer(rel_path)
            analyzer.visit(tree)
            file_analyses[rel_path] = analyzer
        except SyntaxError as e:
            parse_errors.append(f"{rel_path}: SyntaxError: {e}")
        except Exception as e:
            parse_errors.append(f"{rel_path}: {type(e).__name__}: {e}")

    # ── Pass 2: Build import_by mapping ──────
    # For each file, which other files import from its module path?
    # Map module_path -> rel_path (both ways)
    module_to_file: dict[str, str] = {}
    for rel_path in file_analyses:
        # Convert file path to module-style path
        # e.g. "src/ui/app.py" -> "src.ui.app"
        module_path = rel_path.replace("/", ".").replace("\\", ".")
        if module_path.endswith(".py"):
            module_path = module_path[:-3]
        module_to_file[module_path] = rel_path
        # Also map parent package paths
        parts = module_path.split(".")
        for i in range(1, len(parts)):
            pkg = ".".join(parts[:i])
            if pkg not in module_to_file:
                module_to_file[pkg] = rel_path  # rough mapping for packages

    # Build imported_by: file -> list of files that import it
    imported_by: dict[str, list[str]] = {p: [] for p in file_analyses}
    for rel_path, analyzer in file_analyses.items():
        for imp_module in analyzer.imports:
            # Find which file this import refers to
            target_file = module_to_file.get(imp_module)
            if target_file and target_file != rel_path and target_file in imported_by:
                if rel_path not in imported_by[target_file]:
                    imported_by[target_file].append(rel_path)

    # ── Pass 3: Build functions section ──────
    # Track all function definitions (qualified name -> info)
    # For ambiguity: if same function name in multiple files, use full path
    all_functions: dict[str, dict[str, Any]] = {}
    # Map function name -> list of (file, class)
    func_name_to_defs: dict[str, list[tuple[str, str | None]]] = {}

    for rel_path, analyzer in file_analyses.items():
        for func_info in analyzer.functions:
            fname = func_info["name"]
            if fname not in func_name_to_defs:
                func_name_to_defs[fname] = []
            func_name_to_defs[fname].append((rel_path, func_info["class"]))

    for rel_path, analyzer in file_analyses.items():
        for func_info in analyzer.functions:
            fname = func_info["name"]
            class_name = func_info["class"]
            # Qualified key: ClassName.method_name or just function_name
            if class_name:
                qualified_key = f"{class_name}.{fname}"
            else:
                qualified_key = fname

            # If multiple files define same name, use "file::func" key
            defs = func_name_to_defs.get(fname, [])
            unqualified_definitions = [d for d in defs if d[1] == class_name]
            if len(unqualified_definitions) > 1:
                qualified_key = f"{rel_path}::{qualified_key}"

            if qualified_key not in all_functions:
                all_functions[qualified_key] = {
                    "defined_in": rel_path,
                    "class": class_name,
                    "line": func_info["line"],
                    "calls": func_info["calls"],
                    "called_by": [],
                }

    # ── Pass 4: Build called_by mapping ──────
    # For each file's function calls, find which defined functions they call
    for caller_file, analyzer in file_analyses.items():
        for func_info in analyzer.functions:
            for call_name in func_info["calls"]:
                # Find matching function definition
                for func_key, func_data in all_functions.items():
                    # Match by function name (last segment of key)
                    key_base = func_key.split("::")[-1]  # strip file prefix if present
                    simple_name = key_base.split(".")[-1]  # strip class prefix
                    if (call_name == simple_name or
                            call_name == key_base or
                            call_name.endswith(f".{simple_name}")):
                        # Don't add self-references
                        if caller_file != func_data["defined_in"]:
                            if caller_file not in func_data["called_by"]:
                                func_data["called_by"].append(caller_file)
                        break

    # ── Pass 5: Build classes section ────────
    all_classes: dict[str, dict[str, Any]] = {}
    for rel_path, analyzer in file_analyses.items():
        for cls_info in analyzer.classes:
            cname = cls_info["name"]
            # Handle duplicates with file prefix
            if cname in all_classes:
                key = f"{rel_path}::{cname}"
            else:
                key = cname
            all_classes[key] = {
                "defined_in": rel_path,
                "bases": cls_info["bases"],
                "methods": cls_info["methods"],
                "line": cls_info["line"],
                "used_in": [],  # filled in pass 6
            }

    # ── Pass 6: Classes used_in mapping ──────
    # Find files that import or reference each class name
    for rel_path, analyzer in file_analyses.items():
        for cls_key, cls_data in all_classes.items():
            cname = cls_key.split("::")[-1]
            # Check if this file imports from the file defining the class
            defining_file = cls_data["defined_in"]
            if (rel_path != defining_file and
                    defining_file in imported_by and
                    rel_path in imported_by[defining_file]):
                if rel_path not in cls_data["used_in"]:
                    cls_data["used_in"].append(rel_path)

    # ── Pass 7: Assemble final graph ──────────
    files_section: dict[str, dict[str, Any]] = {}
    for rel_path, analyzer in file_analyses.items():
        files_section[rel_path] = {
            "functions": [f["name"] for f in analyzer.functions],
            "classes": [c["name"] for c in analyzer.classes],
            "imports_from": sorted(set(analyzer.imports)),
            "imported_by": sorted(imported_by.get(rel_path, [])),
        }

    graph = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "total_files": len(file_analyses),
        "parse_errors": parse_errors,
        "files": files_section,
        "functions": all_functions,
        "classes": all_classes,
    }

    return graph


# ─────────────────────────────────────────────
# Summary Printer
# ─────────────────────────────────────────────

def print_summary(graph: dict[str, Any], show_callers: str | None = None):
    """Print a human-readable summary of the dependency graph."""
    print(f"\n{'='*60}")
    print(f"DEPENDENCY GRAPH SUMMARY")
    print(f"{'='*60}")
    print(f"Project:    {graph['project_root']}")
    print(f"Generated:  {graph['generated_at']}")
    print(f"Files:      {graph['total_files']}")
    print(f"Functions:  {len(graph['functions'])}")
    print(f"Classes:    {len(graph['classes'])}")

    if graph.get("parse_errors"):
        print(f"\n⚠️  Parse Errors ({len(graph['parse_errors'])}):")
        for err in graph["parse_errors"]:
            print(f"   {err}")

    # Most-imported files
    print(f"\n📦 Most-Imported Files (top 10):")
    by_importers = sorted(
        graph["files"].items(),
        key=lambda x: len(x[1]["imported_by"]),
        reverse=True,
    )
    for fpath, fdata in by_importers[:10]:
        if fdata["imported_by"]:
            print(f"   {len(fdata['imported_by']):3d} importers  {fpath}")

    # Most-called functions
    print(f"\n🔧 Most-Called Functions (top 10):")
    by_callers = sorted(
        graph["functions"].items(),
        key=lambda x: len(x[1]["called_by"]),
        reverse=True,
    )
    for fname, fdata in by_callers[:10]:
        if fdata["called_by"]:
            print(f"   {len(fdata['called_by']):3d} callers  {fname}  ({fdata['defined_in']})")

    # Specific function lookup
    if show_callers:
        print(f"\n🔍 Callers of '{show_callers}':")
        found = False
        for fname, fdata in graph["functions"].items():
            if show_callers.lower() in fname.lower():
                print(f"   Function: {fname}")
                print(f"   Defined:  {fdata['defined_in']}")
                if fdata["called_by"]:
                    print(f"   Called by:")
                    for caller in fdata["called_by"]:
                        print(f"     - {caller}")
                else:
                    print(f"   Called by: (none found)")
                found = True
        if not found:
            print(f"   (no function matching '{show_callers}' found)")

    print(f"\n{'='*60}\n")


# ─────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a dependency graph for a Python project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ChurnPilot
  python framework/tools/generate_dependency_graph.py \\
      --root projects/churn_copilot/app \\
      --output projects/churn_copilot/app/DEPENDENCY_GRAPH.json

  # StatusPulse
  python framework/tools/generate_dependency_graph.py \\
      --root projects/statuspulse \\
      --output projects/statuspulse/DEPENDENCY_GRAPH.json

  # Print summary only (no output file)
  python framework/tools/generate_dependency_graph.py --root . --summary

  # Find all callers of a specific function
  python framework/tools/generate_dependency_graph.py --root . --find go_to_add_card
        """,
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Project root directory to scan",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path (default: <root>/DEPENDENCY_GRAPH.json)",
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Print human-readable summary to stdout",
    )
    parser.add_argument(
        "--find", "-f",
        help="Find all callers of a specific function name",
    )
    parser.add_argument(
        "--no-file",
        action="store_true",
        help="Don't write output file (useful with --summary or --find)",
    )
    args = parser.parse_args()

    # Validate root
    root_path = Path(args.root)
    if not root_path.exists():
        print(f"❌ Error: Project root not found: {args.root}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Scanning {root_path.resolve()} ...")
    import time
    start = time.time()

    graph = build_dependency_graph(args.root)

    elapsed = time.time() - start
    print(f"✅ Analyzed {graph['total_files']} files in {elapsed:.2f}s")

    if graph.get("parse_errors"):
        print(f"⚠️  {len(graph['parse_errors'])} parse errors (see graph.parse_errors)")

    # Output file
    if not args.no_file:
        output_path = args.output or str(root_path / "DEPENDENCY_GRAPH.json")
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(graph, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"📄 Graph written to: {output_file}")

    # Summary
    if args.summary or args.find:
        print_summary(graph, show_callers=args.find)
    elif not args.no_file:
        # Brief stats
        funcs_with_callers = sum(
            1 for f in graph["functions"].values() if f["called_by"]
        )
        print(f"   {len(graph['functions'])} functions, "
              f"{funcs_with_callers} have cross-file callers")
        print(f"   {len(graph['classes'])} classes defined")

    return 0


if __name__ == "__main__":
    sys.exit(main())

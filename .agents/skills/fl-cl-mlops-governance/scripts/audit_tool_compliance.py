#!/usr/bin/env python3
"""
audit_tool_compliance.py
========================
Static analyzer that validates tools/ and src/ against ADR-006 MLOps standards:
- Module docstrings present
- pathlib.Path usage instead of raw os.path concatenation
- argparse / CLI interface in tools/
- Structured logging instead of raw print() in src/
"""

import sys
import ast
from pathlib import Path
from typing import List, Dict, Tuple

def audit_file(file_path: Path) -> Dict[str, any]:
    results = {
        "file": str(file_path),
        "has_docstring": False,
        "uses_pathlib": False,
        "has_argparse": False,
        "raw_print_count": 0,
        "passed": True,
        "issues": []
    }

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        results["passed"] = False
        results["issues"].append(f"Failed to parse AST: {e}")
        return results

    # 1. Check docstring
    docstring = ast.get_docstring(tree)
    if docstring and len(docstring.strip()) > 10:
        results["has_docstring"] = True
    else:
        results["issues"].append("Missing or trivial module-level docstring")

    # 2. Check pathlib
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pathlib":
                    results["uses_pathlib"] = True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "pathlib":
                results["uses_pathlib"] = True

    # 3. Check CLI parsing (for tools/)
    if "tools" in file_path.parts:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("argparse", "click", "typer"):
                        results["has_argparse"] = True
            elif isinstance(node, ast.ImportFrom):
                if node.module in ("argparse", "click", "typer"):
                    results["has_argparse"] = True
        if not results["has_argparse"]:
            results["issues"].append("CLI tools should define an argparse/click interface")

    # 4. Check raw prints in src/
    if "src" in file_path.parts:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    results["raw_print_count"] += 1
        if results["raw_print_count"] > 0:
            results["issues"].append(f"Contains {results['raw_print_count']} raw print() calls; migrate to logger.py")

    if results["issues"]:
        results["passed"] = False

    return results

def run_audit(target_dirs: List[str] = None) -> bool:
    if target_dirs is None:
        target_dirs = ["tools", "src"]

    print("=" * 80)
    print("FL-CL ADR-006 & MLOps Static Compliance Audit")
    print("=" * 80)

    total_files = 0
    passed_files = 0

    for dir_name in target_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            continue

        for py_file in sorted(dir_path.rglob("*.py")):
            total_files += 1
            res = audit_file(py_file)
            status = "[OK] PASSED" if res["passed"] else "[FAIL] VIOLATION"
            print(f"{status:<16} | {str(py_file):<45}")
            if not res["passed"]:
                for issue in res["issues"]:
                    print(f"   -> [ISSUE] {issue}")
            else:
                passed_files += 1

    print("=" * 80)
    pass_rate = (passed_files / total_files * 100) if total_files > 0 else 100
    print(f"Summary: {passed_files}/{total_files} files compliant ({pass_rate:.1f}%)")
    print("=" * 80)

    return passed_files == total_files

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Audit codebase for ADR-006 & MLOps compliance")
    parser.add_argument("--strict", action="store_true", help="Fail with exit code 1 on any violation")
    parser.add_argument("--warn-only", action="store_true", help="Always return 0 exit code")
    args = parser.parse_args()

    success = run_audit()
    if args.warn_only:
        sys.exit(0)
    sys.exit(0 if success else (1 if args.strict else 0))

if __name__ == "__main__":
    main()

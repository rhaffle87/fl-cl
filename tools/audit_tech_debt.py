"""
tools/audit_tech_debt.py — Technical Debt & Ponytail Ledger Auditor

Scans the repository for technical debt markers (TODO, FIXME, HACK, XXX, BUG, ponytail:)
across source code, infrastructure, and tools using strict word-boundary matching.
Categorizes findings by severity and exports a structured technical debt ledger.

Target environment: Local / Proxmox VE testbed
Usage:
    python tools/audit_tech_debt.py [--strict] [--export data/reports/technical_debt_ledger.csv]
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Debt markers with strict word boundaries and severity classification
MARKERS = [
    (re.compile(r'\bFIXME\b'), "FIXME", "HIGH"),
    (re.compile(r'\bBUG\b'), "BUG", "HIGH"),
    (re.compile(r'\bXXX\b'), "XXX", "HIGH"),
    (re.compile(r'\bHACK\b'), "HACK", "MEDIUM"),
    (re.compile(r'ponytail:'), "ponytail:", "MEDIUM"),
    (re.compile(r'\bTODO\b'), "TODO", "LOW"),
]

SCAN_DIRS = ["src", "tools", "infra", ".agents", "configs"]
EXCLUDE_EXTS = {".pyc", ".png", ".jpg", ".pdf", ".zip", ".tar", ".gz", ".pt", ".onnx", ".csv"}
EXCLUDE_FILES = {"audit_tech_debt.py", "audit_docs.py", "audit_codebase.py"}


def scan_technical_debt():
    findings = []
    
    for scan_dir in SCAN_DIRS:
        target_path = PROJECT_ROOT / scan_dir
        if not target_path.exists():
            continue
            
        for file_path in target_path.rglob("*"):
            if file_path.is_dir() or file_path.suffix in EXCLUDE_EXTS:
                continue
            if file_path.name in EXCLUDE_FILES:
                continue
            if "scratch" in file_path.parts or ".git" in file_path.parts:
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
                
            lines = content.splitlines()
            for lineno, line in enumerate(lines, 1):
                clean = line.strip()
                for regex, marker_name, severity in MARKERS:
                    match = regex.search(clean)
                    if match:
                        desc = clean[match.start():].strip()
                        findings.append({
                            "file": str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                            "line": lineno,
                            "marker": marker_name,
                            "severity": severity,
                            "snippet": clean[:120],
                            "description": desc[:100],
                        })
    return findings


def export_ledger(findings, export_path: Path):
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with open(export_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "line", "marker", "severity", "snippet", "description"])
        writer.writeheader()
        for row in findings:
            writer.writerow(row)
    print(f"[OK] Technical debt ledger exported to: {export_path}")


def main():
    parser = argparse.ArgumentParser(description="Technical Debt & Ponytail Ledger Auditor")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero code if HIGH severity debt is found")
    parser.add_argument("--export", default=str(PROJECT_ROOT / "data" / "reports" / "technical_debt_ledger.csv"),
                        help="Path to export CSV ledger")
    args = parser.parse_args()

    print("=" * 70)
    print("       FL-CL TECHNICAL DEBT & PONYTAIL LEDGER AUDITOR")
    print("=" * 70)

    findings = scan_technical_debt()
    
    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    med_count = sum(1 for f in findings if f["severity"] == "MEDIUM")
    low_count = sum(1 for f in findings if f["severity"] == "LOW")

    print(f"\n[*] Scan Results:")
    print(f"    - Total Debt Items : {len(findings)}")
    print(f"    - HIGH Severity    : {high_count}")
    print(f"    - MEDIUM Severity  : {med_count}")
    print(f"    - LOW Severity     : {low_count}\n")

    if findings:
        print(f"{'SEVERITY':<10} | {'LOCATION':<40} | {'DESCRIPTION'}")
        print("-" * 75)
        for f in findings:
            loc = f"{f['file']}:{f['line']}"
            print(f"{f['severity']:<10} | {loc:<40} | {f['description']}")
        print("-" * 75)
    else:
        print("  [SUCCESS] Zero technical debt or unaddressed stubs found across scanned codebase!")

    if args.export:
        export_ledger(findings, Path(args.export))

    print("=" * 70)
    if args.strict and high_count > 0:
        print(f"[FAIL] Strict audit failed: {high_count} HIGH severity technical debt items require resolution.")
        sys.exit(1)
    else:
        print("[PASS] Technical debt audit completed successfully.")


if __name__ == "__main__":
    main()

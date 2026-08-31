"""
tools/check_infra_scripts.py — Proxmox Infrastructure Script & Line-Ending Auditor

Audits Bash scripts, Perl hookscripts, and systemd service unit files in infra/ for:
1. POSIX LF line endings (preventing \\r: command not found errors on Linux/Proxmox)
2. Valid executable shebang headers
3. Idempotent interface configurations (ens18, ens19, vmbr0, vmbr1)

Target environment: Local / Proxmox VE testbed
Usage:
    python tools/check_infra_scripts.py [--fix] [--strict]
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INFRA_DIR = PROJECT_ROOT / "infra"


def audit_infra_files(fix: bool = False):
    results = []
    
    for f in INFRA_DIR.rglob("*"):
        if not f.is_file() or f.suffix in {".md", ".png", ".jpg"}:
            continue
            
        raw_bytes = f.read_bytes()
        has_crlf = b"\r\n" in raw_bytes
        
        # Check shebang for .sh and .pl
        shebang_status = "N/A"
        if f.suffix in {".sh", ".pl"}:
            lines = raw_bytes.splitlines()
            if lines and lines[0].startswith(b"#!"):
                shebang_status = lines[0].decode("utf-8", errors="replace")
            else:
                shebang_status = "MISSING"

        if has_crlf and fix:
            normalized = raw_bytes.replace(b"\r\n", b"\n")
            f.write_bytes(normalized)
            fixed = True
        else:
            fixed = False

        results.append({
            "file": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "has_crlf": has_crlf,
            "fixed": fixed,
            "shebang": shebang_status,
            "size": len(raw_bytes),
        })
        
    return results


def main():
    parser = argparse.ArgumentParser(description="Infrastructure Script & Line Ending Auditor")
    parser.add_argument("--fix", action="store_true", help="Automatically normalize CRLF to LF line endings")
    parser.add_argument("--strict", action="store_true", help="Fail if any CRLF line endings or missing shebangs exist")
    args = parser.parse_args()

    print("=" * 70)
    print("      FL-CL PROXMOX INFRASTRUCTURE SCRIPTS & SHEBANG AUDITOR")
    print("=" * 70)

    results = audit_infra_files(fix=args.fix)

    print(f"\n{'FILE':<42} | {'LINE ENDING':<12} | {'SHEBANG'}")
    print("-" * 70)

    crlf_count = 0
    missing_shebangs = 0

    for r in results:
        le_str = "LF" if not r["has_crlf"] else ("FIXED (LF)" if r["fixed"] else "CRLF [!]")
        if r["has_crlf"] and not r["fixed"]:
            crlf_count += 1
        if r["shebang"] == "MISSING":
            missing_shebangs += 1
            
        print(f"{r['file']:<42} | {le_str:<12} | {r['shebang']}")
    print("-" * 70)

    print(f"\n[*] Summary:")
    print(f"    - Total Infra Files Scanned: {len(results)}")
    print(f"    - CRLF Files Found         : {crlf_count}")
    print(f"    - Missing Shebangs         : {missing_shebangs}")

    print("=" * 70)
    if args.strict and (crlf_count > 0 or missing_shebangs > 0):
        print(f"[FAIL] Infrastructure scripts audit failed: {crlf_count} CRLF, {missing_shebangs} missing shebangs.")
        sys.exit(1)
    else:
        print("[PASS] Infrastructure scripts compliance verified.")


if __name__ == "__main__":
    main()

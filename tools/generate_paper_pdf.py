"""
generate_paper_pdf.py — Compile IEEE Transactions LaTeX Manuscript to PDF via Testbed TeX Engine.

Synchronizes LaTeX source, BibTeX references, and vector figures to the cluster aggregator
(10.10.130.10), executes a 3-pass pdflatex + bibtex build, and fetches the compiled PDF.

Usage:
    python3 tools/generate_paper_pdf.py [--aggregator 10.10.130.10] [--output docs/paper/manuscript.pdf]
"""

import argparse
import sys
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAPER_DIR = PROJECT_ROOT / "docs" / "paper"


def run_ssh(cmd, host):
    res = subprocess.run(["ssh", "-o", "BatchMode=yes", f"root@{host}", cmd], capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def run_scp_to_remote(local_path, remote_path, host):
    res = subprocess.run(["scp", "-o", "BatchMode=yes", "-r", str(local_path), f"root@{host}:{remote_path}"], capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def run_scp_from_remote(remote_path, local_path, host):
    res = subprocess.run(["scp", "-o", "BatchMode=yes", f"root@{host}:{remote_path}", str(local_path)], capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def main():
    parser = argparse.ArgumentParser(description="Compile IEEE Transactions LaTeX Manuscript to PDF via Remote TeX Engine")
    parser.add_argument("--aggregator", default="10.10.130.10", help="Aggregator node IP with TeX Live environment (default: 10.10.130.10)")
    parser.add_argument("--output", default=str(PAPER_DIR / "manuscript.pdf"), help="Destination path for compiled PDF")
    args = parser.parse_args()

    print("========================================================================")
    print("      FL-CL Publication Manuscript LaTeX PDF Compilation Suite")
    print("========================================================================")

    # 1. Ensure remote build directory exists
    print(f"[*] Setting up build workspace on aggregator ({args.aggregator})...")
    run_ssh("rm -rf /tmp/paper_build && mkdir -p /tmp/paper_build/figures", args.aggregator)

    # 2. Copy paper sources and figures to remote
    print("[*] Uploading LaTeX sources and vector figures...")
    run_scp_to_remote(PAPER_DIR / "manuscript.tex", "/tmp/paper_build/manuscript.tex", args.aggregator)
    run_scp_to_remote(PAPER_DIR / "references.bib", "/tmp/paper_build/references.bib", args.aggregator)
    run_scp_to_remote(PAPER_DIR / "figures", "/tmp/paper_build/", args.aggregator)

    # 3. Check and install IEEEtran.cls if missing
    print("[*] Checking IEEEtran document class...")
    rc, out, err = run_ssh("kpsewhich IEEEtran.cls || echo 'not-found'", args.aggregator)
    if "not-found" in out or rc != 0:
        print("  [*] Installing texlive-publishers for IEEEtran...")
        run_ssh("DEBIAN_FRONTEND=noninteractive apt-get install -y texlive-publishers", args.aggregator)

    # 4. Compile with pdflatex + bibtex + pdflatex (Pass 2) + pdflatex (Pass 3)
    print("[*] Compiling LaTeX manuscript (Pass 1)...")
    rc, out, err = run_ssh("cd /tmp/paper_build && pdflatex -interaction=nonstopmode manuscript.tex", args.aggregator)
    
    print("[*] Running BibTeX...")
    run_ssh("cd /tmp/paper_build && bibtex manuscript || true", args.aggregator)

    print("[*] Compiling LaTeX manuscript (Pass 2 - Read Citations)...")
    rc, out, err = run_ssh("cd /tmp/paper_build && pdflatex -interaction=nonstopmode manuscript.tex", args.aggregator)

    print("[*] Compiling LaTeX manuscript (Pass 3 - Final Cross References)...")
    rc, out, err = run_ssh("cd /tmp/paper_build && pdflatex -interaction=nonstopmode manuscript.tex", args.aggregator)

    # 5. Fetch PDF back to local workspace
    out_pdf = Path(args.output)
    print(f"[*] Fetching compiled PDF to {out_pdf}...")
    rc, out, err = run_scp_from_remote("/tmp/paper_build/manuscript.pdf", out_pdf, args.aggregator)

    if out_pdf.exists() and out_pdf.stat().st_size > 0:
        print(f"\n[SUCCESS] Compiled PDF generated: {out_pdf} ({out_pdf.stat().st_size:,} bytes)")
        print("========================================================================\n")
        sys.exit(0)
    else:
        print(f"\n[FAIL] PDF generation failed or empty. Log:\n{err}")
        print("========================================================================\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

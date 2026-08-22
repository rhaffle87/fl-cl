"""
compile_paper_pdf.py — Compile IEEE Transactions LaTeX Manuscript to PDF via Testbed TeX Engine.
"""

import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PAPER_DIR = PROJECT_ROOT / "docs" / "paper"
AGGREGATOR = "10.10.130.10"


def run_ssh(cmd):
    res = subprocess.run(["ssh", "-o", "BatchMode=yes", f"root@{AGGREGATOR}", cmd], capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def run_scp_to_remote(local_path, remote_path):
    res = subprocess.run(["scp", "-o", "BatchMode=yes", "-r", str(local_path), f"root@{AGGREGATOR}:{remote_path}"], capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def run_scp_from_remote(remote_path, local_path):
    res = subprocess.run(["scp", "-o", "BatchMode=yes", f"root@{AGGREGATOR}:{remote_path}", str(local_path)], capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def main():
    print("========================================================================")
    print("      FL-CL Publication Manuscript LaTeX PDF Compilation Suite")
    print("========================================================================")

    # 1. Ensure remote build directory exists
    print("[*] Setting up build workspace on aggregator (10.10.130.10)...")
    run_ssh("rm -rf /tmp/paper_build && mkdir -p /tmp/paper_build/figures")

    # 2. Copy paper sources and figures to remote
    print("[*] Uploading LaTeX sources and vector figures...")
    run_scp_to_remote(PAPER_DIR / "manuscript.tex", "/tmp/paper_build/manuscript.tex")
    run_scp_to_remote(PAPER_DIR / "references.bib", "/tmp/paper_build/references.bib")
    for fig in (PAPER_DIR / "figures").glob("*.pdf"):
        run_scp_to_remote(fig, f"/tmp/paper_build/figures/{fig.name}")
    for fig in (PAPER_DIR / "figures").glob("*.png"):
        run_scp_to_remote(fig, f"/tmp/paper_build/figures/{fig.name}")
    for fig in (PAPER_DIR / "figures").glob("*.jpg"):
        run_scp_to_remote(fig, f"/tmp/paper_build/figures/{fig.name}")

    # 3. Check and install IEEEtran.cls if missing
    print("[*] Checking IEEEtran document class...")
    rc, out, err = run_ssh("kpsewhich IEEEtran.cls || echo 'not-found'")
    if "not-found" in out or rc != 0:
        print("  [*] Installing texlive-publishers for IEEEtran...")
        run_ssh("DEBIAN_FRONTEND=noninteractive apt-get install -y texlive-publishers")

    # 4. Compile with pdflatex + bibtex + pdflatex (Pass 2) + pdflatex (Pass 3)
    print("[*] Compiling LaTeX manuscript (Pass 1)...")
    rc, out, err = run_ssh("cd /tmp/paper_build && pdflatex -interaction=nonstopmode manuscript.tex")
    
    print("[*] Running BibTeX...")
    run_ssh("cd /tmp/paper_build && bibtex manuscript || true")

    print("[*] Compiling LaTeX manuscript (Pass 2 - Read Citations)...")
    rc, out, err = run_ssh("cd /tmp/paper_build && pdflatex -interaction=nonstopmode manuscript.tex")

    print("[*] Compiling LaTeX manuscript (Pass 3 - Final Cross References)...")
    rc, out, err = run_ssh("cd /tmp/paper_build && pdflatex -interaction=nonstopmode manuscript.tex")

    # 5. Fetch PDF back to local workspace
    print("[*] Fetching compiled manuscript.pdf to local workspace...")
    out_pdf = PAPER_DIR / "manuscript.pdf"
    rc, out, err = run_scp_from_remote("/tmp/paper_build/manuscript.pdf", out_pdf)

    if out_pdf.exists() and out_pdf.stat().st_size > 0:
        print(f"\n[SUCCESS] Compiled PDF generated: {out_pdf} ({out_pdf.stat().st_size} bytes)")
    else:
        print(f"\n[FAIL] PDF generation failed or empty. Log:\n{err}")

    print("========================================================================\n")


if __name__ == "__main__":
    main()

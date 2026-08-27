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
import base64
import io
import tarfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAPER_DIR = PROJECT_ROOT / "docs" / "paper"


def get_ssh_opts():
    key_path = Path.home() / ".ssh" / "id_ed25519"
    opts = ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no"]
    if key_path.exists():
        opts += ["-i", str(key_path)]
    return opts


def run_ssh(cmd, host):
    opts = get_ssh_opts()
    res = subprocess.run(["ssh"] + opts + [f"root@{host}", cmd], capture_output=True, text=True)
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

    # 2. Package and upload LaTeX sources and vector figures
    print("[*] Uploading LaTeX sources and vector figures...")
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
        tar.add(PAPER_DIR / "manuscript.tex", arcname="manuscript.tex")
        tar.add(PAPER_DIR / "references.bib", arcname="references.bib")
        for fig in (PAPER_DIR / "figures").glob("*.*"):
            tar.add(fig, arcname=f"figures/{fig.name}")

    b64_payload = base64.b64encode(tar_buf.getvalue()).decode("ascii")
    # Send archive to remote and unpack
    p = subprocess.Popen(
        ["ssh"] + get_ssh_opts() + [f"root@{args.aggregator}", "base64 -d | tar -xzf - -C /tmp/paper_build"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    p.communicate(input=tar_buf.getvalue())

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
    rc, b64_pdf, err = run_ssh("base64 /tmp/paper_build/manuscript.pdf", args.aggregator)

    if rc == 0 and b64_pdf.strip():
        out_pdf.write_bytes(base64.b64decode(b64_pdf.strip()))

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

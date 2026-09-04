# generate_paper_pdf.py — Compile IEEE Transactions LaTeX Manuscript to PDF via Testbed TeX Engine.
#
# Synchronizes LaTeX source, BibTeX references, and vector figures to the cluster aggregator
# (10.10.130.10), executes a 3-pass pdflatex + bibtex build, and fetches the compiled PDF.
#
# Usage:
# python3 tools/generate_paper_pdf.py [--aggregator 10.10.130.10] [--output docs/paper/manuscript.pdf]

import argparse
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAPER_DIR = PROJECT_ROOT / "docs" / "paper"


def parse_host_port(host_str):
    if ":" in host_str:
        parts = host_str.split(":", 1)
        return parts[0], int(parts[1])
    return host_str, 22


def get_ssh_opts(port=22, is_scp=False):
    key_path = Path.home() / ".ssh" / "id_ed25519"
    opts = [
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=3",
    ]
    if port and port != 22:
        if is_scp:
            opts += ["-P", str(port)]
        else:
            opts += ["-p", str(port)]
    if key_path.exists():
        opts += ["-i", str(key_path)]
    return opts


def run_ssh(cmd, host_str, retries=3):
    host, port = parse_host_port(host_str)
    opts = get_ssh_opts(port=port, is_scp=False)
    rc, stdout, stderr = -1, "", ""
    for attempt in range(retries):
        res = subprocess.run(
            ["ssh"] + opts + [f"root@{host}", cmd], capture_output=True, text=True
        )
        rc, stdout, stderr = res.returncode, res.stdout, res.stderr
        if rc == 0:
            return rc, stdout, stderr
        if attempt < retries - 1:
            time.sleep(1)
    return rc, stdout, stderr


def upload_tarball(tar_path, host_str):
    host, port = parse_host_port(host_str)
    opts = get_ssh_opts(port=port, is_scp=False)
    with open(tar_path, "rb") as f:
        tar_data = f.read()
    for attempt in range(3):
        res = subprocess.run(
            ["ssh"] + opts + [f"root@{host}", "tar -xzf - -C /tmp/paper_build"],
            input=tar_data,
        )
        if res.returncode == 0:
            return 0
        if attempt < 2:
            time.sleep(1)
    return -1


def download_pdf(out_path, host_str):
    host, port = parse_host_port(host_str)
    opts = get_ssh_opts(port=port, is_scp=False)
    for attempt in range(3):
        res = subprocess.run(
            ["ssh"] + opts + [f"root@{host}", "cat /tmp/paper_build/manuscript.pdf"],
            capture_output=True,
        )
        if res.returncode == 0 and len(res.stdout) > 10000:
            with open(out_path, "wb") as f:
                f.write(res.stdout)
            return 0
        if attempt < 2:
            time.sleep(1)
    return -1


def find_live_aggregator(preferred_host):
    candidates = [
        preferred_host,
        "100.84.192.94:22",
        "10.28.10.58:2224",
        "10.10.130.10:22",
        "100.117.17.27:22",
    ]
    seen = set()
    for h in candidates:
        if h in seen:
            continue
        seen.add(h)
        rc, out, _ = run_ssh("echo ok", h, retries=1)
        if rc == 0 and "ok" in out:
            return h
    return preferred_host


def main():
    parser = argparse.ArgumentParser(
        description="Compile IEEE Transactions LaTeX Manuscript to PDF via Remote TeX Engine"
    )
    parser.add_argument(
        "--aggregator",
        default="100.84.192.94:22",
        help="Aggregator node IP/host:port with TeX Live environment (default: 100.84.192.94:22)",
    )
    parser.add_argument(
        "--output",
        default=str(PAPER_DIR / "manuscript.pdf"),
        help="Destination path for compiled PDF",
    )
    args = parser.parse_args()

    args.aggregator = find_live_aggregator(args.aggregator)

    print("========================================================================")
    print("      FL-CL Publication Manuscript LaTeX PDF Compilation Suite")
    print("========================================================================")

    # 1. Ensure remote build directory exists
    print(f"[*] Setting up build workspace on aggregator ({args.aggregator})...")
    run_ssh(
        "rm -rf /tmp/paper_build && mkdir -p /tmp/paper_build/figures", args.aggregator
    )

    # 2. Package and upload LaTeX sources and vector figures
    print("[*] Uploading LaTeX sources and vector figures...")
    temp_tar = Path(tempfile.gettempdir()) / "flcl_paper_build.tar.gz"
    with tarfile.open(temp_tar, mode="w:gz") as tar:
        tar.add(PAPER_DIR / "manuscript.tex", arcname="manuscript.tex")
        tar.add(PAPER_DIR / "references.bib", arcname="references.bib")
        for fig in (PAPER_DIR / "figures").glob("*.*"):
            tar.add(fig, arcname=f"figures/{fig.name}")

    if upload_tarball(temp_tar, args.aggregator) != 0:
        print("[FAIL] Failed to upload build tarball.")
        sys.exit(1)

    # 3. Check and install IEEEtran.cls if missing
    print("[*] Checking IEEEtran document class...")
    rc, out, err = run_ssh(
        "kpsewhich IEEEtran.cls || echo 'not-found'", args.aggregator
    )
    if "not-found" in out or rc != 0:
        print("  [*] Installing texlive-publishers for IEEEtran...")
        run_ssh(
            "DEBIAN_FRONTEND=noninteractive apt-get install -y texlive-publishers",
            args.aggregator,
        )

    # 4. Compile with pdflatex + bibtex + pdflatex (Pass 2) + pdflatex (Pass 3)
    print("[*] Compiling LaTeX manuscript (Pass 1)...")
    run_ssh(
        "cd /tmp/paper_build && pdflatex -interaction=nonstopmode manuscript.tex",
        args.aggregator,
    )

    print("[*] Running BibTeX...")
    run_ssh("cd /tmp/paper_build && bibtex manuscript || true", args.aggregator)

    print("[*] Compiling LaTeX manuscript (Pass 2 - Read Citations)...")
    run_ssh(
        "cd /tmp/paper_build && pdflatex -interaction=nonstopmode manuscript.tex",
        args.aggregator,
    )

    print("[*] Compiling LaTeX manuscript (Pass 3 - Final Cross References)...")
    run_ssh(
        "cd /tmp/paper_build && pdflatex -interaction=nonstopmode manuscript.tex",
        args.aggregator,
    )

    # 5. Fetch PDF back to local workspace
    out_pdf = Path(args.output)
    print(f"[*] Fetching compiled PDF to {out_pdf}...")
    fetch_rc = download_pdf(out_pdf, args.aggregator)

    if fetch_rc == 0 and out_pdf.exists() and out_pdf.stat().st_size > 10000:
        print(
            f"\n[SUCCESS] Compiled PDF generated: {out_pdf} ({out_pdf.stat().st_size:,} bytes)"
        )
        print(
            "========================================================================\n"
        )
        sys.exit(0)

    # If scp failed or file too small, print error log
    _, log_content, _ = run_ssh(
        "cat /tmp/paper_build/manuscript.log 2>/dev/null | tail -n 50 || true",
        args.aggregator,
    )
    print(
        f"\n[FAIL] PDF compilation failed on aggregator. LaTeX error log:\n{log_content}"
    )
    print("========================================================================\n")
    sys.exit(1)


if __name__ == "__main__":
    main()

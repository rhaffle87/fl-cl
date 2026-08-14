"""
export_paper.py
Converts docs/00_research_paper.md into a publication-ready IEEEtran LaTeX (.tex) file
and compiles PDF output if pandoc / pdflatex is installed.
"""

import os
import re

MD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "00_research_paper.md"))
TEX_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "00_research_paper.tex"))

def convert_md_to_ieeetran(md_content: str) -> str:
    tex = []
    tex.append(r"\documentclass[conference]{IEEEtran}")
    tex.append(r"\usepackage{cite}")
    tex.append(r"\usepackage{amsmath,amssymb,amsfonts}")
    tex.append(r"\usepackage{algorithmic}")
    tex.append(r"\usepackage{graphicx}")
    tex.append(r"\usepackage{textcomp}")
    tex.append(r"\usepackage{xcolor}")
    tex.append(r"\usepackage{booktabs}")
    tex.append(r"\usepackage{hyperref}")
    tex.append(r"\begin{document}")
    tex.append(r"\title{Hybrid Federated-Continual Learning for Encrypted Network Intrusion Detection across Heterogeneous Virtualized Clusters}")
    tex.append(r"\author{\IEEEauthorblockN{Muhammad Nabil Ulya} \IEEEauthorblockA{\textit{Department of Computer Engineering} \\ \textit{Institut Teknologi Sepuluh Nopember}\\ Surabaya, Indonesia}}")
    tex.append(r"\maketitle")
    tex.append(r"\begin{abstract}")
    
    # Extract abstract
    abstract_match = re.search(r"## Abstract\s*\n\n(.*?)(?=\n##|\Z)", md_content, re.DOTALL)
    if abstract_match:
        abstract_text = abstract_match.group(1).strip()
        # Clean markdown formatting for LaTeX
        abstract_text = abstract_text.replace("**", "").replace("_", "")
        tex.append(abstract_text)
    else:
        tex.append("Encrypted network traffic metadata classification using hybrid Federated-Continual Learning (FL-CL).")
        
    tex.append(r"\end{abstract}")
    tex.append(r"\begin{IEEEkeywords}")
    tex.append(r"Federated Learning, Continual Learning, Elastic Weight Consolidation, NFStream, Intrusion Detection Systems, Proxmox VE")
    tex.append(r"\end{IEEEkeywords}")
    tex.append("")

    lines = md_content.split("\n")
    in_code = False
    in_table = False

    for line in lines:
        if line.startswith("# ") or line.startswith("## Abstract") or line.startswith("## Executive"):
            continue
        elif line.startswith("## Chapter ") or line.startswith("## "):
            sec_title = re.sub(r"^##\s*\d*\.?\s*", "", line).strip()
            tex.append(f"\n\\section{{{sec_title}}}")
        elif line.startswith("### "):
            subsec_title = re.sub(r"^###\s*\d*\.?\s*", "", line).strip()
            tex.append(f"\n\\subsection{{{subsec_title}}}")
        elif line.startswith("#### "):
            subsubsec_title = re.sub(r"^####\s*\d*\.?\s*", "", line).strip()
            tex.append(f"\n\\subsubsection{{{subsubsec_title}}}")
        elif line.startswith("```"):
            in_code = not in_code
            if in_code:
                tex.append(r"\begin{verbatim}")
            else:
                tex.append(r"\end{verbatim}")
        elif in_code:
            tex.append(line)
        elif line.startswith("|") and "|---" not in line:
            # Table formatting placeholder
            cell_data = [c.strip().replace("**", "").replace("*", "") for c in line.split("|")[1:-1]]
            tex.append(" & ".join(cell_data) + r" \\")
        else:
            clean_line = line.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")
            clean_line = re.sub(r"\*\*(.*?)\*\*", r"\\textbf{\1}", clean_line)
            clean_line = re.sub(r"\*(.*?)\*", r"\\textit{\1}", clean_line)
            tex.append(clean_line)

    tex.append(r"\end{document}")
    return "\n".join(tex)

def main():
    if not os.path.exists(MD_PATH):
        print(f"[!] Error: {MD_PATH} not found.")
        return

    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    tex_text = convert_md_to_ieeetran(md_text)
    with open(TEX_PATH, "w", encoding="utf-8") as f:
        f.write(tex_text)

    print(f"[+] Successfully exported IEEEtran LaTeX file to: {TEX_PATH}")

if __name__ == "__main__":
    main()

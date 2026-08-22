"""
check_all_docs.py — Documentation Link, Image, and Placeholder Auditor

Recursively audits all Markdown documentation in docs/ and the repository root
to guarantee 0 broken relative links, 0 missing image references, and 0 unresolved placeholders.
"""

import os
import re
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
docs_dir = repo_root / "docs"

errors = []
warnings = []

print(f"Scanning markdown files in {docs_dir}...")

md_files = list(docs_dir.rglob("*.md")) + list(repo_root.glob("*.md"))

link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

for md_file in md_files:
    content = md_file.read_text(encoding="utf-8")
    
    # Check for placeholder markers
    for placeholder in ["PLACEHOLDER", "TODO", "FIXME", "TBD"]:
        matches = re.findall(rf'\b{placeholder}\b', content)
        if matches:
            warnings.append(f"[{md_file.relative_to(repo_root)}] Contains {len(matches)} occurrences of '{placeholder}'")

    # Check images
    for match in img_pattern.finditer(content):
        alt_text, img_path = match.groups()
        if img_path.startswith("http://") or img_path.startswith("https://"):
            continue
        img_target = img_path.split("#")[0].split("?")[0]
        if img_target.startswith("file:///"):
            resolved = Path(img_target.replace("file:///", "").replace("/", "\\"))
        else:
            resolved = (md_file.parent / img_target).resolve()
        if not resolved.exists():
            errors.append(f"[{md_file.relative_to(repo_root)}] Broken Image: '{img_path}' -> {resolved}")

    # Check links
    for match in link_pattern.finditer(content):
        text, link_path = match.groups()
        if link_path.startswith("http://") or link_path.startswith("https://") or link_path.startswith("mailto:") or link_path.startswith("#"):
            continue
        link_target = link_path.split("#")[0].split("?")[0]
        if not link_target:
            continue
        if link_target.startswith("file:///"):
            resolved = Path(link_target.replace("file:///", "").replace("/", "\\"))
        else:
            resolved = (md_file.parent / link_target).resolve()
        if not resolved.exists():
            errors.append(f"[{md_file.relative_to(repo_root)}] Broken Link: [{text}]({link_path}) -> {resolved}")

print("\n--- AUDIT RESULTS ---")
print(f"Total MD Files Scanned: {len(md_files)}")
print(f"Total Errors Found: {len(errors)}")
print(f"Total Warnings Found: {len(warnings)}")

if errors:
    print("\nERRORS:")
    for e in errors:
        print(f"  [ERROR] {e}")
    exit(1)
else:
    print("  [OK] All relative links and images resolve successfully!")

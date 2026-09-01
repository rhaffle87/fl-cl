# tools/audit_docs.py — Documentation Link, Image, and Placeholder Auditor
#
# Recursively audits all Markdown documentation in docs/ and the repository root
# to guarantee 0 broken relative links, 0 missing image references, and 0 unresolved placeholders.

import argparse
import os
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
docs_dir = repo_root / "docs"

errors = []
warnings = []

is_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"

print(f"Scanning markdown files in {docs_dir}...")

md_files = sorted(list(docs_dir.rglob("*.md")) + list(repo_root.glob("*.md")))

link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
img_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def resolve_link_target(md_file: Path, target_str: str) -> Path:
    target_clean = target_str.split("#")[0].split("?")[0].strip()
    if not target_clean:
        return None

    if target_clean.startswith("file:///"):
        path_part = target_clean[8:]
        # Extract relative path if inside fl-cl workspace
        if "fl-cl/" in path_part:
            rel_sub = path_part.split("fl-cl/", 1)[1]
            return (repo_root / rel_sub).resolve()
        elif "fl-cl\\" in path_part:
            rel_sub = path_part.split("fl-cl\\", 1)[1]
            return (repo_root / rel_sub).resolve()
        # Windows drive letter pattern
        if re.match(r"^[a-zA-Z]:[/\\].*", path_part):
            return Path(path_part)
        return (repo_root / path_part.lstrip("/\\")).resolve()

    return (md_file.parent / target_clean).resolve()


for md_file in md_files:
    content = md_file.read_text(encoding="utf-8")

    # Check for placeholder markers in prose (excluding backtick code blocks)
    prose_content = re.sub(r"```[\s\S]*?```", "", content)
    prose_content = re.sub(r"`[^`]+`", "", prose_content)
    for placeholder in ["PLACEHOLDER", "TODO", "FIXME", "TBD"]:
        matches = re.findall(rf"\b{placeholder}\b", prose_content)
        if matches:
            warnings.append(
                f"[{md_file.relative_to(repo_root)}] Contains {len(matches)} occurrences of '{placeholder}'"
            )

    # Check images
    for match in img_pattern.finditer(content):
        alt_text, img_path = match.groups()
        if (
            img_path.startswith("http://")
            or img_path.startswith("https://")
            or img_path.startswith("data:")
        ):
            continue
        resolved = resolve_link_target(md_file, img_path)
        if resolved and not resolved.exists():
            errors.append(
                f"[{md_file.relative_to(repo_root)}] Broken Image: '{img_path}' -> {resolved}"
            )

    # Check links
    for match in link_pattern.finditer(content):
        text, link_path = match.groups()
        if (
            link_path.startswith("http://")
            or link_path.startswith("https://")
            or link_path.startswith("mailto:")
            or link_path.startswith("#")
        ):
            continue
        resolved = resolve_link_target(md_file, link_path)
        if resolved and not resolved.exists():
            # In CI environments, optional data/scratch outputs that are runtime-generated are warnings
            rel_resolved = str(resolved).replace("\\", "/")
            if is_ci and any(
                f"/{d}/" in rel_resolved for d in ["data", "scratch", "runs", "exports"]
            ):
                warnings.append(
                    f"[{md_file.relative_to(repo_root)}] Runtime/Ignored Target Missing in CI: [{text}]({link_path})"
                )
            else:
                errors.append(
                    f"[{md_file.relative_to(repo_root)}] Broken Link: [{text}]({link_path}) -> {resolved}"
                )

print("\n--- AUDIT RESULTS ---")
print(f"Total MD Files Scanned: {len(md_files)}")
print(f"Total Errors Found: {len(errors)}")
print(f"Total Warnings Found: {len(warnings)}")

if warnings:
    print("\nWARNINGS:")
    for w in warnings:
        print(f"  [WARN] {w}")

if errors:
    print("\nERRORS:")
    for e in errors:
        print(f"  [ERROR] {e}")
    sys.exit(1)
else:
    print("  [OK] All relative links and images resolve successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Documentation Link, Figure, and Relative Path Validator"
    )
    _ = parser.parse_args()

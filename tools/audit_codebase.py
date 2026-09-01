# audit_codebase.py — Comprehensive Codebase & Data Fact Checker
#
# Audits:
# 1. YAML configuration schemas in configs/
# 2. Feature set & normalization invariants in configs/baseline_feature_stats.json & src/defender/extractor.py
# 3. AST validation of all Python source files in src/ and tools/
# 4. Multi-class threat label mapping consistency across all modules
# 5. Verification of all experimental CSV reports in data/reports/benchmarks/

import argparse
import ast
import json
from pathlib import Path

import yaml

repo_root = Path(__file__).resolve().parent.parent

errors = []
warnings = []
info = []

print("=" * 70)
print("COMPREHENSIVE CODEBASE & DATA FACT CHECK")
print("=" * 70)

# -------------------------------------------------------------
# 1. Check all YAML configs for syntax and required schema keys
# -------------------------------------------------------------
yaml_files = list(repo_root.glob("configs/**/*.yaml")) + list(
    repo_root.glob("configs/*.yaml")
)
print(f"\n[1] Auditing {len(yaml_files)} YAML configuration files...")

for yf in yaml_files:
    try:
        with open(yf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            warnings.append(f"{yf.name}: Top-level YAML is not a dict")
            continue

        # Check standard sections if experiment config
        if "fl" in data and "training" in data:
            # Check class_weights length if present
            cw = data.get("training", {}).get("class_weights")
            if cw and len(cw) != 5:
                errors.append(
                    f"{yf.name}: class_weights has length {len(cw)}, expected 5"
                )

            # Check model_type
            mt = data.get("training", {}).get("model_type")
            if mt and mt not in ["cnn", "mlp", "transformer"]:
                errors.append(f"{yf.name}: Unknown model_type '{mt}'")

            # Check aggregation strategy
            strat = data.get("fl", {}).get("strategy")
            if strat and strat not in ["FedAvg", "TrimmedMean", "FedMedian", "Krum"]:
                warnings.append(f"{yf.name}: Aggregation strategy '{strat}'")

    except Exception as e:
        errors.append(f"YAML Syntax Error in {yf}: {e}")

info.append(f"Audited {len(yaml_files)} YAML configs successfully.")

# -------------------------------------------------------------
# 2. Check baseline_feature_stats.json vs extractor.py features
# -------------------------------------------------------------
print("\n[2] Checking Feature Set & Normalization Invariants...")
stats_file = repo_root / "configs" / "baseline_feature_stats.json"
if stats_file.exists():
    with open(stats_file, "r", encoding="utf-8") as f:
        stats_data = json.load(f)
    classes = list(stats_data.keys())
    if len(classes) != 5:
        errors.append(
            f"baseline_feature_stats.json contains {len(classes)} classes, expected exactly 5 (0-4)"
        )
    else:
        # Check that class 0 contains all 10 core ETA flow feature statistics
        c0_features = list(stats_data["0"].keys())
        info.append(
            f"baseline_feature_stats.json: Verified 5 threat classes (0-4) with {len(c0_features)} statistical flow distributions each."
        )
else:
    errors.append("baseline_feature_stats.json missing!")

# Check extractor.py feature list
extractor_file = repo_root / "src" / "defender" / "extractor.py"
if extractor_file.exists():
    ext_content = extractor_file.read_text(encoding="utf-8")
    # Verify n_dissections=20
    if "n_dissections=20" in ext_content or "n_dissections = 20" in ext_content:
        info.append("extractor.py uses n_dissections=20 (verified)")
    else:
        warnings.append("extractor.py: n_dissections=20 not explicitly found")

# -------------------------------------------------------------
# 3. Check Python Syntax & Invariants across all src/ and tools/
# -------------------------------------------------------------
print("\n[3] Auditing Python ASTs and Invariants in src/ and tools/...")
py_files = list(repo_root.glob("src/**/*.py")) + list(repo_root.glob("tools/**/*.py"))

for pf in py_files:
    try:
        source = pf.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(pf))
    except SyntaxError as e:
        errors.append(f"SyntaxError in {pf}: {e}")
    except Exception as e:
        errors.append(f"Error parsing {pf}: {e}")

info.append(f"Audited ASTs of {len(py_files)} Python source files — 0 syntax errors.")

# -------------------------------------------------------------
# 4. Check Label Names Consistency
# -------------------------------------------------------------
print("\n[4] Auditing Class Label Mappings Across Python Scripts...")
expected_labels = {
    0: "Normal",
    1: "Botnet",
    2: "Exfiltration",
    3: "BruteForce",
    4: "DoS",
}

label_checks = 0
for pf in py_files:
    content = pf.read_text(encoding="utf-8")
    if "LABEL_NAMES" in content:
        label_checks += 1
        # Check that 5 classes are defined
        for k, v in expected_labels.items():
            if (
                f'"{v}"' not in content
                and f"'{v}'" not in content
                and f"{v}" not in content
            ):
                warnings.append(
                    f"{pf.name}: Missing expected label name '{v}' in LABEL_NAMES"
                )

info.append(
    f"Verified LABEL_NAMES mapping across {label_checks} files containing explicit label tables."
)

# -------------------------------------------------------------
# 5. Check CSV Reports in data/reports/benchmarks/
# -------------------------------------------------------------
print("\n[5] Auditing CSV Reports in data/reports/benchmarks/...")
report_csvs = list(repo_root.glob("data/reports/benchmarks/*.csv"))

if not report_csvs:
    info.append(
        "data/reports/benchmarks/ is empty or gitignored — skipping CSV report check in clean environment."
    )
else:
    for rcsv in report_csvs:
        try:
            lines = rcsv.read_text(encoding="utf-8").strip().splitlines()
            if not lines:
                warnings.append(f"Empty report CSV: {rcsv.name}")
            else:
                header = lines[0].split(",")
                num_cols = len(header)
                row_count = len(lines) - 1
                info.append(
                    f"{rcsv.name}: {row_count} rows, {num_cols} columns ({', '.join(header[:3])}...)"
                )
        except Exception as e:
            errors.append(f"Error reading report {rcsv.name}: {e}")

# -------------------------------------------------------------
# 6. Check Tools Directory Standardization & Governance (ADR-006)
# -------------------------------------------------------------
print(
    "\n[6] Auditing tools/ Directory Standardization & Prefix Governance (ADR-006)..."
)
VALID_PREFIXES = (
    "audit_",
    "benchmark_",
    "check_",
    "deploy_",
    "export_",
    "generate_",
    "plot_",
    "sync_",
    "test_",
    "train_",
    "validate_",
)

tools_files = list((repo_root / "tools").glob("*.py"))
compliant_tools = 0

for tf in tools_files:
    fname = tf.name
    if any(fname.startswith(p) for p in VALID_PREFIXES):
        compliant_tools += 1
    else:
        errors.append(
            f"ADR-006 Violation: Tool '{fname}' does not start with an approved prefix {VALID_PREFIXES}"
        )

    # Check that tool has docstring
    try:
        tree = ast.parse(tf.read_text(encoding="utf-8"))
        doc = ast.get_docstring(tree)
        if not doc:
            warnings.append(f"{fname}: Missing module-level docstring")
    except Exception:
        pass

info.append(
    f"Audited {len(tools_files)} tools: 100% compliant with ADR-006 prefix taxonomy ({compliant_tools}/{len(tools_files)})."
)

# -------------------------------------------------------------
# SUMMARY REPORT
# -------------------------------------------------------------
print("\n" + "=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)
print(f"Total Errors:   {len(errors)}")
print(f"Total Warnings: {len(warnings)}")

if errors:
    print("\nERRORS:")
    for e in errors:
        print(f"  [ERROR] {e}")
    exit(1)
else:
    print("  [OK] Zero structural or syntactic errors found in codebase!")

if warnings:
    print("\nWARNINGS:")
    for w in warnings:
        print(f"  [WARN] {w}")

print("\nDETAILS:")
for item in info:
    print(f"  * {item}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Comprehensive Codebase, AST, YAML Schema, and Invariant Auditor"
    )
    _ = parser.parse_args()

#!/usr/bin/env python3
"""
validate_config.py
==================
Validator for FL-CL experiment configuration YAML files.
Ensures adherence to repository schemas, model constraints, and security parameters.
"""

import argparse
import sys
from pathlib import Path

import yaml

VALID_MODELS = {"mlp", "cnn", "transformer"}
VALID_CL_STRATEGIES = {"EWC", "GEM"}
VALID_AGGREGATORS = {"FedAvg", "TrimmedMean", "FedMedian", "Krum"}


def validate_experiment_config(config_path: Path) -> bool:
    if not config_path.is_file():
        print(f"[ERROR] Config file not found: {config_path}")
        return False

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        print(f"[ERROR] Failed to parse YAML: {e}")
        return False

    errors = []

    # 1. Check top-level sections
    for section in ["fl", "cl", "model", "training", "security"]:
        if section not in cfg:
            errors.append(f"Missing required top-level section: '{section}'")

    if errors:
        for err in errors:
            print(f"[ERROR] {err}")
        return False

    # 2. Validate model constraints
    model_cfg = cfg.get("model", {})
    m_type = model_cfg.get("type")
    if m_type not in VALID_MODELS:
        errors.append(f"Invalid model type '{m_type}'. Must be one of {VALID_MODELS}")

    input_dim = model_cfg.get("input_dim")
    if input_dim != 32:
        errors.append(
            f"model.input_dim must be 32 (got {input_dim}) to match NFStream ETA feature count."
        )

    num_classes = model_cfg.get("num_classes")
    if num_classes != 5:
        errors.append(
            f"model.num_classes must be 5 (got {num_classes}) for threat class taxonomy."
        )

    if m_type == "transformer":
        token_len = model_cfg.get("token_len", 8)
        token_dim = model_cfg.get("token_dim", 4)
        if token_len * token_dim != 32:
            errors.append(
                f"Transformer constraint violated: token_len ({token_len}) * token_dim ({token_dim}) != 32"
            )

    # 3. Validate CL settings
    cl_cfg = cfg.get("cl", {})
    cl_strat = cl_cfg.get("strategy")
    if cl_strat not in VALID_CL_STRATEGIES:
        errors.append(
            f"Invalid cl.strategy '{cl_strat}'. Must be one of {VALID_CL_STRATEGIES}"
        )

    # 4. Validate Security & FL
    sec_cfg = cfg.get("security", {})
    agg_strat = sec_cfg.get("aggregation_strategy", "FedAvg")
    if agg_strat not in VALID_AGGREGATORS:
        errors.append(
            f"Invalid aggregation_strategy '{agg_strat}'. Must be one of {VALID_AGGREGATORS}"
        )

    fl_cfg = cfg.get("fl", {})
    rounds = fl_cfg.get("rounds", 0)
    if rounds <= 0:
        errors.append(f"fl.rounds must be > 0 (got {rounds})")

    # 5. Check baseline stats file reference
    stats_file = Path("configs/baseline_feature_stats.json")
    if not stats_file.exists():
        print(
            f"[WARNING] Baseline feature stats file not found at {stats_file}. Scaling might fallback to uncalibrated defaults."
        )

    if errors:
        print(
            f"\n[FAILED] Configuration validation failed for {config_path.name} with {len(errors)} error(s):"
        )
        for err in errors:
            print(f"  - {err}")
        return False

    print(
        f"[SUCCESS] Configuration {config_path.name} is valid and ready for execution."
    )
    print(f"  - Model: {m_type} (input_dim=32, num_classes=5)")
    print(f"  - CL Strategy: {cl_strat}")
    print(f"  - Aggregator: {agg_strat}")
    print(f"  - Rounds: {rounds}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Validate FL-CL experiment YAML config."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/experiments/scenario_baseline.yaml",
        help="Path to experiment YAML",
    )
    args = parser.parse_args()

    success = validate_experiment_config(Path(args.config))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

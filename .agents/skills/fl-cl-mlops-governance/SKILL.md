---
name: fl-cl-mlops-governance
description: Enforce ADR-006 compliance, statistical model promotion verification, 1-click rollback, and Model Card governance in FL-CL.
---

# FL-CL MLOps Governance Skill

This skill guides agents through auditing code quality, enforcing architectural decisions (ADR-006), validating candidate model promotions with bootstrap significance, executing automated rollbacks, and generating model cards.

---

## 1. Governance Architecture & Principles

All code, models, and orchestration pipelines in `fl-cl` must adhere strictly to:
1. **ADR-006 Standard**: All production scripts in `tools/` and `src/` must have docstrings, top-level module prefixes (`[AUDIT]`, `[EVAL]`, `[SIM]`, `[SERVER]`, `[CLIENT]`, `[OPS]`), `pathlib.Path` usage, and CLI argument parsers.
2. **Statistical Model Promotion**: No model candidate may be promoted to `@champion` without achieving statistically significant improvement over baseline (bootstrap resampling $p < 0.05$ or non-overlapping 95% CI on Macro-F1).
3. **1-Click Rollback**: The registry tracks `@previous_champion` so faulty models can be instantly demoted and reverted without training downtime.
4. **Model Card Maintenance**: Any architecture update must be reflected in `docs/MODEL_CARD.md`.

---

## 2. Standard Governance Workflows

### Step 1: Audit Codebase for ADR-006 Compliance
Run the governance audit script to verify module docstrings, logging conventions, and error handling:
```bash
python .agents/skills/fl-cl-mlops-governance/scripts/audit_tool_compliance.py
```

### Step 2: Validate & Promote Model Candidate
Evaluate candidate model against current champion with bootstrap significance testing:
```bash
python tools/validate_promotion.py \
    --candidate-checkpoint models/checkpoints/candidate_round_10.pt \
    --champion-checkpoint models/checkpoints/champion.pt \
    --test-dir scratch/mock_flows \
    --num-bootstraps 1000 \
    --alpha 0.05 \
    --promote
```

### Step 3: Rollback Faulty Champion Model
Instantly revert current champion to the previously verified champion alias:
```bash
python tools/validate_promotion.py --rollback
```

### Step 4: Audit Model Card Documentation
Verify `data/models/MODEL_CARD.md` aligns with current benchmark metrics and hyperparameter configurations:
```bash
python -c "import pathlib; assert pathlib.Path('data/models/MODEL_CARD.md').exists(), 'Model Card missing!'"
```

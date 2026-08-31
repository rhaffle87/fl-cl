---
name: fl-cl-continual-learning
description: Evaluate catastrophic forgetting, compute Backward Transfer (BWT), configure class-weighted EWC/GEM continual learning, and tune stability-plasticity tradeoffs in FL-CL.
---

# FL-CL Continual Learning Skill

This skill guides agents through analyzing continual learning strategies (Elastic Weight Consolidation, Gradient Episodic Memory), diagnosing catastrophic forgetting, and evaluating Backward Transfer (BWT) metrics on non-stationary cyberattack traffic streams.

---

## 1. Core Mathematical Foundations

Continual learning in `fl-cl` balances the **stability-plasticity dilemma**:
- **Elastic Weight Consolidation (EWC)**: Penalizes updates to parameters that were critical for prior traffic classes using the empirical Fisher Information Matrix:
  $$L(\theta) = L_{new}(\theta) + \sum_i \frac{\lambda}{2} F_i (\theta_i - \theta_{i}^*)^2$$
- **Class-Weighted EWC**: Scales parameter importances $F_i$ based on inverse class frequency in the historical stream to prevent minority zero-day attacks from being washed out.
- **Backward Transfer (BWT)**: Measures how learning new attacks affects performance on historical attacks:
  $$BWT = \frac{1}{T-1} \sum_{i=1}^{T-1} (R_{T,i} - R_{i,i})$$
  - $BWT > 0$: Positive backward transfer (learning new attacks helped old ones).
  - $BWT \approx 0$: No forgetting (ideal retention).
  - $BWT < 0$: Catastrophic forgetting occurred.

---

## 2. Standard Workflows

### Step 1: Diagnose Forgetting and Compute BWT
Run the forgetting diagnostic tool across continual task evaluations:
```bash
python .agents/skills/fl-cl-continual-learning/scripts/diagnose_forgetting.py \
    --eval-matrix results/continual_matrix.csv \
    --bwt-threshold -0.05
```

### Step 2: Validate BWT from Checkpoint Sequence
Validate historical task performance across saved sequential checkpoints:
```bash
python tools/validate_bwt.py \
    --checkpoints-dir models/checkpoints \
    --test-dir scratch/mock_flows \
    --model-type cnn
```

### Step 3: Run Quarantine Continual Fine-Tuning
Execute class-weighted continual fine-tuning on newly identified malicious quarantine flows:
```bash
python tools/train_quarantine_continual.py \
    --base-model models/checkpoints/champion.pt \
    --quarantine-dir /mnt/ramdisk/quarantine \
    --ewc-lambda 400.0 \
    --output-model models/checkpoints/quarantine_updated.pt
```

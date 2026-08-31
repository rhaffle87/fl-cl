# FL-CL Project Context & Engineering Standards

> **Workspace Rules**: All AI agents and developers working in `fl-cl` must strictly adhere to this specification.
> **Last Updated**: 2026-08-31 | **Author**: Rafli Alif Ihza Hartono (ITS Surabaya)

---

## 1. System Identity & Objective

| Property | Value |
| :--- | :--- |
| **System** | `fl-cl` — Hybrid Federated-Continual Learning Intrusion Detection System |
| **Target Network** | Encrypted network flow classification (32-dim ETA metadata features) |
| **Infrastructure** | 3-node bare-metal Proxmox VE cluster (`its`, `node2`, `pve`) on flat L2 `10.10.0.0/16` |
| **Core Frameworks** | PyTorch 2.x, Avalanche 0.5+ (CL), Flower 1.32+ (FL), NFStream 6.5+ (ETA), MLflow 3.15+ |
| **Classification** | 5 classes: `0: Normal`, `1: Botnet`, `2: Exfiltration`, `3: BruteForce`, `4: DoS` |

---

## 2. Directory Layout & Governance

```text
fl-cl/
├── .agents/
│   ├── rules/                <- Project context & coding invariants (project-context.md, ponytail.md)
│   └── skills/               <- Custom domain skills (runner, proxmox-ops, mlops, cl, edge-opt)
├── configs/
│   ├── baseline_feature_stats.json <- Global Z-score scaling parameters (fixed source of truth)
│   ├── experiment.yaml       <- Master configuration schema
│   └── experiments/          <- 16 reproducible benchmark experiment YAML definitions
├── data/
│   ├── models/               <- Exported champion checkpoints and TorchScript artifacts
│   └── reports/              <- Ground-truth CSV benchmark results & evaluation metrics
├── docs/                     <- Monograph (docs/paper/), defense dossier (10_arguments.md), ADRs
├── infra/                    <- Proxmox IaC scripts (host config, VM provision, hookscripts, guest setup)
├── src/                      <- Production core application code
│   ├── logger.py             <- Centralized stderr logger factory (get_logger)
│   ├── notifications.py      <- Telegram & webhook notification dispatcher
│   ├── orchestrate.py        <- Master pipeline controller
│   ├── sweep.py              <- Multi-run hyperparameter grid search controller
│   ├── aggregator/           <- Flower server, robust aggregators, MLflow logging, dashboard
│   ├── defender/             <- Flower clients, Avalanche EWC/GEM, NFStream extractor, model factory
│   └── traffic_gen/          <- Multi-engine attack generator (Kali / Python fallback)
├── tools/                    <- ADR-006 prefixed production utilities, test suites & deployment tools
└── scratch/                  <- Temporary/exploratory debug scripts only (never imported by src/)
```

---

## 3. Mandatory Engineering Invariants

1. **No Raw Data Across Boundaries**: Raw PCAP flows and payload bytes remain local on defender VMs (`/mnt/ramdisk/flows/`). Only aggregated model weights traverse the network via Flower gRPC (TCP/8080).
2. **Standard Libraries & PyTorch Primitives First (Ponytail Rule)**: Favor native PyTorch modules (`nn.Linear`, `nn.Conv1d`, `nn.TransformerEncoderLayer`) over wrapper libraries.
3. **No Hardcoded Shapes (CNN Dynamic FC Rule)**: When modifying `CyberDefenseCNN`, compute `fc_input_dim` dynamically via dummy forward pass. Hardcoding breaks hyperparameter sweeps.
4. **Centralized Logging**: Never use raw `print()` in `src/`. Always use `from logger import get_logger; _log = get_logger(__name__)`.
5. **ADR-006 Tool Standardization**: Every script in `tools/` must start with an approved prefix (`audit_`, `benchmark_`, `check_`, `deploy_`, `export_`, `generate_`, `plot_`, `sync_`, `test_`, `train_`, `validate_`), define an `argparse` CLI, and resolve paths using `pathlib.Path(__file__).resolve().parent.parent`.
6. **Z-Score Normalization Invariant**: Use `configs/baseline_feature_stats.json` for scaling. Never compute normalization locally on individual client batches to prevent cross-organization covariate shift.

---

## 4. Operational Skill Index (`.agents/skills/`)

| Skill | Purpose | Primary Execution Script |
| :--- | :--- | :--- |
| `fl-cl-experiment-runner` | YAML validation & hyperparameter sweep tracing | `python .agents/skills/fl-cl-experiment-runner/scripts/validate_config.py --config <yaml>` |
| `fl-cl-proxmox-ops` | Proxmox VE cluster health, socket & VM state audits | `python .agents/skills/fl-cl-proxmox-ops/scripts/check_cluster_health.py` |
| `fl-cl-mlops-governance` | ADR-006 AST linter, docstrings & CLI compliance | `python .agents/skills/fl-cl-mlops-governance/scripts/audit_tool_compliance.py` |
| `fl-cl-continual-learning` | EWC/GEM Backward Transfer ($BWT$) stability diagnostic | `python .agents/skills/fl-cl-continual-learning/scripts/diagnose_forgetting.py` |
| `fl-cl-edge-inference-opt` | CPU edge latency profiler (FP32 / JIT / INT8) | `python .agents/skills/fl-cl-edge-inference-opt/scripts/profile_inference.py --model cnn` |

---

## 5. Ground-Truth Empirical Baselines

All numbers reflect validated benchmark reports in `data/reports/`:

| Metric | Ground-Truth Value | Benchmark Configuration |
| :--- | :---: | :--- |
| **Champion FL Accuracy** | **99.72%** (Cold-start 100r: **99.88%**) | 1D-CNN + EWC ($\lambda=1.0$) + TrimmedMean ($\beta=0.10$) |
| **DP-SGD Retention** | **99.51%** ($\varepsilon \approx 6.08, \delta=10^{-5}$) | Noise multiplier $\sigma=0.30$, Clip $C=1.0$ |
| **Poison Defense Accuracy** | **99.53%** | 20% malicious label flip neutralized via TrimmedMean |
| **GEM Botnet Recall Recovery**| **100.0%** ($F_1 = 0.6905$) | Episodic memory $P=512$, memory strength $\gamma=0.20$ |
| **EWC Botnet Degradation** | $BWT = -0.8544$ (Fisher collapse) | Botnet class minority in local stream |
| **Cluster Edge Throughput** | **101,258 flows/sec** (dual node) | FP32 batch size 32 |
| **Per-Flow Inference Latency**| **17.47 $\mu\text{s}$** (Defender A) | 1D-CNN FP32 CPU batch size 16 |
| **Model Footprint** | MLP: 19.8 KB \| CNN: 46.4 KB \| Transf: 74.2 KB | INT8 dynamic quantization |
| **FL Weight Payload** | **294.5 KB / round** | Compressed PyTorch parameter tensors |

---

## 6. Pre-Commit & Continuous Verification

Before completing any task or pushing changes, execute the test verification suite:

```bash
# 1. Codebase & documentation invariant audits
python tools/audit_all.py
python tools/audit_facts_and_metrics.py

# 2. ADR-006 MLOps static compliance
python .agents/skills/fl-cl-mlops-governance/scripts/audit_tool_compliance.py

# 3. Model forward pass, TorchScript, and quantization checks
python tools/test_models.py

# 4. End-to-end synthetic local training convergence
python tools/test_local_train.py
```

---

## 7. Specialized Agent Skills (.agents/skills/)

| Skill Name | Core Operational Script | Description |
| :--- | :--- | :--- |
| `fl-cl-experiment-runner` | `validate_config.py` | Experiment YAML schema validation & hyperparameter sweep tracing. |
| `fl-cl-proxmox-ops` | `check_cluster_health.py` | PVE bare-metal health checks, VM/LXC state auditing, and port-mirroring. |
| `fl-cl-mlops-governance` | `audit_tool_compliance.py` | ADR-006 compliance auditing, candidate model promotion, and 1-click rollback. |
| `fl-cl-continual-learning` | `diagnose_forgetting.py` | EWC/GEM backward transfer ($BWT$), catastrophic forgetting, and stability checks. |
| `fl-cl-edge-inference-opt` | `profile_inference.py` | Eager FP32 vs TorchScript JIT vs INT8 dynamic quantization profiling on CPU. |
| `fl-cl-dataset-intelligence`| `profile_datasets.py` | Statistical profiling, schema mapping, and cross-dataset scorecard generation. |

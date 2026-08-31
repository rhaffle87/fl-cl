# ADR-006: Tools Directory Standardization, Naming Taxonomy, and Governance

## Status
Accepted

## Date
2026-08-25

## Context
As the `fl-cl` codebase expanded to encompass multi-node Proxmox orchestration, differential privacy benchmarking, ONNX export, automated LLM reporting, and MLOps champion/challenger validation gates, utility scripts in the `tools/` directory accumulated varied naming conventions, inconsistent CLI argument parsing, and overlapping responsibilities.

Uncontrolled expansion of utility scripts presents several engineering challenges:
1. **Tool Discovery & Cognitive Load**: Researchers and operators cannot easily predict whether a tool is a synthetic offline unit test, a live testbed deployer, a diagnostic inspector, or an automated publication generator without inspecting source code.
2. **Path & Environment Inconsistencies**: Scripts used conflicting ways of resolving repository roots (`os.path.dirname` chaining vs `pathlib.Path`, differing `sys.path` orders), risking runtime `ImportError` on defender VMs.
3. **Exploratory vs Production Script Contamination**: Single-use or temporary scratch scripts were occasionally committed to `tools/`, violating the workspace governance rule separating `scratch/` from `tools/`.
4. **CI/CD Pipeline Rigidity**: Renaming scripts without maintaining compatibility aliases risks breaking existing cluster cron jobs, remote SCP wrappers, and automated testbed runners.

## Decision
We establish a formal, prefix-governed operational taxonomy for all utilities in `tools/`, enforce structural and CLI conventions, and mandate strict separation between production utilities and exploratory scratch scripts.

### 1. Functional Prefix Taxonomy

Every production script in `tools/` must begin with an approved lowercase verb/functional category followed by an underscore (`<prefix>_<descriptor>.py`):

| Prefix | Functional Category | Expected Behavior & Constraints | Examples |
| :--- | :--- | :--- | :--- |
| **`audit_`** | Static Analysis & Governance | Audits codebase syntax, YAML schemas, documentation links, and architectural invariants without side effects. Returns exit code 0 on success, 1 on error. | `audit_codebase.py`, `audit_docs.py` |
| **`benchmark_`** | Empirical Sweeps & Profiling | Runs multi-point parameter sweeps (e.g. Byzantine attack scenarios, DP noise multipliers, hardware inference throughput) and exports structured CSV/JSON results to `data/reports/`. | `benchmark_byzantine.py`, `benchmark_cross_dataset.py`, `benchmark_dp.py`, `benchmark_latency.py`, `benchmark_onnx.py` |
| **`check_`** | Live Edge Diagnostics | Standalone diagnostic tools intended for direct execution or SCP transfer to defender nodes to inspect flow queues, ramdisk label balance, and feature distributions. | `check_dataset.py`, `check_features.py` |
| **`deploy_`** | Cluster Operations | Manages remote SSH/SCP execution across the Proxmox cluster (10.10.130.10–12) and synchronizes artifacts back to the local workspace. | `deploy_testbed.py` |
| **`export_`** | Format & Graph Compilation | Serializes and exports model weights to portable formats (ONNX, TorchScript, dynamic INT8 quantization) with strict numerical parity validation. | `export_onnx.py` |
| **`generate_`** / **`regenerate_`** | Artifact & Report Generation | Generates publication figures, LaTeX PDF manuscripts, and Ollama LLM threat intelligence summaries. | `generate_paper_figures.py`, `regenerate_figures.py`, `generate_paper_pdf.py`, `generate_llm_report.py` |
| **`plot_`** | Metric Visualization | Parses MLflow databases, CSV reports, or external datasets (e.g. CIC-IDS2017) to produce high-resolution graphical visualizations. | `plot_metrics.py`, `plot_cicids2017.py` |
| **`sync_`** | Cloud & Webhook Synchronization | Synchronizes benchmark CSV tables and live training telemetry to remote Google Sheets or external sinks. | `sync_sheets_webhook.py` |
| **`test_`** | Offline Regression & Unit Tests | Pure Python/PyTorch offline unit tests using synthetic or mocked inputs. Must execute in <30 seconds without requiring live Proxmox nodes or external network connectivity. | `test_models.py`, `test_local_train.py`, `test_comprehensive.py` |
| **`train_`** | Standalone Training Diagnostics | Standalone local training loops on edge nodes to isolate model convergence issues outside the distributed Flower federated orchestrator. | `train_local.py` |
| **`validate_`** | Production Quality Gates | Evaluates candidate model checkpoints against held-out flow datasets, computes per-class F1 bounds and BWT degradation, and cryptographically signs or promotes models in MLflow. | `validate_model.py`, `validate_bwt.py`, `validate_promotion.py` |

### 2. Standardization & Script Architecture Guidelines

All scripts in `tools/` must adhere to the following architecture rules:
1. **Module Docstring**: Must begin with a top-level docstring specifying the script purpose, target environment, and CLI usage examples.
2. **Robust Path Resolution**: Must resolve the project root using `pathlib.Path(__file__).resolve().parent.parent` and cleanly inject `src/`, `src/defender/`, and `src/aggregator/` into `sys.path`.
3. **CLI Argument Parsing**: Must use `argparse.ArgumentParser` with explicit `--help` descriptions, sane defaults, and type annotations for all configurable arguments.
4. **Standardized Exit Codes**:
   - `0`: Success / Verification Passed
   - `1`: Syntax / Runtime / Critical Error
   - `2`: Quality Gate Rejection (e.g. JSD divergence or F1 threshold violation)
5. **Output Organization**:
   - CSV/JSON reports $\rightarrow$ `data/reports/`
   - Model artifacts $\rightarrow$ `data/models/`
   - Generated plots $\rightarrow$ `data/exports/plots/` or `CIC-IDS2017/plots/`
   - Manuscript figures $\rightarrow$ `docs/paper/figures/`

### 3. Separation of `tools/` and `scratch/`

- **`tools/`**: Reserved exclusively for reusable, production-grade utilities, test suites, benchmarks, and operational tools that are part of the core repository lifecycle.
- **`scratch/`**: Designated for one-off debug scripts, exploratory snippets, and temporary experiment files. Exploratory scripts must never be placed directly in `tools/`.

### 4. Direct Canonical Naming & Retirement of Deprecated Shims

To maintain a pristine, unambiguous codebase without redundant wrapper files, all legacy non-standard entry points (`local_train.py`, `ci_cd_promote.py`, `compile_paper_pdf.py`, `evaluate_bwt.py`, `deploy_to_testbed.py`) have been fully retired and removed. All workflows, orchestrators, and docs directly target their canonical prefixed counterparts.

## Consequences

### Positive
- **Instant Discoverability**: Script functionality and execution scope are immediately obvious from the file prefix.
- **Automated Governance**: `tools/audit_codebase.py` enforces the 100% prefix taxonomy compliance as an automated CI/CD test, preventing naming drift.
- **Zero Redundancy**: Eliminates forwarding wrappers and file clutter in `tools/`.
- **Clean Separation of Concerns**: Isolates synthetic tests (`test_*`), live diagnostics (`check_*`), benchmarks (`benchmark_*`), and promotion gates (`validate_*`).

### Negative / Trade-offs
- External run scripts or manual shell histories referencing legacy names must be updated to use the canonical prefixed tool names.

# FL-CL Scratch & Diagnostics Directory

This directory contains utility scripts for testbed deployment, local architectural verification, model quantization checks, and MLflow database inspection.

## Core Retained Scripts

### 1. Testbed Automation & Execution
* **`deploy_to_testbed.py`**: Automated runner executing all 5 core experiment configurations (`quick_test.yaml`, `baseline.yaml`, `dp_sgd.yaml`, `data_poisoning.yaml`, `robust_agg.yaml`) and the 4-tier benchmark suite (`benchmark_quick.yaml`, `benchmark_balanced.yaml`, `benchmark_stressed.yaml`, `benchmark_realworld.yaml`) directly on the 3-node physical Proxmox testbed (`10.10.130.10`).
* **`run_benchmarks.py`**: Local multi-thread benchmark execution orchestrator.
* **`monitor.py`**: Real-time process and log convergence monitor for testbed runs.

### 2. Architectural Verification & Testing
* **`test_models.py`**: Model verification suite checking forward pass shape calculators, TorchScript compilation, 8-bit dynamic quantization, and Fisher-guided pruning.
* **`test_local_train.py`**: End-to-end training convergence verification suite on synthetic 5-class network flow data.
* **`debug_local_training.py`**: Diagnostic harness for debugging EWC penalty calculations and Avalanche strategy hooks locally.
* **`test_comprehensive_suite.py`**: Multi-scenario local validation harness testing DP noise limits and label-poisoning sensitivity.
* **`test_confusion_matrix.py`**: Generates 5x5 confusion matrix heatmaps from evaluation outputs.

### 3. MLflow Database & Registry Utilities
* **`query_mlflow.py`**: Interrogates local/remote SQLite `mlflow.db` for run metrics, parameters, and tags.
* **`query_registry.py`**: Lists registered models in MLflow along with version aliases (`champion`, `challenger`).
* **`register_champion.py`**: Explicit script to promote or demote model versions in the MLflow Model Registry.
* **`restore_experiment.py`**: Utility script to restore archived or soft-deleted MLflow experiments.
* **`inspect_db.py`**: SQL schema and table inspector for MLflow tracking databases.

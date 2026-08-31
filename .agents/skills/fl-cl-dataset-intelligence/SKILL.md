---
name: fl-cl-dataset-intelligence
description: Exhaustive statistical profiling, schema mapping, cross-dataset analysis, and reporting across all cyber defense datasets and benchmark CSVs.
---

# FL-CL Dataset Intelligence Skill

This skill provides autonomous workflows, schema dictionaries, and profiling tools for analyzing raw intrusion detection datasets (`CIC-IDS2017`, `CIRA-CIC-DoHBrw-2020`, `CSE-CIC-IDS2018`, `CSE-CIC-IDS2018-v2`, `USTC-TFC2016`), inspecting live 32-feature Encrypted Traffic Analysis (`ETA`) streams, and synthesizing benchmark evaluation matrices from `data/reports/`.

---

## 1. Supported Datasets & Schemas

| Dataset | Primary Format | Volume | Schema & Protocol Scope |
| :--- | :--- | :---: | :--- |
| **`CIC-IDS2017`** | 8 CSVs (`datasets/CIC-IDS2017/`) | 843.66 MB | 79 CICFlowMeter features: DDoS, PortScan, Botnet, Infiltration, WebAttacks, SSH/FTP BruteForce, DoS. |
| **`CIRA-CIC-DoHBrw-2020`** | 3 CSVs (`datasets/CIRA-CIC-DoHBrw-.../`) | 786.51 MB | Hierarchical DoH features: L1 (DoH/Non-DoH), L2 (DoH Browsing), L3 (DoH Tunnels: dns2tcp, dnscat2, iodine, dnstt, tcp-over-dns, tuns). |
| **`CSE-CIC-IDS2018`** | PCAPs & CSVs (`datasets/CSE-CIC-IDS2018/`) | Multi-GB | AWS cloud-scale multi-subnet infiltration and volumetric DDoS traffic. |
| **`USTC-TFC2016`** | Encrypted PCAPs (`datasets/USTC-TFC2016/`) | 20 Classes | 10 Malware families (Zeus, Virut, Cridex, etc.) vs. 10 Benign applications (BitTorrent, Skype, FaceTime, etc.). |
| **`Live Testbed ETA`** | RAMDisk CSVs (`/mnt/ramdisk/flows/`) | Dynamic | 32 NFStream flow features extracted on `ens19` (packet counts, byte volumes, timing jitter, TCP flags, moments). |
| **`Baseline Stats`** | JSON (`src/defender/baseline_feature_stats.json`) | 5 Classes | 10 statistical flow moments for Z-score normalization and covariate shift prevention. |
| **`Benchmark Reports`** | 14 CSVs (`data/reports/*.csv`) | Tabular | 72-matrix, Byzantine, DP-SGD, OOD energy, multi-runtime latency, and BWT reports. |

---

## 2. Standard Operational Workflows

### Workflow 1: Profile All Datasets and Generate Markdown Summary
Run the comprehensive profiler to scan all raw datasets and benchmark evaluation matrices:
```bash
python .agents/skills/fl-cl-dataset-intelligence/scripts/profile_datasets.py --all --output data/reports/dataset_profiling_summary.md
```

### Workflow 2: Profile a Specific Dataset
Inspect the column schemas, missing values, and file stats for a target dataset:
```bash
# Profile CIC-IDS2017
python .agents/skills/fl-cl-dataset-intelligence/scripts/profile_datasets.py --dataset CIC-IDS2017

# Profile CIRA DoH Tunneling Dataset
python .agents/skills/fl-cl-dataset-intelligence/scripts/profile_datasets.py --dataset CIRA-CIC-DoHBrw-2020

# Profile USTC-TFC2016 Encrypted Malware
python .agents/skills/fl-cl-dataset-intelligence/scripts/profile_datasets.py --dataset USTC-TFC2016
```

### Workflow 3: Synthesize Benchmark Reports Matrix
Generate an executive scorecard aggregating all 14 benchmark CSV reports in `data/reports/`:
```bash
python .agents/skills/fl-cl-dataset-intelligence/scripts/profile_datasets.py --reports-only
```

### Workflow 4: Evaluate Cross-Dataset Generalization
Benchmark a trained model checkpoint against heterogeneous datasets (CIC-IDS2017 vs. USTC-TFC2016):
```bash
python tools/benchmark_cross_dataset.py \
    --model-type cnn \
    --checkpoint models/checkpoints/champion.pt \
    --output data/reports/cross_dataset_benchmark_report.csv
```

---

## 3. Schema Reference & Feature Mapping

For complete feature dictionaries, class taxonomy tables, and normalization parameters, refer to:
* **[Dataset Catalog Reference](file:///e:/Projects/fl-cl/.agents/skills/fl-cl-dataset-intelligence/references/dataset_catalog.md)**

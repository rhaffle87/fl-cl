# FL-CL Dataset Catalog & Schema Reference

A centralized technical catalog defining the schema mappings, feature sets, class taxonomies, and normalization standards across all datasets in the `fl-cl` project.

---

## 1. Feature Schemas & Cross-Dataset Mappings

### 1.1 32-Dimensional Live ETA Flow Schema (NFStream)
Extracted on edge defender network interfaces (`ens19`) and processed in memory via RAMDisk:

| Feature Index | Feature Name | DataType | Description |
| :---: | :--- | :---: | :--- |
| 0 | `bidirectional_packets` | `int64` | Total packets exchanged across flow lifetime. |
| 1 | `bidirectional_bytes` | `int64` | Total bytes exchanged across flow lifetime. |
| 2 | `bidirectional_duration_ms` | `float32` | Total flow active duration in milliseconds. |
| 3 | `src2dst_packets` | `int64` | Packets transmitted from source to destination. |
| 4 | `src2dst_bytes` | `int64` | Bytes transmitted from source to destination. |
| 5 | `dst2src_packets` | `int64` | Packets transmitted from destination to source. |
| 6 | `dst2src_bytes` | `int64` | Bytes transmitted from destination to source. |
| 7 | `src2dst_min_ps` | `float32` | Minimum packet size in forward direction. |
| 8 | `src2dst_mean_ps` | `float32` | Mean packet size in forward direction. |
| 9 | `src2dst_stddev_ps` | `float32` | Standard deviation of forward packet sizes. |
| 10 | `src2dst_max_ps` | `float32` | Maximum packet size in forward direction. |
| 11 | `dst2src_min_ps` | `float32` | Minimum packet size in backward direction. |
| 12 | `dst2src_mean_ps` | `float32` | Mean packet size in backward direction. |
| 13 | `dst2src_stddev_ps` | `float32` | Standard deviation of backward packet sizes. |
| 14 | `dst2src_max_ps` | `float32` | Maximum packet size in backward direction. |
| 15 | `src2dst_min_piat_ms` | `float32` | Minimum packet inter-arrival time (forward). |
| 16 | `src2dst_mean_piat_ms` | `float32` | Mean packet inter-arrival time (forward). |
| 17 | `src2dst_stddev_piat_ms` | `float32` | Standard deviation of packet inter-arrival time (forward). |
| 18 | `src2dst_max_piat_ms` | `float32` | Maximum packet inter-arrival time (forward). |
| 19 | `dst2src_min_piat_ms` | `float32` | Minimum packet inter-arrival time (backward). |
| 20 | `dst2src_mean_piat_ms` | `float32` | Mean packet inter-arrival time (backward). |
| 21 | `dst2src_stddev_piat_ms` | `float32` | Standard deviation of packet inter-arrival time (backward). |
| 22 | `dst2src_max_piat_ms` | `float32` | Maximum packet inter-arrival time (backward). |
| 23 | `src2dst_syn_packets` | `int64` | TCP SYN packet count (forward). |
| 24 | `src2dst_cwr_packets` | `int64` | TCP Congestion Window Reduced count. |
| 25 | `src2dst_ece_packets` | `int64` | TCP ECN-Echo count. |
| 26 | `src2dst_urg_packets` | `int64` | TCP URG packet count. |
| 27 | `src2dst_ack_packets` | `int64` | TCP ACK packet count. |
| 28 | `src2dst_psh_packets` | `int64` | TCP PSH packet count. |
| 29 | `src2dst_rst_packets` | `int64` | TCP RST packet count. |
| 30 | `src2dst_fin_packets` | `int64` | TCP FIN packet count. |
| 31 | `application_is_tls` | `int64` | Binary indicator (1 if TLS 1.2/1.3 handshake detected). |

---

## 2. Canonical 5-Class Threat Taxonomy

| Class ID | Threat Class | MITRE ATT&CK Mapping | Description & Attack Mechanics | Penalty Weight ($w_c$) |
| :---: | :--- | :--- | :--- | :---: |
| **0** | **Normal** | N/A | Benign HTTP/HTTPS browsing, API queries, SSH sessions. | `1.0` |
| **1** | **Botnet** | `T1071` (Standard App Layer Protocol) | Periodic C2 beaconing with randomized jitter on ports 8080/8888. | `250.0` |
| **2** | **Exfiltration** | `T1048` (Exfiltration Over Alternative Protocol) | High-entropy DNS TXT queries tunneling data over port 53. | `2.0` |
| **3** | **BruteForce** | `T1110` (Brute Force) | High-frequency SSH authentication attempts on port 22. | `5.0` |
| **4** | **DoS** | `T1498` (Network Denial of Service) | Slowloris low-and-slow HTTP header exhaustion on port 80. | `50.0` |

---

## 3. Benchmark Reports Catalog (`data/reports/`)

| Report CSV | Primary Metric | Target Research Dimension |
| :--- | :--- | :--- |
| `master_matrix_benchmark_report.csv` | Acc, F1, Loss, Latency | 72-combination grid sweep across backbones, CL algorithms, aggregators. |
| `byzantine_robustness_benchmark.csv` | Val Accuracy under Poison | Resilience of TrimmedMean, FedMedian, Krum under 10%–50% label poisoning. |
| `privacy_utility_curve.csv` | $(\varepsilon, \delta)$-DP vs. Macro F1 | Differential Privacy utility preservation across $\sigma \in [0.0, 0.20]$. |
| `multi_runtime_latency_report.csv` | Latency ($\mu\text{s}$) & Speedup | CPU execution provider comparison (PyTorch FP32 vs JIT vs ONNX AVX-512). |
| `bwt_report.csv` | Backward Transfer ($\text{BWT}$) | Quantifying catastrophic forgetting across multi-phase continual learning. |
| `ood_benchmark_report.csv` | Free Energy AUROC | Energy-based zero-day unknown threat detection. |
| `cross_dataset_benchmark_report.csv`| Generalization Gap | Validation across CIC-IDS2017 and USTC-TFC2016. |
| `ewc_sensitivity_results.csv` | $\lambda_{\text{EWC}}$ Sensitivity | Fisher Information Matrix scaling effects under class imbalance. |
| `latency_quantization_report.csv` | INT8 vs FP32 Latency | Post-training dynamic quantization benchmark. |
| `quarantine_retrain_report.csv` | A-GEM Retraining Time | Continual fine-tuning latency on isolated zero-day quarantine buffers. |
| `adversarial_stress_benchmark.csv` | FGSM Adversarial Robustness | Evasion robustness under gradient perturbation attacks ($\epsilon=0.01\text{–}0.1$). |
| `technical_debt_ledger.csv` | Debt Items & Severity | Automated static audit of technical debt markers across codebase. |

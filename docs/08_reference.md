# API Reference & Module Documentation

Comprehensive technical reference for all core Python modules, classes, and functions across the `fl-cl` codebase.

---

## 1. Model Factory & Architectures (`src/defender/model.py`)

### `get_model(model_type, input_dim=32, num_classes=5, **kwargs) -> nn.Module`
Factory function to dynamically instantiate neural network backbones.

* **Parameters**:
 * `model_type` (`str`): `"mlp"`, `"cnn"`, or `"transformer"`.
 * `input_dim` (`int`): Input feature dimension (default: 32).
 * `num_classes` (`int`): Number of classification threat categories (default: 5).
 * `**kwargs`: Backbone-specific hyperparameter overrides.
* **Returns**: Initialized `torch.nn.Module` instance.

---

### `CyberDefenseNet`
* **File**: [model.py](file:///e:/Projects/fl-cl/src/defender/model.py#L22-L50)
* **Description**: 3-layer Multi-Layer Perceptron (MLP) with dropout regularization.
* **Constructor**:
 ```python
 CyberDefenseNet(input_dim=32, num_classes=5, hidden_dim1=64, hidden_dim2=32, dropout=0.2)
 ```
* **Throughput**: ~633,600 flows/sec | **Footprint**: 0.017 MB state dict.

---

### `CyberDefenseCNN`
* **File**: [model.py](file:///e:/Projects/fl-cl/src/defender/model.py#L52-L108)
* **Description**: 1D Convolutional Neural Network for temporal/spatial flow feature extraction.
* **Constructor**:
 ```python
 CyberDefenseCNN(input_dim=32, num_classes=5, conv_channels1=16, conv_channels2=32, kernel_size=3, fc_dim=64, dropout=0.2)
 ```
* **Key Feature**: Dynamically computes linear layer input dimensions via dummy forward pass (`self.conv(torch.zeros(1, 1, input_dim))`).

---

### `CyberDefenseTransformer`
* **File**: [model.py](file:///e:/Projects/fl-cl/src/defender/model.py#L110-L195)
* **Description**: Transformer-based classifier treating flow features as token sequences.
* **Constructor**:
 ```python
 CyberDefenseTransformer(input_dim=32, num_classes=5, token_len=8, token_dim=4, d_model=32, nhead=4, dim_feedforward=64, num_layers=2, fc_dim=32, dropout=0.1)
 ```
* **Invariant**: Enforces `assert token_len * token_dim == input_dim`.

---

## 2. Continual Learning Engine (`src/defender/cl_strategy.py`)

### `get_continual_learner(...)`
* **File**: [cl_strategy.py](file:///e:/Projects/fl-cl/src/defender/cl_strategy.py#L30-L143)
* **Description**: Instantiates an Avalanche CL strategy wrapper with custom gradient clipping and class-weighted loss.
* **Signature**:
 ```python
 def get_continual_learner(
 model, device, strategy_name="EWC", ewc_lambda=0.8,
 patterns_per_exp=256, memory_strength=0.5, class_weights=None,
 lr=0.01, momentum=0.9, batch_size=32, dp_enabled=False,
 dp_noise_multiplier=0.1, dp_max_grad_norm=1.0
 )
 ```
* **Parameters**:
 * `strategy_name`: `"EWC"`, `"GEM"`, or `"NAIVE"`.
 * `ewc_lambda`: Fisher regularization coefficient (default: 0.8).
 * `patterns_per_exp`: Memory buffer pattern capacity for GEM (default: 256–512).
 * `memory_strength`: Quadratic programming constraint projection margin for GEM (default: 0.2–0.5).
 * `class_weights`: List of 5 class weights (default: `[1.0, 250.0, 2.0, 5.0, 50.0]`).
* **Returns**: Avalanche strategy object (`EWC`, `GEM`, or `Naive`).

---

## 3. Flow Extraction Engine (`src/defender/extractor.py`)

### `extract_features(interface: str, out_dir: str, batch_size: int = 500)`
* **File**: [extractor.py](file:///e:/Projects/fl-cl/src/defender/extractor.py#L25-L108)
* **Description**: Captures mirrored packet streams via NFStream, extracts 18 flow metadata features, and writes batched CSVs directly to tmpfs RAMDisk.
* **Extracted Schema**:
 * TLS Fingerprints: `ja3_hash`, `ja3s_hash`, `sni`, `application`
 * Flow Volumes: `bidirectional_packets`, `bidirectional_bytes`, `duration_ms`
 * Directional Split: `src2dst_packets`, `src2dst_bytes`, `dst2src_packets`, `dst2src_bytes`
 * Inter-arrival Times: `src2dst_mean_piat_ms`, `dst2src_mean_piat_ms`
 * Network Metadata: `src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`

---

## 4. Federated Aggregator Server (`src/aggregator/server.py`)

### `MLflowFedAvg`
* **File**: [server.py](file:///e:/Projects/fl-cl/src/aggregator/server.py#L104-L350)
* **Description**: Custom Flower `fl.server.strategy.FedAvg` extension with MLflow tracking and robust aggregation algorithms.
* **Constructor**:
 ```python
 MLflowFedAvg(checkpoint_dir="/opt/mlflow-artifacts/checkpoints",
 export_torchscript=True, aggregation_strategy="FedAvg",
 trimmed_mean_beta=0.1, model_type="mlp", prune_fraction=0.2, **kwargs)
 ```
* **Supported Aggregation Strategies**:
 * `"FedAvg"`: Sample-weighted linear parameter averaging.
 * `"TrimmedMean"`: Coordinate-wise $\beta$-trimmed mean discarding upper/lower 10% outlier client parameters.
 * `"FedMedian"`: Coordinate-wise median aggregation.
 * `"Krum"`: Geometric distance-based single client selection.

### `weighted_avg(metrics: List[Tuple[int, Metrics]]) -> Metrics`
Computes sample-weighted accuracy, per-class F1-scores, and 5x5 confusion matrix cells across all responding edge defenders.

---

## 5. Real-Time Inference Loop (`src/defender/inference_loop.py`)

### `load_model(checkpoint_path: str, device: torch.device) -> Tuple[torch.jit.ScriptModule, float]`
Loads TorchScript JIT compiled checkpoint and records file modification timestamp for automatic hot-reloading.

### `scale_features(X: np.ndarray, available_cols: List[str], stats_path: Optional[str]) -> np.ndarray`
Applies deterministic Z-score normalization based on precomputed baseline Normal traffic statistics to prevent covariate drift.

### `preprocess_batch(df: pd.DataFrame, stats_path: Optional[str]) -> torch.Tensor`
Converts raw flow DataFrame into normalized 32-dimensional PyTorch tensors with dynamic padding.

---

## 6. Operational & MLOps Tools Reference (ADR-006)

### `tools/validate_promotion.py`
Automated candidate model validation and champion promotion gate:
* **Per-Class F1 Thresholds**:
  * Normal (0): $\ge 0.50$
  * Botnet (1): $\ge 0.60$
  * Exfiltration (2): $\ge 0.70$
  * BruteForce (3): $\ge 0.50$
  * DoS (4): $\ge 0.70$
* **Promotion Action**: Assigns `champion` alias in MLflow Model Registry upon 100% threshold compliance and notifies Telegram.

### `tools/validate_bwt.py`
Computes class-wise accuracy, F1-scores, and BWT forgetting deltas against historical baseline milestones with cryptographic SHA-256 validation signing.

### `tools/train_local.py`
Runs standalone local defender training outside Flower FL loops to diagnose convergence and print full confusion matrices.

### `tools/deploy_testbed.py`
Orchestrates multi-tier benchmark execution across Proxmox nodes (`10.10.130.10–12`) via passwordless SSH and synchronizes run exports.

### `tools/benchmark_onnx.py`
Evaluates multi-runtime inference latency and throughput across PyTorch FP32, TorchScript JIT, and ONNX Runtime (AVX2 acceleration) across batch sizes 1 to 256.

### `tools/benchmark_byzantine.py`
Evaluates Byzantine resilience across `FedAvg`, `FedMedian`, `Krum`, and `TrimmedMean` under 10%–50% label poisoning, sign-flipping, and Gaussian noise attacks.

### `tools/benchmark_dp.py`
Computes the Differential Privacy (DP-SGD) privacy-utility trade-off curve across noise multipliers $\sigma \in [0.0, 1.0]$ with formal $(\epsilon, \delta)$ accounting.

### `tools/test_attack_gen.py`
Validates modular dual-engine attack generator functionality, tool fallback order, and RFC/MITRE compliance across all 5 threat categories.

---

## 7. Modular Attack Generator Reference (`src/traffic_gen/attack_flow.py`)

### `run_attack_scenario(args)`
Main orchestration entry point for traffic generation. Dispatches attack vectors based on `--engine`:
* **`--engine auto`** (Default): Discovers installed Kali binaries (`slowhttptest`, `ncrack`, `medusa`, `hping3`, `scapy`); falls back gracefully to pure Python implementations if absent.
* **`--engine kali`**: Enforces strictly native Kali offensive security utilities with subprocess timeout guards and resource cleanup.
* **`--engine python`**: Enforces lightweight pure Python socket routines for cross-platform and CI environments.

### Supported Threat Vectors:
1. **Benign Browsing**: High-frequency HTTP GET requests simulating legitimate user browsing.
2. **SSH Brute-Force**: Multi-threaded password spraying targeting port 22 (`hydra` / `ncrack` / `medusa` vs. socket auth loop).
3. **Slowloris DoS**: Low-bandwidth persistent partial HTTP header holding targeting port 80/443 (`slowhttptest` / `hping3` vs. socket pool).
4. **DNS Exfiltration**: High-entropy TXT/CNAME query tunneling targeting port 53 (`scapy` / `iodine` vs. RFC 1035 UDP packer).
5. **Botnet C2 Beaconing**: Multi-round HTTP POST beacons with randomized jitter on ports 8080/8888/9000.

---

## 8. Regulatory & Statutory Compliance Standards Mapping

| Standard | Target Requirement | Verification Mechanism & Command |
| :--- | :--- | :--- |
| **UU PDP No. 27/2022** *(Art. 65–66)* | Raw personal data localization within local secure enclave. | Verified via `src/defender/client.py` and tmpfs RAMDisk isolation (`/mnt/ramdisk/flows/`). |
| **GDPR (EU 2016/679)** *(Art. 5, 25, 32)* | Privacy by Design via cryptographic DP-SGD bounds. | Verified via `python tools/benchmark_dp.py` ($C=1.0, \sigma=0.30 \implies \epsilon=6.08, \delta=10^{-5}$). |
| **NIST SP 800-94 / 800-145** | Network IDPS behavioral flow anomaly detection. | Verified via 32-feature extraction in `src/defender/extractor.py`. |
| **MITRE ATT&CK Enterprise** | Standardized threat taxonomy mapping. | Covered TTPs: T1498 (DoS), T1110 (BruteForce), T1048 (DNS Exfil), T1071 (C2 Beaconing). |
| **ISO/IEC 27001 / 27701** | ISMS / PIMS Lineage & Auditability. | Verified via `python tools/audit_codebase.py` and SHA-256 dataset lineage graphs. |
| **RFC 1035 / 793 / 7230** | Wire protocol formatting and state machine conformance. | Verified via `python tools/test_attack_gen.py`. |



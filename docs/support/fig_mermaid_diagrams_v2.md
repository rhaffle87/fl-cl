# Mermaid Diagrams — FL-CL Thesis Figures (v2)

This document contains publication-ready, stable Mermaid diagrams for the FL-CL system.
All diagrams use standard, non-experimental Mermaid syntax (`flowchart`, `sequenceDiagram`, `pie`) with 4-space indentation to ensure maximum compatibility across GitHub, VS Code, and Markdown documentation renderers.

---

## 1. fig_proxmox_cluster.png — Cluster Network Topology

```mermaid
flowchart TB
    subgraph Cluster ["Proxmox VE 3-Node Hypervisor Cluster"]
        subgraph WAN_Plane ["Management Plane (vmbr0 — 192.168.x.x)"]
            PVE_GW["Physical Uplink Gateway"]
        end

        subgraph Data_Plane ["Isolated L2 Data Plane (vmbr1 — 10.10.0.0/16)"]
            subgraph Node_ITS ["Node 1: its (10.10.10.11 — Dell R630, 2x 1GbE LACP)"]
                DefenderA["Defender Node A<br/>VM 310 (10.10.130.11)<br/>NFStream + PyTorch + Avalanche"]
                TargetA["Target Host A1<br/>VM 311 (10.10.110.15)"]
                MirrorA["tc mirred Port Mirror<br/>(tap311i0 → tap310i1)"]
            end

            subgraph Node_NODE2 ["Node 2: node2 (10.10.10.12 — Dell R630, 2x 1GbE LACP)"]
                DefenderB["Defender Node B<br/>VM 320 (10.10.130.12)<br/>NFStream + PyTorch + Avalanche"]
                TargetB["Target Host B1<br/>VM 321 (10.10.120.15)"]
                TrafficGen["Offensive Traffic Gen<br/>VM 400 (10.10.140.10)<br/>Hydra / Slowloris / Synthetic"]
                MirrorB["tc mirred Port Mirror<br/>(tap321i0 → tap320i1)"]
            end

            subgraph Node_PVE ["Node 3: pve (10.10.10.13 — Dell R760xs, 1x 1GbE)"]
                Aggregator["FL Aggregator & MLOps<br/>LXC 300 (10.10.130.10)<br/>Flower gRPC + MLflow Registry"]
            end
        end
    end

    TrafficGen -->|Attack Streams| TargetA
    TrafficGen -->|Attack Streams| TargetB
    TargetA --- MirrorA -.->|Mirrored Ingress/Egress| DefenderA
    TargetB --- MirrorB -.->|Mirrored Ingress/Egress| DefenderB
    DefenderA <==>|Flower gRPC / MLflow Logs| Aggregator
    DefenderB <==>|Flower gRPC / MLflow Logs| Aggregator
```

---

## 2. fig_cnn_1d_architecture.png — 1D-CNN Backbone (CyberDefenseCNN)

```mermaid
flowchart LR
    In["Input Flow Vector<br/>(32 Scaled ETA Features)"] --> Unsqueeze["Unsqueeze<br/>(1 × 32)"]
    Unsqueeze --> Conv1["Conv1d(1 → 16, k=3, p=1)"]
    Conv1 --> Act1["ReLU"]
    Act1 --> Pool1["MaxPool1d(kernel=2) → (16 × 16)"]
    Pool1 --> Conv2["Conv1d(16 → 32, k=3, p=1)"]
    Conv2 --> Act2["ReLU"]
    Act2 --> Pool2["MaxPool1d(kernel=2) → (32 × 8)"]
    Pool2 --> Flatten["Flatten → (256-dim)"]
    Flatten --> FC1["FC(256 → 64)"]
    FC1 --> Act3["ReLU"]
    Act3 --> Drop["Dropout(p=0.2)"]
    Drop --> FC2["FC(64 → 5 Classes)"]
    FC2 --> Out["Output Logits<br/>0: Normal | 1: Botnet C2<br/>2: Exfiltration | 3: BruteForce | 4: DoS"]
```

---

## 3. fig_mlp_architecture.png — Multi-Layer Perceptron (CyberDefenseNet)

```mermaid
flowchart LR
    In["Input: 32-dim ETA Features"] --> FC1["FC(32 → 64) + ReLU + Dropout(p=0.2)"]
    FC1 --> FC2["FC(64 → 32) + ReLU"]
    FC2 --> FC3["FC(32 → 5 Classes)"]
    FC3 --> C0["Class 0: Normal"]
    FC3 --> C1["Class 1: Botnet C2"]
    FC3 --> C2["Class 2: DNS Exfiltration"]
    FC3 --> C3["Class 3: SSH BruteForce"]
    FC3 --> C4["Class 4: DoS / DDoS"]
```

---

## 4. fig_transformer_architecture.png — Tabular Transformer (CyberDefenseTransformer)

```mermaid
flowchart LR
    In["Input: 32-dim Vector"] --> Reshape["Reshape:<br/>8 tokens × 4 dim"]
    Reshape --> Proj["Linear Projection (4 → 32)<br/>+ Sinusoidal Positional Encoding"]

    subgraph Encoder ["Transformer Encoder (2 Layers, nhead=4, d_model=32)"]
        direction LR
        subgraph L1 ["Layer 1"]
            direction TB
            MHSA1["Multi-Head Self-Attention (4 heads)"] --> AddNorm1["Add & LayerNorm"]
            AddNorm1 --> FFN1["FFN (32 → 64 → 32)"] --> AddNorm2["Add & LayerNorm"]
        end
        subgraph L2 ["Layer 2"]
            direction TB
            MHSA2["Multi-Head Self-Attention (4 heads)"] --> AddNorm3["Add & LayerNorm"]
            AddNorm3 --> FFN2["FFN (32 → 64 → 32)"] --> AddNorm4["Add & LayerNorm"]
        end
        L1 --> L2
    end

    Proj --> Encoder
    Encoder --> GAP["Global Average Pooling (mean over 8 tokens)"]
    GAP --> FC1["FC(32 → 32) + ReLU + Dropout(p=0.1)"]
    FC1 --> FC2["FC(32 → 5 Classes)"]
    FC2 --> Out["5 Threat Class Logits"]
```

---

## 5. fig_avalanche_cl_framework.png — Continual Learning Lifecycle

```mermaid
flowchart LR
    subgraph Stream ["Stream of Non-Stationary Experiences"]
        E1["Exp 1: Normal"] --> E2["Exp 2: DoS"]
        E2 --> E3["Exp 3: SSH Brute"]
        E3 --> E4["Exp 4: DNS Exfil"]
        E4 --> E5["Exp 5: Botnet C2 (Sparse)"]
    end

    Stream --> CL_Engine

    subgraph CL_Engine ["Avalanche Continual Learning Strategy"]
        direction TB
        Strategy_Select{"Strategy Engine"}
        Strategy_Select -->|Baseline| EWC["EWC Plugin:<br/>L_ewc = L_curr + (λ/2) Σ F_i (θ - θ*)^2"]
        Strategy_Select -->|Champion| GEM["GEM Plugin (s=0.2):<br/>Episodic Buffer M_k + QP Projection<br/>Subject to: ⟨g, g_k⟩ ≥ 0"]
    end

    CL_Engine --> Model["PyTorch Model<br/>(CyberDefenseCNN)"]
    Model --> Eval["Evaluation Plugins<br/>(BWT, Per-Class F1, Loss)"]
    Eval --> Loggers["MLOps Logging<br/>(MLflow Server + TensorBoard)"]
```

---

## 6. fig_ewc_fisher_collapse.png — EWC Fisher Collapse Under Sparse Traffic

```mermaid
flowchart TB
    subgraph Imbalance ["1. Traffic Class Imbalance per Batch (NFStream Window)"]
        direction LR
        S_Norm["Normal Traffic: 2,000 flows (94.8%)"]
        S_DoS["DoS: 100 flows (4.7%)"]
        S_SSH["SSH Brute: 50 flows (2.4%)"]
        S_Exfil["DNS Exfil: 30 flows (1.4%)"]
        S_Bot["Botnet C2: ~12 flows (0.57% Sparse)"]
    end

    subgraph Fisher ["2. Resulting Fisher Information Matrix Diagonal (F_i)"]
        direction LR
        F_Norm["F_Normal: Extremely Large (High Weight Protection)"]
        F_Other["F_DoS / F_SSH: Moderate (Sufficient Protection)"]
        F_Bot["F_Botnet ≈ 0 (Vanishing Fisher Diagonal)"]
    end

    subgraph Impact ["3. Empirical Continual Learning Impact"]
        direction TB
        EWC_Fail["EWC Penalty: (λ/2) · (0) · (θ - θ*)^2 = 0<br/>Minority class weights drift freely during subsequent tasks"]
        Collapse["Catastrophic Forgetting:<br/>Botnet BWT = -0.8544 | Botnet Recall Collapses to 0.0%"]
        GEM_Fix["Resolution via GEM (s=0.2):<br/>Hard QP Gradient Constraint ⟨g, g_k⟩ ≥ 0 → BWT = 0.000 | Botnet Recall = 100.0%"]
    end

    Imbalance ==> Fisher
    Fisher ==> Impact
```

---

## 7. fig_fedavg_vs_trimmedmean.png — Byzantine Robustness Comparison

```mermaid
flowchart TB
    subgraph Scenario ["Federated Aggregation under 20% Byzantine Label Poisoning"]
        direction LR
        C1["Defender A (Benign)"]
        C2["Defender B (Benign)"]
        C3["Defender C (Benign)"]
        C4["Defender D (Benign)"]
        C_Poison["Compromised Node (Poisoned: 20% Label Flip)"]
    end

    Scenario --> FedAvg_Path
    Scenario --> TrimmedMean_Path

    subgraph FedAvg_Path ["FedAvg (Naive Coordinate-wise Mean)"]
        direction TB
        Agg_Avg["Standard Weighted Average<br/>Includes poisoned gradient directly"]
        Res_Avg["Degraded Global Model<br/>Accuracy: 75.80% | Botnet F1: Collapsed"]
        Agg_Avg --> Res_Avg
    end

    subgraph TrimmedMean_Path ["TrimmedMean Aggregator (β = 0.10 — Champion)"]
        direction TB
        Agg_Trim["Sort coordinate values & trim top/bottom 10%<br/>Discards Byzantine outlier updates"]
        Res_Trim["Resilient Global Model<br/>Accuracy: 99.53% | Botnet Recall: 100.0% | Botnet F1: 69.0%"]
        Agg_Trim --> Res_Trim
    end
```

---

## 8. fig_continual_bwt_matrix.png — Backward Transfer (BWT) Performance

```mermaid
flowchart TB
    subgraph Matrix ["Backward Transfer (BWT) Matrix Across Experiment Tracks"]
        direction TB
        subgraph Track1 ["1. EWC Baseline (100 Rounds)"]
            T1_Res["Normal: -0.001 | SSH: 0.000 | DoS: 0.000 | Exfil: 0.000<br/>Botnet C2: -0.8544 (Severe Collapse) | Avg BWT: -0.1711"]
        end
        subgraph Track2 ["2. EWC with 50% Node Dropout"]
            T2_Res["Normal: -0.014 | SSH: 0.000 | DoS: 0.000 | Exfil: 0.000<br/>Botnet C2: -0.7751 (Persistent Forgetting) | Avg BWT: -0.1558"]
        end
        subgraph Track3 ["3. GEM Untuned (s = 0.5)"]
            T3_Res["Normal: -0.002 | SSH: 0.000 | DoS: 0.000 | Exfil: 0.000<br/>Botnet C2: 0.000 (100% Recall, F1: 38.1%) | Avg BWT: -0.0004"]
        end
        subgraph Track4 ["4. GEM Precision Tuned (s = 0.2 — v34/v35 Champion)"]
            T4_Res["Normal: 0.000 | SSH: 0.000 | DoS: 0.000 | Exfil: 0.000<br/>Botnet C2: 0.000 (100% Recall, F1: 69.05%) | Avg BWT: 0.0000"]
        end
    end
```

---

## 9. fig_dp_sgd_noise.png — Differential Privacy Noise Sensitivity

```mermaid
flowchart LR
    subgraph Noise_Levels ["DP-SGD Noise Multiplier (σ) Sweep"]
        direction TB
        S0["σ = 0.00 (Clean Baseline)<br/>Acc: 99.72% | Botnet F1: 0.7119 | All Pass"]
        S1["σ = 0.05<br/>Acc: 99.68% | Botnet F1: 0.6980 | All Pass"]
        S2["σ = 0.10<br/>Acc: 99.64% | Botnet F1: 0.6820 | All Pass"]
        S3["σ = 0.15<br/>Acc: 99.58% | Botnet F1: 0.6700 | All Pass"]
        S4["σ = 0.20 (Production Setting)<br/>Acc: 99.53% | Botnet F1: 0.6570 | All Pass"]
        S5["σ = 0.30<br/>Acc: 99.46% | Botnet F1: 0.6450 | All Pass"]
    end

    subgraph Threshold ["MLflow Promotion Gate Rule"]
        Gate["Threshold: Min Per-Class F1 ≥ 0.60<br/>Result: All classes retain >0.64 F1 across entire sweep σ ∈ [0.00, 0.30]"]
    end

    Noise_Levels --> Threshold
```

---

## 10. fig_int8_quantization.png — Hardware Inference Acceleration

```mermaid
flowchart TB
    subgraph Benchmark ["Hardware Inference Throughput & Latency (Batch = 16)"]
        direction TB
        subgraph MLP ["MLP (CyberDefenseNet — 17 KB)"]
            M_FP32["FP32: 100,789 flows/sec (9.92 μs)"]
            M_INT8["INT8: 56,440 flows/sec (17.72 μs — 0.56x edge overhead)"]
            M_ONNX["ONNX Runtime: 419,646 flows/sec (2.38 μs — 4.16x Speedup)"]
        end
        subgraph CNN ["1D-CNN (CyberDefenseCNN — 70 KB — Champion)"]
            C_FP32["FP32: 14,624 flows/sec (68.38 μs)"]
            C_INT8["INT8: 9,140 flows/sec (109.41 μs — 0.62x edge overhead)"]
            C_ONNX["ONNX Runtime: 140,940 flows/sec (7.09 μs — 9.64x Speedup)"]
        end
        subgraph Xformer ["Transformer (CyberDefenseTransformer — 512 KB)"]
            T_FP32["FP32: 17,742 flows/sec (56.36 μs)"]
            T_INT8["INT8: 11,200 flows/sec (89.28 μs — 0.63x edge overhead)"]
            T_ONNX["ONNX Runtime: 16,035 flows/sec (62.36 μs — 0.90x CPU overhead)"]
        end
    end
```

---

## 11. fig_mlflow_tracking_dashboard.png — MLOps Observability & Promotion Gate

```mermaid
flowchart TB
    subgraph Dashboard ["MLOps Automated Experiment & Registry Pipeline"]
        direction LR
        subgraph Runs ["Experiment Runs Tracking"]
            R20["run_v20: 99.72% Acc (Baseline r100)"]
            R33["run_v33: 99.45% Acc (GEM untuned)"]
            R34["run_v34: 99.51% Acc (GEM s=0.2, F1=69.0%)"]
            R35["run_v35: 99.53% Acc (20% Poison Robust)"]
        end

        subgraph Metrics ["Logged Metrics & Artifacts"]
            M1["Global Accuracy & Loss per Round"]
            M2["Per-Class Backward Transfer (BWT)"]
            M3["5×5 Confusion Matrix Heatmap Artifact"]
        end

        subgraph Registry ["Model Registry & Promotion Gate"]
            V35["CyberDefenseCNN v35 → alias: champion"]
            V34["CyberDefenseCNN v34 → alias: challenger / gem-v34"]
            V20["CyberDefenseCNN v20 → alias: baseline-r100"]
        end
    end

    Runs --> Metrics --> Registry
```

---

## 12. fig_non_iid_distributions.png — Non-IID Class Heterogeneity

```mermaid
pie title IID Baseline Distribution (Uniform 20% Assumption)
    "Normal" : 20
    "Botnet C2" : 20
    "DNS Exfiltration" : 20
    "SSH Brute Force" : 20
    "DoS / DDoS" : 20
```

```mermaid
pie title Org A (defender-a) — Local Observed Distribution
    "Normal" : 70
    "SSH Brute Force" : 20
    "DoS / DDoS" : 8
    "DNS Exfiltration" : 2
```

> **Note**: Botnet C2 is **0% (unobserved)** at Org A. Without Federated Learning, Org A suffers a 100% detection blindspot for Botnet threats.

```mermaid
pie title Org B (defender-b) — Local Observed Distribution
    "Normal" : 65
    "DoS / DDoS" : 25
    "Botnet C2" : 5
    "DNS Exfiltration" : 5
```

> **Note**: SSH Brute Force is **0% (unobserved)** at Org B. Federated aggregation transfers knowledge bidirectionally between Defender A and Defender B.

---

## 13. fig_telegram_alerting_workflow.png — Real-Time Alerting Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Orch as Orchestrator (orchestrate.py)
    participant Notif as Notification Engine (notifications.py)
    participant TeleAPI as Telegram Bot API (api.telegram.org)
    participant Dev as Researcher Mobile Client

    Orch->>Notif: trigger_notification(event="round_eval", metrics={acc: 0.9953, bwt: 0.000, botnet_f1: 0.6905})
    Note over Notif: Format Markdown payload with promotion gate status
    Notif->>TeleAPI: HTTPS POST /sendMessage (chat_id, text, parse_mode="Markdown")
    TeleAPI->>Dev: Push Notification
    Note over Dev: "🟢 Round 100/100 Complete<br/>Acc: 99.53% | Botnet Recall: 100% | BWT: 0.000<br/>Gate: ALL_PASS → Promoted to @champion"
```

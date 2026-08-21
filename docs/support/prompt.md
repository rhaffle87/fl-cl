# docs/support/prompt.md
# Image Generation Prompts for FL-CL Thesis Figures
#
# Each entry covers:
#   - What the figure must communicate
#   - A detailed AI image-generation prompt (use with Midjourney, DALL-E 3, Stable Diffusion, or Adobe Firefly)
#   - Highly relevant Google Image search queries to find real reference material
#   - Suggested academic figures from published papers (as search queries for Google Scholar/Semantic Scholar)
#
# Style baseline for ALL figures (prepend to any AI prompt):
#   "Clean academic technical diagram, white background, dark navy blue and orange color scheme,
#    monospace labels, IEEE paper figure style, 300 DPI, no shadows, vector-like precision"

---

## fig_proxmox_cluster.png
**Context**: Chapter 3.2 — Cluster Topology and Network Audit
**Role in paper**: Shows the physical 3-node Proxmox VE cluster layout: two Dell PowerEdge R630s (nodes `its` and `node2`) with LACP bonds and one Dell PowerEdge R760xs (node `pve`), all connected via an unmanaged switch, with two logical bridges (vmbr0 management, vmbr1 flat L2 data plane).

### AI Generation Prompt
```
Clean academic network infrastructure diagram, IEEE paper style, white background, dark navy and orange palette.
Show three server rack units labeled "its (R630, LACP bond0)", "node2 (R630, LACP bond0)", "pve (R760xs)".
Each server has two network ports: one to a grey "Unmanaged Switch" (flat L2 data plane, vmbr1, 10.10.0.0/16)
and one to a separate "Management Switch" (vmbr0, 192.168.x.x).
Draw LACP bond symbols (two parallel lines) on the its and node2 data-plane links.
Label the data-plane switch "Flat L2 / vmbr1 — 10.10.0.0/16" and the management switch "OOB Management / vmbr0".
Include a small legend. Minimalist, no 3D perspective, vector-like linework.
```

### Google Image Search Queries
- `proxmox ve cluster physical network diagram`
- `proxmox three node cluster vmbr1 flat network topology`
- `dell poweredge rack server LACP bond network diagram`
- `proxmox cluster corosync network topology ieee diagram`

### Academic Figure Reference Searches (Google Scholar)
- `"proxmox" "federated learning" testbed topology figure`
- `"proxmox VE" "cluster" network "vmbr" diagram`

---

## fig_cnn_1d_architecture.png
**Context**: Chapter 6.1 — Neural Network Architectures (`model.py`)
**Role in paper**: Diagrams the CyberDefenseCNN architecture: input 32-dim vector → unsqueeze to (1,32) → Conv1d(1→16, k=3) → ReLU → MaxPool1d(2) → Conv1d(16→32, k=3) → ReLU → MaxPool1d(2) → Flatten → FC(64) → ReLU → Dropout(0.2) → FC(5 classes).

### AI Generation Prompt
```
Clean academic neural network architecture diagram, IEEE paper style, white background, navy and orange.
Show a 1D Convolutional Neural Network for tabular/sequential input classification.
Left side: a horizontal bar labeled "Input: 32-dim ETA feature vector".
Then: Unsqueeze layer (add channel dim), Conv1d block (filters=16, kernel=3, padding=1) with orange activation bars,
ReLU activation arrow, MaxPool1d(2) compression block,
second Conv1d block (filters=32, kernel=3) with deeper orange, ReLU, MaxPool1d(2),
Flatten layer (grey), Fully Connected (64 neurons, green), Dropout(p=0.2) node (dashed border),
final FC output layer (5 neurons, labeled: Normal / Botnet / Exfiltration / BruteForce / DoS).
Show feature map width shrinking across pooling layers. Label all kernel sizes and channel counts.
Horizontal left-to-right flow. Minimalist, vector precision.
```

### Google Image Search Queries
- `1D CNN architecture diagram network intrusion detection`
- `Conv1d MaxPool1d neural network architecture visualization`
- `1D convolutional neural network tabular data classification`
- `CyberDefense 1D CNN encrypted traffic classification architecture`

### Academic Figure Reference Searches
- `"1D-CNN" "intrusion detection" architecture figure`
- `"Conv1d" "network traffic" classification diagram`
- `"1D convolutional" "ETA" "encrypted traffic" architecture`

---

## fig_mlp_architecture.png
**Context**: Chapter 6.1 — Multi-Layer Perceptron (CyberDefenseNet)
**Role in paper**: Diagrams the baseline MLP: Input(32) → FC(64) → ReLU → Dropout(0.2) → FC(32) → ReLU → FC(5). Shows neuron counts, activation types, and 5 output class labels.

### AI Generation Prompt
```
Clean academic feedforward neural network diagram, IEEE paper style, white background, navy and orange palette.
Show a Multi-Layer Perceptron with 4 layers arranged left to right:
- Input layer: 32 neurons (small circles, grey), labeled "32-dim ETA Features"
- Hidden layer 1: 64 neurons (orange circles), labeled "FC(64) + ReLU + Dropout(0.2)"
- Hidden layer 2: 32 neurons (lighter orange circles), labeled "FC(32) + ReLU"
- Output layer: 5 neurons (navy circles), labeled with class names below each:
  "Normal", "Botnet", "Exfil", "BruteForce", "DoS"
Draw connecting lines between layers (not every connection, use representative fan-out arrows).
Add small boxes next to each hidden layer noting the activation function.
Clean, minimal, academic. No 3D effects.
```

### Google Image Search Queries
- `feedforward neural network architecture diagram 4 layers`
- `MLP multilayer perceptron classification architecture`
- `neural network intrusion detection system diagram layers`

### Academic Figure Reference Searches
- `"MLP" "intrusion detection" "architecture" figure IEEE`
- `"feedforward" "network traffic classification" layer diagram`

---

## fig_transformer_architecture.png
**Context**: Chapter 6.1 — Transformer Classifier (CyberDefenseTransformer)
**Role in paper**: Diagrams the Transformer backbone: Input(32) → Reshape to (8 tokens × 4 dim) → Linear projection (4→32) + Positional Encoding → TransformerEncoder (nhead=4, 2 layers, FF=64) → Global Average Pooling → FC(32) → ReLU → Dropout(0.1) → FC(5 classes).

### AI Generation Prompt
```
Clean academic Transformer architecture diagram for tabular data classification, IEEE paper style,
white background, navy and orange palette.
Left: Input box "32-dim feature vector". Arrow to "Reshape: 8 tokens × 4 dim" block.
Then: "Linear Projection (4→32)" block with "⊕ Positional Encoding" annotation (sinusoidal wave icon).
Then: A stacked Transformer Encoder block showing 2 identical sub-layers, each with:
  - Multi-Head Self-Attention (nhead=4) box
  - Add & Norm (layer norm) residual connection
  - Feed-Forward Network (dim=64) box
  - Add & Norm residual connection
Show sequence dimension (8 tokens) on the left axis.
Then: "Global Average Pooling (mean over tokens)" → FC(32) → ReLU → Dropout(0.1) → FC(5 output classes).
Right-side output labeled with 5 threat classes. Compact, vector-like, academic.
```

### Google Image Search Queries
- `transformer encoder architecture diagram classification`
- `transformer tabular data classification architecture`
- `self-attention encoder multi-head network diagram`
- `vision transformer ViT architecture adapted tabular`

### Academic Figure Reference Searches
- `"Transformer" "network intrusion detection" architecture figure`
- `"self-attention" "encrypted traffic" classifier diagram`
- `"TabTransformer" "tabular" classification architecture`

---

## fig_avalanche_cl_framework.png
**Context**: Chapter 2.3 — Continual Learning and Chapter 6.2 — CL Strategy
**Role in paper**: Shows how Avalanche wraps PyTorch models: the Experience stream (sequential attack tasks), the CL strategy (EWC or GEM), the plugin system (evaluation plugins, loggers), and how Avalanche coordinates the train-evaluate-log loop. Shows the data flow: Task_1 → EWC → Task_2 → EWC + penalty → … → Task_N.

### AI Generation Prompt
```
Clean academic software architecture diagram for a Continual Learning framework, IEEE paper style,
white background, navy and teal palette.
Show a pipeline from left to right with labeled blocks:
1. "Stream of Experiences" (5 boxes labeled Task_1 to Task_5, representing attack classes)
2. "Avalanche CL Strategy" center block containing two sub-blocks:
   - "EWC Plugin: Fisher penalty on important weights"
   - "GEM Plugin: Episodic memory buffer M_k, QP gradient projection"
3. "PyTorch Model" block (CyberDefenseNet) receiving strategy outputs
4. "Evaluation Plugins" block logging BWT, accuracy, loss per task
5. "Logger" block outputting to MLflow and TensorBoard
Show arrows: task data → strategy → model → metrics → logger.
Draw a memory buffer icon (stack of rows) for GEM.
Use task color gradient (lightest to darkest = Task_1 to Task_5) to show sequential learning.
Academic, vector-like, no gradients or 3D.
```

### Google Image Search Queries
- `Avalanche continual learning framework architecture diagram`
- `continual learning experience stream EWC GEM framework`
- `catastrophic forgetting mitigation pipeline diagram`
- `sequential task learning neural network framework`

### Academic Figure Reference Searches
- `"Avalanche" "continual learning" framework architecture`
- `"EWC" "GEM" "continual learning" comparison diagram`
- `Lomonaco Avalanche framework figure`

---

## fig_ewc_fisher_collapse.png
**Context**: Chapter 9.2.1 — Mathematical Collapse of EWC Under Sparse Threat Windows
**Role in paper**: Visualizes why EWC fails for Botnet detection. Two bar charts or a heatmap: left shows the very imbalanced class distribution (Normal: ~2000 samples, Botnet: ~10-25 samples), right shows the resulting Fisher Information Matrix diagonal — F_Normal is huge, F_Botnet collapses to near zero. A caption arrow from "F_Botnet ≈ 0 → weights drift freely → BWT = -0.8544".

### AI Generation Prompt
```
Two-panel academic figure, IEEE paper style, white background, navy and red palette.
Left panel title: "Class Sample Distribution (Per Round)".
Horizontal bar chart: Normal=2000 (navy), SSH=~50 (orange), DoS=~100 (orange),
Botnet=~12 (red, very short bar, labeled "~12 samples"), Exfiltration=~30 (orange).
Right panel title: "Fisher Information Matrix Diagonal (F_i)".
Same classes on Y-axis. Horizontal bars: Normal has huge value (extends to edge, navy),
all others are moderate, Botnet has a nearly invisible near-zero bar (red, dotted outline),
labeled "F_Botnet ≈ 0 → weights unprotected → forgetting".
Add annotation text in red: "EWC penalty vanishes for Botnet → BWT = -0.8544".
Minimalist, academic, vector precision.
```

### Google Image Search Queries
- `EWC elastic weight consolidation Fisher information matrix visualization`
- `catastrophic forgetting class imbalance Fisher diagonal`
- `Fisher information matrix diagonal neural network heatmap`
- `EWC failure sparse class intrusion detection`

### Academic Figure Reference Searches
- `"Fisher information" "catastrophic forgetting" "imbalanced" visualization`
- `"EWC" "elastic weight consolidation" "Fisher" collapse figure`
- Kirkpatrick et al. 2017 EWC paper figure

---

## fig_fedavg_vs_trimmedmean.png
**Context**: Chapter 9.3 — Multi-Aggregator Byzantine Robustness Suite
**Role in paper**: Side-by-side comparison of FedAvg vs. TrimmedMean under poisoning. Shows how FedAvg naively includes poisoned gradients (pulling the global model toward a bad direction), while TrimmedMean sorts and trims outlier updates before averaging.

### AI Generation Prompt
```
Two-panel comparison diagram, IEEE paper style, white background, navy/orange vs red palette.
Left panel labeled "FedAvg (Standard Aggregation)":
  - 5 client arrows converging to an aggregator
  - One arrow colored red (labeled "Poisoned Client — 20% label flip")
  - The resulting averaged gradient vector is pulled toward the red poisoned direction
  - Red dashed circle around the final result, labeled "Model compromised: 88.2% accuracy"
Right panel labeled "TrimmedMean (β=0.10)":
  - Same 5 client arrows, red one visible
  - TrimmedMean box shows sorted weight values with the top/bottom 10% clipped (shown as X marks)
  - The resulting average excludes outlier, points in correct direction
  - Green circle labeled "Resilient: 95.9% accuracy, 100% Botnet recall"
Below both panels: a number line showing sorted aggregation values with trim boundaries marked.
Clean, vector-like, academic.
```

### Google Image Search Queries
- `federated learning Byzantine robustness FedAvg TrimmedMean comparison`
- `robust aggregation federated learning poisoning attack diagram`
- `TrimmedMean aggregation Byzantine tolerance illustration`
- `federated learning poisoning defense visualization`

### Academic Figure Reference Searches
- `"TrimmedMean" "Byzantine" "federated learning" aggregation figure`
- `"robust aggregation" "federated" comparison diagram`
- Blanchard et al. Machine Teaching Byzantine tolerance figure
- `"Krum" "TrimmedMean" "FedAvg" Byzantine comparison`

---

## fig_continual_bwt_matrix.png
**Context**: Chapter 9.2 — Continual Learning Analysis, BWT Results
**Role in paper**: A matrix or heatmap showing per-class Backward Transfer (BWT) scores across experiments: EWC baseline vs. GEM. Rows = classes (Normal, Botnet, SSH, DoS, Exfil), columns = experiment track. Colors encode BWT value (red = severe forgetting, green = no forgetting, blue = slight improvement).

### AI Generation Prompt
```
Academic heatmap matrix figure, IEEE paper style, white background, red-to-green diverging colormap.
Title: "Per-Class Backward Transfer (BWT) Across Experiment Tracks".
Y-axis (rows): 5 threat classes — Normal, Botnet, SSH Brute Force, DoS, DNS Exfiltration.
X-axis (columns): 4 experiment tracks — "EWC Baseline", "EWC 50% Dropout", "GEM (s=0.5)", "GEM Tuned (s=0.2)".
Fill each cell with a color value:
  - Normal: all tracks green (BWT ≈ 0.000 to -0.014)
  - Botnet: EWC Baseline = deep red (BWT = -0.8544), EWC Dropout = red (-0.7751),
            GEM s=0.5 = light green (0.00, 100% recall), GEM Tuned = green (0.00)
  - SSH/DoS/Exfil: all tracks light green to white (BWT ≈ 0.000)
Show numerical values inside each cell. Add a colorbar labeled "BWT value (lower is worse)".
Clean academic layout, no 3D.
```

### Google Image Search Queries
- `backward transfer matrix continual learning heatmap`
- `BWT per-task matrix forgetting evaluation`
- `continual learning evaluation matrix intrusion detection`
- `catastrophic forgetting per-class matrix visualization`

### Academic Figure Reference Searches
- `"backward transfer" "continual learning" evaluation matrix figure`
- `"BWT" "per-class" forgetting heatmap`
- Lopez-Paz GEM 2017 BWT evaluation table/figure

---

## fig_dp_sgd_noise.png
**Context**: Chapter 9.6 — Differential Privacy Noise Sensitivity Curve
**Role in paper**: A line chart showing classification accuracy (or F1-score) vs. DP noise multiplier σ ∈ {0.00, 0.05, 0.10, 0.15, 0.20, 0.30}. One line per class (5 lines). Shows that Normal/Exfil/BruteForce/DoS lines are nearly flat (resilient), while the Botnet line degrades more steeply as σ increases. Horizontal dashed line marks the promotion gate threshold.

### AI Generation Prompt
```
Academic line chart figure, IEEE paper style, white background, distinct color per class.
X-axis: "DP Noise Multiplier σ" with values 0.00, 0.05, 0.10, 0.15, 0.20, 0.30.
Y-axis: "F1-Score" from 0.60 to 1.00.
Five lines:
  - Normal (navy): starts at 0.9979, barely drops to 0.9950 at σ=0.30 (nearly flat)
  - Exfiltration (teal): starts at 0.9992, drops to 0.9960 (nearly flat)
  - BruteForce (green): starts at 0.9943, drops to 0.9880 (nearly flat)
  - DoS (orange): starts at 0.9815, drops to 0.9540 (slight slope)
  - Botnet (red, dashed): starts at 0.7119 at σ=0.00, drops to 0.6450 at σ=0.30 (steeper)
Add a horizontal dashed grey line at F1=0.60 labeled "Promotion Gate Threshold".
Add a vertical dashed line at σ=0.20 labeled "Production Deployment σ: 99.5% accuracy retained".
Add markers (circles) at each data point. Clean legend. Academic.
```

### Google Image Search Queries
- `differential privacy noise multiplier accuracy tradeoff curve`
- `DP-SGD privacy utility tradeoff line chart`
- `Gaussian noise sigma accuracy federated learning chart`
- `differential privacy F1 score sensitivity curve intrusion detection`

### Academic Figure Reference Searches
- `"differential privacy" "accuracy" "noise multiplier" sensitivity curve federated`
- `"DP-SGD" "Opacus" privacy utility tradeoff figure`
- Abadi et al. 2016 DP-SGD figure
- `"Gaussian mechanism" "epsilon delta" "F1" intrusion detection`

---

## fig_int8_quantization.png
**Context**: Chapter 9.4 — Multi-Runtime Hardware Inference Benchmark
**Role in paper**: Bar chart or grouped chart comparing model memory footprint and throughput under FP32, INT8 Dynamic Quantization, and ONNX Runtime for all three backbone architectures. Highlights that ONNX Runtime gives 3.88x speedup for CNN at batch=1, while INT8 alone on edge batches causes 0.56x overhead.

### AI Generation Prompt
```
Grouped bar chart, IEEE paper style, white background, three color groups (navy=FP32, orange=INT8, teal=ONNX Runtime).
Title: "Model Inference Throughput: FP32 vs INT8 vs ONNX Runtime".
X-axis: 3 backbone models — "MLP (CyberDefenseNet)", "1D-CNN (CyberDefenseCNN)", "Transformer".
Y-axis (left): "Throughput (flows/sec)" with values up to 200,000.
For each model, 3 bars side by side (FP32, INT8, ONNX).
Values (approx, from batch=16):
  - MLP: FP32=100,789, INT8=~56,000, ONNX=419,646
  - CNN: FP32=14,624, INT8=~9,000, ONNX=140,940
  - Transformer: FP32=17,742, INT8=~11,000, ONNX=16,035
Add small text above ONNX bars: "4.16x" for MLP, "9.64x" for CNN, "0.90x" for Transformer.
Add a second Y-axis (right) for "Memory Footprint (KB)" shown as horizontal dashes:
  - MLP: FP32=17KB, INT8=9KB
  - CNN: FP32=70KB, INT8=46KB
Include a legend. Clean, academic, no 3D.
```

### Google Image Search Queries
- `INT8 quantization throughput comparison bar chart neural network`
- `model quantization accuracy latency tradeoff visualization`
- `ONNX runtime vs PyTorch inference benchmark chart`
- `dynamic quantization speedup edge inference benchmark`

### Academic Figure Reference Searches
- `"INT8 quantization" "inference" throughput comparison figure`
- `"ONNX Runtime" "PyTorch" "latency" benchmark neural network`
- `"model compression" "quantization" IDS inference benchmark`

---

## fig_mlflow_tracking_dashboard.png
**Context**: Chapter 8.4 — MLOps Observability Stack and Model Registry
**Role in paper**: A schematic or mock-up of the MLflow tracking dashboard as used in this project. Shows: experiment run list (left column), per-round metric curves (accuracy, loss, BWT), a confusion matrix heatmap logged as artifact, and the Model Registry pane showing versions with `champion` and `challenger` aliases.

### AI Generation Prompt
```
Screenshot-style mockup of an MLflow experiment tracking dashboard, IEEE paper style diagram version,
white background with light grey panels, navy and orange highlights.
Left panel: "Experiment Runs" list table with columns Run ID, Status, Accuracy, Loss, BWT.
  Rows: run_v20 (99.72%, champion), run_v33 (99.45%, gem-v33), run_v35 (99.53%, champion).
Center panel: Two line charts stacked:
  Top: "Global Accuracy per Round" (X=round 1-100, Y=99.0%-99.9%), navy line converging.
  Bottom: "Training Loss per Round" (X=round 1-100, Y=0.00-0.50), orange line decreasing.
Right panel: "Model Registry" pane showing:
  CyberDefenseCNN v35 — alias: champion (green badge)
  CyberDefenseCNN v34 — alias: gem-v34 (blue badge)
  CyberDefenseCNN v20 — alias: baseline-r100 (grey badge)
Add small 5x5 confusion matrix thumbnail (heatmap) at bottom right.
Clean mockup diagram, not a real screenshot. Labeled clearly for academic publication.
```

### Google Image Search Queries
- `MLflow experiment tracking dashboard model registry`
- `MLflow runs comparison accuracy loss chart`
- `MLflow model registry champion alias screenshot`
- `MLOps experiment tracking federated learning dashboard`

### Academic Figure Reference Searches
- `"MLflow" "federated learning" "model registry" figure`
- `"MLOps" "experiment tracking" "continual learning" dashboard`
- `"model registry" "champion" "production" MLflow IDS`

---

## fig_non_iid_distributions.png
**Context**: Chapter 2.4 / Chapter 10.3 — Non-IID Data Heterogeneity
**Role in paper**: Shows the fundamental challenge of Non-IID (non-independently and identically distributed) data in federated learning. Two or three side-by-side pie/bar charts showing different class distributions per organization: Org A sees mostly SSH + Normal, Org B sees mostly DoS + Normal, neither has seen Botnet. Contrasted with the IID assumption (uniform distribution).

### AI Generation Prompt
```
Three-panel comparison figure, IEEE paper style, white background.
Title: "Non-IID Data Heterogeneity in Federated Intrusion Detection".
Left panel titled "IID Assumption (Ideal)": pie chart with 5 equal 20% slices, one color each:
  Normal (navy), Botnet (red), Exfiltration (orange), BruteForce (green), DoS (teal).
Center panel titled "Org A (defender-a) — Actual Distribution":
  Horizontal bar chart. Normal=70%, SSH BruteForce=20%, DoS=8%, Exfiltration=2%, Botnet=0%.
  Botnet bar is absent or ~0 with a "Not observed" label.
Right panel titled "Org B (defender-b) — Actual Distribution":
  Normal=65%, DoS=25%, Botnet=5%, Exfiltration=5%, SSH=0%.
Add a label below: "Without FL: each org misses attack classes it has not observed locally."
Then a green arrow pointing right: "With FL Aggregation: knowledge shared across orgs."
Clean academic, vector-like, no 3D.
```

### Google Image Search Queries
- `non-IID federated learning data heterogeneity distribution`
- `federated learning class imbalance non-IID data distribution visualization`
- `IID vs non-IID federated learning comparison chart`
- `heterogeneous data distribution federated intrusion detection`

### Academic Figure Reference Searches
- `"non-IID" "federated learning" "data heterogeneity" figure`
- `"heterogeneous" "class distribution" "federated" intrusion detection diagram`
- McMahan et al. 2017 Communication-Efficient Federated Learning non-IID figure

---

## fig_telegram_alerting_workflow.png
**Context**: Chapter 8 — Observability Stack
**Role in paper**: Diagrams the automated Telegram notification pipeline triggered by the orchestrator (`src/notifications.py`). Shows: experiment event (round complete / gate passed / champion promoted) → orchestrator → notifications.py → Telegram Bot API → researcher's phone. Includes the types of messages sent (accuracy, BWT, promotion status).

### AI Generation Prompt
```
Clean technical workflow diagram, IEEE paper style, white background, navy and green palette.
Title: "Automated Telegram Experiment Notification Pipeline".
Sequence from left to right:
1. Box: "Orchestrator (orchestrate.py)" — labeled "Training Round Complete / Gate Evaluated"
2. Arrow labeled "trigger_notification(event, metrics)"
3. Box: "notifications.py" — containing: "Format message: round, accuracy, BWT, gate status"
4. Arrow labeled "HTTPS POST"
5. Box: "Telegram Bot API (api.telegram.org)" — cloud icon, green
6. Arrow labeled "Push notification"
7. Smartphone icon labeled "Researcher Mobile" showing a sample message bubble:
   "Round 51/100 | Acc: 99.88% | Loss: 0.0257 | BWT_Botnet: -0.854 | Gate: PASS | alias: champion"
Add small icons: gear (orchestrator), code file (notifications.py), cloud (API), phone (researcher).
Clean, flat, academic, no perspective distortion.
```

### Google Image Search Queries
- `Telegram bot API notification workflow diagram`
- `automated alerting pipeline machine learning experiment`
- `MLOps notification webhook diagram telegram`
- `experiment monitoring notification system architecture`

### Academic Figure Reference Searches
- `"Telegram" "experiment monitoring" "notification" federated learning figure`
- `"automated alerting" "machine learning" "pipeline" diagram`

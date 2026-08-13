# FL-CL Testbed Execution Workflow

This document outlines the ideal end-to-end workflow for setting up and running Federated Continual Learning (FL-CL) experiments on the Proxmox heterogeneous cluster. It serves as a guide to the chronological execution sequence driven by the `src/orchestrate.py` master controller.

## 1. Concept & Scope

The objective of this architecture is to seamlessly merge **Continual Learning** (preventing catastrophic forgetting on sequential cyber threats) with **Federated Learning** (allowing multiple organizations to collaboratively improve a model without sharing raw PCAP data).

The orchestration unifies these components:
- **Networking**: Target VMs producing traffic, mirrored via `tc` to Defender VMs.
- **Data Pipeline**: NFStream converts raw encrypted packet streams to ETA feature tensors.
- **FL-CL Engine**: Avalanche wraps PyTorch models with EWC, and Flower bridges local CL across distributed client nodes.

## 2. Pre-Flight Phase: Infrastructure & Validation

Before launching training, the orchestrator validates the environment to prevent runtime crashes during multi-hour distributed training runs.

### A. Flat L2 Connectivity
All nodes reside on a flat `10.10.0.0/16` subnet to bypass physical switch VLAN-trunking restrictions. The orchestrator ensures that:
- Defender VMs (e.g., `10.10.130.11`) can reach the Aggregator LXC (`10.10.130.10`).
- The Traffic Generator (`10.10.140.10`) can target the target VMs.

### B. Configuration Loading
The orchestrator reads the core experiment configuration (e.g., `configs/experiments/baseline.yaml`). This config explicitly defines:
- **Federated parameters**: FL rounds, aggregation strategy (e.g., FedAvg).
- **Continual parameters**: EWC Lambda (regularization strength), CL task sequence.
- **Model parameters**: Architecture (MLP/CNN) and learning rates.

## 3. Execution Phase: The Training Loop

The `src/orchestrate.py` script sequences the deployment exactly in the order of the data pipeline:

### Step 1: Start Benign Targets
Target VMs (`target-a1`, `target-b1`) are seeded with simple HTTP servers (`simple_httpd.sh`). Meanwhile, Defender nodes send normal `curl` requests to these targets to generate continuous background 'Normal' class traffic.

### Step 2: Initialize NFStream
Defender nodes execute `extractor.py` to listen on their promiscuous mirror interfaces (`ens19`). Extracted flows are serialized into small CSV batches directly into the `/mnt/ramdisk/flows/` RAM disk to prevent disk I/O bottlenecks.

### Step 3: Start Global Aggregator
The central Flower server (`server.py`) starts on the aggregator node. It initializes the central MLflow tracking server to capture global evaluation metrics, waiting for client connections.

### Step 4: Traffic Generation
The centralized Traffic Generator sequentially launches attack campaigns using `attack_flow.py`:
1. `ssh` (SSH Brute Force)
2. `slowloris` (DoS)
3. `dns_exfil` (DNS Exfiltration)
4. `botnet` (C2 Beaconing)

This orchestrated sequential arrival of threats naturally enforces a Continual Learning class-incremental task sequence.

### Step 5: Data Quality Gate
Before allowing clients to train, an in-process gate checks the RAM disk distributions during `client.py`'s `fit()` loop. It calculates the Jensen-Shannon Divergence (JSD) against the baseline distribution. If the divergence exceeds the threshold, the client skips local training for that round and snapshots the drifted batch to persistent storage (`~/drift_snapshots/`) to prevent poisoning the FL round with bad data and enable offline debugging.

### Step 6: Start FL-CL Clients
With traffic flowing and quality verified, Defender VMs launch `client.py`. Each client dynamically reads the CSVs from the RAM disk, computes the EWC Fisher matrix on the new attack task, and updates the local PyTorch model before syncing gradients with the aggregator.

### Step 7: Model Serving & A/B Testing
When the aggregation round completes and the global model passes validation gates (F1, BWT, Comm Overhead), `server.py` registers the model in the MLflow Model Registry and promotes it to the `champion` alias. In production deployments, exported TorchScript models can be served (or shadow-deployed) to evaluate against live traffic without impacting the primary decision boundary.

## 4. Post-Flight Phase: Evaluation & MLOps

Once all FL rounds complete, the orchestrator triggers the evaluation and shutdown sequence:

### A. Visual Report Generation
The `tools/plot_metrics.py` script queries MLflow, generating visualization plots (Loss, BWT, global accuracy vs class accuracy) into the `exports/` directory. 

### B. Process Teardown
To maintain cluster hygiene, the orchestrator issues a `pkill` command to terminate all background Python, `nc`, and `tcpreplay` processes on remote VMs.

### C. Telegram Notification
A summarized report of the experiment's final metrics (Global Accuracy, Final BWT) is pushed to the researcher via Telegram.

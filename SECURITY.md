# Security, Privacy & Regulatory Compliance Policy

## 1. Secure-by-Design Architecture

The **FL-CL (Federated Learning - Continual Learning)** collaborative cyber defense system is engineered from the ground up to operate in high-threat, multi-tenant, and regulated enterprise environments. It enforces strict privacy preservation, cryptographic verification, and Byzantine adversarial resilience across every architectural layer.

---

## 2. Threat Model & Adversarial Surface

```
┌────────────────────────┬──────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Threat Category        │ Adversary Capability             │ Architectural Mitigation & Security Invariant          │
├────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. Data Exfiltration   │ Passive eavesdropping on transit │ Zero raw packet transmission; flows isolated in        │
│    & Interception      │ or physical network links.       │ ephemeral tmpfs RAMDisks; gRPC over TLS.               │
├────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 2. Gradient Inversion  │ Reconstructing raw network flows │ Client-side DP-SGD (C=1.0, sigma=0.30); coordinate     │
│    (Model Inversion)   │ from shared weight updates.      │ aggregation over batched mini-updates.                 │
├────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 3. Byzantine Poisoning │ Compromised defender nodes flip  │ Robust Aggregation: TrimmedMean (beta=0.10), FedMedian,│
│    & Gradient Attacks  │ labels (0->4) or flip signs.     │ and Krum neutralize malicious outlier updates.         │
├────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 4. NaN / Inf Injection │ Malicious floating point corrupts│ Aggregator NaN/Inf guard sanitizes perturbed weight    │
│    Exploits            │ server-side aggregation.         │ entries to 0.0 prior to assembly.                      │
├────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 5. Supply Chain & Code │ Unauthorized tampering with model│ SHA-256 cryptographic dataset lineage graph, Git commit│
│    Drift Tampering     │ checkpoints or training flows.   │ hash tagging, and TorchScript dynamic compilation.     │
└────────────────────────┴──────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 3. Cryptographic & Privacy Controls

### A. Zero Raw Data Transmission (Data Minimization)
Raw packet captures and IP payloads **never leave the local defender node**. NFStream extracts 32 statistical flow features (packet counts, directional byte volumes, durations, PIAT distributions) directly into a volatile in-memory **tmpfs RAMDisk** (`/mnt/ramdisk/flows/`). Only privacy-preserving parameter weights ($\theta_t$) are synchronized across the network.

### B. Client-Side Differential Privacy (DP-SGD)
- **Gradient Clipping**: Bounded by maximum gradient norm $C = 1.0$ prior to momentum accumulation.
- **Calibrated Noise Multiplier**: $\sigma = 0.30$.
- **Formal Privacy Guarantee**: Under Moments Accountant analysis, $T=100$ rounds at $\delta = 10^{-5}$ yields a tight $(\epsilon \le 6.08)$ differential privacy guarantee, mathematically proving that individual network flow records cannot be reconstructed from global weights.

### C. Byzantine-Robust Aggregation
Aggregator supports coordinate-wise and distance-based secure aggregation:
- **`TrimmedMean` ($\beta=0.10$)**: Trims top/bottom $\beta$ fraction of extreme parameter updates per coordinate.
- **`FedMedian`**: Coordinate-wise median aggregation immune to arbitrary sign-flipping.
- **`Krum` / `MultiKrum`**: Selects candidate vectors minimizing Euclidean distance to $n - f - 2$ neighbors.

---

## 4. Statutory & Regulatory Compliance Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 LEGAL & REGULATORY COMPLIANCE VERIFICATION                                         │
├───────────────────────┬────────────────────────────────────────────┬───────────────────────────────────────────────┤
│ Statute / Framework   │ Legal / Regulatory Mandate                 │ FL-CL Architectural Implementation & Evidence │
├───────────────────────┼────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 1. UU PDP No. 27/2022 │ Strict prohibition of unauthorized transfer│ Zero Raw Flow Transmission: Raw network flows │
│    (Indonesia PDP)    │ of personal data outside authorized secure │ remain exclusively in local volatile tmpfs    │
│    Articles 65 & 66   │ jurisdiction boundaries.                   │ RAMDisks; only weight updates cross subnets.  │
├───────────────────────┼────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 2. GDPR (EU 2016/679) │ Article 5: Data Minimization & Purpose     │ DP-SGD (sigma=0.30, C=1.0) & ephemeral tmpfs  │
│    Articles 5, 25, 32 │ Article 25: Privacy by Design & Default   │ storage enforce cryptographic pseudonymization│
│                       │ Article 32: Security of Processing         │ and irreversibility of model weights.         │
├───────────────────────┼────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 3. NIST SP 800-94 /   │ Standards for Network Intrusion Detection  │ 32-Dimensional Statistical Flow Representation│
│    NIST SP 800-145    │ and Prevention Systems (IDPS); continuous  │ without payload inspection; per-class recall  │
│                       │ behavioral anomaly verification.           │ tracking and automated promotion gates.       │
├───────────────────────┼────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 4. MITRE ATT&CK       │ Standardized adversary tactic, technique,  │ Validated Threat Coverage:                    │
│    Enterprise Matrix  │ and procedure (TTP) categorization.        │ - T1498 (Network Denial of Service / Slowloris)│
│                       │                                            │ - T1110 (Brute Force / SSH Authentication)    │
│                       │                                            │ - T1048 (Exfiltration Over Alternative Port)  │
│                       │                                            │ - T1071 (Application Layer C2 Protocol Beacon)│
├───────────────────────┼────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 5. ISO/IEC 27001 /    │ Information Security & Privacy Information │ Cryptographic Provenance Lineage: SHA-256     │
│    ISO/IEC 27701      │ Management System (ISMS/PIMS) controls.    │ flow hashes, Git commit tags, MLflow audit log│
├───────────────────────┼────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 6. RFC 1035 / 793 /   │ Wire-level protocol compliance for DNS,    │ Dual-Engine Generator (--engine auto|kali)    │
│    RFC 7230 / 7540    │ TCP state machines, and HTTP transports.   │ generates valid RFC datagrams & TCP sessions. │
└───────────────────────┴────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 5. Vulnerability Disclosure & Incident Response

### Security Contacts
If you identify a potential security vulnerability, memory safety issue, or compliance deviation within the `fl-cl` codebase, please submit a private report to the project maintainers.

### Response SLA
- **Initial Acknowledgment**: Within 24 hours.
- **Triage & Remediation Plan**: Within 72 hours.
- **Coordinated Security Patch**: Released alongside automated verification regression tests in `tools/`.

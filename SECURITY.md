# Security Policy

## Secure-by-Design Commitment
This project adheres to strict Secure-by-Design principles to safeguard our Federated Continual Learning (FL-CL) infrastructure. We enforce the following security practices:
- **Zero Secrets in Source Control**: All API keys (e.g., Ollama proxy tokens, Telegram notification tokens), private SSH keys, and target credentials must never be committed to Git. They are managed dynamically using git-ignored `.env` configurations.
- **Dynamic Topology Configuration**: Node and host IP addresses are fully decoupled from logic. They are resolved at runtime via environment variables or loaded from local `configs/experiment.yaml` configurations.
- **Minimal Privilege & Isolation**: Virtual machines and containers are configured with the minimum required networking and permissions. Administrative access requires SSH keys with strict permission rules.

## Supported Versions
Only the latest release of the main branch is supported with security updates.

| Version | Supported |
| --- | --- |
| 1.0.x (Current) | :white_check_mark: |
| < 1.0.0 | :x: |

## Reporting a Vulnerability
If you discover a security vulnerability in this project, please report it immediately and privately rather than opening a public issue.

### Disclosure Process
1. Email your report to the project maintainers.
2. Include a detailed description of the vulnerability, steps to reproduce, and any proof-of-concept (PoC) code or logs.
3. You will receive an initial response acknowledging your report within 48 hours.
4. We will coordinate a timeline for a security patch prior to public disclosure.

Thank you for helping keep this project secure.

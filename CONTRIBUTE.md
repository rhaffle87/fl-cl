# Contributing Guidelines

Thank you for your interest in contributing to the Federated Continual Learning (FL-CL) Cyberdefense project! Please review the guidelines below to ensure a smooth development process.

## Code of Conduct & Secure Guidelines
- **Strictly No Secrets**: Never hardcode API keys, passwords, private SSH key paths, or static network IPs in any Python scripts, shell scripts, or configs. All settings must resolve through `.env` variables or YAML config variables.
- **Run Local Audits**: Before pushing any changes, run a local scan to ensure no credentials or debug configs are leaked.
- **Python Syntax Check**: Verify that all modified scripts compile without syntax errors:
  ```bash
  python -m py_compile src/**/*.py runs/*.py tools/*.py
  ```

## Development Workflow
1. **Fork and Clone**: Create a local copy of the repository.
2. **Environment Setup**:
   - Copy `.env.example` to `.env`.
   - Update the variables (e.g., `AGGREGATOR_HOST`, `SSH_KEY_PATH`, `TELEGRAM_BOT_TOKEN`) with your target configuration.
   - Create your local Python virtual environment:
     ```bash
     python -m venv venv
     source venv/bin/activate  # On Windows: .\venv\Scripts\activate
     pip install -r requirements.txt  # If applicable
     ```
3. **Branching**: Use descriptive branch names:
   - Features: `feature/your-feature-name`
   - Bugfixes: `bugfix/your-bugfix-name`
   - Security: `security/your-security-fix`
4. **Commit Messages**: Write clear, descriptive commit messages starting with semantic tags (e.g., `feat:`, `fix:`, `sec:`, `docs:`).

## Coding Standards
- **Style**: Adhere to PEP 8 standards for Python code.
- **Documentation**: Keep comments concise but descriptive. Document all function parameters and return types.
- **Robustness**: Ensure SSH operations have standard keep-alives and timeouts set to prevent administrative connection hangs.

We appreciate your contributions to keeping our federated cyberdefense stack secure and reliable!

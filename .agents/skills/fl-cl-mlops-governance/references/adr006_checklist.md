# ADR-006 Quality & Governance Checklist

## Mandatory Code Quality Rules

### 1. Docstrings & Headers
- Every file must begin with a docstring summarizing its role, inputs, outputs, and system interactions.
- Every public function and class method must specify parameter types and return type annotations.

### 2. Standard Path Manipulation
- All file manipulations must use `pathlib.Path` objects.
- String concatenation with `+` or raw `os.path.join` is prohibited.

### 3. Centralized Logging
- Production modules in `src/` must NOT use bare `print()` calls.
- Use `src/logger.py` (`setup_logger(__name__)`) to output structured JSON/rich console logs with appropriate levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

### 4. Mathematical Sanitization & Numerical Stability
- All tensor computations transmitted across gRPC or serialized to disk must pass through `torch.nan_to_num()` or `torch.clamp()`.
- Continual learning Fisher matrix inverses must use damping factor $\epsilon = 10^{-8}$ to prevent singular matrix division.

### 5. Ephemeral Data Isolation (Zero Persistence Mandate)
- Raw network packet captures and extracted tabular flow CSV/Parquet files must strictly reside in `/mnt/ramdisk/` (`tmpfs`).
- No raw traffic data may be saved to persistent block storage or git repositories.

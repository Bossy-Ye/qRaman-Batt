# QRaman-Batt
**Recipe-driven Raman QA for batteries: 2–5 windows → Green / Amber / Red.**

- **Recipe (JSON/JSONC):** expected bands (ν), tolerances (±tol), widths (σ), weights, and instrument profile.
- **Edge flow:** load recipe → cut 2–5 windows → constrained fit + classify (PEAK / DRIFTED / NOT-PEAK) → aggregate decision → log (with reason codes).
- **Bench:** classical RBF-SVM baseline now; QSVM kernel is a pluggable option later.

## Quick start
```bash
pip install -e .
pytest
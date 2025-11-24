# Raman → Fast Decisions (Quantum-Ready)

Edge app for turning a live Raman spectrum into **GREEN/AMBER/RED** with **reason codes** in ~1–2 minutes using **2–5 sentinel windows**.
- **Recipe** (JSON): expected bands + tolerances + instrument profile
- **Edge**: cut windows → fit/classify → aggregate → log
- **Bench**: classical RBF–SVM baseline; QSVM is a pluggable option later

### Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python edge/runner.py --recipe recipes/stationA-0.1.0.json --spectrum data/run001.csv --out logs/001.json
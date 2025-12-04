# Quantum Benchmark Plan (QSVM & LR–VQE)

**Goal:** Keep quantum **optional**. Adopt only if it **beats a strong classical baseline** under the conditions that matter (low SNR, overlaps, drift) without breaking the 2-minute runtime budget.

**Reason:** LR–VQE can produce Raman-relevant polarizability-derivative tables when high-level DFT is too slow for the chemistry; QSVM’s fidelity kernel captures phase-level structure that boosts low-SNR/overlap accuracy and strengthens OOD checks.

---

## Reference roles (GOLD vs BASE vs Quantum)

- **GOLD:** Small, high-fidelity reference set (high-level DFT / CC / experiment) used **only for benchmarking** a handful of representative motifs.
- **BASE (archive-only):** Current operational tables (archive, vendor PDFs, low-level DFT) used in production today.
- **Quantum (LR–VQE):** Candidate generator of expected-bands tables for new/changed chemistries.

LR–VQE must:
1. **Match or beat BASE with respect to GOLD** on the benchmark panel (scientific sanity), and  
2. **Improve or match QC behaviour vs BASE** in the end-to-end pipeline for realistic recipes.

---

## Tasks (A, B, C)

### B — Window classifier: QSVM vs RBF-SVM

- **Data:** Windows around sentinel bands for three use cases:
  - Electrolyte QC: PF₆ (~745), EC (~717), POF₃ watch (870–900), CO₂ (~1388)
  - Interphase QC: Li₂CO₃ (~1090), Graphite G (~1580 anchor)
  - LFP QC: PO₄ (~950), PO₄ bend (~590)
- **Data Source:** To be decided.
- **Splits:** Station A1 local runs → train/val/test = 60/20/20 (stratified by band & class).
  - **Stress grid:** SNR ∈ {12, 8, 6, 4}, drift ∈ {0, ±5, ±10 cm⁻¹}, overlap ∈ {none, moderate, strong}.  
    The stress grid is chosen as a small matrix of test scenarios that combine the DOE factors at chosen levels. It lets us see where the system fails gracefully and pick sensible thresholds: band’s τ (confidence), κ_min (OOD similarity), and SNR_min.
- **Models:** 
  - Classical: RBF-SVM (γ via median heuristic + small grid; C grid-search).
  - Quantum: QSVM (fidelity kernel, 16–32 qubits, depth 1–2; Nyström rank *r*; SV cap *S*).
- **Metrics:**  
  - **Window-level:** accuracy, **F1 (peak)**, **F1 (drifted)**, **AUROC (OOD κ)**, **calibration** (ECE/Brier), **latency** (ms/window).  
  - **Sample-level:** **FAR/FRR** and latency.

---

### A — Expected-bands table: LR–VQE vs References

- **Targets:** Small/medium molecules or motifs relevant to the bands above (electrolyte species, carbonate/PO₄ motifs, graphitic fragment).
- **Reference roles:**
  - **GOLD:** High-level classical / experimental Raman for a small benchmark panel of motifs.
  - **BASE:** Existing archive / low-level DFT tables used in production; evaluated against the same GOLD where available.
  - **Quantum (LR–VQE):** New tables generated via LR–VQE.
- **Outputs compared:** 
  - **Peak positions:** MAE in cm⁻¹ **vs GOLD** on the benchmark panel (BASE and LR–VQE both measured against GOLD).
  - **Activity ordering:** Kendall/Spearman τ of relative band strengths **vs GOLD**.
  - **Widths:** qualitative check vs local FWHM; used as priors in QC fits.
- **Metrics:**  
  - **MAE(ν)** (cm⁻¹ vs GOLD on the benchmark panel),  
  - **τ(activity)** (rank correlation vs GOLD),  
  - **time-to-first-table** (wall-clock),  
  - **cloud cost**.

---

### C — End-to-end decision impact

- **Pipeline:** recipe → cut windows → (QSVM or RBF) → per-band rules → **Green/Amber/Red**.
- **Metrics:** **FAR** (false-accept), **FRR** (false-reject), **decision latency** (sample→decision), **% Amber**, and **reason-code coverage**.

---

## Success Criteria (gates to adopt quantum)

### Classifier: QSVM vs RBF-SVM

**QSVM must beat RBF-SVM** at the hard points:

- At **SNR 4–6** **and** with **moderate overlap**, QSVM shows:
  - **≥ 20% relative reduction** in window error rate, **or** **+0.05 absolute F1** on *peak* (≈ +5 percentage points),
  - **No latency blow-up**: ≤ 2× RBF per window and **≤ 2 min** per sample overall.
- **OOD guard (κ):** AUROC **≥ 0.90** on held-out odd cases (additives, aging, unusual baselines), with calibration (ECE/Brier) **no worse** than RBF-SVM.

If these conditions are not met, **use RBF-SVM** (same interface and downstream logic).

---

### LR–VQE: vs GOLD (calibration) and vs archive-only BASE (operational)

**LR–VQE must pass both:**

1. **Calibration gate (benchmark panel, vs GOLD):**
   - On bands we actually use:
     - **MAE(ν)\_Q ≤ MAE(ν)\_BASE** and **MAE(ν)\_Q ≤ 10 cm⁻¹** vs GOLD.
     - **τ(activity)\_Q ≥ τ(activity)\_BASE** and **τ(activity)\_Q ≥ 0.7** (activity ordering defensible).
   - **time-to-first-table\_Q ≤ 24 h** (including queueing) and practical cost.

2. **Operational gate (new/changed chemistry, vs archive-only BASE in pipeline C):**
   - When plugged into the full pipeline:
     - LR–VQE tables **reduce FRR by ≥ 0.5 percentage points at the same FAR**, or  
     - **Beat archive/DFT by ≥ 20% in MAE(ν)** on relevant bands (where ground truth or later GOLD is available).
   - End-to-end **FAR/FRR remain within targets**, and table turnaround stays **≤ 24 h**.

If these gates are not met → **stay with classical** (DFT/RBF/archive-only) and keep the interface identical.

---

## Fairness & Protocol

- **Same windows, same preprocessing** for RBF and QSVM.
- **Hyperparameter budget parity** (comparable search effort).
- **Shots & rank disclosure:** report QSVM shots per kernel element, Nyström rank *r*, and SV cap *S*.
- **Confidence calibration:** reliability diagrams (ECE/Brier) for both models.
- **Stats:** 5× repeats with different splits; report mean ± 95% CI; McNemar’s test on paired window errors.
- For LR–VQE vs BASE on the benchmark panel: report MAE(ν) and τ(activity) for both **relative to GOLD**.

---

## Targets (Benchmark Report)

### A — Expected-bands / reference table quality (vs GOLD on benchmark panel)

| Metric                  | Target                                                  | Rationale                                                                 |
|-------------------------|--------------------------------------------------------:|---------------------------------------------------------------------------|
| MAE_ν (cm⁻¹ vs GOLD)    | **≤ 4.0**                                               | ≤ ~½ of typical tol (8–10), so table error alone won’t flip PEAK↔DRIFTED. |
| Rank corr of intensity  | **≥ 0.70** (Spearman/Kendall)                           | Relative strengths must track reality for stable fits/RMSE.               |
| Turnaround              | **≤ 8 h (same day)**                                    | Recipe updates fit within a work shift.                                   |
| Adoption gate           | **Beats archive/DFT (BASE) by ≥20% MAE vs GOLD** *or* improves C-FRR by **≥0.5 pp** at same FAR | Justifies LR–VQE over classical seed. |

---

### B — Per-window classifier (test at SNR 4–6, moderate overlap)

| Metric                       | Target                       | Rationale                                      |
|------------------------------|-----------------------------:|-----------------------------------------------|
| Accuracy                     | **≥ 0.93**                   | Keeps window errors from dominating end-to-end. |
| F1_peak                      | **≥ 0.92**                   | Peak detection drives *must-have* passes.     |
| F1_drifted                   | **≥ 0.80**                   | Needed for clean Amber vs Remesure calls.     |
| κ-AUROC (OOD)                | **≥ 0.90**                   | Robust odd-window detection.                  |
| Latency/window (compute)     | **≤ 100 ms (CPU)** / **≤ 250 ms (QSVM remote)** | Fits the ≤2 min/sample budget with 2–5 windows. |

---

### C — End-to-end (2–5 windows per sample)

| Metric               | Target         | Rationale                          |
|----------------------|---------------:|------------------------------------|
| FAR (false accept)   | **≤ 0.5%**     | Avoid bad cells passing QA.        |
| FRR (false reject)   | **≤ 2.0%**     | Don’t over-reject good product.    |
| Latency/sample       | **≤ 120 s**    | “Minutes—not days” on the line.    |
| % Amber              | **≤ 10%**      | Re-measures stay manageable.       |
| Reason-code coverage | **100%**       | Every decision auditable.          |

---

## Consistency checks

- Worst case 5 windows × 250 ms compute = **1.25 s** compute → leaves ~**118 s** for acquisition/I/O, matching **≤120 s** total.  
- A’s **MAE_ν ≤ 4 cm⁻¹ vs GOLD** aligns with tol **8–10 cm⁻¹**, so table error alone won’t breach the **\|Δν\| ≤ tol** rule.  
- Adoption gate ties A → C: LR–VQE is used only if it **measurably** improves end-to-end decisions or table accuracy over the archive/DFT BASE.

---

## Runtime & Cost Envelope

- **Windows/sample:** 2–5; **points/window:** 32 (typ).
- **QSVM budget:** Nyström rank *r* (e.g., 24–64), SV cap *S* (≤ 64); shots chosen for ±0.02 kernel tolerance.
- **Edge time:** preprocessing + fit + kernel calls must fit the ~1–2 min sample budget (queueing excluded).
- **Fallback:** If queue/latency spikes → **RBF-SVM** with same inputs/outputs; decision logic unchanged.

---

## Reproducibility

- Fix seeds; log recipe + model hashes; export CSVs for all metrics.
- Keep a small **stress set** (synthetic noise/overlap/drift) in the repo to re-run B/C quickly.
- For LR–VQE, keep the benchmark panel definition (GOLD systems) and raw reference calculations versioned, so MAE_ν and τ(activity) are repeatable.
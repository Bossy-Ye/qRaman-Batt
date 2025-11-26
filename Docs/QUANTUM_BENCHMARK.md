# Quantum Benchmark Plan (QSVM & LR–VQE)

**Goal:** Keep quantum **optional**. Adopt only if it **beats a strong classical baseline** under the conditions that matter (low SNR, overlaps, drift) without breaking the 2-minute runtime budget.

**Reason:** LR–VQE can produce Raman-relevant polarizability-derivative tables when high-level DFT is too slow for the chemistry; QSVM’s fidelity kernel captures phase-level structure that boosts low-SNR/overlap accuracy and strengthens OOD checks.

---


## Tasks (A, B, C)

**B — Window classifier: QSVM vs RBF-SVM**
- **Data:** Windows around sentinel bands for three use cases:
  - Electrolyte QC: PF6 (~745), EC (~717), POF3 watch (870–900), CO2 (~1388)
  - Interphase QC: Li2CO3 (~1090), Graphite G (~1580 anchor)
  - LFP QC: PO4 (~950), PO4 bend (~590)
- **Data Source:** To be decided.
- **Splits:** Station A1 local runs → train/val/test = 60/20/20 (stratified by band & class).
  - **Stress grid:** SNR ∈ {12, 8, 6, 4}, drift ∈ {0, ±5, ±10 cm⁻¹}, overlap ∈ {none, moderate, strong}. 
  Stress grid is chosen so as a small matrix of test scenarios that combine the DOE factors at chosen 
  levels helping us probe easy. It tells us exactly where the system fails gracefully and pick sensible thresholds,
  band’s τ (confidence), κ_min (OOD similarity), and SNR_min.
- **Models:** 
  - Classical: RBF-SVM (γ via median heuristic + small grid; C grid-search).
  - Quantum: QSVM (fidelity kernel, 16–32 qubits, depth 1–2; Nyström rank r; SV cap S).
- **Metrics:** per-window **accuracy**, **F1 (peak)**, **F1 (drifted)**, **AUROC (OOD κ)**, and **latency** (ms/window).

**A — Expected-bands table: LR–VQE vs Classical References**
- **Targets:** Small/medium molecules or motifs relevant to the bands above (electrolyte species, carbonate/PO4 motifs).
- **Outputs compared:** 
  - **Peak positions** (MAE in cm⁻¹ vs trusted classical/archival),
  - **Activity ordering** (Kendall τ of relative band strengths),
  - **Widths** (qualitative check vs local FWHM; used as priors).
- **Metrics:** **MAE(ν)**, **τ(activity)**, **time-to-first-table** (wall-clock), **cloud cost**.

**C — End-to-end decision impact**
- **Pipeline:** recipe → cut windows → (QSVM or RBF) → per-band rules → **Green/Amber/Red**.
- **Metrics:** **FAR** (false-accept), **FRR** (false-reject), **decision latency** (sample→decision), **reason-code coverage**.

---

## Success Criteria (gates to adopt quantum)

**Classifier (QSVM) must beat RBF-SVM** at the hard points:
- At **SNR 4–6** **and** with **moderate overlap**, QSVM shows:
  - **≥ 20% relative reduction** in window error rate (or **+0.05 F1** on *peak*),
  - **No latency blow-up**: ≤ 2× RBF per window and **≤ 2 min** per sample overall.
- **OOD guard (κ)**: AUROC **≥ 0.90** on held-out odd cases (additives, aging, unusual baselines).

**LR–VQE must beat “archive-only” when new/changed chemistry appears:**
- **MAE(ν) ≤ 10 cm⁻¹** on the bands we actually use **or**
- **τ(activity) ≥ 0.7** so the weight ordering is defensible,
- **Table turnaround ≤ 24 h** (including queueing) and practical cost.

If these gates are not met → **stay with classical** (DFT/RBF) and keep the interface identical.

---

## Fairness & Protocol

- **Same windows, same preprocessing** for RBF and QSVM.
- **Hyperparameter budget parity** (comparable search effort).
- **Shots & rank disclosure**: report QSVM shots per kernel element, Nyström rank *r*, and SV cap *S*.
- **Confidence calibration:** reliability diagrams (ECE/Brier) for both models.
- **Stats:** 5× repeats with different splits; report mean ± 95% CI; McNemar’s test on paired window errors.

---

## Targets (Benchmark Report)

### A — Expected-bands / reference table quality
| Metric                  | Target                          | Rationale |
|-------------------------|--------------------------------:|-----------|
| MAE_ν (cm⁻¹)            | **≤ 4.0**                       | ≤ ~½ of typical tol (8–10), so table error won’t flip PEAK↔DRIFTED. |
| Rank corr of intensity  | **≥ 0.70** (Spearman)           | Relative strengths must track reality for stable fits/RMSE. |
| Turnaround              | **≤ 8 h (same day)**            | Recipe updates fit within a work shift. |
| Adoption gate           | **Beats archive/DFT by ≥20% MAE** *or* improves C-FRR by **≥0.5 pp** at same FAR | Justifies LR–VQE over classical seed. |

---

### B — Per-window classifier (test at SNR 4–6, moderate overlap)
| Metric        | Target                 | Rationale |
|---------------|-----------------------:|-----------|
| Accuracy      | **≥ 0.93**             | Keeps window errors from dominating end-to-end. |
| F1_peak       | **≥ 0.92**             | Peak detection drives *must-have* passes. |
| F1_drifted    | **≥ 0.80**             | Needed for clean Amber vs Remesure calls. |
| κ-AUROC (OOD) | **≥ 0.90**             | Robust odd-window detection. |
| Latency/window (compute) | **≤ 100 ms (CPU)** / **≤ 250 ms (QSVM remote)** | Fits the ≤2 min/sample budget with 2–5 windows. |

---

### C — End-to-end (2–5 windows per sample)
| Metric               | Target         | Rationale |
|----------------------|---------------:|-----------|
| FAR (false accept)   | **≤ 0.5%**     | Avoid bad cells passing QA. |
| FRR (false reject)   | **≤ 2.0%**     | Don’t over-reject good product. |
| Latency/sample       | **≤ 120 s**    | “Minutes—not days” on the line. |
| % Amber              | **≤ 10%**      | Re-measures stay manageable. |
| Reason-code coverage | **100%**       | Every decision auditable. |

---

### Consistency checks
- Worst case 5 windows × 250 ms compute = **1.25 s** compute → leaves ~**118 s** for acquisition/I/O, matching **≤120 s** total.  
- A’s **MAE_ν ≤ 4 cm⁻¹** aligns with tol **8–10 cm⁻¹**, so table error alone won’t breach the **|Δν| ≤ tol** rule.  
- Adoption gate ties A → C: LR–VQE is used only if it **measurably** improves end-to-end decisions or table accuracy.

## Runtime & Cost Envelope

- **Windows/sample:** 2–5; **points/window:** 32 (typ).
- **QSVM budget:** Nyström rank *r* (e.g., 24–64), SV cap *S* (≤ 64); shots chosen for ±0.02 kernel tolerance.
- **Edge time:** preprocessing + fit + kernel calls must fit the ~1–2 min sample budget (queueing excluded).
- **Fallback:** If queue/latency spikes → **RBF-SVM** with same inputs/outputs; decision logic unchanged.

---

## Reproducibility

- Fix seeds; log recipe + model hashes; export CSVs for all metrics.
- Keep a small **stress set** (synthetic noise/overlap/drift) in the repo to re-run B/C quickly.
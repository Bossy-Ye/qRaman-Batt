# THRESHOLDS_GUIDE.md
**Author:** Boshuai Ye · **Email:** boshuai.ye@oulu.fi · **Date:** 2025-11-25  
**Scope:** How to set recipe thresholds from local data so decisions are fast, consistent, and auditable.

---

## 0) Quick idea
We make **Green / Amber / Red** calls from 2–5 *sentinel bands* by enforcing fixed per-band limits:

- **Shift:** \|Δν\| ≤ **tol**  
- **Fit error:** **RMSE** ≤ **ε**  
- **Signal quality:** **SNR** ≥ **SNR_min**  
- **Classifier trust:** **confidence** ≥ **τ**, **OOD similarity** ≥ **κ_min**

Then aggregate by **role**: all *must-have* satisfied and no *must-not* detected → **Green**; any *must-not* or unresolved overlap → **Red**; otherwise **Amber**. (Do anchor auto-alignment first.)

---

## 1) Inputs we need (small data collection)
- **Instrument resolution** `res` (cm⁻¹) for the Raman station.  
- **Local calibration runs:** 10–20 quick, *known-good* measurements with anchor auto-alignment on.  
- **Tiny DOE** (1 day): a few repeats across temperature / SoC (or cycle state) / laser power to quantify real-world drift.

---

## 2) How to set each number

### A) Band tolerance **tolₖ** (cm⁻¹)
Goal: allow normal instrument + chemistry drift, reject real mismatches.

1. From 10–20 local runs (after anchor auto-align), compute **Δνₖ = ν_obs − ν_recipe** for the band.  
2. Take **P95(|Δν|ₗₒcₐₗ,ₖ)** = 95th percentile of |Δνₖ|.  
3. From the mini-DOE, measure extra drift margins (pick what matters for our use case) and sum them:
   - Temperature: **m_T = |dν/dT| · ΔT_max**  
   - SoC / cycling: **m_SoC** = P95 of added |Δν| across states  
   - Laser power change: **m_P** = P95 of added |Δν|  
   - Composition tweak (e.g., moisture): **m_comp** = P95 of added |Δν|  
   - **m_chem = m_T + m_SoC + m_P + m_comp**
4. Set  
   **tolₖ = max( 5×res , P95(|Δν|ₗₒcₐₗ,ₖ) + m_chem )** → round up to a clean integer.

> If DOE not ready yet: start with **m_chem = max(3×res, 0.3×P95(|Δν|ₗₒcₐₗ))**, then replace with measured values.

---

### B) Band width **σₖ** (cm⁻¹)
- Fit peaks in our 10–20 local runs, get **(Full Width at Half Maximum) FWHM** per band.  
- Convert with **σ = FWHM / (2√(2 ln 2)) ≈ FWHM / 2.355**.  
- Take **median σ** across runs; round to nearest integer.

---

### C) Fit error **ε (RMSE)** (normalized)
- Normalize windows (unit L2 or robust z-score).  
- Fit each calibration window with our constrained lineshape; compute **RMSE**.  
- Set **ε** to the **P95** of those RMSE values, then add a small safety margin (e.g., +0.01).  
- Typical starting point: **ε ≈ 0.05–0.07**.

---

### D) Classifier confidence **τ**
- Train the baseline classifier (classical RBF-SVM or QSVM) on noisy/drifted *stress* windows (simulate low SNR, small shifts, overlaps).  
- Sweep the decision threshold and plot validation accuracy vs. threshold.  
- Pick **τ** where false accepts (bad windows marked “peak”) stay below our target (e.g., FAR ≤ 0.5%).  
- Typical starting point: **τ ≈ 0.60–0.70**.

---

### E) OOD similarity **κ_min**
- Build a small reference bank per band (templates from local “good” windows; optionally LR–VQE template).  
- Compute a kernel similarity (quantum fidelity or classical RBF) from a new window to the bank; average the top-k matches → **κ**.  
- Choose **κ_min** from an ROC curve that separates **in-distribution** vs **out-of-distribution** windows (hold out some “odd” cases).  
- Typical starting point: **κ_min ≈ 0.60** with target **AUROC ≥ 0.90**. Start with 0.60, then re-fit it from our local data, pick **κ_min** that hits the target target **AUROC ≥ 0.90**.

---

### F) Signal-to-Noise **SNR_min**
- Define SNR as **peak height / baseline-noise std** in the window.  
- From local runs at “normal” and “low” SNR, find the lowest SNR where fits remain reliable (RMSE ≤ ε, confidence ≥ τ).  
- Set **SNR_min** just above that elbow. Typical: **SNR_min ≈ 5–8**.
- Temporarily use SNR_min = 6, then recompute after the first 10-20 runs.

---

## 3) One tiny numeric example (illustration)
- `res = 1.0 cm⁻¹` → `5×res = 5`  
- Local P95(|Δν|) for PO₄ 950 band: **3.4**  
- DOE: `m_T = 0.7`, `m_SoC = 1.9`, `m_P = 0.6` → `m_chem = 3.2`  
- **tol = max(5, 3.4 + 3.2) = 6.6 → round to 8 cm⁻¹**  
- Median FWHM ≈ 16 → **σ ≈ 16 / 2.355 ≈ 6.8 → 7 cm⁻¹**  
- From validation curves: **ε = 0.06**, **τ = 0.65**, **κ_min = 0.60**, **SNR_min = 6**.

---

## 4) Maintenance & versioning
- **When to update the recipe:**  
  - After anchor correction, median |Δνₖ| exceeds **0.5·tolₖ** across the last 10 “good” samples; **or**  
  - **κ** (OOD) falls below **κ_min** on **≥2** sentinel bands in **≥5** samples; **or**  
  - Chemistry/process changes (new solvent/additive/temp regime).
- **What to do:** Refresh expected band centers/widths (archives → DFT → LR–VQE if needed), re-measure 5–10 fresh runs, recompute tol/σ/ε/τ/κ_min, **bump version**.

---

## 5) Summary defaults (first install, then tighten)

| Parameter | Typical start | How to finalize |
|---|---|---|
| `tol_k`  | `max(5×res, P95Δν_local,k) + m_chem` | From local + DOE |
| `σ_k`    | `median_local(FWHM/2.355)`            | From local |
| `ε`      | `0.05–0.07`                           | `P95(local RMSE) + margin` |
| `τ`      | `0.60–0.70`                           | From validation curve / FAR target |
| `κ_min`  | `0.60`                                | From OOD ROC (`AUROC ≥ 0.90`) |
| `SNR_min` | `5–8`                                 | From SNR “elbow” |

## 6) Glossary
- **Δν**: band shift = ν_observed − ν_recipe (cm⁻¹)  
- **tol**: allowed shift window (cm⁻¹)  
- **σ**: expected linewidth/uncertainty (cm⁻¹)  
- **RMSE (ε)**: fit error on the window (normalized)  
- **confidence (τ)**: classifier score threshold (SVM/QSVM)  
- **κ**: OOD similarity to a reference bank; **κ_min** is its cutoff  
- **SNR**: signal-to-noise in the window; **SNR_min** is its cutoff

---

**Implementation hint:** store the computed values back into our station’s recipe JSON (bump `version` and keep notes), and log the calibration artifacts (cal runs list, DOE summary, ROC plots) for audit.
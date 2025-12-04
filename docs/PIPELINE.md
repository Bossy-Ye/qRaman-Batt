# qRaman-Batt QC Pipeline

This document describes the core data flow of the qRaman-Batt QC engine.  
It covers how spectra, recipes, classifiers, and decisions connect end to end.

In v0.1.0 the recipes are hand-crafted from literature values and
engineering judgement (via QRaman-Batt design). They are only used
as priors to exercise the pipeline. Once enough accepted spectra are
logged per use-case, we will recompute tol, epsilon and snr_min from
data and version the recipes to v1.x.x.

---

## 1. Inputs

### 1.1 Live Spectrum

Provided by the Raman instrument:

- `nu`ν — wavenumbers (cm⁻¹)
- `intensity` — Raman intensity values (same length as `nu`)

These arrays are the only runtime input from the station.

### 1.2 Recipe (JSONC)

A recipe defines:

**Per-band parameters**

- `center` — expected band center (cm⁻¹)
- `tol` — allowed shift tolerance \|Δν\| (cm⁻¹)
- `sigma` — expected linewidth (cm⁻¹)
- `role` — `anchor`, `must_have`, `must_not`, or `watch`
- `window_range.min` / `.max` — extraction window
- optional `fit_lims.amp_min` / `.amp_max` / `.sigma_min` / `.sigma_max`

**Global thresholds**

- `epsilon` — maximum allowed RMSE (fit error)
- `tau` — classifier confidence threshold
- `kappa_min` — minimum similarity (OOD threshold)
- `snr_min` — minimum acceptable signal-to-noise ratio

Recipes are versioned and validated against `schema.jsonc`.

---

## 2. Per-Band Processing

For each band defined in the recipe:

### 2.1 Window Extraction

Select the part of the spectrum within:

- `[band.window_min, band.window_max]`

Return `(nu_window, intensity_window)`.

### 2.2 Peak Metrics

On each window we compute:

1. **Center shift (Δν)**  
   - estimate the observed center as the ν at maximum intensity  
   - `delta_nu = center_obs − band.center`

2. **Signal-to-noise ratio (SNR)**  
   - baseline ≈ median of the window  
   - signal = peak height above baseline  
   - noise = robust std (MAD-based) outside a small region around the peak  
   - `snr = peak_height / noise_std`

3. **RMSE (fit error)**  
   - use the recipe band as a template (Gaussian model by default)  
   - assume: `intensity ≈ baseline + amp_hat * g(x)`  
     - baseline = median(intensity)  
     - `g(x)` = Gaussian with band.center and band.sigma  
     - `amp_hat` = least-squares amplitude  
   - compute `rmse = sqrt(mean((y − model)²))`

RMSE answers: *“How well does this window look like the expected band model?”*

### 2.3 Classifier Inference

Features are currently the raw intensities of the band window.

Supported classifier backends via `Classifier`:

- `method="dummy"` — simple baseline (used in tests)
- `method="rbf"` — classical RBF-SVM (scikit-learn)
- `method="qsvm"` — quantum SVM backend

Each classifier returns:

- `confidence` ∈ [0, 1] — probability / score that a valid peak is present
- `kappa` ∈ [0, 1] — similarity or OOD score (1 = in-distribution)

---

## 3. Band Label Assignment

Metrics and classifier outputs are mapped to a semantic label using recipe thresholds.

Possible labels:

- `PEAK_OK`  
  peak present, good SNR/RMSE, and \|Δν\| ≤ tol

- `PEAK_DRIFTED`  
  peak present, but \|Δν\| > tol

- `NO_PEAK`  
  classifier not confident enough (`confidence < tau`)

- `BAD_QUALITY`  
  `snr < snr_min` or `rmse > epsilon`

- `OOD`  
  out-of-distribution window (`kappa < kappa_min`)

- `MUST_NOT_HIT`  
  forbidden band that shows a peak (`role == "must_not"` + peak detected)

Each `BandResult` contains:

- `band` (BandConfig)
- `label` (BandLabel)
- `metrics` (center, Δν, snr, rmse, confidence, kappa)
- `reasons[]` — short human-readable explanations

---

## 4. Sample-Level Decision

Band-level labels are aggregated into a single QC decision.

### Rules

1. **RED**
   - any `must_not` band has label `MUST_NOT_HIT`, or  
   - any `must_have` band has label `NO_PEAK` or `OOD`

2. **AMBER**
   - no RED condition  
   - at least one band is `PEAK_DRIFTED`, `BAD_QUALITY`, or `OOD`

3. **GREEN**
   - all bands are acceptable (`PEAK_OK` or benign `watch` behavior)

The final `SampleResult` includes:

- `recipe` — the RecipeConfig used
- `bands[]` — all `BandResult`s
- `decision` — `"GREEN"`, `"AMBER"`, or `"RED"`
- `reasons[]` — high-level reasons (for logs / UI)

---

## 5. Quantum Modules

The pipeline is designed so quantum components plug in without changing the overall structure.

### 5.1 QSVM (Inference)

- acts as a drop-in replacement for the classical RBF-SVM
- runs in the classifier step (Section 2.3)
- returns `confidence` and `kappa` used in the same decision logic

### 5.2 LR-VQE (Recipe Refinement, Offline)

- used in calibration / recipe design, not in the edge agent
- can refine:
  - expected centers
  - tolerances
  - linewidths
  - fitting constraints
- idea: align recipe parameters with quantum-resolved vibrational information when needed

These quantum modules need benchmark, work has not been done yet at the moment when this file is created at 2nd Dec 2025; the pipeline still works with purely classical models.

---

## 6. Repository Structure

Typical layout:

- `recipes/*.jsonc` — QC recipes per station / use case  
- `recipes/schema.jsonc` — JSON schema for recipes  
- `edge/recipes.py` — recipe loading, validation, dataclasses  
- `edge/qc_pipeline.py` — core QC logic (metrics, labels, aggregation)  
- `edge/classifier/` — optional classifier implementations (RBF, QSVM, etc.)  
- `tests/` — unit tests for pipeline and classifiers  

---

## 7. End-to-End Summary

High-level flow:

1. Load recipe (JSONC → `RecipeConfig`)
2. Take live spectrum `(nu, intensity)`
3. For each band:
   - extract window
   - compute Δν, SNR, RMSE
   - run classifier → `confidence`, `kappa`
   - assign band label
4. Aggregate all bands → `GREEN` / `AMBER` / `RED` + reasons

Recipes hold the domain knowledge.  
The pipeline keeps the control logic deterministic, while classifiers (classical or quantum) can evolve behind the same interface.
# Bands → Role (v0.1, Station A1)
**Author:** Boshuai Ye · **Email:** boshuai.ye@oulu.fi · **Date:** 2025-11-24

**Decision rule.** We issue auditable **Green / Amber / Red** calls by measuring 2–5 pre-defined “sentinel” bands and enforcing fixed per-band thresholds — |Δν| ≤ **tol**ₖ, **RMSE** ≤ **ε**, **SNR** ≥ **SNR_min**, **confidence** ≥ **τ**, **κ** ≥ **κ_min** — then aggregate by **role**:
- All **must-have** satisfied and **no must-not** detected → **Green**
- Any **must-not** or unresolved overlap → **Red**
- Otherwise **Amber** (after anchor auto-alignment)

Use the defaults below as seeds; tighten **ν**/**tol**/**σ** after 10–20 local calibration runs per station.

---

## Quick summary (ordered by use-case)
**Order:** Electrolyte QC → Interphase QC → Cathode LFP QC

| Band                     | Electrolyte QC | Interphase QC | Cathode LFP QC | Notes                       |
|---|---|---|---|---|
| **PF₆⁻ ~745 cm⁻¹**       | **must-have**  | should-have   | –              | Electrolyte integrity       |
| **EC ~717 cm⁻¹**         | should-have    | –             | –              | Solvent sanity check        |
| **Li₂CO₃ ~1090 cm⁻¹**    | should-have    | **must-have** | –              | SEI carbonate               |
| **POF₃ 870–900 (watch)** | **must-not**   | **must-not**  | –              | Decomposition alarm         |
| **CO₂ ~1388 (watch)**    | **must-not**   | –             | –              | Gas by-product              |
| **Graphite G ~1580**     | anchor         | anchor        | –              | Alignment (electrodes)      |
| **PO₄ ~950 (LFP)**       | –              | –             | **must-have**  | LFP fingerprint             |
| **PO₄ ~590 (LFP)**       | –              | –             | should-have    | LFP secondary               |

---

## Electrolyte QC essentials

### PF₆⁻ (≈740–750 cm⁻¹) — Electrolyte integrity/speciation
- **Criticality:** Direct probe of LiPF₆ anion → electrolyte presence/coordination.  
- **Measurability:** Strong; good SNR at 785 nm in carbonates.  
- **Specificity:** Region relatively clean; interferences manageable.  
- **Actionability:** Missing / low-SNR / severely drifted ⇒ no green-light; re-measure or quarantine.  
- **Role:** `must-have`  
- **Defaults:** ν = 745, tol = 8, σ = 6  
- **Interferences:** `EC_ring_717`, `solvent_ring`  
- **Ref:** J. Phys. Chem. C 119 (2015), **DOI: 10.1021/acs.jpcc.5b00826**.

### EC ring (≈717 cm⁻¹) — Solvent sanity
- **Criticality:** Confirms carbonate solvent present; catches empty/blocked vial issues.  
- **Measurability:** Strong ring-breathing mode; robust at 785 nm.  
- **Actionability:** If missing while PF₆⁻ also weak → instrument/sample issue; re-measure.  
- **Role:** `should-have`  
- **Defaults:** ν = 717, tol = 10, σ = 7  
- **Interferences:** (few)  
- **Refs:** Smith & Dent, *Modern Raman Spectroscopy* (Wiley, 2005); Long, *The Raman Effect* (Wiley, 2002).

### POF₃ (watch, ≈870–900 cm⁻¹) — Electrolyte decomposition alarm
- **Criticality:** Flag for LiPF₆ hydrolysis/decomposition.  
- **Measurability:** Moderate; exact ν depends on environment → verify locally.  
- **Specificity:** PVDF binder ~840–880 cm⁻¹ can confuse; mark as interference.  
- **Actionability:** Confident presence within tol with κ/τ met ⇒ **RED** (quarantine).  
- **Role:** `must-not`  
- **Defaults:** ν = 880, tol = 20, σ = 12  
- **Interferences:** `PVDF_840_880`, `phosphate_like`  
- **Ref:** P. Cabo-Fernandez et al., Phys. Chem. Chem. Phys. 21, 16127–16135 (2019), **DOI: 10.1039/C9CP02430A**.

### CO₂ (watch, ≈1388 cm⁻¹) — Gas by-product alarm
- **Criticality:** Decomposition/venting indicator.  
- **Measurability:** Clear line; can be weak at low concentration.  
- **Actionability:** Detected with adequate SNR/κ ⇒ **AMBER/RED** depending on level.  
- **Role:** `must-not`  
- **Defaults:** ν = 1388, tol = 12, σ = 10  
- **Interferences:** (few)  
- **Refs:** Long (2002); Smith & Dent (2005).

---

## Interphase (SEI/CEI, cathode side) QC essentials

### Li₂CO₃ (≈1088–1095 cm⁻¹) — solid-electrolyte interphase (SEI) carbonate marker
- **Criticality:** Signature of inorganic carbonate in SEI/CEI.  
- **Measurability:** Moderate–strong; overlaps with carbonates/phosphates → use constrained fits.  
- **Actionability:** Present/position/width trend interphase formation/aging; absence when expected → review.  
- **Role:** `must-have` (interphase QC), `should-have` (electrolyte QC)  
- **Defaults:** ν = 1090, tol = 10, σ = 7  
- **Interferences:** `phosphate_like`, `polycarbonates`  
- **Refs:** Reviewed in Smith & Dent (2005); numerous operando SEI studies place Li₂CO₃ near ~1090 cm⁻¹.

### Graphite G (≈1580 cm⁻¹) — Alignment/health anchor
- **Criticality:** Stable, sharp band for wavenumber alignment on graphite electrodes.  
- **Measurability:** Strong on anodes/carbon additives.  
- **Actionability:** Used to auto-align; not a pass/fail band by itself.  
- **Role:** `anchor`  
- **Defaults:** ν = 1580, tol = 6, σ = 10  
- **Interferences:** `Graphite_D_1350`  
- **Ref:** A. C. Ferrari & J. Robertson, Phys. Rev. B 61, 14095–14107 (2000), **DOI: 10.1103/PhysRevB.61.14095**.

---

## Cathode LFP QC essentials

### PO₄ (≈950 cm⁻¹) — LFP cathode fingerprint
- **Criticality:** Symmetric PO₄ stretch; primary identity/phase marker for LiFePO₄.  
- **Measurability:** Strong; good even at short dwell.  
- **Actionability:** Missing/drifted/weak ⇒ cathode issue or mis-pointing.  
- **Role:** `must-have`  
- **Defaults:** ν = 950, tol = 8, σ = 7  
- **Interferences:** (few)  
- **Refs:** Representative LiFePO₄ Raman papers in *J. Raman Spectrosc.* and *J. Power Sources* (choose station-validated references).

### PO₄ bend (≈590 cm⁻¹) — LFP secondary check
- **Criticality:** Confirms lattice; complements 950 band.  
- **Measurability:** Moderate; can broaden with (de)lithiation/temperature.  
- **Actionability:** Consistency with 950 improves confidence; mismatch triggers review.  
- **Role:** `should-have`  
- **Defaults:** ν = 590, tol = 10, σ = 8  
- **Interferences:** (few)

---

## How to apply
1. **Seed** a recipe with these defaults per use-case; pick 2–5 sentinel bands.  
2. **Localize** per station: run 10–20 known-good samples; tighten **tol** and adjust **σ** to match linewidth/SNR; store station drift.  
3. **Run** the daily loop: auto-align to an anchor (if present) → measure windows → fit/classify → aggregate by roles → output **G/A/R** + reason codes.  
4. **Update** the recipe when chemistry changes or OOD/κ alerts persist; bump version, re-validate on fresh runs.

---

## Glossary (symbols)
- **ν**: band center (cm⁻¹)  
- **tol**: allowed shift window (cm⁻¹)  
- **σ**: width/uncertainty (cm⁻¹)  
- **SNR**: signal-to-noise ratio (peak height ÷ noise std in a nearby flat region)  
- **RMSE (ε)**: fit error on the window (normalized)  
- **τ**: classifier confidence cutoff  
- **κ**: out-of-distribution similarity cutoff (kernel similarity vs. reference bank)

---

## References
- LiPF₆ / PF₆⁻: J. Phys. Chem. C 119 (2015), **DOI: 10.1021/acs.jpcc.5b00826**.  
- Graphite (G/D): A. C. Ferrari & J. Robertson, Phys. Rev. B 61, 14095–14107 (2000), **DOI: 10.1103/PhysRevB.61.14095**.  
- Raman basics & CO₂: D. A. Long, *The Raman Effect* (Wiley, 2002); E. Smith & G. Dent, *Modern Raman Spectroscopy* (Wiley, 2005).  
- LiPF₆ decomposition / POF₃: P. Cabo-Fernandez et al., Phys. Chem. Chem. Phys. 21, 16127–16135 (2019), **DOI: 10.1039/C9CP02430A**.  
- LiFePO₄ (LFP) Raman: representative papers in *J. Raman Spectrosc.* and *J. Power Sources*; select specific citations that match your station conditions.
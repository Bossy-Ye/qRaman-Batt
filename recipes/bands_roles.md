# Bands → Role (v0.1, Station A1)
**Author:** Boshuai Ye · **Email:** boshuai.ye@oulu.fi · **Date:** 2025-11-24

Short, practical notes that map common battery Raman bands to decision **roles** for our recipes (`must-have`, `should-have`, `must-not`, `anchor`). Use these as defaults; tighten `ν`/`tol`/`σ` after 10–20 local calibration runs per station.

---

## Quick summary (ordered by use-case)
**Order:** Electrolyte QC → Interphase QC → Cathode LFP QC

| Band                 | Electrolyte QC | Interphase QC | Cathode LFP QC | Notes |
|---|---|---|---|---|
| **PF₆⁻ ~745**         | **must-have**  | should-have   | –              | Electrolyte integrity |
| **EC ~717**           | should-have    | –             | –              | Solvent sanity check |
| **Li₂CO₃ ~1090**      | should-have    | **must-have** | –              | SEI carbonate |
| **POF₃ 870–900 (watch)** | **must-not**   | **must-not**  | –              | Decomposition alarm |
| **CO₂ ~1388 (watch)** | **must-not**   | –             | –              | Gas by-product |
| **Graphite G ~1580**  | anchor         | anchor        | –              | Alignment (electrodes) |
| **PO₄ ~950 (LFP)**    | –              | –             | **must-have**  | LFP fingerprint |
| **PO₄ ~590 (LFP)**    | –              | –             | should-have    | LFP secondary |

---

## Electrolyte QC essentials

### PF₆⁻ (≈740–750 cm⁻¹) — Electrolyte integrity/speciation
- **Criticality:** Direct probe of LiPF₆ anion → electrolyte presence/coordination.
- **Measurability:** Strong; good SNR at 785 nm in carbonates.
- **Specificity:** Region relatively clean; interferences manageable.
- **Actionability:** Missing/low-SNR/severely drifted ⇒ no green-light; re-measure or quarantine.
- **Role:** `must-have`
- **Defaults:** ν=745, tol=8, σ=6
- **Interferences:** `EC_ring_717`, `solvent_ring`

### EC ring (≈717 cm⁻¹) — Solvent sanity
- **Criticality:** Confirms carbonate solvent present; catches empty/blocked vial issues.
- **Measurability:** Strong ring-breathing mode; robust at 785 nm.
- **Actionability:** If missing while PF₆⁻ also weak → instrument/sample issue; re-measure.
- **Role:** `should-have`
- **Defaults:** ν=717, tol=10, σ=7
- **Interferences:** (few)

### POF₃ (watch, ≈870–900 cm⁻¹) — Electrolyte decomposition alarm
- **Criticality:** Flag for LiPF₆ hydrolysis/decomposition.
- **Measurability:** Moderate; exact ν depends on environment → verify locally.
- **Specificity:** PVDF binder ~840–880 cm⁻¹ can confuse; mark as interference.
- **Actionability:** Confident presence within tol with κ/τ met ⇒ **RED** (quarantine).
- **Role:** `must-not`
- **Defaults:** ν=880, tol=20, σ=12
- **Interferences:** `PVDF_840_880`, `phosphate_like`

### CO₂ (watch, ≈1388 cm⁻¹) — Gas by-product alarm
- **Criticality:** Decomposition/venting indicator.
- **Measurability:** Clear line; can be weak at low concentration.
- **Actionability:** Detected with adequate SNR/κ ⇒ **AMBER/RED** depending on level.
- **Role:** `must-not`
- **Defaults:** ν=1388, tol=12, σ=10
- **Interferences:** (few)

---

## Interphase (SEI/CEI) QC essentials

### Li₂CO₃ (≈1088–1095 cm⁻¹) — SEI carbonate marker
- **Criticality:** Signature of inorganic carbonate in SEI/CEI.
- **Measurability:** Moderate–strong; overlaps with carbonates/phosphates → use constrained fits.
- **Actionability:** Present/position/width trend interphase formation/aging; absence when expected → review.
- **Role:** `must-have` (interphase QC), `should-have` (electrolyte QC)
- **Defaults:** ν=1090, tol=10, σ=7
- **Interferences:** `phosphate_like`, `polycarbonates`

### Graphite G (≈1580 cm⁻¹) — Alignment/health anchor
- **Criticality:** Stable, sharp band for wavenumber alignment on graphite electrodes.
- **Measurability:** Strong on anodes/carbon additives.
- **Actionability:** Used to auto-align; not a pass/fail band by itself.
- **Role:** `anchor`
- **Defaults:** ν=1580, tol=6, σ=10
- **Interferences:** `Graphite_D_1350`

---

## Cathode LFP QC essentials

### PO₄ (≈950 cm⁻¹) — LFP cathode fingerprint
- **Criticality:** Symmetric PO₄ stretch; primary identity/phase marker for LiFePO₄.
- **Measurability:** Strong; good even at short dwell.
- **Actionability:** Missing/drifted/weak ⇒ cathode issue or mis-pointing.
- **Role:** `must-have`
- **Defaults:** ν=950, tol=8, σ=7
- **Interferences:** (few)

### PO₄ bend (≈590 cm⁻¹) — LFP secondary check
- **Criticality:** Confirms lattice; complements 950 band.
- **Measurability:** Moderate; can broaden with (de)lithiation/temperature.
- **Actionability:** Consistency with 950 improves confidence; mismatch triggers review.
- **Role:** `should-have`
- **Defaults:** ν=590, tol=10, σ=8
- **Interferences:** (few)

---

**How to apply:** Use the **Role** + **Defaults** as the starting values for each recipe’s `bands` entries (`nu`, `tol`, `σ`, `interferences`, `weight`). After local calibration (10–20 runs), tighten `tol` and adjust `σ` to match your station’s linewidth/SNR. Keep at least one `anchor` in electrode recipes for auto-alignment.
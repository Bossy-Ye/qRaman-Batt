# edge/qc_pipeline.py
"""
QC pipeline for qRaman-Batt.
— author: Boshuai Ye <boshuai.ye@oulu.fi> — created: 2025-11-28 —

Responsibilities:
- Take a live spectrum (ν, I) and a RecipeConfig.
- For each band:
    * cut window
    * compute metrics (Δν, SNR, RMSE)
    * run classifier (RBF / QSVM / OTHERS) to get (confidence, κ)
    * map metrics + thresholds -> BandLabel
- Aggregate band-level labels into a sample-level Green / Amber / Red decision.

The classifier backend is pluggable via the `Classifier` class:
    method="dummy" | "rbf" | "qsvm"
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Sequence, Tuple

import numpy as np

from .recipes import BandConfig, RecipeConfig

try:
    # classical baseline
    from sklearn.svm import SVC  # type: ignore[import]
except Exception:
    SVC = None


# ---------------------------------------------------------------------------
# Unified classifier abstraction
# ---------------------------------------------------------------------------


class Classifier:
    """
    Unified interface for all QC classifiers (dummy, RBF-SVM, QSVM).

    Usage:
        clf = Classifier(method="dummy")
        conf, kappa = clf.predict(features, band)

        # or
        clf = Classifier(method="rbf", model=svm_model)
        clf = Classifier(method="qsvm", model="qsvm_model_id", client=qsvm_client)
    """

    def __init__(self, method: str, model=None, client=None):
        """
        Args:
            method:
                "dummy"  - baseline for testing
                "rbf"    - classical RBF-SVM backend
                "qsvm"   - quantum SVM backend
            model:
                for method="rbf": sklearn.svm.SVC or compatible
                for method="qsvm": quantum model identifier / handle
            client:
                for method="qsvm": object used to talk to the QSVM service/backend
        """
        self.method = method.lower()
        self.model = model
        self.client = client

        if self.method not in {"dummy", "rbf", "qsvm"}:
            raise ValueError("method must be one of: 'dummy', 'rbf', 'qsvm'")

        if self.method == "rbf" and self.model is None:
            raise ValueError("RBF classifier requires a 'model' (sklearn SVC).")

        if self.method == "rbf" and SVC is None:
            raise RuntimeError(
                "scikit-learn is not installed. Install with `pip install scikit-learn` "
                "or avoid using method='rbf'."
            )

        if self.method == "qsvm" and (self.model is None or self.client is None):
            raise ValueError("QSVM classifier requires both 'model' and 'client'.")

    def predict(self, features: np.ndarray, band: BandConfig) -> Tuple[float, float]:
        """
        Predict on one band window.

        Args:
            features: 1D array of window features (e.g. normalized intensities).
            band: BandConfig for the current band.

        Returns:
            (confidence, kappa):
                confidence: P(peak | window, band) in [0, 1]
                kappa: OOD / similarity score in [0, 1]
        """
        if self.method == "dummy":
            return self._predict_dummy(features)

        if self.method == "rbf":
            return self._predict_rbf(features)

        if self.method == "qsvm":
            return self._predict_qsvm(features, band)

        raise RuntimeError(f"Unsupported classifier method: {self.method}")

    # ------------------------
    # Backend implementations
    # ------------------------

    def _predict_dummy(self, features: np.ndarray) -> Tuple[float, float]:
        """Baseline: confidence ~ max intensity, κ = 1.0."""
        if features.size == 0:
            return 0.0, 0.0
        peak = float(features.max())
        confidence = float(np.clip(peak, 0.0, 1.0))
        kappa = 1.0
        return confidence, kappa

    def _predict_rbf(self, features: np.ndarray) -> Tuple[float, float]:
        """Classical RBF-SVM backend using a single sklearn SVC-like model."""
        if self.model is None:
            raise RuntimeError("RBF model is not set on Classifier.")

        X = features.reshape(1, -1)
        model = self.model

        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)[0]  # type: ignore[call-arg]
            # Assume positive class index 1 = "peak"
            confidence = float(proba[1])
        else:
            # Fall back to decision_function + logistic mapping
            df = float(model.decision_function(X)[0])  # type: ignore[attr-defined]
            confidence = float(1.0 / (1.0 + np.exp(-df)))

        # No explicit OOD yet → treat everything as in-distribution.
        kappa = 1.0
        return confidence, kappa

    def _predict_qsvm(self, features: np.ndarray, band: BandConfig) -> Tuple[float, float]:
        """
        Quantum SVM backend.

        This is a thin wrapper. The actual quantum logic lives in self.client.
        We assume self.client has a method like:

            client.predict({ "model_id": ..., "band": ..., "features": [...] })

        and returns a dict with keys "confidence" and optional "kappa".
        """
        if self.client is None or self.model is None:
            raise RuntimeError("QSVM backend requires both client and model.")

        payload = {
            "model_id": self.model,
            "band": band.name,
            "features": features.tolist(),
        }
        resp = self.client.predict(payload)

        confidence = float(resp["confidence"])
        kappa = float(resp.get("kappa", 1.0))
        return confidence, kappa


# ---------------------------------------------------------------------------
# Band-level metrics and labels
# ---------------------------------------------------------------------------


class BandLabel(str, Enum):
    """Semantic state of a sentinel band in a QC decision."""

    PEAK_OK = "PEAK_OK"               # peak present, good SNR/RMSE, |Δν| ≤ tol
    PEAK_DRIFTED = "PEAK_DRIFTED"     # peak present but |Δν| > tol
    NO_PEAK = "NO_PEAK"               # no reliable peak (confidence < τ)
    BAD_QUALITY = "BAD_QUALITY"       # SNR < SNR_min or RMSE > ε
    OOD = "OOD"                       # out-of-distribution (κ < κ_min)
    MUST_NOT_HIT = "MUST_NOT_HIT"     # forbidden band appears as a peak


@dataclass
class BandMetrics:
    """Raw metrics for one band window."""

    center_obs: float          # estimated peak center (cm^-1)
    delta_nu: float            # center_obs - band.center (cm^-1)
    snr: float                 # signal-to-noise
    rmse: float                # fit error
    confidence: float          # classifier P(peak)
    kappa: float               # OOD similarity


@dataclass
class BandResult:
    """Full result for one band: label + metrics + explanations."""

    band: BandConfig
    label: BandLabel
    metrics: BandMetrics
    reasons: List[str]


@dataclass
class SampleResult:
    """Aggregated decision for one whole spectrum."""

    recipe: RecipeConfig
    bands: List[BandResult]
    decision: str        # "GREEN" | "AMBER" | "RED"
    reasons: List[str]   # high-level decision reasons (e.g. must-not hit, drifted)


# ---------------------------------------------------------------------------
# Helper functions: windows, metrics
# ---------------------------------------------------------------------------


def _extract_window(
    nu: np.ndarray,
    intensity: np.ndarray,
    band: BandConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (ν_window, I_window) for the band window."""
    mask = (nu >= band.window_min) & (nu <= band.window_max)
    return nu[mask], intensity[mask]


def _estimate_center(nu: np.ndarray, intensity: np.ndarray) -> float:
    """
    Very simple peak-center estimate as ν at max intensity.
    Later this can be replaced with a proper peak fit (Gaussian/Voigt).
    """
    if nu.size == 0:
        return float("nan")
    idx = int(np.argmax(intensity))
    return float(nu[idx])


def _compute_snr(intensity: np.ndarray) -> float:
    """Estimate SNR = (peak_height) / (noise_std), robust to peaks and drift."""
    if intensity.size == 0:
        return 0.0

    # --- get the signal above baseline
    y = np.asarray(intensity, dtype=float)
    median = float(np.median(y))
    residual = y - median

    # --- signal ---
    peak_idx = int(np.argmax(residual))
    peak_height = float(residual[peak_idx])
    if peak_height <= 0:
        return 0.0

    # --- noise region: exclude window around peak ---
    n = residual.size
    half_width = max(1, n // 10)   # 10% of window
    left = max(0, peak_idx - half_width)
    right = min(n, peak_idx + half_width + 1)

    noise_residual = np.concatenate([residual[:left], residual[right:]])
    if noise_residual.size < 3:
        noise_residual = residual - np.median(residual)

    # --- robust noise estimate ---
    mad = 1.4826 * np.median(np.abs(noise_residual - np.median(noise_residual)))
    noise_std = float(mad) if mad > 0 else 1e-9

    return peak_height / noise_std


# ---------------------------------------------------------------------------
# Peak models (Gaussian now, extensible to pseudo-Voigt / templates)
# ---------------------------------------------------------------------------


def _gaussian(x: np.ndarray, amp: float, center: float, sigma: float) -> np.ndarray:
    """Simple Gaussian peak model."""
    if sigma <= 0:
        return np.zeros_like(x, dtype=float)
    z = (x - center) / sigma
    return amp * np.exp(-0.5 * z * z)


def _lorentzian(x: np.ndarray, amp: float, center: float, gamma: float) -> np.ndarray:
    """Simple Lorentzian peak model."""
    if gamma <= 0:
        return np.zeros_like(x, dtype=float)
    z = (x - center) / gamma
    return amp / (1.0 + z * z)


def _pseudovoigt(
    x: np.ndarray,
    amp: float,
    center: float,
    sigma: float,
    eta: float,
) -> np.ndarray:
    """
    Pseudo-Voigt peak model: linear combination of Gaussian and Lorentzian.

    eta in [0, 1]:
      eta = 0 -> pure Gaussian
      eta = 1 -> pure Lorentzian
    """
    eta = float(np.clip(eta, 0.0, 1.0))
    g = _gaussian(x, amp=amp, center=center, sigma=sigma)
    # For simplicity, use gamma ≈ sigma; can be refined later if needed.
    l = _lorentzian(x, amp=amp, center=center, gamma=sigma)
    return eta * l + (1.0 - eta) * g


def _peak_template(x: np.ndarray, band: BandConfig) -> np.ndarray:
    """
    Return a unit-amplitude template g(x) for this band.

    Current behaviour:
      - default / missing shape -> Gaussian(center=band.center, sigma=band.sigma)
      - shape == "gaussian"    -> same as default
      - shape == "pseudovoigt" -> pseudo-Voigt with band.eta (default 0.5)
      - shape == "template"    -> use band.template (1D array) if compatible,
                                  otherwise fall back to Gaussian.

    This keeps the QC code ready for more realistic models without forcing
    schema changes right now: extra attributes like `shape`, `eta`, `template`
    are optional and safely ignored if absent.
    """
    x = np.asarray(x, dtype=float)
    center = float(band.center)
    sigma = float(band.sigma)

    shape = getattr(band, "shape", "gaussian")

    # 1) pure Gaussian (default)
    if shape == "gaussian" or shape is None:
        return _gaussian(x, amp=1.0, center=center, sigma=sigma)

    # 2) pseudo-Voigt (Gaussian + Lorentzian mix)
    if shape == "pseudovoigt":
        eta = float(getattr(band, "eta", 0.5))  # default: 50% mix
        return _pseudovoigt(x, amp=1.0, center=center, sigma=sigma, eta=eta)

    # 3) data-driven template (e.g. from calibration)
    if shape == "template":
        template = getattr(band, "template", None)
        if isinstance(template, np.ndarray) and template.ndim == 1 and template.size == x.size:
            return template.astype(float)
        # Shape mismatch → fall back to Gaussian
        return _gaussian(x, amp=1.0, center=center, sigma=sigma)

    # Unknown shape → be conservative and fall back to Gaussian
    return _gaussian(x, amp=1.0, center=center, sigma=sigma)


def _compute_rmse(nu: np.ndarray, intensity: np.ndarray, band: BandConfig) -> float:
    """
    Model-based RMSE for a single band window.

    Idea:
      - Use a band-specific peak template g(x) (Gaussian / pseudo-Voigt / template).
      - Assume intensity = baseline + amp * g(x).
      - Estimate:
            baseline = median(intensity)
            amp_hat  = argmin ||y - (baseline + amp * g)||^2
                    = (g^T y0) / (g^T g), where y0 = y - baseline
      - Optionally clamp amp_hat to band.fit_lims.amp_min/max.
      - RMSE = sqrt(mean( (y - model)^2 )).

    This makes RMSE meaningful: "how well does this window match the expected
    band model for this station and use-case?"
    """
    if nu.size == 0 or intensity.size == 0:
        # No data → treat as bad fit.
        return 1.0

    x = np.asarray(nu, dtype=float)
    y = np.asarray(intensity, dtype=float)

    # Baseline approximation
    baseline = float(np.median(y))
    y0 = y - baseline

    # Band-specific template with unit amplitude
    g = _peak_template(x, band)
    print(g)
    # If template is degenerate, fall back to "roughness around median"
    norm_g2 = float(np.dot(g, g))
    if norm_g2 <= 1e-12:
        residuals = y - baseline
        mse = float(np.mean(residuals**2))
        return float(np.sqrt(mse))

    # Closed-form least-squares amplitude: (g^T y0) / (g^T g)
    amp_hat = float(np.dot(g, y0) / norm_g2)

    # Apply amplitude limits from recipe, if provided
    if band.fit_lims is not None:
        if band.fit_lims.amp_min is not None:
            amp_hat = max(amp_hat, float(band.fit_lims.amp_min))
        if band.fit_lims.amp_max is not None:
            amp_hat = min(amp_hat, float(band.fit_lims.amp_max))

    model = baseline + amp_hat * g
    residuals = y - model
    mse = float(np.mean(residuals**2))
    return float(np.sqrt(mse))


# ---------------------------------------------------------------------------
# Label decision from metrics + thresholds
# ---------------------------------------------------------------------------


def make_band_label(
    band: BandConfig,
    recipe: RecipeConfig,
    delta_nu: float,
    snr: float,
    rmse: float,
    confidence: float,
    kappa: float,
) -> BandLabel:
    """
    Map metrics + thresholds to a semantic BandLabel.

    Priority:
      1) OOD              -> OOD
      2) signal quality   -> BAD_QUALITY
      3) no reliable peak -> NO_PEAK
      4) drift            -> PEAK_DRIFTED
      5) default peak     -> PEAK_OK
      6) must-not override -> MUST_NOT_HIT
    """
    # 1) OOD dominates
    if kappa < recipe.kappa_min:
        return BandLabel.OOD

    # 2) bad signal quality
    if snr < recipe.snr_min or rmse > recipe.epsilon:
        return BandLabel.BAD_QUALITY

    # 3) classifier says "no reliable peak"
    if confidence < recipe.tau:
        return BandLabel.NO_PEAK

    # 4) peak present but drifted
    if abs(delta_nu) > band.tol:
        base = BandLabel.PEAK_DRIFTED
    else:
        base = BandLabel.PEAK_OK

    # 5) must-not override
    if band.role == "must-not" and base in {BandLabel.PEAK_OK, BandLabel.PEAK_DRIFTED}:
        return BandLabel.MUST_NOT_HIT

    return base


# ---------------------------------------------------------------------------
# Band and sample evaluation
# ---------------------------------------------------------------------------


def evaluate_band(
    nu: np.ndarray,
    intensity: np.ndarray,
    band: BandConfig,
    recipe: RecipeConfig,
    classifier: Classifier,
) -> BandResult:
    """
    Evaluate a single band:
      - cut window
      - compute metrics (center, Δν, SNR, RMSE)
      - run classifier backend (RBF / QSVM / dummy)
      - choose BandLabel
      - collect reasons
    """
    w_nu, w_I = _extract_window(nu, intensity, band)
    center_obs = _estimate_center(w_nu, w_I)
    delta_nu = center_obs - band.center if not np.isnan(center_obs) else float("nan")
    snr = _compute_snr(w_I)
    rmse = _compute_rmse(w_nu, w_I, band)
    # For now, raw intensities are the features.
    features = w_I.astype(float) if w_I.size > 0 else np.zeros(0, dtype=float)
    confidence, kappa = classifier.predict(features, band)

    metrics = BandMetrics(
        center_obs=center_obs,
        delta_nu=delta_nu,
        snr=snr,
        rmse=rmse,
        confidence=confidence,
        kappa=kappa,
    )

    label = make_band_label(
        band=band,
        recipe=recipe,
        delta_nu=delta_nu,
        snr=snr,
        rmse=rmse,
        confidence=confidence,
        kappa=kappa,
    )

    # Human-readable reasons (for logging / UI)
    reasons: List[str] = []
    if kappa < recipe.kappa_min:
        reasons.append(f"κ<{recipe.kappa_min:.2f} (got {kappa:.2f})")
    if snr < recipe.snr_min:
        reasons.append(f"SNR<{recipe.snr_min:.1f} (got {snr:.2f})")
    if rmse > recipe.epsilon:
        reasons.append(f"RMSE>{recipe.epsilon:.3f} (got {rmse:.3f})")
    if not np.isnan(delta_nu) and abs(delta_nu) > band.tol:
        reasons.append(f"|Δν|>{band.tol:.1f} (got {delta_nu:.2f})")
    if confidence < recipe.tau:
        reasons.append(f"conf<{recipe.tau:.2f} (got {confidence:.2f})")
    if label == BandLabel.MUST_NOT_HIT:
        reasons.append("must-not band appears as peak")

    return BandResult(band=band, label=label, metrics=metrics, reasons=reasons)


def aggregate_sample(recipe: RecipeConfig, band_results: List[BandResult]) -> SampleResult:
    """
    Aggregate band-level results into Green / Amber / Red.

    Simple rules:
      - RED if any must-not band is MUST_NOT_HIT
      - RED if any must-have band is NO_PEAK or OOD (hard fail)
      - else AMBER if any band is PEAK_DRIFTED, BAD_QUALITY, or OOD
      - else GREEN
    """
    decision = "GREEN"
    reasons: List[str] = []

    for br in band_results:
        role = br.band.role
        lbl = br.label

        # any must-not hit → RED
        if role == "must-not" and lbl == BandLabel.MUST_NOT_HIT:
            decision = "RED"
            reasons.append(f"must-not band {br.band.name} hit")
            # RED is terminal but we still scan others for logging

        # must-have that is completely missing or OOD → RED
        if role == "must-have" and lbl in {BandLabel.NO_PEAK, BandLabel.OOD}:
            decision = "RED"
            reasons.append(f"must-have band {br.band.name} is {lbl.value}")

    if decision != "RED":
        # downgrade to AMBER if there is any degraded band
        for br in band_results:
            if br.label in {BandLabel.PEAK_DRIFTED, BandLabel.BAD_QUALITY, BandLabel.OOD}:
                if decision != "AMBER":
                    decision = "AMBER"
                reasons.append(f"band {br.band.name} is {br.label.value}")

    return SampleResult(
        recipe=recipe,
        bands=band_results,
        decision=decision,
        reasons=reasons,
    )


def run_qc_on_spectrum(
    nu: Sequence[float],
    intensity: Sequence[float],
    recipe: RecipeConfig,
    classifier: Classifier,
) -> SampleResult:
    """
    Main entry point for edge agent.

    Input:
        - nu: wavenumbers (cm^-1)
        - intensity: Raman intensities
        - recipe: RecipeConfig loaded from recipes/ (per station/use-case)
        - classifier: Classifier(method="dummy" | "rbf" | "qsvm", ...)

    Output:
        SampleResult with per-band labels + overall decision (GREEN/AMBER/RED).
    """
    nu_arr = np.asarray(nu, dtype=float)
    I_arr = np.asarray(intensity, dtype=float)

    band_results = [
        evaluate_band(nu_arr, I_arr, band, recipe, classifier)
        for band in recipe.bands
    ]
    return aggregate_sample(recipe, band_results)
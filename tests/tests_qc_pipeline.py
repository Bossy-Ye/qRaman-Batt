# tests/test_qc_pipeline.py
"""
Tests for the QC pipeline and unified Classifier abstraction.

We do NOT depend on JSONC recipe files here; instead we construct
RecipeConfig / BandConfig objects directly to keep tests fast and focused.
"""
from __future__ import annotations

# tests/conftest.py
import sys
from pathlib import Path

# Add src/ to sys.path so `import edge` works in tests
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from typing import Dict

import numpy as np

from edge.qc_pipeline import (
    Classifier,
    BandLabel,
    evaluate_band,
    run_qc_on_spectrum,
)
from edge.qc_pipeline import BandConfig, RecipeConfig

# ---------------------------------------------------------------------------
# Helpers to build minimal recipe / band configs for tests
# ---------------------------------------------------------------------------


def make_simple_band(
    name: str = "TestBand",
    center: float = 5.0,
    tol: float = 5.0,
    sigma: float = 2.0,
    role: str = "must-have",
    window_min: float = 4.0,
    window_max: float = 6.0,
) -> BandConfig:
    """Create a minimal BandConfig for unit tests."""
    return BandConfig(
        name=name,
        center=center,
        tol=tol,
        sigma=sigma,
        role=role,
        window_min=window_min,
        window_max=window_max,
        fit_lims=None,
        notes=None,
        # shape/eta/template use their defaults from BandConfig
    )


def make_simple_recipe(
    recipe_name: str = "test_recipe",
    bands: list[BandConfig] | None = None,
    epsilon: float = 1.0,
    tau: float = 0.5,
    kappa_min: float = 0.5,
    snr_min: float = 1.0,
) -> RecipeConfig:
    """Create a minimal RecipeConfig for unit tests."""
    if bands is None:
        bands = [make_simple_band()]

    return RecipeConfig(
        recipe_name=recipe_name,
        recipe_version="0.0.1",
        station="A1",
        bands=bands,
        epsilon=epsilon,
        tau=tau,
        kappa_min=kappa_min,
        snr_min=snr_min,
        notes=None,
        raw=None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dummy_classifier_green_peak_ok():
    """
    With a clear peak in-band and loose thresholds, Dummy classifier
    should produce PEAK_OK and overall GREEN.

    This uses a slightly wider window so that the SNR routine's
    "exclude 10% around the peak" logic has a meaningful noise region.
    """
    band = make_simple_band(
        name="PO4",
        center=10.0,
        tol=5.0,
        window_min=5.0,
        window_max=15.0,
        role="must-have",
    )
    recipe = make_simple_recipe(
        bands=[band],
        epsilon=1.0,
        tau=0.5,
        kappa_min=0.5,
        snr_min=1.0,
    )

    # Synthetic spectrum: 0–20 with a sharp peak at ν = 10
    nu = np.linspace(0.0, 20.0, 201)  # 0.1 cm⁻¹ step
    intensity = np.zeros_like(nu)
    peak_idx = np.argmin(np.abs(nu - 10.0))
    intensity[peak_idx] = 1.0  # single clear peak

    clf = Classifier(method="dummy")

    # Band-level check
    band_result = evaluate_band(nu, intensity, band, recipe, clf)
    assert band_result.label == BandLabel.PEAK_OK
    assert band_result.metrics.confidence == 1.0
    assert band_result.metrics.kappa == 1.0
    # sanity: SNR should be clearly high with a single strong spike
    assert band_result.metrics.snr > 10.0

    # Sample-level aggregation
    sample_result = run_qc_on_spectrum(nu, intensity, recipe, clf)
    assert sample_result.decision == "GREEN"
    assert len(sample_result.bands) == 1
    assert sample_result.bands[0].label == BandLabel.PEAK_OK


def test_must_not_band_triggers_red():
    """
    If a must-not band has a strong peak, the decision should be RED
    with MUST_NOT_HIT label.
    """
    band = make_simple_band(
        name="POF3_watch",
        center=5.0,
        tol=5.0,
        window_min=4.0,
        window_max=6.0,
        role="must-not",
    )
    recipe = make_simple_recipe(
        bands=[band],
        epsilon=1.0,
        tau=0.5,
        kappa_min=0.5,
        snr_min=1.0,
    )

    nu = np.linspace(0.0, 10.0, 11)
    intensity = np.zeros_like(nu)
    intensity[5] = 1.0  # strong peak

    clf = Classifier(method="dummy")

    band_result = evaluate_band(nu, intensity, band, recipe, clf)
    assert band_result.label == BandLabel.MUST_NOT_HIT

    sample_result = run_qc_on_spectrum(nu, intensity, recipe, clf)
    assert sample_result.decision == "RED"
    # At least one reason should mention must-not
    assert any("must-not band" in r for r in sample_result.reasons)


def test_bad_quality_downgrades_to_amber():
    """
    Low SNR / high RMSE should produce BAD_QUALITY and overall AMBER
    when there is no must-have / must-not hard failure.

    Here we use a neutral 'watch' band so that BAD_QUALITY only
    downgrades the decision, it does not force RED.
    """
    band = make_simple_band(
        name="Li2CO3",
        center=5.0,
        tol=5.0,
        window_min=4.0,
        window_max=6.0,
        role="watch",
    )
    # Require SNR >= 1.0; we'll build a flat, noisy-looking window with SNR ~ 0
    recipe = make_simple_recipe(
        bands=[band],
        epsilon=0.5,
        tau=0.5,
        kappa_min=0.5,
        snr_min=1.0,
    )

    nu = np.linspace(0.0, 10.0, 11)
    # constant intensity: no peak, SNR ~ 0
    intensity = np.ones_like(nu) * 0.5

    clf = Classifier(method="dummy")

    band_result = evaluate_band(nu, intensity, band, recipe, clf)
    assert band_result.label == BandLabel.BAD_QUALITY

    sample_result = run_qc_on_spectrum(nu, intensity, recipe, clf)
    # No must-have / must-not hard fail -> AMBER
    assert sample_result.decision == "AMBER"
    assert any("SNR<" in r or "RMSE>" in r for r in sample_result.reasons)


class FakeQsvmClient:
    """Minimal fake QSVM client used to test the qsvm backend routing."""

    def __init__(self, responses: Dict[str, Dict[str, float]]):
        """
        responses: mapping band_name -> {"confidence": float, "kappa": float}
        """
        self.responses = responses

    def predict(self, payload: Dict) -> Dict[str, float]:
        band_name = payload.get("band")
        return self.responses.get(band_name, {"confidence": 0.0, "kappa": 1.0})


def test_qsvm_backend_uses_kappa_for_ood_and_triggers_red():
    """
    QSVM backend should route through client.predict(...) and respect κ for OOD.

    We simulate:
      - must-have band
      - high confidence (peak) but low κ < kappa_min
      -> label OOD and overall RED.
    """
    band = make_simple_band(
        name="PF6",
        center=5.0,
        tol=5.0,
        window_min=4.0,
        window_max=6.0,
        role="must-have",
    )
    recipe = make_simple_recipe(
        bands=[band],
        epsilon=1.0,
        tau=0.5,
        kappa_min=0.8,  # require fairly high similarity
        snr_min=1.0,
    )

    nu = np.linspace(0.0, 10.0, 11)
    intensity = np.zeros_like(nu)
    intensity[5] = 1.0

    # Fake QSVM client: high confidence but low κ => OOD
    fake_client = FakeQsvmClient(
        responses={
            "PF6": {"confidence": 0.9, "kappa": 0.5},
        }
    )
    clf = Classifier(method="qsvm", model="dummy_qsvm_model", client=fake_client)

    band_result = evaluate_band(nu, intensity, band, recipe, clf)
    assert band_result.metrics.confidence == 0.9
    assert band_result.metrics.kappa == 0.5
    assert band_result.label == BandLabel.OOD

    sample_result = run_qc_on_spectrum(nu, intensity, recipe, clf)
    # must-have + OOD -> RED
    assert sample_result.decision == "RED"
    assert any("OOD" in br.label.value for br in sample_result.bands)
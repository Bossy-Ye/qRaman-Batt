# tests/test_recipes.py

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edge.recipes import (
    load_recipe,
    load_recipes_from_index,
    RecipeConfig,
    BandConfig,
)
from edge.recipes import format_recipe

REPO_ROOT = ROOT
RECIPES_DIR = REPO_ROOT / "recipes"


def test_load_cathode_lfp_recipe():
    path = RECIPES_DIR / "cathode_lfp_qc.jsonc"
    cfg = load_recipe(path, validate=False)
    print(format_recipe(cfg))
    assert isinstance(cfg, RecipeConfig)
    assert cfg.recipe_name == "cathode_lfp_qc"
    assert cfg.station == "A1"
    assert len(cfg.bands) >= 2

    assert 0 < cfg.epsilon < 1
    assert 0 < cfg.tau <= 1
    assert 0 < cfg.kappa_min <= 1
    assert cfg.snr_min > 0

    po4_main = next(b for b in cfg.bands if b.name == "PO4_950")
    assert isinstance(po4_main, BandConfig)
    assert po4_main.center == 950.0
    assert po4_main.role == "must_have"
    assert po4_main.window_min < po4_main.center < po4_main.window_max


def test_load_electrolyte_recipe():
    path = RECIPES_DIR / "electrolyte_qc.jsonc"
    cfg = load_recipe(path, validate=False)
    print(format_recipe(cfg))
    assert cfg.recipe_name == "electrolyte_qc"
    assert cfg.station == "A1"
    assert len(cfg.bands) >= 3

    pf6 = next(b for b in cfg.bands if b.name == "PF6")
    assert pf6.role == "must_have"
    assert 730.0 <= pf6.window_min < pf6.center < pf6.window_max <= 760.0

    g_band = next(b for b in cfg.bands if b.name == "Graphite_G")
    assert g_band.role == "anchor"


def test_load_interphase_recipe():
    path = RECIPES_DIR / "interphase_qc.jsonc"
    cfg = load_recipe(path, validate=False)
    print(format_recipe(cfg))
    assert cfg.recipe_name == "interphase_qc"
    assert cfg.station == "A1"
    assert len(cfg.bands) >= 2

    li2co3 = next(b for b in cfg.bands if b.name == "Li2CO3")
    assert li2co3.role == "must_have"
    assert 1070.0 <= li2co3.window_min < li2co3.center < li2co3.window_max <= 1110.0

    g_band = next(b for b in cfg.bands if b.name == "Graphite_G")
    assert g_band.role == "anchor"


def test_load_all_recipes_from_index():
    index_path = RECIPES_DIR / "index.jsonc"
    recipes = load_recipes_from_index(index_path, validate=False)

    for name in ("electrolyte_qc", "interphase_qc", "cathode_lfp_qc"):
        assert name in recipes
        cfg = recipes[name]
        assert isinstance(cfg, RecipeConfig)
        assert cfg.recipe_name == name
        assert len(cfg.bands) > 0


def test_numeric_constraints_all_recipes():
    """
    Numeric sanity checks for all recipes listed in index.jsonc.

    These tests do NOT check chemistry, only that numbers are
    internally consistent and within plausible ranges.
    """
    index_path = RECIPES_DIR / "index.jsonc"
    recipes = load_recipes_from_index(index_path, validate=False)

    assert recipes, "No recipes loaded from index.jsonc"

    for name, cfg in recipes.items():
        print(format_recipe(cfg))
        # ---- Global thresholds ----
        # epsilon: RMSE in [0, ~0.2]
        assert 0.0 < cfg.epsilon < 0.2, f"{name}: epsilon out of range: {cfg.epsilon}"

        # tau, kappa_min: probabilities in (0, 1]
        assert 0.0 < cfg.tau <= 1.0, f"{name}: tau out of range: {cfg.tau}"
        assert 0.0 < cfg.kappa_min <= 1.0, f"{name}: kappa_min out of range: {cfg.kappa_min}"

        # snr_min: positive, not ridiculous (say <= 50)
        assert 0.0 < cfg.snr_min <= 50.0, f"{name}: snr_min out of range: {cfg.snr_min}"

        # ---- Per-band checks ----
        assert cfg.bands, f"{name}: recipe has no bands"

        for band in cfg.bands:
            # Window must be proper interval
            assert band.window_min < band.window_max, (
                f"{name}/{band.name}: window_min >= window_max "
                f"({band.window_min} >= {band.window_max})"
            )

            # Center must lie inside its own window
            assert band.window_min < band.center < band.window_max, (
                f"{name}/{band.name}: center {band.center} not inside "
                f"[{band.window_min}, {band.window_max}]"
            )

            # Tolerances and widths must be positive
            assert band.tol > 0.0, f"{name}/{band.name}: tol <= 0"
            assert band.sigma > 0.0, f"{name}/{band.name}: sigma <= 0"

            # Window should not be absurdly tiny relative to tol
            window_span = band.window_max - band.window_min
            assert window_span >= band.tol, (
                f"{name}/{band.name}: window span {window_span} < tol {band.tol}"
            )

            # (Optional) sanity: band not insanely far from 0–4000 cm-1
            assert 0.0 < band.center < 4000.0, (
                f"{name}/{band.name}: center {band.center} looks out of Raman range"
            )
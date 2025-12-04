# edge/recipes.py
"""
Recipe loading and validation for qRaman-Batt.
— author: Boshuai Ye <boshuai.ye@oulu.fi> — created: 2025-11-27 —

Responsibilities:
- Read JSONC recipe files (with // comments).
- Validate against recipes/schema.jsonc (if jsonschema is available).
- Expose typed dataclasses for downstream use in the edge pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import json

try:
    import jsonschema  # type: ignore[import]
except Exception:  # pragma: no cover - optional dependency
    jsonschema = None


# --------------------------------------------------------------------
# Dataclasses
# --------------------------------------------------------------------


@dataclass
class FitLims:
    """Optional physical constraints for peak fitting."""

    amp_min: Optional[float] = None
    amp_max: Optional[float] = None
    sigma_min: Optional[float] = None
    sigma_max: Optional[float] = None


@dataclass
class BandConfig:
    """
    Per-band thresholds and metadata.

    Matches a single entry in recipe['bands'] as defined in schema.jsonc.
    """

    name: str
    center: float
    tol: float
    sigma: float
    role: str
    window_min: float
    window_max: float

    # Optional model / fitting configuration
    fit_lims: Optional[FitLims] = None
    notes: Optional[str] = None

    # Band-shape model (all optional with safe defaults)
    # "gaussian" | "pseudovoigt" | "template"
    shape: str = "gaussian"
    # For pseudo-Voigt; ignored otherwise
    eta: Optional[float] = None
    # Optional fixed template for this band (same length as window)
    template: Optional[List[float]] = None


@dataclass
class RecipeConfig:
    """
    Full recipe configuration: metadata, per-band thresholds, and global thresholds.
    """

    recipe_name: str
    recipe_version: str
    station: str
    bands: List[BandConfig]
    epsilon: float
    tau: float
    kappa_min: float
    snr_min: float
    notes: Optional[str] = None
    # keep original dict for debugging / logging
    raw: Dict[str, Any] | None = None


# --------------------------------------------------------------------
# JSONC utilities
# --------------------------------------------------------------------


def _strip_jsonc_comments(text: str) -> str:
    """
    Very simple JSONC comment stripper.

    Removes:
    - line comments starting with //
    - block comments /* ... */

    Assumes recipes do not contain these comment patterns inside string literals.
    This keeps dependencies minimal; if that becomes an issue later, switch to a
    proper JSONC/JSON5 parser.
    """
    import re

    # Remove /* ... */ (non-greedy, across lines)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Remove // ... end-of-line
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    return text


def _load_jsonc(path: Path) -> Dict[str, Any]:
    """Load a JSONC file by stripping comments first."""
    text = path.read_text(encoding="utf-8")
    clean = _strip_jsonc_comments(text)
    return json.loads(clean)


# --------------------------------------------------------------------
# Schema loading / validation
# --------------------------------------------------------------------


def _load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load the recipe JSON schema (also JSONC)."""
    return _load_jsonc(schema_path)


def _validate_recipe_dict(data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """
    Validate a recipe dictionary against the schema, if jsonschema is available.

    Raises:
        jsonschema.ValidationError if the recipe is invalid.
        RuntimeError if jsonschema is not installed and validation is requested.
    """
    if jsonschema is None:
        raise RuntimeError(
            "jsonschema is not installed, cannot validate recipe. "
            "Install with `pip install jsonschema` or disable strict validation."
        )
    jsonschema.validate(instance=data, schema=schema)


# --------------------------------------------------------------------
# Conversion helpers: dict → dataclasses
# --------------------------------------------------------------------


def _band_from_dict(entry: Dict[str, Any]) -> BandConfig:
    """Convert a single band dictionary into a BandConfig."""
    window = entry.get("window_range", {})
    fit_lims_raw = entry.get("fit_lims")

    fit_lims = None
    if isinstance(fit_lims_raw, dict):
        fit_lims = FitLims(
            amp_min=fit_lims_raw.get("amp_min"),
            amp_max=fit_lims_raw.get("amp_max"),
            sigma_min=fit_lims_raw.get("sigma_min"),
            sigma_max=fit_lims_raw.get("sigma_max"),
        )

    # Normalise role for backwards-compatibility:
    #   "must_have" → "must-have"
    #   "must_not"  → "must-not"
    raw_role = str(entry["role"])
    role = raw_role.replace("_", "-")

    # Normalise / validate shape
    raw_shape = str(entry.get("shape", "gaussian")).lower()
    if raw_shape not in {"gaussian", "pseudovoigt", "template"}:
        shape = "gaussian"
    else:
        shape = raw_shape

    eta = entry.get("eta")
    template = entry.get("template")

    return BandConfig(
        name=entry["name"],
        center=float(entry["center"]),
        tol=float(entry["tol"]),
        sigma=float(entry["sigma"]),
        role=role,
        window_min=float(window["min"]),
        window_max=float(window["max"]),
        fit_lims=fit_lims,
        notes=entry.get("notes"),
        shape=shape,
        eta=float(eta) if eta is not None else None,
        template=list(template) if isinstance(template, list) else None,
    )


def _recipe_from_dict(data: Dict[str, Any]) -> RecipeConfig:
    """Convert a validated recipe dictionary into a RecipeConfig dataclass."""
    bands_raw = data.get("bands", [])
    bands = [_band_from_dict(b) for b in bands_raw]

    return RecipeConfig(
        recipe_name=data["recipe_name"],
        recipe_version=data["recipe_version"],
        station=data["station"],
        bands=bands,
        epsilon=float(data["epsilon"]),
        tau=float(data["tau"]),
        kappa_min=float(data["kappa_min"]),
        snr_min=float(data["snr_min"]),
        notes=data.get("notes"),
        raw=data,
    )


# --------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------


def load_recipe(
    recipe_path: Path,
    schema_path: Optional[Path] = None,
    validate: bool = True,
) -> RecipeConfig:
    """
    Load a single QC recipe from a JSONC file.

    Args:
        recipe_path: Path to a recipe file, e.g. recipes/electrolyte_qc.jsonc.
        schema_path: Path to schema.jsonc. If None, defaults to
                     recipe_path.parent / 'schema.jsonc'.
        validate: If True, validate the recipe against the schema using jsonschema.

    Returns:
        RecipeConfig dataclass instance.
    """
    if schema_path is None:
        schema_path = recipe_path.parent / "schema.jsonc"

    recipe_dict = _load_jsonc(recipe_path)

    if validate:
        schema_dict = _load_schema(schema_path)
        _validate_recipe_dict(recipe_dict, schema_dict)

    return _recipe_from_dict(recipe_dict)


def load_recipes_from_index(
    index_path: Path,
    schema_path: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, RecipeConfig]:
    """
    Load all recipes listed in an index.jsonc file.

    index.jsonc can be either:
      - a flat mapping { "recipe_name": "file.jsonc", ... }, or
      - a dict with a 'current' mapping:
            {
              "station_id": "A1",
              "version": "0.1.0",
              "current": {
                  "electrolyte_qc": "electrolyte_qc.jsonc",
                  ...
              }
            }
    """
    if schema_path is None:
        schema_path = index_path.parent / "schema.jsonc"

    index_dict = _load_jsonc(index_path)
    base_dir = index_path.parent

    # Support both flat mapping and {"current": {...}} style
    if (
        isinstance(index_dict, dict)
        and "current" in index_dict
        and isinstance(index_dict["current"], dict)
    ):
        mapping = index_dict["current"]
    else:
        mapping = index_dict

    recipes: Dict[str, RecipeConfig] = {}
    for name, rel_path in mapping.items():
        recipe_file = base_dir / rel_path
        cfg = load_recipe(recipe_file, schema_path=schema_path, validate=validate)
        recipes[name] = cfg

    return recipes


def format_recipe(recipe: RecipeConfig) -> str:
    """
    Return a human-readable summary of a recipe, suitable for CLI logs or debug.

    Example layout:

    Recipe: electrolyte_qc (v0.1.0) @ A1
      epsilon=0.06  tau=0.65  kappa_min=0.60  snr_min=6.0

      Bands:
        name          center   tol   sigma   role        shape      window
        ------------------------------------------------------------------
        PF6           745.0    8.0   6.0     must-have   gaussian   [730.0, 760.0]
        EC_ring_717   717.0   10.0   7.0     watch       gaussian   [700.0, 735.0]
        ...
    """
    lines: List[str] = []

    # Header
    lines.append(
        f"Recipe: {recipe.recipe_name} (v{recipe.recipe_version}) @ {recipe.station}"
    )
    lines.append(
        f"  epsilon={recipe.epsilon:.3f}  "
        f"tau={recipe.tau:.3f}  "
        f"kappa_min={recipe.kappa_min:.3f}  "
        f"snr_min={recipe.snr_min:.1f}"
    )
    if recipe.notes:
        lines.append(f"  notes: {recipe.notes}")

    lines.append("")
    lines.append("  Bands:")
    lines.append(
        "    {name:<14} {center:>7} {tol:>7} {sigma:>7} {role:<10} {shape:<10} {window}".format(
            name="name",
            center="center",
            tol="tol",
            sigma="sigma",
            role="role",
            shape="shape",
            window="window",
        )
    )
    lines.append("    " + "-" * 80)

    for b in recipe.bands:
        window_str = f"[{b.window_min:.1f}, {b.window_max:.1f}]"
        lines.append(
            "    {name:<14} {center:>7.1f} {tol:>7.1f} {sigma:>7.1f} {role:<10} {shape:<10} {window}".format(
                name=b.name[:14],
                center=b.center,
                tol=b.tol,
                sigma=b.sigma,
                role=b.role,
                shape=b.shape,
                window=window_str,
            )
        )

    return "\n".join(lines)
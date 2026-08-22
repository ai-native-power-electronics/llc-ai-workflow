from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "llc-demo-config-v1"
SUPPORTED_TOPOLOGY = "half_bridge_llc_center_tapped"
SUPPORTED_OPERATING_CONDITION = "fixed_input_full_load"
FHA_MODEL_VERSION = "center-tapped-fha-v1"
EQUIVALENT_MODEL_VERSION = "switched-linear-equivalent-v1"


class ConfigurationError(ValueError):
    """A configuration cannot safely enter the engineering workflow."""


EXPECTED_KEYS = {
    "top": {
        "schema_version",
        "run_name",
        "seed",
        "candidate_count",
        "input_spec",
        "design_space",
        "fha_screen",
        "equivalent_solver",
        "decision_thresholds",
        "ml_export",
        "demo",
    },
    "input_spec": {
        "vin_v",
        "vout_v",
        "pout_w",
        "topology",
        "operating_condition",
        "units",
    },
    "input_units": {"vin_v", "vout_v", "pout_w"},
    "design_space": {
        "ln_min",
        "ln_max",
        "q_min",
        "q_max",
        "fr_hz_min",
        "fr_hz_max",
        "turns_ratio_ns_np_min",
        "turns_ratio_ns_np_max",
    },
    "fha_screen": {
        "model_version",
        "fsw_hz_min",
        "fsw_hz_max",
        "frequency_grid_points",
        "gain_relative_error_max",
        "minimum_inductive_phase_deg",
    },
    "equivalent_solver": {
        "model_version",
        "steps_per_cycle",
        "minimum_cycles",
        "maximum_cycles",
        "convergence_check_cycles",
        "convergence_relative_tolerance",
        "measurement_cycles",
        "series_resistance_ohm",
        "absolute_current_limit_a",
        "absolute_voltage_limit_v",
        "timeout_seconds",
    },
    "decision_thresholds": {
        "vout_relative_error_max",
        "pout_relative_error_max",
        "power_ratio_min_percent",
        "power_ratio_max_percent",
        "fsw_hz_min",
        "fsw_hz_max",
        "require_low_side_commutation_proxy",
        "require_high_side_commutation_proxy",
    },
    "ml_export": {"split_seed", "train_fraction", "validation_fraction", "test_fraction"},
    "demo": {"include_forced_failure_case"},
}


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _unknown_keys(section: str, data: Any, expected: set[str], errors: list[str]) -> None:
    if not isinstance(data, dict):
        errors.append(f"CONFIGURATION_ERROR: {section} must be an object")
        return
    unknown = sorted(set(data) - expected)
    missing = sorted(expected - set(data))
    for key in unknown:
        errors.append(f"CONFIGURATION_ERROR: unknown field {section}.{key}")
    for key in missing:
        errors.append(f"CONFIGURATION_ERROR: missing field {section}.{key}")


def _positive(section: dict[str, Any], key: str, label: str, errors: list[str]) -> None:
    value = section.get(key)
    if not _is_number(value) or value <= 0:
        errors.append(f"CONFIGURATION_ERROR: {label} must be a positive number")


def _range(section: dict[str, Any], low: str, high: str, label: str, errors: list[str]) -> None:
    _positive(section, low, low, errors)
    _positive(section, high, high, errors)
    if _is_number(section.get(low)) and _is_number(section.get(high)) and section[low] >= section[high]:
        errors.append(f"CONFIGURATION_ERROR: {low} must be lower than {high} ({label})")


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ConfigurationError("CONFIGURATION_ERROR: top-level value must be an object")
    errors: list[str] = []
    _unknown_keys("config", config, EXPECTED_KEYS["top"], errors)
    if config.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"CONFIGURATION_ERROR: schema_version must be {SCHEMA_VERSION!r}"
        )
    if not isinstance(config.get("run_name"), str) or not config.get("run_name", "").strip():
        errors.append("CONFIGURATION_ERROR: run_name must be a non-empty string")
    if not isinstance(config.get("seed"), int) or isinstance(config.get("seed"), bool):
        errors.append("CONFIGURATION_ERROR: seed must be an integer")
    count = config.get("candidate_count")
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 10000:
        errors.append("CONFIGURATION_ERROR: candidate_count must be an integer from 1 to 10000")

    spec = config.get("input_spec", {})
    _unknown_keys("input_spec", spec, EXPECTED_KEYS["input_spec"], errors)
    if isinstance(spec, dict):
        for key in ("vin_v", "vout_v", "pout_w"):
            _positive(spec, key, f"input_spec.{key}", errors)
        for key in ("topology", "operating_condition"):
            if not isinstance(spec.get(key), str) or not spec.get(key, "").strip():
                errors.append(f"CONFIGURATION_ERROR: input_spec.{key} must be a non-empty string")
        if spec.get("topology") != SUPPORTED_TOPOLOGY:
            errors.append(
                "CONFIGURATION_ERROR: this release only supports "
                f"{SUPPORTED_TOPOLOGY}"
            )
        if spec.get("operating_condition") != SUPPORTED_OPERATING_CONDITION:
            errors.append(
                "CONFIGURATION_ERROR: this release only supports operating_condition "
                f"{SUPPORTED_OPERATING_CONDITION}"
            )
        units = spec.get("units", {})
        _unknown_keys("input_spec.units", units, EXPECTED_KEYS["input_units"], errors)
        expected_units = {"vin_v": "V", "vout_v": "V", "pout_w": "W"}
        if isinstance(units, dict):
            for key, expected in expected_units.items():
                if units.get(key) != expected:
                    errors.append(
                        f"CONFIGURATION_ERROR: input_spec.units.{key} must be {expected!r}"
                    )

    space = config.get("design_space", {})
    _unknown_keys("design_space", space, EXPECTED_KEYS["design_space"], errors)
    if isinstance(space, dict):
        _range(space, "ln_min", "ln_max", "inductance ratio", errors)
        _range(space, "q_min", "q_max", "quality factor", errors)
        _range(space, "fr_hz_min", "fr_hz_max", "resonant frequency", errors)
        _range(
            space,
            "turns_ratio_ns_np_min",
            "turns_ratio_ns_np_max",
            "turns ratio",
            errors,
        )

    fha = config.get("fha_screen", {})
    _unknown_keys("fha_screen", fha, EXPECTED_KEYS["fha_screen"], errors)
    if isinstance(fha, dict):
        if fha.get("model_version") != FHA_MODEL_VERSION:
            errors.append(
                "CONFIGURATION_ERROR: FHA model_version is code-owned and must be "
                f"{FHA_MODEL_VERSION}"
            )
        _range(fha, "fsw_hz_min", "fsw_hz_max", "FHA switching frequency", errors)
        _positive(fha, "gain_relative_error_max", "fha_screen.gain_relative_error_max", errors)
        points = fha.get("frequency_grid_points")
        if not isinstance(points, int) or isinstance(points, bool) or points < 3:
            errors.append("CONFIGURATION_ERROR: fha_screen.frequency_grid_points must be an integer >= 3")
        if not _is_number(fha.get("minimum_inductive_phase_deg")):
            errors.append("CONFIGURATION_ERROR: fha_screen.minimum_inductive_phase_deg must be numeric")

    solver = config.get("equivalent_solver", {})
    _unknown_keys("equivalent_solver", solver, EXPECTED_KEYS["equivalent_solver"], errors)
    if isinstance(solver, dict):
        if solver.get("model_version") != EQUIVALENT_MODEL_VERSION:
            errors.append(
                "CONFIGURATION_ERROR: equivalent solver model_version is code-owned and must be "
                f"{EQUIVALENT_MODEL_VERSION}"
            )
        for key in (
            "steps_per_cycle",
            "minimum_cycles",
            "maximum_cycles",
            "convergence_check_cycles",
            "measurement_cycles",
        ):
            value = solver.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"CONFIGURATION_ERROR: equivalent_solver.{key} must be a positive integer")
        if isinstance(solver.get("steps_per_cycle"), int) and solver["steps_per_cycle"] % 2:
            errors.append("CONFIGURATION_ERROR: equivalent_solver.steps_per_cycle must be even")
        if (
            isinstance(solver.get("minimum_cycles"), int)
            and isinstance(solver.get("maximum_cycles"), int)
            and solver["minimum_cycles"] > solver["maximum_cycles"]
        ):
            errors.append("CONFIGURATION_ERROR: minimum_cycles must not exceed maximum_cycles")
        for key in (
            "convergence_relative_tolerance",
            "series_resistance_ohm",
            "absolute_current_limit_a",
            "absolute_voltage_limit_v",
            "timeout_seconds",
        ):
            _positive(solver, key, f"equivalent_solver.{key}", errors)

    thresholds = config.get("decision_thresholds", {})
    _unknown_keys("decision_thresholds", thresholds, EXPECTED_KEYS["decision_thresholds"], errors)
    if isinstance(thresholds, dict):
        for key in (
            "vout_relative_error_max",
            "pout_relative_error_max",
            "power_ratio_min_percent",
            "power_ratio_max_percent",
            "fsw_hz_min",
            "fsw_hz_max",
        ):
            _positive(thresholds, key, f"decision_thresholds.{key}", errors)
        if (
            _is_number(thresholds.get("power_ratio_min_percent"))
            and _is_number(thresholds.get("power_ratio_max_percent"))
            and thresholds["power_ratio_min_percent"] >= thresholds["power_ratio_max_percent"]
        ):
            errors.append("CONFIGURATION_ERROR: power_ratio_min_percent must be lower than power_ratio_max_percent")
        if (
            _is_number(thresholds.get("fsw_hz_min"))
            and _is_number(thresholds.get("fsw_hz_max"))
            and thresholds["fsw_hz_min"] >= thresholds["fsw_hz_max"]
        ):
            errors.append("CONFIGURATION_ERROR: decision fsw_hz_min must be lower than fsw_hz_max")
        for key in (
            "require_low_side_commutation_proxy",
            "require_high_side_commutation_proxy",
        ):
            if not isinstance(thresholds.get(key), bool):
                errors.append(f"CONFIGURATION_ERROR: decision_thresholds.{key} must be boolean")

    ml_export = config.get("ml_export", {})
    _unknown_keys("ml_export", ml_export, EXPECTED_KEYS["ml_export"], errors)
    if isinstance(ml_export, dict):
        if not isinstance(ml_export.get("split_seed"), int) or isinstance(ml_export.get("split_seed"), bool):
            errors.append("CONFIGURATION_ERROR: ml_export.split_seed must be an integer")
        fractions = [ml_export.get(key) for key in ("train_fraction", "validation_fraction", "test_fraction")]
        if not all(_is_number(value) and value > 0 for value in fractions):
            errors.append("CONFIGURATION_ERROR: ML split fractions must be positive numbers")
        elif abs(sum(fractions) - 1.0) > 1e-12:
            errors.append("CONFIGURATION_ERROR: ML split fractions must sum to 1.0")

    demo = config.get("demo", {})
    _unknown_keys("demo", demo, EXPECTED_KEYS["demo"], errors)
    if isinstance(demo, dict) and not isinstance(demo.get("include_forced_failure_case"), bool):
        errors.append("CONFIGURATION_ERROR: demo.include_forced_failure_case must be boolean")

    if errors:
        raise ConfigurationError("\n".join(errors))
    return copy.deepcopy(config)


def load_and_validate_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"CONFIGURATION_ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"CONFIGURATION_ERROR: invalid JSON: {exc}") from exc
    return validate_config(config)

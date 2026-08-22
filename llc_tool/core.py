from __future__ import annotations

import math
import random
import time
from typing import Any

from .config import EQUIVALENT_MODEL_VERSION, FHA_MODEL_VERSION
from .io_utils import canonical_json, sha256_bytes


RECORD_SCHEMA_VERSION = "llc-engineering-record-v2"


def derive_run_definition_id(config: dict[str, Any]) -> str:
    """Hash every calculation-affecting input while excluding the display name."""
    definition = {
        key: value
        for key, value in config.items()
        if key not in {"run_name", "demo"}
    }
    material = {
        "configuration": definition,
        "implementation_contract": {
            "fha_model_version": FHA_MODEL_VERSION,
            "equivalent_model_version": EQUIVALENT_MODEL_VERSION,
        },
    }
    digest = sha256_bytes(canonical_json(material).encode("utf-8"))
    return f"run-definition-{digest[:20]}"


def _latin_hypercube_values(
    count: int, low: float, high: float, rng: random.Random
) -> list[float]:
    unit = [(index + rng.random()) / count for index in range(count)]
    rng.shuffle(unit)
    return [low + value * (high - low) for value in unit]


def calculate_components(
    *,
    ln: float,
    q: float,
    fr_hz: float,
    turns_ratio_ns_np: float,
    vin_v: float,
    vout_v: float,
    pout_w: float,
) -> dict[str, float]:
    del vin_v
    load_ohm = vout_v * vout_v / pout_w
    turns_ratio_np_ns = 1.0 / turns_ratio_ns_np
    rac_primary_ohm = (8.0 / (math.pi**2)) * (turns_ratio_np_ns**2) * load_ohm
    z0_ohm = q * rac_primary_ohm
    lr_h = z0_ohm / (2.0 * math.pi * fr_hz)
    cr_f = 1.0 / (2.0 * math.pi * fr_hz * z0_ohm)
    lm_h = ln * lr_h
    return {
        "load_ohm": load_ohm,
        "turns_ratio_np_ns": turns_ratio_np_ns,
        "rac_primary_ohm": rac_primary_ohm,
        "z0_ohm": z0_ohm,
        "lr_h": lr_h,
        "cr_f": cr_f,
        "lm_h": lm_h,
    }


def evaluate_fha(candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    screen = config["fha_screen"]
    spec = config["input_spec"]
    design = candidate["design_variables"]
    required_gain = (
        2.0 * design["turns_ratio_np_ns"] * spec["vout_v"] / spec["vin_v"]
    )
    count = int(screen["frequency_grid_points"])
    f_min = float(screen["fsw_hz_min"])
    f_max = float(screen["fsw_hz_max"])
    min_phase = float(screen["minimum_inductive_phase_deg"])
    best: tuple[float, float, float, float] | None = None
    min_gain = math.inf
    max_gain = -math.inf
    max_phase = -math.inf
    for index in range(count):
        frequency = f_min + (f_max - f_min) * index / (count - 1)
        omega = 2.0 * math.pi * frequency
        z_lm = complex(0.0, omega * design["lm_h"])
        z_lr = complex(0.0, omega * design["lr_h"])
        z_cr = complex(0.0, -1.0 / (omega * design["cr_f"]))
        z_parallel = z_lm * design["rac_primary_ohm"] / (
            z_lm + design["rac_primary_ohm"]
        )
        z_input = z_lr + z_cr + z_parallel
        gain = abs(z_parallel / z_input)
        phase_deg = math.degrees(math.atan2(z_input.imag, z_input.real))
        min_gain = min(min_gain, gain)
        max_gain = max(max_gain, gain)
        max_phase = max(max_phase, phase_deg)
        if phase_deg >= min_phase:
            relative_error = abs(gain - required_gain) / required_gain
            if best is None or relative_error < best[0]:
                best = (relative_error, frequency, gain, phase_deg)

    reason_codes: list[str]
    if best is None:
        gate_result = "reject"
        reason_codes = ["FHA_NO_INDUCTIVE_OPERATING_POINT"]
        relative_error = frequency = gain = phase_deg = None
    else:
        relative_error, frequency, gain, phase_deg = best
        if relative_error > float(screen["gain_relative_error_max"]):
            gate_result = "reject"
            reason_codes = [
                "FHA_GAIN_TARGET_NOT_REACHED_WITHIN_ALLOWED_SEARCH_AND_PHASE_REGION"
            ]
        else:
            gate_result = "pass"
            reason_codes = ["FHA_GAIN_AND_INDUCTIVE_PHASE_PASS"]

    warnings: list[str] = []
    if gate_result == "pass" and frequency is not None and (
        math.isclose(frequency, f_min, rel_tol=0.0, abs_tol=1e-9)
        or math.isclose(frequency, f_max, rel_tol=0.0, abs_tol=1e-9)
    ):
        warnings.append("FHA_SEARCH_BOUNDARY_HIT")
    if (
        gate_result == "reject"
        and frequency is not None
        and math.isclose(frequency, f_max, rel_tol=0.0, abs_tol=1e-9)
    ):
        warnings.append("FHA_REJECT_AT_UPPER_SEARCH_BOUNDARY")

    return {
        "method": "fundamental-harmonic approximation",
        "model_version": FHA_MODEL_VERSION,
        "execution_status": "completed",
        "gate_result": gate_result,
        "operating_point_id": candidate["operating_point_id"],
        "metrics": {
            "required_gain": required_gain,
            "best_gain": gain,
            "best_frequency_hz": frequency,
            "best_input_phase_deg": phase_deg,
            "gain_relative_error": relative_error,
            "minimum_gain_on_grid": min_gain,
            "maximum_gain_on_grid": max_gain,
            "maximum_input_phase_deg": max_phase,
        },
        "thresholds": {
            "gain_relative_error_max": screen["gain_relative_error_max"],
            "minimum_inductive_phase_deg": screen["minimum_inductive_phase_deg"],
            "fsw_hz_min": f_min,
            "fsw_hz_max": f_max,
        },
        "reason_codes": reason_codes,
        "warnings": warnings,
    }


def fha_response_curve(
    candidate: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    """Return the configured FHA sweep for human explanation, not a new authority."""
    screen = config["fha_screen"]
    spec = config["input_spec"]
    design = candidate["design_variables"]
    required_gain = (
        2.0 * design["turns_ratio_np_ns"] * spec["vout_v"] / spec["vin_v"]
    )
    count = int(screen["frequency_grid_points"])
    f_min = float(screen["fsw_hz_min"])
    f_max = float(screen["fsw_hz_max"])
    points: list[dict[str, float]] = []
    for index in range(count):
        frequency = f_min + (f_max - f_min) * index / (count - 1)
        omega = 2.0 * math.pi * frequency
        z_lm = complex(0.0, omega * design["lm_h"])
        z_lr = complex(0.0, omega * design["lr_h"])
        z_cr = complex(0.0, -1.0 / (omega * design["cr_f"]))
        z_parallel = z_lm * design["rac_primary_ohm"] / (
            z_lm + design["rac_primary_ohm"]
        )
        z_input = z_lr + z_cr + z_parallel
        points.append(
            {
                "frequency_hz": frequency,
                "gain": abs(z_parallel / z_input),
                "input_phase_deg": math.degrees(
                    math.atan2(z_input.imag, z_input.real)
                ),
            }
        )
    return {
        "required_gain": required_gain,
        "minimum_inductive_phase_deg": float(
            screen["minimum_inductive_phase_deg"]
        ),
        "fsw_hz_min": f_min,
        "fsw_hz_max": f_max,
        "points": points,
    }


def generate_candidates(
    config: dict[str, Any], *, execution_id: str | None = None
) -> list[dict[str, Any]]:
    count = int(config["candidate_count"])
    rng = random.Random(int(config["seed"]))
    space = config["design_space"]
    dimensions = {
        "ln": _latin_hypercube_values(count, space["ln_min"], space["ln_max"], rng),
        "q": _latin_hypercube_values(count, space["q_min"], space["q_max"], rng),
        "fr_hz": _latin_hypercube_values(
            count, space["fr_hz_min"], space["fr_hz_max"], rng
        ),
        "turns_ratio_ns_np": _latin_hypercube_values(
            count,
            space["turns_ratio_ns_np_min"],
            space["turns_ratio_ns_np_max"],
            rng,
        ),
    }
    spec = config["input_spec"]
    run_definition_id = derive_run_definition_id(config)
    bound_execution_id = execution_id or f"unbound-{run_definition_id}"
    spec_hash = sha256_bytes(canonical_json(spec).encode("utf-8"))
    candidates: list[dict[str, Any]] = []
    for index in range(count):
        base = {key: values[index] for key, values in dimensions.items()}
        components = calculate_components(
            **base,
            vin_v=spec["vin_v"],
            vout_v=spec["vout_v"],
            pout_w=spec["pout_w"],
        )
        design = {**base, **components}
        hardware_design = {
            "lr_h": design["lr_h"],
            "cr_f": design["cr_f"],
            "lm_h": design["lm_h"],
            "turns_ratio_ns_np": design["turns_ratio_ns_np"],
        }
        operating_point = {
            "vin_v": spec["vin_v"],
            "vout_target_v": spec["vout_v"],
            "pout_target_w": spec["pout_w"],
            "load_ohm": design["load_ohm"],
            "temperature_c": None,
            "control_condition": spec["operating_condition"],
        }
        design_hash = sha256_bytes(
            canonical_json(hardware_design).encode("utf-8")
        )
        operating_point_hash = sha256_bytes(
            canonical_json(operating_point).encode("utf-8")
        )
        candidate_id = f"llc-{index + 1:04d}"
        candidate: dict[str, Any] = {
            "schema_version": RECORD_SCHEMA_VERSION,
            "candidate_id": candidate_id,
            "design_id": f"design-{design_hash[:16]}",
            "operating_point_id": f"op-{operating_point_hash[:16]}",
            "run_definition_id": run_definition_id,
            "execution_id": bound_execution_id,
            "method_definition_id": (
                f"{run_definition_id}:{candidate_id}:{EQUIVALENT_MODEL_VERSION}"
            ),
            "method_run_id": (
                f"{bound_execution_id}:{candidate_id}:{EQUIVALENT_MODEL_VERSION}"
            ),
            "input_spec": {
                "spec_hash": spec_hash,
                "values": {
                    key: value for key, value in spec.items() if key != "units"
                },
                "units": spec["units"],
            },
            "hardware_design": hardware_design,
            "operating_point": operating_point,
            "design_variables": design,
            "units": {
                "fr_hz": "Hz",
                "lr_h": "H",
                "lm_h": "H",
                "cr_f": "F",
                "load_ohm": "ohm",
                "rac_primary_ohm": "ohm",
                "z0_ohm": "ohm",
                "turns_ratio_ns_np": "1",
                "turns_ratio_np_ns": "1",
                "ln": "1",
                "q": "1",
            },
        }
        candidate["fha_screen"] = evaluate_fha(candidate, config)
        candidate["method_inputs"] = {
            "rac_primary_ohm": design["rac_primary_ohm"],
            "selected_frequency_hz": candidate["fha_screen"]["metrics"][
                "best_frequency_hz"
            ],
            "fha_model_version": FHA_MODEL_VERSION,
            "equivalent_solver": {
                **dict(config["equivalent_solver"]),
                "model_version": EQUIVALENT_MODEL_VERSION,
            },
        }
        candidates.append(candidate)
    return candidates


def _equivalent_step(
    state: tuple[float, float, float],
    drive_v: float,
    dt: float,
    lr_h: float,
    cr_f: float,
    lm_h: float,
    rac_ohm: float,
    series_resistance_ohm: float,
) -> tuple[float, float, float]:
    def derivative(values: tuple[float, float, float]) -> tuple[float, float, float]:
        i_lr, v_cr, i_lm = values
        v_parallel = rac_ohm * (i_lr - i_lm)
        return (
            (drive_v - series_resistance_ohm * i_lr - v_cr - v_parallel) / lr_h,
            i_lr / cr_f,
            v_parallel / lm_h,
        )

    k1 = derivative(state)
    k2_state = tuple(state[index] + 0.5 * dt * k1[index] for index in range(3))
    k2 = derivative(k2_state)
    k3_state = tuple(state[index] + 0.5 * dt * k2[index] for index in range(3))
    k3 = derivative(k3_state)
    k4_state = tuple(state[index] + dt * k3[index] for index in range(3))
    k4 = derivative(k4_state)
    return tuple(
        state[index]
        + dt * (k1[index] + 2.0 * k2[index] + 2.0 * k3[index] + k4[index]) / 6.0
        for index in range(3)
    )


def simulate_design(
    *,
    design: dict[str, float],
    input_spec: dict[str, Any],
    frequency_hz: float,
    solver: dict[str, Any],
) -> dict[str, Any]:
    steps_per_cycle = int(solver["steps_per_cycle"])
    dt = 1.0 / (frequency_hz * steps_per_cycle)
    state = (0.0, 0.0, 0.0)
    started = time.perf_counter()
    converged = False
    failure_reasons: list[str] = []
    previous_checkpoint: tuple[float, float, float] | None = None
    cycles_completed = 0

    def drive_for_step(step: int) -> float:
        return (
            input_spec["vin_v"] / 2.0
            if step < steps_per_cycle // 2
            else -input_spec["vin_v"] / 2.0
        )

    for cycle in range(1, int(solver["maximum_cycles"]) + 1):
        for step in range(steps_per_cycle):
            state = _equivalent_step(
                state,
                drive_for_step(step),
                dt,
                design["lr_h"],
                design["cr_f"],
                design["lm_h"],
                design["rac_primary_ohm"],
                float(solver["series_resistance_ohm"]),
            )
            if not all(math.isfinite(value) for value in state):
                failure_reasons.append("EQUIVALENT_MODEL_NONFINITE_STATE")
                break
            if max(abs(state[0]), abs(state[2])) > float(
                solver["absolute_current_limit_a"]
            ):
                failure_reasons.append("EQUIVALENT_MODEL_CURRENT_LIMIT")
                break
            if abs(state[1]) > float(solver["absolute_voltage_limit_v"]):
                failure_reasons.append("EQUIVALENT_MODEL_VOLTAGE_LIMIT")
                break
            if time.perf_counter() - started > float(solver["timeout_seconds"]):
                failure_reasons.append("METHOD_TIMEOUT")
                break
        cycles_completed = cycle
        if failure_reasons:
            break
        if (
            cycle >= int(solver["minimum_cycles"])
            and cycle % int(solver["convergence_check_cycles"]) == 0
        ):
            if previous_checkpoint is not None:
                scales = (
                    max(1.0, abs(state[0]), abs(previous_checkpoint[0])),
                    max(input_spec["vin_v"], abs(state[1]), abs(previous_checkpoint[1])),
                    max(1.0, abs(state[2]), abs(previous_checkpoint[2])),
                )
                relative_delta = max(
                    abs(state[index] - previous_checkpoint[index]) / scales[index]
                    for index in range(3)
                )
                if relative_delta <= float(solver["convergence_relative_tolerance"]):
                    converged = True
                    break
            previous_checkpoint = state

    if not converged and not failure_reasons:
        failure_reasons.append("EQUIVALENT_MODEL_STEADY_STATE_NOT_REACHED")

    samples: list[tuple[float, float, float, float, float, float]] = []
    low_side_currents: list[float] = []
    high_side_currents: list[float] = []
    if converged:
        sample_index = 0
        for _ in range(int(solver["measurement_cycles"])):
            for step in range(steps_per_cycle):
                drive_v = drive_for_step(step)
                state = _equivalent_step(
                    state,
                    drive_v,
                    dt,
                    design["lr_h"],
                    design["cr_f"],
                    design["lm_h"],
                    design["rac_primary_ohm"],
                    float(solver["series_resistance_ohm"]),
                )
                i_lr, v_cr, i_lm = state
                v_parallel = design["rac_primary_ohm"] * (i_lr - i_lm)
                samples.append(
                    (sample_index * dt, drive_v, i_lr, i_lm, v_cr, v_parallel)
                )
                if step == steps_per_cycle // 2 - 1:
                    low_side_currents.append(i_lr)
                if step == steps_per_cycle - 1:
                    high_side_currents.append(i_lr)
                sample_index += 1

    metrics: dict[str, float] = {}
    execution_status = "failed"
    if samples:
        sample_count = len(samples)
        v_parallel_values = [row[5] for row in samples]
        cosine = 0.0
        sine = 0.0
        for index, value in enumerate(v_parallel_values):
            phase = 2.0 * math.pi * ((index % steps_per_cycle) + 1) / steps_per_cycle
            cosine += value * math.cos(phase)
            sine += value * math.sin(phase)
        fundamental_peak = 2.0 * math.hypot(cosine, sine) / sample_count
        output_voltage = (
            math.pi * fundamental_peak / (4.0 * design["turns_ratio_np_ns"])
        )
        output_power = output_voltage * output_voltage / design["load_ohm"]
        input_power = sum(row[1] * row[2] for row in samples) / sample_count
        power_ratio = (
            100.0 * output_power / input_power if input_power > 0.0 else math.nan
        )
        i_lr_values = [row[2] for row in samples]
        i_lm_values = [row[3] for row in samples]
        v_cr_values = [row[4] for row in samples]
        metrics = {
            "output_voltage_v": output_voltage,
            "output_power_w": output_power,
            "input_power_w": input_power,
            "equivalent_model_power_ratio_percent": power_ratio,
            "switching_frequency_hz": frequency_hz,
            "resonant_current_rms_a": math.sqrt(
                sum(value * value for value in i_lr_values) / sample_count
            ),
            "resonant_current_peak_a": max(abs(value) for value in i_lr_values),
            "magnetizing_current_peak_a": max(abs(value) for value in i_lm_values),
            "resonant_capacitor_voltage_rms_v": math.sqrt(
                sum(value * value for value in v_cr_values) / sample_count
            ),
            "resonant_capacitor_voltage_peak_v": max(
                abs(value) for value in v_cr_values
            ),
            "low_side_commutation_current_sign_proxy": (
                1.0 if low_side_currents and min(low_side_currents) > 0.0 else 0.0
            ),
            "high_side_commutation_current_sign_proxy": (
                1.0 if high_side_currents and max(high_side_currents) < 0.0 else 0.0
            ),
            "tank_fundamental_peak_v": fundamental_peak,
        }
        if all(math.isfinite(value) for value in metrics.values()):
            execution_status = "completed"
        else:
            failure_reasons.append("EQUIVALENT_MODEL_INVALID_TELEMETRY")

    elapsed = time.perf_counter() - started
    if execution_status != "completed" and not failure_reasons:
        failure_reasons.append("METHOD_DID_NOT_PRODUCE_VALID_RESULT")
    return {
        "method": "time-stepped linear-equivalent evaluation",
        "model_version": EQUIVALENT_MODEL_VERSION,
        "execution_status": execution_status,
        "convergence": {
            "converged": converged,
            "cycles_completed": cycles_completed,
            "time_step_seconds": dt,
            "reason_codes": failure_reasons,
        },
        "measurement_window": {
            "cycles": solver["measurement_cycles"],
            "samples": len(samples),
        },
        "metrics": metrics,
        "elapsed_seconds": elapsed,
        "reason_codes": failure_reasons or ["EQUIVALENT_MODEL_CONVERGED"],
        "samples": samples,
    }


def classify_evaluation(
    evaluation: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    if evaluation["execution_status"] != "completed":
        return {
            "execution_status": "failed",
            "gate_result": "not_applicable",
            "engineering_approval": "pending",
            "reason_codes": evaluation["reason_codes"],
            "score": None,
        }

    metrics = evaluation["metrics"]
    spec = config["input_spec"]
    thresholds = config["decision_thresholds"]
    voltage_error = abs(metrics["output_voltage_v"] - spec["vout_v"]) / spec["vout_v"]
    power_error = abs(metrics["output_power_w"] - spec["pout_w"]) / spec["pout_w"]
    reason_codes: list[str] = []
    if voltage_error > thresholds["vout_relative_error_max"]:
        reason_codes.append("OUTPUT_VOLTAGE_OUT_OF_TOLERANCE")
    if power_error > thresholds["pout_relative_error_max"]:
        reason_codes.append("OUTPUT_POWER_OUT_OF_TOLERANCE")
    if not (
        thresholds["power_ratio_min_percent"]
        <= metrics["equivalent_model_power_ratio_percent"]
        <= thresholds["power_ratio_max_percent"]
    ):
        reason_codes.append("EQUIVALENT_MODEL_POWER_RATIO_OUT_OF_BOUNDS")
    if not (
        thresholds["fsw_hz_min"]
        <= metrics["switching_frequency_hz"]
        <= thresholds["fsw_hz_max"]
    ):
        reason_codes.append("SWITCHING_FREQUENCY_OUT_OF_BOUNDS")
    if (
        thresholds["require_low_side_commutation_proxy"]
        and metrics["low_side_commutation_current_sign_proxy"] < 0.5
    ):
        reason_codes.append("LOW_SIDE_COMMUTATION_CURRENT_SIGN_PROXY_FAIL")
    if (
        thresholds["require_high_side_commutation_proxy"]
        and metrics["high_side_commutation_current_sign_proxy"] < 0.5
    ):
        reason_codes.append("HIGH_SIDE_COMMUTATION_CURRENT_SIGN_PROXY_FAIL")
    score = (
        10.0 * voltage_error
        + 5.0 * power_error
        + max(0.0, 95.0 - metrics["equivalent_model_power_ratio_percent"]) / 100.0
    )
    return {
        "execution_status": "completed",
        "gate_result": "reject" if reason_codes else "pass",
        "engineering_approval": "pending",
        "reason_codes": reason_codes or ["AUTOMATED_ELECTRICAL_GATE_PASS"],
        "score": score,
    }


def make_record(candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if candidate["fha_screen"]["gate_result"] == "reject":
        return {
            **candidate,
            "time_domain_evaluation": {
                "method": "time-stepped linear-equivalent evaluation",
                "model_version": EQUIVALENT_MODEL_VERSION,
                "execution_status": "not_run",
                "reason_codes": ["NOT_RUN_AFTER_FHA_REJECT"],
                "metrics": {},
            },
            "decision_contract": {
                "execution_status": "not_run",
                "gate_result": "reject",
                "engineering_approval": "pending",
                "reason_codes": candidate["fha_screen"]["reason_codes"],
                "score": None,
            },
        }

    frequency = float(candidate["fha_screen"]["metrics"]["best_frequency_hz"])
    evaluation = simulate_design(
        design=candidate["design_variables"],
        input_spec=config["input_spec"],
        frequency_hz=frequency,
        solver=config["equivalent_solver"],
    )
    samples = evaluation.pop("samples")
    del samples
    decision = classify_evaluation(evaluation, config)
    return {
        **candidate,
        "time_domain_evaluation": evaluation,
        "decision_contract": decision,
    }


def forced_failure_case(
    config: dict[str, Any], *, execution_id: str | None = None
) -> dict[str, Any]:
    run_definition_id = derive_run_definition_id(config)
    bound_execution_id = execution_id or f"unbound-{run_definition_id}"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "candidate_id": "demo-forced-failure",
        "design_id": "not_applicable",
        "operating_point_id": "not_applicable",
        "run_definition_id": run_definition_id,
        "execution_id": bound_execution_id,
        "method_definition_id": (
            f"{run_definition_id}:forced-pipeline-test:forced-failure-fixture-v1"
        ),
        "method_run_id": (
            f"{bound_execution_id}:forced-pipeline-test:forced-failure-fixture-v1"
        ),
        "synthetic_demo_case": True,
        "purpose": "Demonstrate that a method failure is never converted to an electrical rejection.",
        "time_domain_evaluation": {
            "method": "forced pipeline timeout test",
            "model_version": "forced-failure-fixture-v1",
            "execution_status": "failed",
            "metrics": {},
            "reason_codes": ["FORCED_PIPELINE_TIMEOUT_TEST"],
        },
        "decision_contract": {
            "execution_status": "failed",
            "gate_result": "not_applicable",
            "engineering_approval": "pending",
            "reason_codes": ["FORCED_PIPELINE_TIMEOUT_TEST"],
            "score": None,
        },
    }


def legacy_metric_view(metrics: dict[str, float]) -> dict[str, float]:
    """Map v2 terminology to the archived v1 metric names for tolerant replay."""
    return {
        "vout_real": metrics["output_voltage_v"],
        "pout_avg": metrics["output_power_w"],
        "pin_avg": metrics["input_power_w"],
        "efficiency": metrics["equivalent_model_power_ratio_percent"],
        "fsw": metrics["switching_frequency_hz"],
        "ilr_rms": metrics["resonant_current_rms_a"],
        "ilr_peak": metrics["resonant_current_peak_a"],
        "ilm_peak": metrics["magnetizing_current_peak_a"],
        "vcr_rms": metrics["resonant_capacitor_voltage_rms_v"],
        "vcr_peak": metrics["resonant_capacitor_voltage_peak_v"],
        "zvs_ls_flag": metrics["low_side_commutation_current_sign_proxy"],
        "zvs_hs_flag": metrics["high_side_commutation_current_sign_proxy"],
        "tank_fundamental_peak_v": metrics["tank_fundamental_peak_v"],
    }

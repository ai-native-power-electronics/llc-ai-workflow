from __future__ import annotations

import csv
import json
import platform
import re
import sys
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from .config import (
    EQUIVALENT_MODEL_VERSION,
    ConfigurationError,
    validate_config,
)
from .core import (
    classify_evaluation,
    derive_run_definition_id,
    forced_failure_case,
    generate_candidates,
    legacy_metric_view,
    make_record,
    simulate_design,
)
from .io_utils import (
    canonical_json,
    load_json,
    sha256_bytes,
    sha256_file,
    utc_now,
    write_json,
    write_jsonl,
)
from .report import write_html_report, write_plots, write_verification_failure_html


ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?i)(?:(?<![a-z])[a-z]:[\\/]|/(?:users|home)/)"
)


def _prepare_empty_output(path: Path) -> Path:
    output = path.resolve()
    if output.exists() and any(output.iterdir()):
        raise ConfigurationError(
            f"OUTPUT_ERROR: destination is not empty: {output}. Choose a new output directory."
        )
    output.mkdir(parents=True, exist_ok=True)
    return output


def _write_waveform(
    path: Path, samples: list[tuple[float, float, float, float, float, float]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["time_s", "drive_v", "i_lr_a", "i_lm_a", "v_cr_v", "v_parallel_v"]
        )
        writer.writerows(samples)


def _write_candidate_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = [
        "candidate_id",
        "design_id",
        "operating_point_id",
        "run_definition_id",
        "execution_id",
        "method_definition_id",
        "method_run_id",
        "execution_status",
        "gate_result",
        "engineering_approval",
        "fha_gate_result",
        "fha_warning_codes",
        "ln",
        "q",
        "fr_hz",
        "turns_ratio_ns_np",
        "fha_best_frequency_hz",
        "output_voltage_v",
        "output_power_w",
        "equivalent_model_power_ratio_percent",
        "resonant_current_rms_a",
        "resonant_capacitor_voltage_peak_v",
        "target_available",
        "reason_codes",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            design = record["design_variables"]
            metrics = record["time_domain_evaluation"].get("metrics", {})
            contract = record["decision_contract"]
            writer.writerow(
                {
                    "candidate_id": record["candidate_id"],
                    "design_id": record["design_id"],
                    "operating_point_id": record["operating_point_id"],
                    "run_definition_id": record["run_definition_id"],
                    "execution_id": record["execution_id"],
                    "method_definition_id": record["method_definition_id"],
                    "method_run_id": record["method_run_id"],
                    "execution_status": contract["execution_status"],
                    "gate_result": contract["gate_result"],
                    "engineering_approval": contract["engineering_approval"],
                    "fha_gate_result": record["fha_screen"]["gate_result"],
                    "fha_warning_codes": "|".join(
                        record["fha_screen"].get("warnings", [])
                    ),
                    "ln": design["ln"],
                    "q": design["q"],
                    "fr_hz": design["fr_hz"],
                    "turns_ratio_ns_np": design["turns_ratio_ns_np"],
                    "fha_best_frequency_hz": record["fha_screen"]["metrics"][
                        "best_frequency_hz"
                    ],
                    "output_voltage_v": metrics.get("output_voltage_v"),
                    "output_power_w": metrics.get("output_power_w"),
                    "equivalent_model_power_ratio_percent": metrics.get(
                        "equivalent_model_power_ratio_percent"
                    ),
                    "resonant_current_rms_a": metrics.get("resonant_current_rms_a"),
                    "resonant_capacitor_voltage_peak_v": metrics.get(
                        "resonant_capacitor_voltage_peak_v"
                    ),
                    "target_available": str(
                        contract["execution_status"] == "completed"
                    ).lower(),
                    "reason_codes": "|".join(contract["reason_codes"]),
                }
            )


def _split_for_design(design_id: str, config: dict[str, Any]) -> str:
    ml = config["ml_export"]
    digest = sha256_bytes(f"{ml['split_seed']}:{design_id}".encode("utf-8"))
    value = int(digest[:16], 16) / float(16**16)
    if value < ml["train_fraction"]:
        return "train"
    if value < ml["train_fraction"] + ml["validation_fraction"]:
        return "validation"
    return "test"


def _write_ml_exports(
    output: Path, records: list[dict[str, Any]], config: dict[str, Any]
) -> None:
    fields = [
        "candidate_id",
        "design_id",
        "operating_point_id",
        "run_definition_id",
        "execution_id",
        "method_definition_id",
        "method_run_id",
        "split",
        "method_fidelity",
        "execution_status",
        "gate_result",
        "engineering_approval",
        "fha_warning_codes",
        "target_available",
        "hardware_lr_h",
        "hardware_cr_f",
        "hardware_lm_h",
        "hardware_turns_ratio_ns_np",
        "operating_vin_v",
        "operating_load_ohm",
        "operating_temperature_c",
        "operating_control_condition",
        "method_rac_primary_ohm",
        "method_selected_frequency_hz",
        "method_solver_model_version",
        "ln",
        "q",
        "fr_hz",
        "turns_ratio_ns_np",
        "fha_gain_relative_error",
        "fha_best_frequency_hz",
        "output_voltage_v",
        "output_power_w",
        "equivalent_model_power_ratio_percent",
        "resonant_current_rms_a",
        "resonant_current_peak_a",
        "resonant_capacitor_voltage_peak_v",
        "reason_codes",
    ]
    splits: dict[str, str] = {}
    with (output / "ml_dataset_v1.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            design = record["design_variables"]
            hardware = record["hardware_design"]
            operating_point = record["operating_point"]
            method_inputs = record["method_inputs"]
            metrics = record["time_domain_evaluation"].get("metrics", {})
            contract = record["decision_contract"]
            split = _split_for_design(record["design_id"], config)
            splits[record["design_id"]] = split
            target_available = contract["execution_status"] == "completed"
            writer.writerow(
                {
                    "candidate_id": record["candidate_id"],
                    "design_id": record["design_id"],
                    "operating_point_id": record["operating_point_id"],
                    "run_definition_id": record["run_definition_id"],
                    "execution_id": record["execution_id"],
                    "method_definition_id": record["method_definition_id"],
                    "method_run_id": record["method_run_id"],
                    "split": split,
                    "method_fidelity": "time-stepped-linear-equivalent-v1",
                    "execution_status": contract["execution_status"],
                    "gate_result": contract["gate_result"],
                    "engineering_approval": contract["engineering_approval"],
                    "fha_warning_codes": "|".join(
                        record["fha_screen"].get("warnings", [])
                    ),
                    "target_available": str(target_available).lower(),
                    "hardware_lr_h": hardware["lr_h"],
                    "hardware_cr_f": hardware["cr_f"],
                    "hardware_lm_h": hardware["lm_h"],
                    "hardware_turns_ratio_ns_np": hardware[
                        "turns_ratio_ns_np"
                    ],
                    "operating_vin_v": operating_point["vin_v"],
                    "operating_load_ohm": operating_point["load_ohm"],
                    "operating_temperature_c": operating_point[
                        "temperature_c"
                    ],
                    "operating_control_condition": operating_point[
                        "control_condition"
                    ],
                    "method_rac_primary_ohm": method_inputs[
                        "rac_primary_ohm"
                    ],
                    "method_selected_frequency_hz": method_inputs[
                        "selected_frequency_hz"
                    ],
                    "method_solver_model_version": method_inputs[
                        "equivalent_solver"
                    ]["model_version"],
                    "ln": design["ln"],
                    "q": design["q"],
                    "fr_hz": design["fr_hz"],
                    "turns_ratio_ns_np": design["turns_ratio_ns_np"],
                    "fha_gain_relative_error": record["fha_screen"]["metrics"][
                        "gain_relative_error"
                    ],
                    "fha_best_frequency_hz": record["fha_screen"]["metrics"][
                        "best_frequency_hz"
                    ],
                    "output_voltage_v": metrics.get("output_voltage_v") if target_available else "",
                    "output_power_w": metrics.get("output_power_w") if target_available else "",
                    "equivalent_model_power_ratio_percent": metrics.get(
                        "equivalent_model_power_ratio_percent"
                    )
                    if target_available
                    else "",
                    "resonant_current_rms_a": metrics.get("resonant_current_rms_a")
                    if target_available
                    else "",
                    "resonant_current_peak_a": metrics.get("resonant_current_peak_a")
                    if target_available
                    else "",
                    "resonant_capacitor_voltage_peak_v": metrics.get(
                        "resonant_capacitor_voltage_peak_v"
                    )
                    if target_available
                    else "",
                    "reason_codes": "|".join(contract["reason_codes"]),
                }
            )

    split_counts = Counter(splits.values())
    write_json(
        output / "split_manifest.json",
        {
            "schema_version": "llc-design-split-v1",
            "split_seed": config["ml_export"]["split_seed"],
            "grouping_key": "design_id",
            "fractions": {
                "train": config["ml_export"]["train_fraction"],
                "validation": config["ml_export"]["validation_fraction"],
                "test": config["ml_export"]["test_fraction"],
            },
            "observed_design_counts": dict(sorted(split_counts.items())),
            "assignments": dict(sorted(splits.items())),
        },
    )
    write_json(
        output / "feature_dictionary.json",
        {
            "schema_version": "llc-feature-dictionary-v1",
            "identity_contract": {
                "design_id": "SHA-256-derived identity of Lr, Cr, Lm and turns ratio only.",
                "operating_point_id": "SHA-256-derived identity of the electrical condition, separate from hardware.",
                "method_run_id": "Concrete execution identity; never used as a split grouping key.",
            },
            "features": {
                "hardware_lr_h": {"unit": "H", "entity": "hardware_design"},
                "hardware_cr_f": {"unit": "F", "entity": "hardware_design"},
                "hardware_lm_h": {"unit": "H", "entity": "hardware_design"},
                "hardware_turns_ratio_ns_np": {
                    "unit": "1",
                    "entity": "hardware_design",
                },
                "operating_vin_v": {"unit": "V", "entity": "operating_point"},
                "operating_load_ohm": {
                    "unit": "ohm",
                    "entity": "operating_point",
                },
                "operating_temperature_c": {
                    "unit": "degC",
                    "entity": "operating_point",
                    "availability": "not configured in the current campaign",
                },
                "operating_control_condition": {
                    "unit": "category",
                    "entity": "operating_point",
                },
                "method_rac_primary_ohm": {
                    "unit": "ohm",
                    "entity": "method_inputs",
                },
                "method_selected_frequency_hz": {
                    "unit": "Hz",
                    "entity": "method_inputs",
                },
                "method_solver_model_version": {
                    "unit": "category",
                    "entity": "method_inputs",
                },
                "ln": {"unit": "1", "source": "design"},
                "q": {"unit": "1", "source": "design"},
                "fr_hz": {"unit": "Hz", "source": "design"},
                "turns_ratio_ns_np": {"unit": "1", "source": "design"},
                "fha_gain_relative_error": {"unit": "1", "source": "FHA"},
                "fha_best_frequency_hz": {"unit": "Hz", "source": "FHA"},
            },
        },
    )
    write_json(
        output / "target_dictionary.json",
        {
            "schema_version": "llc-target-dictionary-v1",
            "target_availability_rule": "Targets exist only when execution_status=completed.",
            "targets": {
                "output_voltage_v": {"unit": "V", "fidelity": "linear-equivalent"},
                "output_power_w": {"unit": "W", "fidelity": "linear-equivalent"},
                "equivalent_model_power_ratio_percent": {
                    "unit": "%",
                    "fidelity": "linear-equivalent",
                    "warning": "Not a device-efficiency claim.",
                },
                "resonant_current_rms_a": {"unit": "A", "fidelity": "linear-equivalent"},
                "resonant_current_peak_a": {"unit": "A", "fidelity": "linear-equivalent"},
                "resonant_capacitor_voltage_peak_v": {
                    "unit": "V",
                    "fidelity": "linear-equivalent",
                },
            },
        },
    )
    (output / "dataset_card.md").write_text(
        "# LLC quick-demo dataset card\n\n"
        "This export is educational and model-bounded. It contains one operating point per design. "
        "It is not a defensible production-training dataset and does not include hardware, magnetic, "
        "thermal or higher-fidelity labels.\n\n"
        "Failures and not-run methods keep `target_available=false`; numerical targets remain empty. "
        "`design_id` depends only on Lr, Cr, Lm and turns ratio; operating-point and method inputs are separate. "
        "All rows sharing a `design_id` are assigned to the same split. The forced failure fixture is "
        "excluded because it is a pipeline test rather than physical data.\n",
        encoding="utf-8",
    )


def _pedagogical_cases(
    records: list[dict[str, Any]],
    config: dict[str, Any],
    execution_id: str,
) -> list[dict[str, Any]]:
    rejected = [
        row for row in records if row["fha_screen"]["gate_result"] == "reject"
    ]
    passed = [row for row in records if row["decision_contract"]["gate_result"] == "pass"]
    cases: list[dict[str, Any]] = []
    if rejected:
        cases.append(
            {
                "case_type": "valid analytical reject",
                "teaching_point": "A valid method showed that a named analytical rule was not met.",
                "record": rejected[0],
            }
        )
    if passed:
        best = min(passed, key=lambda row: row["decision_contract"]["score"])
        cases.append(
            {
                "case_type": "automatic gate pass",
                "teaching_point": "The candidate survives this gate but engineering approval remains pending.",
                "record": best,
            }
        )
    if config["demo"]["include_forced_failure_case"]:
        cases.append(
            {
                "case_type": "forced pipeline failure",
                "teaching_point": "A failed method is not evidence of an electrically bad converter.",
                "record": forced_failure_case(config, execution_id=execution_id),
            }
        )
    return cases


def _create_manifest(
    output: Path,
    config: dict[str, Any],
    *,
    generated_at_utc: str,
    run_definition_id: str,
    execution_id: str,
) -> dict[str, Any]:
    excluded = {"manifest.json", "verification.json", "summary.html"}
    files: dict[str, str] = {}
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        relative = path.relative_to(output).as_posix()
        if relative in excluded:
            continue
        files[relative] = sha256_file(path)
    manifest = {
        "schema_version": "llc-rebuild-manifest-v1",
        "run_name": config["run_name"],
        "created_at_utc": generated_at_utc,
        "run_definition_id": run_definition_id,
        "execution_id": execution_id,
        "candidate_count": config["candidate_count"],
        "seed": config["seed"],
        "core_solver": EQUIVALENT_MODEL_VERSION,
        "ltspice_required_for_core": False,
        "runtime": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "implementation": platform.python_implementation(),
        },
        "source_integrity": {
            "llc_tool/core.py": sha256_file(Path(__file__).with_name("core.py")),
            "llc_tool/workflow.py": sha256_file(Path(__file__).resolve()),
            "llc_tool/config.py": sha256_file(Path(__file__).with_name("config.py")),
            "llc_tool/report.py": sha256_file(Path(__file__).with_name("report.py")),
        },
        "integrity": {"algorithm": "sha256", "files": files},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_output(output_dir: Path, *, write_report: bool = True) -> dict[str, Any]:
    output = output_dir.resolve()
    errors: list[str] = []
    manifest_path = output / "manifest.json"
    if not manifest_path.is_file():
        report = {
            "schema_version": "llc-rebuild-verification-v1",
            "verified_at_utc": utc_now(),
            "status": "FAIL",
            "errors": ["MANIFEST_MISSING"],
        }
        if write_report:
            write_verification_failure_html(output, report)
            report["summary_html_sha256"] = sha256_file(output / "summary.html")
            write_json(output / "verification.json", report)
        return report
    manifest = load_json(manifest_path)
    package_root = Path(__file__).resolve().parents[1]
    for relative, expected_hash in manifest.get("source_integrity", {}).items():
        source_path = package_root / relative
        if not source_path.is_file():
            errors.append(f"SOURCE_MISSING:{relative}")
        elif sha256_file(source_path) != expected_hash:
            errors.append(f"SOURCE_HASH_MISMATCH:{relative}")
    for relative, expected_hash in manifest["integrity"]["files"].items():
        path = output / relative
        if not path.is_file():
            errors.append(f"FILE_MISSING:{relative}")
        elif sha256_file(path) != expected_hash:
            errors.append(f"HASH_MISMATCH:{relative}")

    try:
        candidates = _read_jsonl(output / "candidates.jsonl")
        records = _read_jsonl(output / "candidate_records.jsonl")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        candidates = []
        records = []
        errors.append(f"DATASET_READ_ERROR:{type(exc).__name__}")
    candidate_ids = [row.get("candidate_id") for row in candidates]
    record_ids = [row.get("candidate_id") for row in records]
    if len(candidates) != manifest["candidate_count"]:
        errors.append("CANDIDATE_COUNT_MISMATCH")
    if len(records) != manifest["candidate_count"]:
        errors.append("RECORD_COUNT_MISMATCH")
    if len(set(candidate_ids)) != len(candidate_ids):
        errors.append("DUPLICATE_CANDIDATE_ID")
    if set(candidate_ids) != set(record_ids):
        errors.append("CANDIDATE_RECORD_ID_MISMATCH")
    for record in records:
        candidate_id = record.get("candidate_id")
        contract = record.get("decision_contract", {})
        execution = contract.get("execution_status")
        gate = contract.get("gate_result")
        approval = contract.get("engineering_approval")
        if execution not in {"not_run", "completed", "failed"}:
            errors.append(f"INVALID_EXECUTION_STATUS:{record.get('candidate_id')}")
        if gate not in {"pass", "reject", "review", "not_applicable"}:
            errors.append(f"INVALID_GATE_RESULT:{record.get('candidate_id')}")
        if approval not in {"pending", "approved", "rejected"}:
            errors.append(f"INVALID_ENGINEERING_APPROVAL:{record.get('candidate_id')}")
        if execution == "failed" and gate != "not_applicable":
            errors.append(f"FAILED_GATE_MUST_BE_NOT_APPLICABLE:{candidate_id}")
        if execution == "completed" and gate not in {"pass", "reject", "review"}:
            errors.append(f"COMPLETED_GATE_RESULT_INVALID:{candidate_id}")
        fha = record.get("fha_screen", {})
        fha_execution = fha.get("execution_status")
        fha_gate = fha.get("gate_result")
        time_execution = record.get("time_domain_evaluation", {}).get(
            "execution_status"
        )
        if fha_execution != "completed" or fha_gate not in {"pass", "reject"}:
            errors.append(f"FHA_STAGE_CONTRACT_BROKEN:{candidate_id}")
        if fha_gate == "reject":
            if (
                time_execution != "not_run"
                or execution != "not_run"
                or gate != "reject"
            ):
                errors.append(f"FHA_REJECT_CONTRACT_BROKEN:{candidate_id}")
        elif fha_gate == "pass":
            if time_execution == "failed" and (
                execution != "failed" or gate != "not_applicable"
            ):
                errors.append(f"TIME_FAILURE_CONTRACT_BROKEN:{candidate_id}")
            if time_execution == "completed" and (
                execution != "completed" or gate not in {"pass", "reject", "review"}
            ):
                errors.append(f"TIME_COMPLETION_CONTRACT_BROKEN:{candidate_id}")

    for relative in ("candidate_records.csv", "ml_dataset_v1.csv"):
        try:
            with (output / relative).open("r", newline="", encoding="utf-8") as stream:
                tabular_rows = list(csv.DictReader(stream))
        except (FileNotFoundError, csv.Error) as exc:
            errors.append(f"TABULAR_READ_ERROR:{relative}:{type(exc).__name__}")
            continue
        tabular_by_id = {row.get("candidate_id"): row for row in tabular_rows}
        for record in records:
            candidate_id = record.get("candidate_id")
            row = tabular_by_id.get(candidate_id)
            if row is None:
                errors.append(f"TABULAR_CANDIDATE_MISSING:{relative}:{candidate_id}")
                continue
            contract = record["decision_contract"]
            target_expected = (
                record["time_domain_evaluation"].get("execution_status")
                == "completed"
            )
            if row.get("target_available") != str(target_expected).lower():
                errors.append(
                    f"TARGET_AVAILABILITY_MISMATCH:{relative}:{candidate_id}"
                )
            if row.get("execution_status") != contract["execution_status"]:
                errors.append(f"EXECUTION_STATUS_MISMATCH:{relative}:{candidate_id}")
            if row.get("gate_result") != contract["gate_result"]:
                errors.append(f"GATE_RESULT_MISMATCH:{relative}:{candidate_id}")

    leaked_paths: list[str] = []
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        if path.suffix.lower() not in {".json", ".jsonl", ".csv", ".md", ".html", ".svg"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ABSOLUTE_PATH_PATTERN.search(text):
            leaked_paths.append(path.relative_to(output).as_posix())
    if leaked_paths:
        errors.append("ABSOLUTE_PATH_LEAK:" + ",".join(leaked_paths))

    report_context: tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]] | None
    try:
        report_context = (
            load_json(output / "config_snapshot.json"),
            load_json(output / "summary.json"),
            load_json(output / "pedagogical_cases.json"),
        )
    except (FileNotFoundError, json.JSONDecodeError, TypeError) as exc:
        report_context = None
        errors.append(f"REPORT_CONTEXT_READ_ERROR:{type(exc).__name__}")

    report = {
        "schema_version": "llc-rebuild-verification-v1",
        "verified_at_utc": utc_now(),
        "status": "PASS" if not errors else "FAIL",
        "candidate_count": len(candidates),
        "record_count": len(records),
        "decision_counts": dict(sorted(Counter(row.get("decision_contract", {}).get("gate_result") for row in records).items())),
        "integrity_file_count": len(manifest["integrity"]["files"]),
        "absolute_path_leaks": leaked_paths,
        "errors": errors,
    }
    if write_report:
        if report_context is None:
            write_verification_failure_html(
                output,
                report,
                generated_at_utc=str(manifest.get("created_at_utc", "unknown")),
            )
        else:
            report_config, report_summary, report_cases = report_context
            write_html_report(
                output,
                report_config,
                report_summary,
                report_cases,
                report,
            )
        report["summary_html_sha256"] = sha256_file(output / "summary.html")
        write_json(output / "verification.json", report)
    return report


def run_workflow(config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    config = validate_config(config)
    output = _prepare_empty_output(output_dir)
    generated_at_utc = utc_now()
    run_definition_id = derive_run_definition_id(config)
    execution_id = f"execution-{uuid.uuid4()}"
    write_json(output / "config_snapshot.json", config)
    candidates = generate_candidates(config, execution_id=execution_id)
    write_jsonl(output / "candidates.jsonl", candidates)
    records: list[dict[str, Any]] = []
    records_dir = output / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        record = make_record(candidate, config)
        records.append(record)
        write_json(records_dir / f"{record['candidate_id']}.json", record)
    write_jsonl(output / "candidate_records.jsonl", records)
    _write_candidate_csv(output / "candidate_records.csv", records)

    fha_counts = Counter(row["fha_screen"]["gate_result"] for row in candidates)
    execution_counts = Counter(
        row["decision_contract"]["execution_status"] for row in records
    )
    gate_counts = Counter(row["decision_contract"]["gate_result"] for row in records)
    fha_warning_counts = Counter(
        warning
        for row in candidates
        for warning in row["fha_screen"].get("warnings", [])
    )
    boundary_hit_ids = [
        row["candidate_id"]
        for row in candidates
        if "FHA_SEARCH_BOUNDARY_HIT" in row["fha_screen"].get("warnings", [])
    ]
    reject_boundary_ids = [
        row["candidate_id"]
        for row in candidates
        if "FHA_REJECT_AT_UPPER_SEARCH_BOUNDARY"
        in row["fha_screen"].get("warnings", [])
    ]
    summary = {
        "schema_version": "llc-rebuild-summary-v1",
        "run_name": config["run_name"],
        "generated_at_utc": generated_at_utc,
        "run_definition_id": run_definition_id,
        "execution_id": execution_id,
        "candidate_count": len(candidates),
        "record_count": len(records),
        "fha_counts": {status: fha_counts.get(status, 0) for status in ("pass", "reject")},
        "execution_counts": {
            status: execution_counts.get(status, 0)
            for status in ("not_run", "completed", "failed")
        },
        "gate_counts": {
            status: gate_counts.get(status, 0)
            for status in ("pass", "reject", "review", "not_applicable")
        },
        "fha_warning_counts": dict(sorted(fha_warning_counts.items())),
        "fha_search_boundary_hit_ids": boundary_hit_ids,
        "fha_reject_upper_boundary_ids": reject_boundary_ids,
        "surviving_candidate_count": gate_counts.get("pass", 0),
        "design_space_disposition": (
            "surviving_candidates_present"
            if gate_counts.get("pass", 0)
            else "no_surviving_candidate"
        ),
        "engineering_approval_counts": {
            status: sum(
                1
                for row in records
                if row["decision_contract"]["engineering_approval"] == status
            )
            for status in ("pending", "approved", "rejected")
        },
        "scope": "Preliminary electrical screening at one fixed operating point; no hardware approval.",
    }
    write_json(output / "summary.json", summary)
    cases = _pedagogical_cases(records, config, execution_id)
    write_json(output / "pedagogical_cases.json", cases)

    pass_record = next(
        (
            case["record"]
            for case in cases
            if case["case_type"] == "automatic gate pass"
        ),
        None,
    )
    samples: list[tuple[float, float, float, float, float, float]] = []
    if pass_record is not None:
        replay = simulate_design(
            design=pass_record["design_variables"],
            input_spec=config["input_spec"],
            frequency_hz=pass_record["fha_screen"]["metrics"]["best_frequency_hz"],
            solver=config["equivalent_solver"],
        )
        samples = replay.pop("samples")
        _write_waveform(output / "examples" / "pass_case_waveform.csv", samples)
        write_json(
            output / "examples" / "pass_case_deterministic_replay.json",
            {
                "candidate_id": pass_record["candidate_id"],
                "replay_kind": "deterministic replay using the same model and configuration",
                "evaluation": replay,
                "metrics_exact_match": replay["metrics"]
                == pass_record["time_domain_evaluation"]["metrics"],
            },
        )

    _write_ml_exports(output, records, config)
    write_plots(output, candidates, records, summary, cases, config, samples)
    _create_manifest(
        output,
        config,
        generated_at_utc=generated_at_utc,
        run_definition_id=run_definition_id,
        execution_id=execution_id,
    )
    verification = verify_output(output, write_report=True)
    if verification["status"] != "PASS":
        raise RuntimeError("Generated workflow failed verification: " + ", ".join(verification["errors"]))
    return {
        "output_dir": str(output_dir),
        "summary_html": str(output_dir / "summary.html"),
        "candidate_count": len(candidates),
        "verification_status": verification["status"],
        "gate_counts": summary["gate_counts"],
    }


def replay_archived_candidate(
    *,
    record_path: Path,
    solver_input_path: Path,
    tolerance_path: Path,
    decision_config: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    output = _prepare_empty_output(output_dir)
    reference = load_json(record_path)
    solver_input = load_json(solver_input_path)
    tolerances = load_json(tolerance_path)
    solver = dict(solver_input["solver"])
    solver.setdefault("timeout_seconds", 30.0)
    evaluation = simulate_design(
        design=solver_input["design_variables"],
        input_spec=solver_input["input_spec"],
        frequency_hz=reference["fha_screen"]["metrics"]["best_frequency_hz"],
        solver=solver,
    )
    samples = evaluation.pop("samples")
    _write_waveform(output / "waveform.csv", samples)
    observed_legacy = legacy_metric_view(evaluation["metrics"])
    reference_metrics = reference["simulation"]["telemetry"]["metrics"]
    comparisons: dict[str, Any] = {}
    numeric_pass = True
    for name, tolerance in tolerances["absolute_tolerances"].items():
        reference_value = reference_metrics[name]
        observed_value = observed_legacy[name]
        delta = abs(observed_value - reference_value)
        within = delta <= tolerance
        numeric_pass = numeric_pass and within
        comparisons[name] = {
            "reference": reference_value,
            "observed": observed_value,
            "absolute_delta": delta,
            "absolute_tolerance": tolerance,
            "within_tolerance": within,
        }
    observed_decision = classify_evaluation(evaluation, decision_config)["gate_result"]
    expected_decision = reference["decision"]["status"]
    decision_match = observed_decision == expected_decision
    input_hashes = {
        "record_sha256": sha256_file(record_path),
        "solver_input_sha256": sha256_file(solver_input_path),
        "tolerances_sha256": sha256_file(tolerance_path),
        "decision_config_sha256": sha256_bytes(
            canonical_json(decision_config).encode("utf-8")
        ),
        "candidate_design_sha256": sha256_bytes(
            canonical_json(solver_input["design_variables"]).encode("utf-8")
        ),
        "solver_parameters_sha256": sha256_bytes(
            canonical_json(solver).encode("utf-8")
        ),
        "core_code_sha256": sha256_file(Path(__file__).with_name("core.py")),
    }
    report = {
        "schema_version": "llc-tolerant-replay-verification-v1",
        "candidate_id": reference["candidate_id"],
        "integrity_exact": input_hashes,
        "numeric_reproduction": {
            "status": "PASS" if numeric_pass else "FAIL",
            "comparisons": comparisons,
        },
        "decision_reproduction": {
            "expected": expected_decision,
            "observed": observed_decision,
            "identical": decision_match,
        },
        "status": "PASS" if numeric_pass and decision_match else "FAIL",
    }
    write_json(
        output / "replay_record.json",
        {
            "candidate_id": reference["candidate_id"],
            "replay_kind": "deterministic replay using the same model and configuration",
            "evaluation": evaluation,
        },
    )
    write_json(output / "replay_verification.json", report)
    return report

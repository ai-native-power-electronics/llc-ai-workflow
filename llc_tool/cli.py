from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

from .config import ConfigurationError, load_and_validate_config, validate_config
from .workflow import replay_archived_candidate, run_workflow, verify_output


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _default_output(prefix: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return PACKAGE_ROOT.parent / "LLC_Demo_Runs" / f"{prefix}-{stamp}"


def _ltspice_status() -> dict[str, object]:
    candidates: list[Path] = []
    environment_value = os.environ.get("LTSPICE_PATH")
    if environment_value:
        candidates.append(Path(environment_value))
    if os.name == "nt":
        system_drive = Path(os.environ.get("SystemDrive", "C:"))
        candidates.extend(
            [
                Path(os.environ.get("LOCALAPPDATA", ""))
                / "Programs"
                / "ADI"
                / "LTspice"
                / "LTspice.exe",
                system_drive / "Program Files" / "ADI" / "LTspice" / "LTspice.exe",
            ]
        )
    found = next((path for path in candidates if path.is_file()), None)
    return {
        "adapter": "LTspice",
        "available": found is not None,
        "configured_by": "LTSPICE_PATH" if environment_value and found == Path(environment_value) else "auto-detection" if found else None,
        "path": str(found) if found else None,
        "required_for_core_demo": False,
    }


def doctor() -> dict[str, object]:
    return {
        "python": {
            "available": True,
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "minimum_supported": "3.10",
            "supported": sys.version_info >= (3, 10),
        },
        "core_demo": {
            "available": sys.version_info >= (3, 10),
            "external_python_dependencies": [],
        },
        "optional_adapters": [_ltspice_status()],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m llc_tool",
        description="Rebuildable LLC engineering-decision demonstration.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check the standard-library core and optional adapters.")

    demo = sub.add_parser("demo", help="Run the short educational demonstration from inputs.")
    demo.add_argument("--config", type=Path, default=PACKAGE_ROOT / "configs" / "quick_demo.json")
    demo.add_argument("--output", type=Path)
    demo.add_argument("--candidates", type=int)
    demo.add_argument("--vin", type=float)
    demo.add_argument("--vout", type=float)
    demo.add_argument("--pout", type=float)
    demo.add_argument("--open-report", action="store_true")
    demo.add_argument("--human", action="store_true", help=argparse.SUPPRESS)

    run = sub.add_parser("run", help="Run a named configuration, including the 200-candidate rebuild.")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path)
    run.add_argument("--open-report", action="store_true")

    replay = sub.add_parser("replay", help="Replay an archived record with numeric tolerances.")
    replay.add_argument("--record", type=Path, default=PACKAGE_ROOT / "examples" / "llc-0186.json")
    replay.add_argument(
        "--solver-input",
        type=Path,
        default=PACKAGE_ROOT / "examples" / "llc-0186_solver_input.json",
    )
    replay.add_argument(
        "--tolerances",
        type=Path,
        default=PACKAGE_ROOT / "configs" / "replay_tolerances.json",
    )
    replay.add_argument(
        "--decision-config",
        type=Path,
        default=PACKAGE_ROOT / "configs" / "quick_demo.json",
    )
    replay.add_argument("--output", type=Path)

    verify = sub.add_parser("verify", help="Verify a generated output directory.")
    verify.add_argument("output", type=Path)
    return parser


def _apply_demo_overrides(config: dict, args: argparse.Namespace) -> dict:
    if args.candidates is not None:
        config["candidate_count"] = args.candidates
    if args.vin is not None:
        config["input_spec"]["vin_v"] = args.vin
    if args.vout is not None:
        config["input_spec"]["vout_v"] = args.vout
    if args.pout is not None:
        config["input_spec"]["pout_w"] = args.pout
    return validate_config(config)


def _run_and_maybe_open(
    config: dict, output: Path, open_report: bool, *, human: bool = False
) -> int:
    result = run_workflow(config, output)
    if human:
        print("\nDemo complete.")
        print(f"{result['candidate_count']} candidates generated.")
        print(f"{result['gate_counts']['pass']} passed the automatic gate.")
        print(f"{result['gate_counts']['reject']} were rejected.")
        print(f"Output integrity: {result['verification_status']}")
        print(f"Report: {output / 'summary.html'}")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
        print(f"\nReport: {output / 'summary.html'}")
    if open_report:
        if human:
            print("\nOpening the human-readable report...")
        webbrowser.open((output / "summary.html").resolve().as_uri())
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["core_demo"]["available"] else 1
        if args.command == "demo":
            config = _apply_demo_overrides(load_and_validate_config(args.config), args)
            return _run_and_maybe_open(
                config,
                args.output or _default_output("demo"),
                args.open_report,
                human=args.human,
            )
        if args.command == "run":
            config = load_and_validate_config(args.config)
            return _run_and_maybe_open(
                config, args.output or _default_output("run"), args.open_report
            )
        if args.command == "replay":
            config = load_and_validate_config(args.decision_config)
            result = replay_archived_candidate(
                record_path=args.record,
                solver_input_path=args.solver_input,
                tolerance_path=args.tolerances,
                decision_config=config,
                output_dir=args.output or _default_output("replay-llc-0186"),
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "PASS" else 1
        if args.command == "verify":
            result = verify_output(args.output, write_report=True)
            print(json.dumps(result, indent=2, sort_keys=True))
            print(f"\nHuman report refreshed: {args.output / 'summary.html'}")
            return 0 if result["status"] == "PASS" else 1
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

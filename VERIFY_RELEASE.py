#!/usr/bin/env python3
"""Verify a generated Quickstart or sanitized Evidence Archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


PRIVATE_PATH_PATTERN = re.compile(
    r"(?i)(?:(?<![a-z0-9])[a-z]:[\\/](?![\\/])|/(?:users|home)/[a-z0-9._-]+(?:/|$))"
)
TEXT_SUFFIXES = {".json", ".jsonl", ".csv", ".md", ".txt", ".py", ".html", ".svg", ".bat", ".yml", ".yaml"}
PROHIBITED_SUFFIXES = {".asc", ".net", ".raw", ".pdf"}
REQUIRED_PUBLIC_FILES = (
    "LICENSE",
    "NOTICE",
    "LICENSE_SCOPE.md",
    "SOURCES.md",
    "THIRD_PARTY_NOTICES.md",
    "04_FAILURE/PUBLIC_LTSPICE_FAILURE.json",
    "04_FAILURE/PUBLIC_FAILURE_NOTE.md",
)
EVIDENCE_EXCLUDED_CATEGORIES = {
    "third_party_publications",
    "uncleared_ltspice_schematic_and_derivatives",
    "historical_ltspice_adapter",
    "historical_planning_documents",
    "private_authority_files",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_path_hash_references(value: object):
    """Yield every nested object that declares both a path and a SHA-256."""
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(
            value.get("sha256"), str
        ):
            yield value["path"], value["sha256"]
        for nested in value.values():
            yield from iter_path_hash_references(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_path_hash_references(nested)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-publishable", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    if "excluded_files" in manifest:
        errors.append("DETAILED_EXCLUDED_FILE_INVENTORY_PRESENT")
    excluded_categories = set(manifest.get("excluded_categories", []))
    if manifest.get("release_kind") == "sanitized-evidence-archive":
        if excluded_categories != EVIDENCE_EXCLUDED_CATEGORIES:
            errors.append("EVIDENCE_EXCLUDED_CATEGORIES_INVALID")
    elif excluded_categories:
        errors.append("UNEXPECTED_EXCLUDED_CATEGORIES")
    for relative in REQUIRED_PUBLIC_FILES:
        if not (root / relative).is_file():
            errors.append(f"REQUIRED_PUBLIC_FILE_MISSING:{relative}")
    for relative, expected in manifest["files"].items():
        path = root / relative
        if not path.is_file():
            errors.append(f"FILE_MISSING:{relative}")
        elif sha256(path) != expected:
            errors.append(f"HASH_MISMATCH:{relative}")
    for path in root.rglob("*"):
        if not path.is_file() or path.name == "RELEASE_MANIFEST.json":
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in manifest["files"]:
            errors.append(f"UNMANIFESTED_FILE:{relative}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if PRIVATE_PATH_PATTERN.search(text):
                errors.append(f"PRIVATE_PATH:{relative}")
        if path.suffix.lower() in PROHIBITED_SUFFIXES:
            errors.append(f"PROHIBITED_THIRD_PARTY_OR_MODEL_FILE:{relative}")
        if relative.startswith("04_FAILURE/closed_loop_timeout_v1/"):
            errors.append(f"UNSANITIZED_LTSPICE_FAILURE_FILE:{relative}")
        if relative in {
            "05_CAMPAIGN/authority/campaign_manifest.json",
            "06_REPRODUCIBILITY/artifacts/llc_200_v1/campaign_manifest.json",
        }:
            try:
                campaign_manifest = json.loads(path.read_text(encoding="utf-8"))
                if campaign_manifest.get("source_inventory_status") != "sanitized_logical_ids":
                    errors.append(f"UNSANITIZED_CAMPAIGN_SOURCE_INVENTORY:{relative}")
                for source in campaign_manifest.get("sources", []):
                    if any(key in source for key in ("path", "sha256", "size_bytes")):
                        errors.append(f"CAMPAIGN_SOURCE_METADATA_LEAK:{relative}")
            except json.JSONDecodeError:
                errors.append(f"CAMPAIGN_MANIFEST_JSON_INVALID:{relative}")
    public_failure_path = root / "04_FAILURE" / "PUBLIC_LTSPICE_FAILURE.json"
    if public_failure_path.is_file():
        try:
            public_failure = json.loads(public_failure_path.read_text(encoding="utf-8"))
            if public_failure.get("model_redistributed") is not False:
                errors.append("PUBLIC_FAILURE_REDISTRIBUTES_MODEL")
            if public_failure.get("execution_status") != "failed" or public_failure.get(
                "gate_result"
            ) != "not_applicable":
                errors.append("PUBLIC_FAILURE_STATE_INVALID")
            expected_publication_basis = (
                "Included under the completed owner attestation. The underlying "
                "schematic, netlist, raw output and models are not redistributed."
            )
            if (
                "publication_condition" in public_failure
                or public_failure.get("publication_basis")
                != expected_publication_basis
            ):
                errors.append("PUBLIC_FAILURE_PUBLICATION_BASIS_INVALID")
        except json.JSONDecodeError:
            errors.append("PUBLIC_FAILURE_JSON_INVALID")
    field_note_evidence_path = (
        root / "05_CAMPAIGN" / "authority" / "field_note_evidence.json"
    )
    if field_note_evidence_path.is_file():
        try:
            field_note_evidence = json.loads(
                field_note_evidence_path.read_text(encoding="utf-8")
            )
            failure = field_note_evidence.get("failure", {})
            expected_failure = {
                "classification": "Secondary-method failure; not an electrical rejection.",
                "public_record": "04_FAILURE/PUBLIC_LTSPICE_FAILURE.json",
                "execution_status": "failed",
                "gate_result": "not_applicable",
                "reason_code": "SOLVER_TIMEOUT",
                "model_redistributed": False,
            }
            if failure != expected_failure:
                errors.append("FIELD_NOTE_FAILURE_INDEX_NOT_SANITIZED")
            result = field_note_evidence.get("result", {})
            time_domain = result.get("time_domain", {})
            source_aliases = result.get("source_field_aliases", {})
            expected_aliases = {
                "efficiency_pct": "equivalent_model_power_ratio_percent",
                "zvs_hs_flag": "high_side_commutation_current_sign_proxy",
                "zvs_ls_flag": "low_side_commutation_current_sign_proxy",
            }
            if any(
                key in time_domain
                for key in ("efficiency_pct", "zvs_hs_flag", "zvs_ls_flag")
            ):
                errors.append("FIELD_NOTE_RESULT_LABELS_NOT_SANITIZED")
            if source_aliases != expected_aliases:
                errors.append("FIELD_NOTE_SOURCE_FIELD_ALIASES_INVALID")
            artifact = field_note_evidence.get("artifact", {})
            separate_rerun = artifact.get("separate_directory_rerun_record", {})
            if "independent_rerun_record" in artifact or separate_rerun.get(
                "scope"
            ) != (
                "Same frozen code, model and configuration; not independent "
                "validation."
            ):
                errors.append("FIELD_NOTE_RERUN_SCOPE_NOT_SANITIZED")
            resolved_root = root.resolve()
            for relative, expected_hash in iter_path_hash_references(
                field_note_evidence
            ):
                referenced = (root / relative).resolve()
                try:
                    referenced.relative_to(resolved_root)
                except ValueError:
                    errors.append(
                        f"FIELD_NOTE_EVIDENCE_PATH_ESCAPES_PACKAGE:{relative}"
                    )
                    continue
                if not referenced.is_file():
                    errors.append(f"FIELD_NOTE_EVIDENCE_FILE_MISSING:{relative}")
                elif sha256(referenced) != expected_hash:
                    errors.append(f"FIELD_NOTE_EVIDENCE_HASH_MISMATCH:{relative}")
        except json.JSONDecodeError:
            errors.append("FIELD_NOTE_EVIDENCE_JSON_INVALID")
    license_path = root / "LICENSE"
    if license_path.is_file() and "Apache License" not in license_path.read_text(
        encoding="utf-8", errors="ignore"
    ):
        errors.append("LICENSE_IS_NOT_APACHE_2_0")
    integrity_status = "PASS" if not errors else "FAIL"
    publication_status = manifest.get("publication_status", "BLOCKED")
    report = {
        "schema_version": "llc-public-release-verification-v1",
        "release_kind": manifest.get("release_kind"),
        "release_version": manifest.get("release_version"),
        "integrity_status": integrity_status,
        "publication_status": publication_status,
        "ownership_attestation_status": manifest.get(
            "ownership_attestation_status"
        ),
        "publication_links_status": manifest.get("publication_links_status"),
        "file_count": len(manifest["files"]),
        "errors": sorted(set(errors)),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if errors:
        return 1
    if args.require_publishable and publication_status != "READY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

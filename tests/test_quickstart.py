from __future__ import annotations

import ast
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llc_tool.config import ConfigurationError, load_and_validate_config, validate_config
from llc_tool.core import generate_candidates
from llc_tool.workflow import run_workflow


class QuickstartTests(unittest.TestCase):
    def setUp(self):
        self.config = load_and_validate_config(ROOT / "configs" / "quick_demo.json")

    def test_generation_is_deterministic(self):
        self.assertEqual(
            generate_candidates(self.config), generate_candidates(self.config)
        )

    def test_model_labels_are_code_owned(self):
        bad = copy.deepcopy(self.config)
        bad["fha_screen"]["model_version"] = "invented-model"
        with self.assertRaises(ConfigurationError):
            validate_config(bad)

    def test_default_demo_rebuilds(self):
        with tempfile.TemporaryDirectory(prefix="llc-quickstart-") as directory:
            output = Path(directory) / "run"
            result = run_workflow(self.config, output)
            self.assertEqual(result["verification_status"], "PASS")
            self.assertEqual(result["candidate_count"], 20)
            report = (output / "summary.html").read_text(encoding="utf-8")
            self.assertIn("AI-Native Power Electronics — Rafael Collado", report)
            self.assertIn("https://ainativepower.com/field-notes", report)

    def test_zero_survivors_is_valid(self):
        with tempfile.TemporaryDirectory(prefix="llc-quickstart-zero-") as directory:
            config = copy.deepcopy(self.config)
            config["input_spec"]["vout_v"] = 12.0
            config["input_spec"]["pout_w"] = 100.0
            result = run_workflow(config, Path(directory) / "run")
            self.assertEqual(result["verification_status"], "PASS")
            self.assertEqual(result["gate_counts"]["pass"], 0)

    def test_notebook_json_is_present(self):
        for name in ("llc_quick_demo.ipynb", "llc_colab.ipynb"):
            notebook = json.loads(
                (ROOT / "notebooks" / name).read_text(encoding="utf-8")
            )
            self.assertEqual(notebook["nbformat"], 4)
        colab_text = (ROOT / "notebooks" / "llc_colab.ipynb").read_text(
            encoding="utf-8"
        )
        for required in (
            "pedagogical_cases.json",
            "fha_pass_case.svg",
            "fha_reject_case.svg",
            "https://ainativepower.com/field-notes",
        ):
            self.assertIn(required, colab_text)

    def test_colab_resolves_repository_and_nested_zip_roots(self):
        notebook = json.loads(
            (ROOT / "notebooks" / "llc_colab.ipynb").read_text(encoding="utf-8")
        )
        acquisition_cell = next(
            "".join(cell["source"])
            for cell in notebook["cells"]
            if "def resolve_package_root" in "".join(cell.get("source", []))
        )
        tree = ast.parse(acquisition_cell)
        resolver_node = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "resolve_package_root"
        )
        module = ast.Module(body=[resolver_node], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace: dict[str, object] = {}
        exec(compile(module, "llc_colab.ipynb", "exec"), namespace)
        resolver = namespace["resolve_package_root"]

        def create_minimal_package(root: Path) -> None:
            (root / "llc_tool").mkdir(parents=True)
            (root / "llc_tool" / "__init__.py").write_text("", encoding="utf-8")
            (root / "configs").mkdir()
            (root / "configs" / "quick_demo.json").write_text(
                "{}\n", encoding="utf-8"
            )

        with tempfile.TemporaryDirectory(prefix="llc-colab-root-") as directory:
            base = Path(directory)
            repository_source = base / "repository-source"
            create_minimal_package(repository_source)
            self.assertEqual(resolver(repository_source), repository_source)

            zip_payload = base / "zip-payload"
            create_minimal_package(zip_payload)
            archive = base / "quickstart.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                for path in zip_payload.rglob("*"):
                    if path.is_file():
                        bundle.write(
                            path,
                            Path("llc-ai-workflow-quickstart-v1.0.0")
                            / path.relative_to(zip_payload),
                        )
            extracted = base / "uploaded-zip"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extracted)
            self.assertEqual(
                resolver(extracted),
                extracted / "llc-ai-workflow-quickstart-v1.0.0",
            )

            invalid = base / "invalid-root"
            (invalid / "llc_tool").mkdir(parents=True)
            (invalid / "llc_tool" / "__init__.py").write_text(
                "", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                RuntimeError, "Package root was detected incorrectly"
            ):
                resolver(invalid)

    def test_public_release_has_apache_scope_and_sanitized_failure(self):
        for relative in (
            "LICENSE",
            "NOTICE",
            "LICENSE_SCOPE.md",
            "SOURCES.md",
            "THIRD_PARTY_NOTICES.md",
            "04_FAILURE/PUBLIC_FAILURE_NOTE.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        self.assertIn(
            "Apache License",
            (ROOT / "LICENSE").read_text(encoding="utf-8"),
        )
        failure = json.loads(
            (ROOT / "04_FAILURE" / "PUBLIC_LTSPICE_FAILURE.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(failure["execution_status"], "failed")
        self.assertEqual(failure["gate_result"], "not_applicable")
        self.assertIs(failure["model_redistributed"], False)
        self.assertNotIn("publication_condition", failure)
        self.assertEqual(
            failure["publication_basis"],
            "Included under the completed owner attestation. The underlying "
            "schematic, netlist, raw output and models are not redistributed.",
        )

        result_note = ROOT / "02_RESULT" / "RESULT.md"
        if result_note.is_file():
            result_text = result_note.read_text(encoding="utf-8")
            self.assertIn("Relación de potencia del modelo equivalente", result_text)
            self.assertIn("no constituye una validación independiente", result_text)
            self.assertNotIn("Eficiencia del modelo", result_text)
            self.assertNotIn("La repetición independiente produjo", result_text)

        field_note = ROOT / "01_ARTICLE" / "FIELD_NOTE_FINAL.md"
        if field_note.is_file():
            field_note_text = field_note.read_text(encoding="utf-8")
            self.assertIn("held-out LLC design configurations", field_note_text)
            self.assertNotIn("hardware designs the model has never seen", field_note_text)

        start_here = ROOT / "START_HERE.md"
        if start_here.is_file():
            start_text = start_here.read_text(encoding="utf-8")
            self.assertIn("If automatic acquisition is unavailable", start_text)
            self.assertNotIn("until public URLs exist", start_text)

        release_manifest = ROOT / "RELEASE_MANIFEST.json"
        public_index = ROOT / "05_CAMPAIGN" / "authority" / "field_note_evidence.json"
        if release_manifest.is_file() and public_index.is_file():
            index = json.loads(public_index.read_text(encoding="utf-8"))
            time_domain = index["result"]["time_domain"]
            self.assertNotIn("efficiency_pct", time_domain)
            self.assertNotIn("zvs_hs_flag", time_domain)
            self.assertNotIn("zvs_ls_flag", time_domain)
            self.assertIn("equivalent_model_power_ratio_percent", time_domain)
            self.assertNotIn("independent_rerun_record", index["artifact"])
            self.assertIn("separate_directory_rerun_record", index["artifact"])

        if release_manifest.is_file():
            manifest = json.loads(release_manifest.read_text(encoding="utf-8"))
            if manifest.get("release_kind") == "public-source-repository":
                readme = (ROOT / "README.md").read_text(encoding="utf-8")
                self.assertIn(
                    "[Read Field Note 001](https://ainativepower.com/insights/"
                    "evidence-loop-before-the-model)",
                    readme,
                )
                self.assertIn(
                    "[Get the next evidence-led Field Note]"
                    "(https://ainativepower.com/field-notes)",
                    readme,
                )

    def test_publication_gate_does_not_self_approve_missing_urls(self):
        if not (ROOT / "CHECK_PUBLICATION.py").is_file():
            self.skipTest(
                "The public source repository omits internal release-governance files."
            )
        gate_inputs = (
            "CHECK_PUBLICATION.py",
            "LICENSE",
            "NOTICE",
            "LICENSE_SCOPE.md",
            "SOURCES.md",
            "THIRD_PARTY_NOTICES.md",
            "PUBLICATION_OWNERSHIP.json",
            "OWNERSHIP_ATTESTATION.md",
            "PUBLICATION_LINKS.json",
            "THIRD_PARTY_RIGHTS.json",
            "04_FAILURE/PUBLIC_LTSPICE_FAILURE.json",
            "04_FAILURE/PUBLIC_FAILURE_NOTE.md",
            "01_ARTICLE/FIELD_NOTE_FINAL.md",
            "README.md",
            "START_HERE.md",
            "AI_BUILD_LOG.md",
        )
        with tempfile.TemporaryDirectory(prefix="llc-publication-gate-") as directory:
            gate_root = Path(directory)
            for relative in gate_inputs:
                source = ROOT / relative
                target = gate_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            links_path = gate_root / "PUBLICATION_LINKS.json"
            links = json.loads(links_path.read_text(encoding="utf-8"))
            links["status"] = "blocked_http_checks"
            links["http_checks"]["quickstart_download_url"] = 404
            links_path.write_text(
                json.dumps(links, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, "-B", "CHECK_PUBLICATION.py"],
                cwd=gate_root,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "BLOCKED")
            ownership = json.loads(
                (gate_root / "PUBLICATION_OWNERSHIP.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(ownership["status"], "owner_attested")
            self.assertNotIn("OWNERSHIP_ATTESTATION_REQUIRED", report["blockers"])
            self.assertIn(
                "PUBLIC_URL_NOT_HTTP_200:quickstart_download_url",
                report["blockers"],
            )

    def test_public_docs_do_not_reference_private_verifier(self):
        manifest_path = ROOT / "RELEASE_MANIFEST.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            public_documents = [
                relative
                for relative in manifest["files"]
                if Path(relative).suffix.lower() in {".md", ".yml", ".yaml"}
            ]
        else:
            public_documents = [
                "01_ARTICLE/FIELD_NOTE_FINAL.md",
                "PUBLICATION_GATES.md",
                "LICENSE_SCOPE.md",
                "OWNERSHIP_ATTESTATION.md",
                "CHANGELOG_REBUILDABLE.md",
                "EVIDENCE_ARCHIVE_README.md",
                "QUICKSTART_README.md",
                "PUBLIC_REPOSITORY_README.md",
                "PUBLIC_REPRODUCIBILITY_README.md",
                "PUBLIC_REPRODUCIBILITY_WORKFLOW.yml",
                "08_AI_REVIEW/AI_REVIEW_INSTRUCTIONS.md",
            ]

        ai_instructions = "08_AI_REVIEW/AI_REVIEW_INSTRUCTIONS.md"
        for relative in public_documents:
            path = ROOT / relative
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if relative == ai_instructions:
                private_block = (
                    "Private authority package only:\n\n"
                    "```powershell\n"
                    "py -B VERIFY_PACKAGE.py\n"
                    "```"
                )
                self.assertIn(private_block, text)
                self.assertEqual(text.count("VERIFY_PACKAGE.py"), 1)
                text = text.replace("py -B VERIFY_PACKAGE.py", "", 1)
            self.assertNotIn("VERIFY_PACKAGE.py", text, relative)

    def test_documented_attestation_status_matches_json(self):
        ownership_path = ROOT / "PUBLICATION_OWNERSHIP.json"
        if not ownership_path.is_file():
            manifest = json.loads(
                (ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                manifest["ownership_attestation_status"], "owner_attested"
            )
            return

        ownership = json.loads(ownership_path.read_text(encoding="utf-8"))
        self.assertEqual(ownership["status"], "owner_attested")
        self.assertEqual(ownership["attested_by"], "Rafael Collado")
        self.assertTrue(all(ownership["assertions"].values()))
        attestation_date = ownership["attested_at_utc"][:10]

        expected_fragments = {
            "PUBLICATION_GATES.md": (
                "ownership/employment-IP attestation was completed by Rafael Collado on\n"
                f"  {attestation_date};"
            ),
            "LICENSE_SCOPE.md": (
                "The owner\nattestation required for v1.0.0 was completed before the public "
                "release packages\nwere built."
            ),
            "OWNERSHIP_ATTESTATION.md": (
                f"Rafael Collado completed the ownership/employment-IP attestation on "
                f"{attestation_date}."
            ),
        }
        combined = ""
        for relative, expected in expected_fragments.items():
            path = ROOT / relative
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            combined += "\n" + text.lower()
            self.assertIn(expected, text, relative)
        self.assertNotIn("attestation is still unsigned", combined)
        self.assertNotIn("ownership attestation required before public release", combined)
        self.assertNotIn(
            "remains blocked until `publication_ownership.json` records", combined
        )

    def test_public_markdown_local_references_exist(self):
        manifest_path = ROOT / "RELEASE_MANIFEST.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            documents = [
                ROOT / relative
                for relative in manifest["files"]
                if Path(relative).suffix.lower() == ".md"
            ]
        else:
            documents = [
                ROOT / "START_HERE.md",
                ROOT / "LICENSE_SCOPE.md",
                ROOT / "notebooks" / "README.md",
                ROOT / "PUBLIC_REPOSITORY_README.md",
                ROOT / "01_ARTICLE" / "FIELD_NOTE_FINAL.md",
            ]

        link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
        root_resolved = ROOT.resolve()
        for document in documents:
            if not document.is_file():
                continue
            text = document.read_text(encoding="utf-8")
            for raw_target in link_pattern.findall(text):
                target = raw_target.strip().strip("<>").split()[0]
                if (
                    not target
                    or "{{" in target
                    or target.startswith(("https://", "http://", "mailto:", "#", "/"))
                ):
                    continue
                local_target = unquote(target.split("#", 1)[0].split("?", 1)[0])
                resolved = (document.parent / local_target).resolve()
                try:
                    resolved.relative_to(root_resolved)
                except ValueError:
                    self.fail(f"Public Markdown link escapes package: {document}: {target}")
                self.assertTrue(
                    resolved.exists(),
                    f"Broken public Markdown link: {document.relative_to(ROOT)} -> {target}",
                )


if __name__ == "__main__":
    unittest.main()

# Rebuildable-package change log

## 2026-08-21 — RC11 semantic publication language

- Replaced “model efficiency” in the human result note with
  “equivalent-model power ratio” and explicitly denied full-converter
  efficiency interpretation.
- Reframed the retained rerun as deterministic execution in a separate evidence
  directory using the same frozen code, model and configuration; it is not
  described as independent or higher-fidelity validation.
- Clarified that the frozen ranking selects `llc-0186` as a reproducible
  example, not as a physically optimal design.
- Kept historical v1 records unchanged while translating the derived public
  index to `equivalent_model_power_ratio_percent` and commutation-current sign
  proxies, with explicit source-field aliases for traceability.
- Renamed the derived rerun index entry to
  `separate_directory_rerun_record` and added its validation boundary.
- Replaced the obsolete conditional failure-publication statement with the
  completed owner-attestation basis and retained redistribution exclusions.
- Replaced “hardware designs” with held-out LLC design configurations, made the
  Colab fallback wording durable after publication, and separated the README's
  article and subscription actions.

## 2026-08-21 — RC10 self-contained public evidence

- Rewrote every path-and-hash reference in the public Field Note evidence index
  to a file that exists inside the sanitized Evidence Archive; hashes are
  calculated from the final public files during package construction.
- Extended `VERIFY_RELEASE.py` to recursively validate that indexed paths stay
  inside the package, exist and match their declared SHA-256 values.
- Corrected the AI authority order and claim matrix so they point to the public
  code, root methodology documents, portable inventory and
  `RELEASE_MANIFEST.json` actually distributed.
- Clarified that the generator varies `Ns/Np` while archived v1 reports its
  reciprocal `Np/Ns` for `llc-0186`.
- Added the AI-Native Power Electronics / Rafael Collado identity and a minimal
  newsletter continuation link to generated HTML reports.
- Expanded Colab's reader output with the pass/reject/failed case table, pass
  and reject FHA figures and the same continuation link.

## 2026-08-21 — RC9 distribution closure

- Corrected Colab package-root detection for repository clones and nested ZIP
  extraction, with an explicit configuration-file check and regression test.
- Removed historical planning documents from the public Evidence Archive; they
  remain in the private authority package only.
- Reduced the public Field Note evidence failure block to the sanitized public
  contract and replaced detailed excluded-file inventories with categories.
- Generalized private-path detection so public verifiers contain no workstation
  username or workspace name.
- Repaired public-repository links, added `THIRD_PARTY_RIGHTS.json`, and made
  Field Note artifact links tag-qualified rather than parent-relative.
- Added a public Markdown-link test and a publication gate against parent-relative
  Field Note links.

## 2026-08-21 — RC7 public-document consistency

- Replaced the Field Note's public verification command with
  `VERIFY_RELEASE.py` and documented the complete four-command public check.
- Updated publication gates, license scope and ownership-attestation prose to
  match the recorded `owner_attested` JSON state.
- Added public-only reproducibility README and workflow variants. The Evidence
  Archive no longer describes or invokes excluded historical LTspice files;
  the private authority package retains its own private-verifier guidance.
- Removed the obsolete private Field Note helper from the public archive because
  its authority inputs are intentionally excluded there.
- Added `test_public_docs_do_not_reference_private_verifier` and
  `test_documented_attestation_status_matches_json`.
- Current suites: Quickstart 9 tests, Evidence Archive 26 tests and public source
  9 tests with one expected governance skip.

## 2026-08-21 — owner attestation and RC4 publication audit

- Recorded Rafael Collado's explicit ownership/employment-IP attestation with
  all five assertions true and the actual UTC recording time.
- Replaced the Evidence Archive clean-copy dependency on the excluded historical
  LTspice adapter with the current public-core replay of `llc-0186`.
- Added package-specific README files: Quickstart reports 7 tests, Evidence
  Archive reports 24 tests, and neither instructs the reader to run an absent
  internal verifier.
- Sanitized both public campaign manifests to logical source IDs. Absolute
  workstation paths plus excluded-source filenames, sizes and hashes remain
  only in the private authority package.
- Extended public-release verification to reject an absolute private-workspace
  path and unsanitized campaign-source inventories.
- Rebuilt RC4 and verified clean ZIP extractions: Quickstart 7/7, Evidence
  Archive 24/24, public source 6/6 with one expected governance skip.
- Publication remains blocked only by the not-yet-live versioned endpoints and
  the corresponding unresolved Field Note links.

## 2026-08-21 — publication-rights decision

- Selected Apache License 2.0 and added `LICENSE`, `NOTICE`, license scope,
  sources and third-party notices.
- Added a fail-closed ownership/employment-IP attestation. The license choice
  does not self-certify the right to publish.
- Recorded the five canonical URLs and their live HTTP results. Subscription
  and repository passed; downloads, tag, release and tagged notebook source do
  not yet exist.
- Chose link-only references for both PDFs and excluded the uncleared LTspice
  schematic plus detailed/derived LTspice files from public archives.
- Replaced the public LTspice evidence with a minimal factual failure record;
  detailed authority evidence remains internal.
- Versioned public asset names as `llc-ai-workflow-*-v1.0.0.zip` and added live
  URL and release-content verification.

## 2026-08-21 — independent-review hardening

### Trust contract

- Made topology, operating condition and both model versions code-owned;
  unsupported or invented labels now fail before calculation.
- Added deterministic `run_definition_id`, unique `execution_id` and
  execution-specific `method_run_id`.
- Made `verify` regenerate `summary.html` on PASS or FAIL, show generation and
  verification timestamps, list integrity errors and store the report hash.
- Extended semantic verification across FHA execution/gate, time-domain
  execution, final disposition and target availability.
- Removed the synthetic analytical reject when a run contains no real reject.

### Engineering and reader context

- Added the specific reachability reason and
  `FHA_REJECT_AT_UPPER_SEARCH_BOUNDARY` for all 32 full-run FHA rejects.
- Derived report titles from the run (`quick`, full 200-candidate or custom).
- Made the Windows double-click entry print a human summary, open the report
  and pause on errors.
- Added `AI_BUILD_LOG.md` and repositioned the Field Note around the engineer’s
  decision contract, with the 200 candidates serving as evidence.

### Distribution preflight

- Added a Colab-ready notebook with repository, release-download and manual-ZIP
  paths; a public one-click URL remains a publication gate.
- Added separate Quickstart and sanitized Evidence Archive builders and a
  public-release verifier.
- Added fail-closed gates for an owner-selected license, real HTTPS URLs,
  third-party redistribution decisions, unresolved tokens and private paths.
- The technical suite at that checkpoint contained 22 passing standard-library
  tests on Python 3.13.5; the RC4 suite contains 24. Public release remained
  intentionally blocked at that checkpoint pending owner/legal inputs.

## 2026-08-21 — publication preflight

### Reproducibility

- Added a standard-library core independent of LTspice.
- Added `run_demo.py`, `run_demo.bat` and the advanced `python -m llc_tool` CLI.
- Added validated quick-demo and 200-candidate configurations.
- Added portable candidates and manifest to the historical
  `06_REPRODUCIBILITY` layout, fixing the extracted-package replay path.
- Added tolerant replay for `llc-0186`, separating exact input integrity,
  numerical tolerance and decision identity.

### Decision safety

- Replaced a single overloaded status with `execution_status`, `gate_result` and
  `engineering_approval` in new records.
- Added an explicitly forced failure fixture that must remain
  `failed/not_applicable/pending`.
- Added configuration validation for schemas, units, ranges, thresholds and
  unknown fields.
- Made zero-survivor populations valid completed runs; the pass example and
  waveform are conditional.
- Added `FHA_SEARCH_BOUNDARY_HIT` without changing pass/reject disposition. The
  full campaign flags `llc-0028`, `llc-0066`, `llc-0069`, `llc-0120` and
  `llc-0156` at 180 kHz.

### Reader experience

- Replaced the ambiguous top-level `PASS` badge with `OUTPUT INTEGRITY: PASS`.
- Added stage-specific status columns, pass/reject FHA gain and phase curves,
  and a pass-case waveform with switching instants.
- Added a Run-all browser notebook with one editable parameter cell.
- Added pass, reject and failed teaching cases.
- Added `START_HERE`, engineering brief, decision contract and model limits.

### ML preparation

- Made `design_id` hardware-only, derived `operating_point_id` from the actual
  condition, and separated `method_inputs` including `Rac`, selected frequency
  and solver settings.
- Added target-availability masks; missing targets remain empty.
- Added feature and target dictionaries, dataset card and design-grouped split
  manifest.
- No model was trained and no claim of dataset readiness was added.

### Verification

- Quick demo from inputs: PASS, 20 records, 17 pass and 3 reject under the
  default contract.
- Full rebuild: PASS, 200 records, 168 pass and 32 reject.
- Archived `llc-0186` tolerant replay: PASS with identical decision.
- Notebook automated Run all: PASS.
- Standard-library tests at that checkpoint: 11 passed, including a temporary
  clean-copy rebuild; the later hardening suite above supersedes this count.
- FHA comparisons use `math.isclose(rel_tol=1e-12, abs_tol=1e-15)` and the suite
  includes the 400 V / 12 V / 100 W zero-pass case.
- Authority package verification: PASS.

### Remaining scientific boundary

The changes establish rebuildability, not higher physical fidelity. LTspice
correlation, operating-envelope diversity, magnetics, devices, thermal behavior
and hardware measurements remain future evidence.

# AI build log: where the engineer retained authority

This log is part of the educational artifact. It records how power-electronics
judgment became an implementation brief, what a coding assistant produced, and
where engineering review changed the result. It is a consolidated build record,
not a claim that hidden reasoning or an unedited chat transcript is authority.

## 1. Decisions owned by the engineer

The engineer fixed the following before accepting code:

- topology: half-bridge LLC with center-tapped secondary;
- operating scope: one fixed-input, full-load point;
- candidate variables and bounds: `Ln`, `Q`, resonant frequency and turns ratio;
- FHA equations, 50–180 kHz search, 1% gain error and 2° inductive phase;
- meaning of `pass`, `reject`, `failed`, `review` and human approval;
- time-domain convergence, measurement window and electrical thresholds;
- model exclusions: magnetics, device losses, thermal, EMI, tolerances and
  hardware correlation;
- acceptance tests, provenance fields and fail-closed behavior.

Those are engineering decisions. A coding assistant may implement them but may
not silently rename, broaden or approve them.

## 2. Consolidated implementation brief given to the coding assistant

> Build a standard-library Python demonstration that generates deterministic
> LLC candidates from a validated configuration, applies a named FHA rejection
> gate, evaluates survivors with the named time-stepped linear-equivalent model,
> and emits machine-readable records plus an offline human report. Keep method
> execution, automatic disposition and engineering approval separate. A failed
> method must never become an electrical reject or a zero-valued ML target.
> Preserve one reproducible result, one reusable artifact and one honest method
> failure. Provide a one-command Windows entry point, a Run-all notebook,
> tolerant cross-version replay, grouped ML splits, hashes and clean-extraction
> tests. Do not require LTspice for the core demonstration and do not claim
> hardware readiness.

The detailed numerical contract is in `ENGINEERING_BRIEF.md`; state semantics
are in `DECISION_CONTRACT.md`; prohibited claims are in `MODEL_LIMITS.md`.

## 3. What the coding assistant implemented correctly

- deterministic Latin-hypercube candidate generation;
- LLC component calculation and FHA frequency sweep;
- time-stepped linear-equivalent evaluation and waveform retention;
- explicit pass/reject/failed bookkeeping;
- JSONL, CSV and ML-oriented exports with missing-target masks;
- design-grouped train/validation/test assignment;
- offline HTML and SVG explanations;
- replay, package verification and clean-copy tests;
- standard-library core with LTspice as optional context only.

## 4. Where the first implementation was too strong or ambiguous

Engineering review found and corrected these failures:

| Initial behavior | Why it was unsafe | Engineering correction |
|---|---|---|
| Called a model power ratio “efficiency” | Suggested device or hardware loss authority | Renamed it `equivalent_model_power_ratio_percent` |
| Called current polarity “ZVS” | A sign proxy does not prove device-level ZVS | Renamed it `commutation_current_sign_proxy` |
| Allowed failed methods to look like rejects | Contaminated future labels | Enforced `failed → not_applicable` |
| Used exact float equality across Python versions | Confused bit identity with numerical reproduction | Added `math.isclose` tolerances |
| Failed when zero candidates survived | Treated a valid all-reject result as software failure | Generated a complete zero-pass report |
| Displayed only a final shorthand state | Hid that FHA completed before time-domain was skipped | Added stage-specific columns |
| Allowed arbitrary topology/model labels | Configuration could claim a model the code did not run | Made topology and model versions code-owned |
| Left HTML in PASS after a later failed verification | Human and machine evidence disagreed | Regenerate HTML and record its SHA-256 on every verify |
| Added a synthetic reject when none occurred | A fixture could be mistaken for campaign evidence | Omit it and state that no real reject occurred |
| Reused `method_run_id` across changed runs | Different executions could collide | Added definition, execution and method identities |
| Retained private absolute paths in archived evidence | Leaked workstation details | Public-package builder redacts or excludes them |
| Treated a license choice as the last publication decision | A license cannot establish pre-existing ownership | Added an explicit owner/employment-IP attestation gate |
| Bundled third-party PDFs and an uncleared LTspice model | Public availability is not redistribution permission | Link-only sources; public archives exclude the material and retain only a sanitized failure fact |
| Kept a clean-copy test tied to an excluded historical adapter | The Evidence Archive could not satisfy its own full test suite | Test the public core and tolerant replay that the archive actually distributes |
| Reused the internal README in smaller public packages | Test counts and verifier commands did not match package contents | Generate one README per public package and state its exact verification surface |
| Copied authority manifests with private source inventory | Public evidence leaked workstation paths and excluded-source metadata | Publish logical source IDs; keep full provenance only in the private authority ZIP |

## 5. How authority is checked now

The release must demonstrate:

1. unsupported topology and invented model labels fail configuration;
2. generated outputs pass hash and semantic verification;
3. tampering changes the human report to `OUTPUT INTEGRITY: FAIL`;
4. zero-pass and zero-reject populations remain honest;
5. numerical replay uses tolerances while archived hashes remain exact;
6. every automatic approval remains `pending` for engineering;
7. public packages contain no private paths or unresolved publication gates;
8. Apache-2.0 applies only to cleared original work; ownership and live public
   URLs must pass separate gates before release.

## 6. Reusable prompt pattern for another power engineer

When adapting this project, do not begin with “build me a converter optimizer.”
Begin with:

```text
Topology and operating envelope:
Equations and model authority:
Editable variables and units:
Named thresholds:
Meaning of pass / reject / failed / review:
Required evidence and provenance:
Acceptance tests:
Explicitly unsupported claims:
Human approval boundary:
```

The coding assistant should implement that contract. The engineer must still
own its physical validity, inspect boundary cases and decide what evidence is
safe to publish.

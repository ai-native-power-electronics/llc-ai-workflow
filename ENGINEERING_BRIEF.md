# Engineering brief

## 1. Engineering objective

Create a rebuildable LLC design-automation demonstration that translates a
fixed electrical specification and explicit decision rules into auditable
candidate records. The primary audience understands converters but may not
program.

## 2. Input specification and units

Default operating point:

| Input | Value | Unit |
|---|---:|---|
| Input voltage | 400 | V |
| Output target | 36 | V |
| Output power | 230 | W |
| Topology | Half-bridge LLC, center-tapped secondary | — |

All configuration fields are validated before candidate generation. Unknown
fields, unsupported units, non-positive values and inverted ranges must fail
with a readable `CONFIGURATION_ERROR`.

This release supports exactly:

```text
topology = half_bridge_llc_center_tapped
operating_condition = fixed_input_full_load
FHA model = center-tapped-fha-v1
equivalent model = switched-linear-equivalent-v1
```

The model labels are code-owned. Configuration may repeat them for
serialization, but any different label is rejected before calculation.

## 3. Variables and bounds

| Variable | Minimum | Maximum |
|---|---:|---:|
| `Ln` | 3.0 | 10.0 |
| `Q` | 0.2 | 0.8 |
| Resonant frequency | 70 kHz | 120 kHz |
| `Ns/Np` | 0.18 | 0.24 |

The default quick demo generates 20 deterministic Latin-hypercube candidates
with seed `20260820`. The full rebuild uses the same seed and 200 candidates.

## 4. Equations and assumptions

Tank component identities:

```text
Rload = Vout² / Pout
Rac_primary = (8 / π²) × (Np/Ns)² × Rload
Z0 = Q × Rac_primary
Lr = Z0 / (2πfr)
Cr = 1 / (2πfrZ0)
Lm = Ln × Lr
```

FHA searches a fixed frequency grid for the required gain while preserving an
inductive input phase. FHA is a rejection gate, never hardware approval.
An FHA survivor whose selected point is exactly at 50 or 180 kHz receives
`FHA_SEARCH_BOUNDARY_HIT`; the warning does not silently change its gate result.
An FHA reject whose closest point is 180 kHz receives
`FHA_REJECT_AT_UPPER_SEARCH_BOUNDARY` and the reason
`FHA_GAIN_TARGET_NOT_REACHED_WITHIN_ALLOWED_SEARCH_AND_PHASE_REGION`.

Survivors enter a switched, time-stepped linear-equivalent tank evaluation.
The secondary is represented by the FHA-equivalent AC load. The model does not
contain detailed switches, rectifier drops, magnetics, thermal behavior or a
closed control loop.

## 5. Decision thresholds

FHA:

- gain-relative error ≤ 1%;
- input phase ≥ 2°;
- search range 50–180 kHz.

Linear-equivalent automatic gate:

- output-voltage relative error ≤ 5%;
- output-power relative error ≤ 15%;
- equivalent-model power ratio between 80% and 100.5%;
- switching frequency between 40 and 250 kHz;
- both commutation-current sign proxies must be true.

These are workflow thresholds for the demonstration, not universal LLC design
rules.

## 6. Failure behavior

A method timeout, invalid telemetry or convergence failure must produce:

```text
execution_status = failed
gate_result = not_applicable
engineering_approval = pending
```

It must never be converted into zero-valued targets or an electrical reject.

## 7. Required outputs

- human-readable offline HTML report;
- candidates and records in JSONL and CSV;
- SHA-256 manifest and verification result;
- reject and explicitly forced-failure examples, plus a pass example when one
  exists;
- SVG plots including pass/reject FHA curves and a pass-case waveform when
  available;
- ML export with target-availability mask and design-grouped splits;
- tolerant replay report for `llc-0186`.

## 8. Acceptance tests

- one command works without third-party Python packages;
- core run does not require LTspice;
- deterministic generation produces stable candidates;
- configuration errors are readable;
- pass, reject and failed states remain distinct;
- zero surviving candidates completes successfully and produces a valid report;
- cross-version FHA float comparisons use published numerical tolerances;
- tampering followed by `verify` rewrites the human report to
  `OUTPUT INTEGRITY: FAIL`, lists errors and records the report SHA-256;
- the human report shows FHA execution, FHA gate, time-domain execution and
  final automated disposition as separate columns;
- clean-copy test rebuilds outputs without archived campaign results;
- tolerant replay preserves the decision and stays inside published tolerances;
- generated text contains no absolute path from the author’s computer.

## 9. Identity boundary for future operating points

`run_definition_id` hashes the validated calculation definition;
`execution_id` distinguishes separate invocations; `method_run_id` combines the
definition, execution, candidate and method. `design_id` hashes only the
hardware tuple `Lr`, `Cr`, `Lm` and turns ratio.
`operating_point_id` hashes input voltage, output targets, equivalent load and
the named control condition; temperature is explicit as unconfigured. Method
inputs retain `Rac`, selected frequency and solver settings separately. Thus a
future line/load dataset can keep every condition of the same hardware in one
train, validation or test group.

## 10. Out-of-scope decisions

The software does not approve a converter, choose devices, design magnetics,
establish thermal or EMI compliance, validate control robustness, claim
hardware correlation or certify a surrogate-training dataset.

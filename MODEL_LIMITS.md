# Model limits

## What the core demonstration supports

- deterministic candidate generation from a named seed and design space;
- FHA gain and inductive-phase screening at one operating point;
- a switched, time-stepped linear-equivalent tank evaluation;
- automated comparison with published workflow thresholds;
- preservation of method failures and missing targets;
- reproducible records, reports and ML-oriented exports.

## What it does not support

- hardware approval or production readiness;
- equivalence with the archived closed-loop LTspice schematic;
- semiconductor switching or conduction losses;
- transformer and resonant-inductor construction;
- core loss, copper loss, saturation or leakage tolerances;
- rectifier drops and parasitics;
- thermal, EMI, safety or regulatory conclusions;
- control-loop stability or startup behavior;
- validation across line, load, temperature and manufacturing tolerances;
- a claim that the current 200 rows form a defensible training dataset.

## Terminology

Use:

- **equivalent-model power ratio**, not hardware or converter efficiency;
- **commutation-current sign proxy**, not measured ZVS;
- **time-stepped linear-equivalent evaluation**, not high-fidelity verification;
- **deterministic replay using the same model and configuration**, not an
  independent validation.

## Optional LTspice adapter

LTspice is not imported or invoked by the core demonstration. `doctor` checks
`LTSPICE_PATH` and common Windows locations only to report whether the optional
adapter could be configured.

The archived LTspice timeout remains evidence of a failed secondary method. It
does not invalidate the bookkeeping demonstration, and it does not validate the
linear-equivalent model.

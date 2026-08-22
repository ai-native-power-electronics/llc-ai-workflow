# Engineering decision contract

The workflow records three separate questions. They must not be collapsed into
one status.

## 1. Did the method execute?

`execution_status`:

| Value | Meaning |
|---|---|
| `not_run` | The method was intentionally skipped, for example after FHA reject |
| `completed` | The method produced valid, decision-safe outputs |
| `failed` | The method did not produce a decision-safe result |

## 2. What did the automatic gate conclude?

`gate_result`:

| Value | Meaning |
|---|---|
| `pass` | All named automatic thresholds were met |
| `reject` | A valid method demonstrated that a named threshold was not met |
| `review` | Valid evidence falls outside the automatic boundary |
| `not_applicable` | No gate decision is possible because the method failed |

## 3. Has an engineer approved the design?

`engineering_approval`:

| Value | Meaning |
|---|---|
| `pending` | No accountable engineering disposition has been recorded |
| `approved` | An authorized engineer approved the scoped decision |
| `rejected` | An authorized engineer rejected the scoped decision |

The demonstration writes `pending` for every automatically processed record.

## Stage-specific human presentation

The report does not use the final contract's execution field as shorthand for
every stage. It presents four distinct columns:

| Scenario | FHA execution | FHA gate | Time-domain execution | Final automated disposition |
|---|---|---|---|---|
| FHA reject | `completed` | `reject` | `not_run` | `reject` |
| Surviving candidate | `completed` | `pass` | `completed` | `pass` or `reject` |
| Forced pipeline failure | `not_applicable` | `not_applicable` | `failed` | `not_applicable` |

## Valid final-contract combinations used here

| Scenario | Execution | Gate | Engineering |
|---|---|---|---|
| FHA reject; time-domain method not run | `not_run` | `reject` | `pending` |
| Linear-equivalent thresholds met | `completed` | `pass` | `pending` |
| Valid evaluation violates threshold | `completed` | `reject` | `pending` |
| Forced or real method failure | `failed` | `not_applicable` | `pending` |

## Invalid combinations

```text
execution_status = failed
gate_result = reject
```

This is invalid because a failed method cannot establish electrical behavior.
The same applies to `failed/pass` and `failed/review`; every failed final method
must use `not_applicable`. A completed method must use `pass`, `reject` or
`review`. The verifier also cross-checks FHA state, time-domain state, final
state and target availability, and the tests fail closed on disagreement.

## Machine-learning consequence

`target_available` is true only when `execution_status=completed`. A failure or
not-run method leaves numerical target columns empty. Zero is a physical value,
not a missing-data marker.

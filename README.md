# LLC AI Workflow

Created and maintained by **Rafael Collado**  
**AI-Native Power Electronics**

A rebuildable demonstration for power-electronics engineers who know
converters—but not software. It turns explicit LLC design rules into auditable
candidate records without giving software authority to approve hardware.

[Read Field Note 001](https://ainativepower.com/insights/evidence-loop-before-the-model) ·
[Get the next evidence-led Field Note](https://ainativepower.com/field-notes) ·
[Open the versioned Colab notebook](https://colab.research.google.com/github/ai-native-power-electronics/llc-ai-workflow/blob/v1.0.0/notebooks/llc_colab.ipynb)

## Run the 20-candidate demo

On Windows, double-click `run_demo.bat`. From a terminal:

```powershell
py -B run_demo.py
```

The default run creates 20 deterministic candidates, applies an FHA gate,
evaluates survivors with the named switched linear-equivalent model and opens
an offline HTML report. The core uses only the Python standard library and does
not require LTspice.

## What the engineer controls

- topology, operating condition and supported model versions;
- equations, variable bounds, units and search range;
- the meaning of pass, reject, failed and review;
- numerical thresholds and acceptance tests;
- claims the model is explicitly not allowed to make.

Start with `ENGINEERING_BRIEF.md`, `DECISION_CONTRACT.md` and
`MODEL_LIMITS.md`. `AI_BUILD_LOG.md` records where engineering review corrected
unsafe or ambiguous automation behavior.

## Rebuild and verify

```powershell
py -B -m unittest discover -s tests -p "test_*.py" -v
py -B run_demo.py
py -B -m llc_tool replay
```

The public-source suite contains **11 tests**. One publication-governance test is
expected to skip in this repository because the internal release-gate files are
deliberately not distributed here; evidence integrity is still tested.

The release contains two open artifacts:

- Quickstart: `https://ainativepower.com/downloads/llc-ai-workflow-quickstart-v1.0.0.zip`
- Evidence Archive: `https://ainativepower.com/downloads/llc-ai-workflow-evidence-archive-v1.0.0.zip`

They are not gated behind email. Subscription is the continuation of the
learning sequence, not a prerequisite for inspecting the evidence.

## Evidence boundary

The archived 200-candidate campaign produced 168 single-point
equivalent-model passes and 32 FHA rejects. Those results are preliminary
electrical screening evidence, not converter approval or a defensible surrogate
training dataset.

The public repository does not redistribute the uncleared LTspice schematic,
netlists, raw outputs, model files or third-party PDFs. It contains only a
sanitized factual record of the secondary-method timeout. See `SOURCES.md`,
`THIRD_PARTY_NOTICES.md` and `LICENSE_SCOPE.md`.

## License

Original cleared material is licensed under Apache License 2.0. Third-party
references and software are not relicensed by this repository.

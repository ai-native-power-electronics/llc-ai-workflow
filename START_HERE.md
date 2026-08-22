# Start here

This package teaches one decision: how engineering rules become auditable
automation without giving software the authority to approve hardware.

No programming knowledge is required for the first run. The core demonstration
uses only the Python standard library and does not require LTspice.

## Option 1 — Windows

Double-click:

```text
run_demo.bat
```

The script checks Python, rebuilds a 20-candidate demonstration, prints a human
summary and opens `summary.html`. On error it pauses so the message remains
visible.

## Option 2 — One command

From this folder:

```powershell
py -B run_demo.py
```

Generated runs are placed beside this package in `LLC_Demo_Runs` so the
published evidence remains read-only.

To change the basic specification without editing code:

```powershell
py -B run_demo.py --vin 400 --vout 36 --pout 230 --candidates 20
```

## Option 3 — Notebook

Open `notebooks/llc_quick_demo.ipynb` in Jupyter or VS Code. For Google Colab,
open `notebooks/llc_colab.ipynb`. If automatic acquisition is unavailable, use
its manual ZIP upload fallback. Edit the clearly marked parameter cell, then
choose **Run all**.

The notebook shows:

1. the specification and design space;
2. deterministic candidate generation;
3. the FHA gate;
4. the time-stepped linear-equivalent evaluation;
5. separate execution, gate and engineering states;
6. the available real pass/reject cases and the forced-failure teaching case;
7. FHA gain/phase curves and a pass-case waveform when a survivor exists;
8. offline plots and the ML-oriented export.

A run with zero automatic passes is valid. It still produces records,
verification and a report explaining that the configured design space contains
no survivor; the pass teaching case and pass waveform are simply omitted.

## What the demo creates

Each new run contains:

```text
summary.html
candidate_records.csv
candidate_records.jsonl
manifest.json
verification.json
pedagogical_cases.json
plots/
ml_dataset_v1.csv
feature_dictionary.json
target_dictionary.json
split_manifest.json
dataset_card.md
```

The report badge says `OUTPUT INTEGRITY: PASS`. It verifies the run artifacts;
it is not a design approval.

If no real analytical reject occurs, none is synthesized for the report. The
report states that the configured population contained no real reject.

The output is generated from configuration, seed, equations and rules. It does
not read the archived 200-candidate results.

## Check the environment

```powershell
py -B -m llc_tool doctor
```

The expected message is that the core is available. LTspice may be available or
unavailable; either result is acceptable because it is an optional adapter.

## Replay the published candidate

```powershell
py -B -m llc_tool replay
```

This rebuilds `llc-0186` with the same linear-equivalent model, compares the
metrics with published tolerances and requires the same gate decision. It is a
deterministic replay, not an independent higher-fidelity validation.

## Full 200-candidate rebuild

After the quick demo:

```powershell
py -B -m llc_tool run --config configs\full_campaign.json
```

This creates a new run. It does not overwrite the archived campaign under
`05_CAMPAIGN`.

## Read next

- `ENGINEERING_BRIEF.md`: what the coding assistant was asked to implement.
- `AI_BUILD_LOG.md`: where engineering review changed the implementation.
- `DECISION_CONTRACT.md`: exact state meanings and acceptance rules.
- `MODEL_LIMITS.md`: claims the demonstration cannot support.
- `SERIES_ROADMAP.md`: how this artifact becomes a sequence rather than an
  isolated article.
- `CHANGELOG_REBUILDABLE.md`: exact publication-preflight changes and results.
- [The canonical Field Note](https://ainativepower.com/insights/evidence-loop-before-the-model):
  the reader-facing article on the web.
- Publication-gate details are distributed with the versioned Quickstart and
  Evidence Archive; they are intentionally separate from technical PASS.
- `LICENSE_SCOPE.md` and `THIRD_PARTY_NOTICES.md`: what Apache-2.0 does and does
  not cover.

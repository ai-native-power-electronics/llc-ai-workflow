# Notebook

Open `llc_quick_demo.ipynb`, edit the parameter cell and choose **Run all**.

The notebook uses the package’s standard-library core. Jupyter or a compatible
browser notebook supplies only the interactive display environment; the LLC
workflow itself has no third-party Python dependency.

If the notebook is opened from the `notebooks` directory, it automatically adds
the parent package to Python’s import path. Generated runs are written beside
the package under `LLC_Notebook_Runs`.

The notebook displays the stage-specific status table, FHA gain/phase curves
and the pass-case waveform. If the edited specification produces zero passes,
Run all remains successful and the pass-only visual is omitted.

`llc_colab.ipynb` is the Colab-ready entry point. It can clone the fixed
`v1.0.0` tag, download the versioned Quickstart or use a manual ZIP upload as a
fallback. Publication maintainers verify the tagged notebook and release assets
using the release-gate files included in the versioned Quickstart and Evidence
Archive.

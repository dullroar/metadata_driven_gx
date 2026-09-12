# Notebook walkthrough

This folder is the notebook-first path through the repository. Start with
[`end_to_end.ipynb`](end_to_end.ipynb) if you want to understand the complete workflow
without first learning the command-line entry points.

## Setup

From the repository root, create the environment and install the single dependency set:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/jupyter notebook dbx_notebooks/end_to_end.ipynb
```

The notebook uses the committed `demo_weather` environment, so no data preparation is
needed. The example has six synthetic tables, metadata-driven expectations, and planted
failures that make both passing and failing results visible.

## What the notebook does

1. Finds the repository root and imports `end_to_end` with an ordinary Python import.
2. Runs `end_to_end.run_pipeline()`, the same orchestration used by
   `python end_to_end.py --config-file configs/demo_weather.yaml`.
3. Reads representative summary and detail CSVs from the demo output.
4. Points to the generated GX Data Docs site.

The notebook contains no copy of the generator, consumer, or extractor logic. The source
of truth remains the CSV metadata under `environments/demo_weather/suites/`; generated GX
suites live under `environments/demo_weather/gx/` and flattened results under
`environments/demo_weather/output/`.

The run cell defaults to `CLEAN = False`, which preserves existing generated artifacts.
Set it to `True` only when you intentionally want to reset and regenerate the demo GX
store and output. GX assigns timestamps and identifiers during runs, so those generated
files may show incidental diffs afterward; see the repository's `AGENTS.md` guidance.

This committed notebook is different from the disposable `play/edit_*.ipynb` notebooks
created by `edit_suite.py`: this one teaches the full pipeline, while those are scratch
spaces for editing one suite.

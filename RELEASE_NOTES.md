# Release Notes

This project's version lives here and in each version's commit message
(`vX.Y.Z: <summary>`) -- there are no git tags. Update this file in the same commit as
whatever change it describes; see [CLAUDE.md](CLAUDE.md)/[AGENTS.md](AGENTS.md) for the
standing instruction to AI coding agents to do this without being asked each time.

## v0.0.5

- Added [TESTING_WITH_GX.md](TESTING_WITH_GX.md): an essay on using this repo's
  `environments/` pattern (a config file plus its own `suites/`/`gx/`/`output/`/data
  directories) as a general-purpose, AI-generatable whitebox output-testing harness for
  *any other codebase* that produces tabular output -- including pointing an
  environment's directories at the target codebase's own repo so the generated suites
  and results version-control there instead of here.

## v0.0.4

- Added a committed `dbx_notebooks/end_to_end.ipynb` and notebook-focused README for
  learning the complete `demo_weather` pipeline interactively.
- Exposed `end_to_end.run_pipeline()` so the CLI and notebook share one orchestration
  path instead of duplicating the workflow.
- Added Jupyter and IPython kernel dependencies to `requirements.txt`.

## v0.0.3

- Added `edit_suite.py`: generates (and launches) a disposable Jupyter notebook for
  interactively editing one expectation suite against real data. Replaces the
  `great_expectations suite edit <SUITE>` CLI command GX 1.x removed entirely -- Data
  Docs' own "How to Edit This Suite" button still quotes that dead command. See the new
  "Interactively editing a suite" section in [README.md](README.md) and step in
  [GETTING_STARTED.md](GETTING_STARTED.md).

## v0.0.2

- Documented GX's own GUID/timestamp churn when re-running the committed `demo_weather`
  example, for both humans (a new README.md section) and AI coding agents
  (CLAUDE.md/AGENTS.md), so it doesn't get mistaken for a real diff worth staging,
  committing, or flagging.

## v0.0.1

- Initial extracted, database-agnostic metadata-driven GX stack: expectations described
  as rows in a CSV, compiled into GX suites, run against data, and flattened back into
  readable CSVs, plus a fully worked `demo_weather` environment.

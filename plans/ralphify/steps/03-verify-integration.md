---
id: 03-verify-integration
status: pending
depends_on: [02-build-and-test]
touches:
  - plans/ralphify/steps/03-verify-integration.md
lane: none
requirements: [R3]
gate: python3 scripts/check_context.py && bash scripts/test_docker.sh && git diff --check
evidence: ""
---

# 03-verify-integration

Depends on `02-build-and-test`. Update only the step file. Rerun the context and Docker gate from the integrated worktree as the driver would. Check the template and runner links in `AGENTS.md` and the structural-change rule. Verify README commands and the existing entry points. Record the worktree base commit, exact commands, build result, test counts or concrete smoke assertions, expected opt-in skips, real FUSE result where required, and UTC date. Keep logs outside Git. Gate: `python3 scripts/check_context.py && bash scripts/test_docker.sh && git diff --check`.

The driver writes its own `evidence` field. Put detailed test evidence in the body of the verification step and commit it. The parent verifies the final child commit and result. A green build alone cannot satisfy R2 or R3.

## Repository gate

Install from `requirements.txt`. Run `python end_to_end.py --config-file configs/demo_weather.yaml` using the committed demo inputs and suites in a disposable copy in the container. Check the expected summary and detail CSVs and compare stable row counts, columns, and outcomes with the committed sample. Ignore only fields known to vary across runs, such as timestamps. Scope config or test support changes to the local demo. Preserve Databricks documentation, keep its runtime out of the Docker gate, and leave GX output contracts intact for consumers.

Run `git merge-base HEAD plan/ralphify` to identify the integrated base commit. Replace each pending value in the results below. For each passing check, put details after `PASS`. Include the actual Docker commands or image reference and test counts or concrete smoke results. Record `n/a` in the FUSE field for other repos. If a required test fails or skips, record that in resume notes and leave the result pending.

## Results

- Base commit: `8841dc341cc42cd525a2731ea4fb7d9586a74f48` from
  `git merge-base HEAD plan/ralphify`.
- Commands: PASS. `python3 scripts/check_context.py && bash scripts/test_docker.sh && git diff --check`.
  The context checks passed on the host and in the image. They checked the generated
  indexes, plan, links, and context secrets.
- Docker build: PASS. The gate built a Python 3.11 image from the tracked files.
  The image used the cached install from `requirements.txt`.
- Tests: PASS. In a temporary copy, the container ran
  `python end_to_end.py --config-file configs/demo_weather.yaml`. It ran six suites
  and matched all 12 sample CSVs, with 50 summary rows and 34 detail rows. It compared
  file names, column order, and all row values except `run_date`. The summary rows
  include 21 successful expectations and 29 expected data validation failures.
- Skips: No required tests skipped. The demo skipped the optional GX validation
  cleanup because it had no cleanup quantity. Databricks is outside the Docker gate.
- FUSE: n/a.
- UTC date: 2026-11-22.

## README and entry points

- PASS. The README's direct build and run also passed with a unique local tag.
  `docker build -t metadata-driven-gx:verify-RkK0hlCJ .` installed the dependencies
  from `requirements.txt`. `docker run --rm --network none metadata-driven-gx:verify-RkK0hlCJ`
  matched all 12 sample CSVs through the default image command.
- PASS. In the image, `python <script> --help` exited successfully for all six
  existing CLI scripts. These are `end_to_end.py`, `gx_generator.py`,
  `gx_consumer.py`, `gx_validations_extractor.py`, `clear_old_gx_validations.py`,
  and `edit_suite.py`. The notebook's `end_to_end.run_pipeline` entry point
  imported as a callable.
- PASS. Both GitHub links in `AGENTS.md` resolved to the expected repositories.
  The structure rule names the layout, plan format, generated indexes, worktree
  rules, and validation commands.
- PASS. The README's two Ralph invocations match the local runner's usage. Its
  status parser reported two done steps and one pending step before this update.
  The active driver owns plan execution and worktree changes.

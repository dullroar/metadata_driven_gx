"""edit_suite.py -- generate a disposable Jupyter notebook for interactively editing one
Great Expectations suite.

Great Expectations' 1.x line dropped the `great_expectations` CLI entirely (no more
`great_expectations suite edit <SUITE>`) -- but the Data Docs template shipped inside the
`great_expectations` package still has a leftover "How to Edit This Suite" popup that
quotes that removed command (render/view/templates/edit_expectations_instructions_modal.j2
in the installed package). This script is this repo's replacement: it builds the same kind
of disposable, load-suite-then-iterate notebook the old CLI used to scaffold, using the
current fluent (Batch.validate) API instead of the removed one, and wired to this repo's
own config/data-loading conventions (see gx_consumer.py) instead of a plain CSV read.

Usage:
    python edit_suite.py CUSTOMERS --config-file configs/demo_weather.yaml

Writes play/edit_<SUITE>.ipynb (gitignored -- see repo .gitignore's `play/` entry) and,
unless --no-launch is passed, opens it by executing `jupyter notebook` on it.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import gx_consumer  # noqa: E402  (path must be set up first)

PLAY_DIR = ROOT / "play"


def _table_for_suite(suite_name: str) -> str:
    """Look up the source table for `suite_name` the same way gx_consumer does: from
    meta.table on the suite's own expectations, not from any naming convention."""
    suite_path = Path(gx_consumer.CONFIG["expectations_dir"]) / f"{suite_name}.json"
    if not suite_path.exists():
        raise RuntimeError(f"No expectation suite file at {suite_path}")
    table = gx_consumer._table_from_meta(suite_path)
    if table is None:
        raise RuntimeError(
            f"Suite '{suite_name}' has no meta.table on any expectation in {suite_path}"
        )
    return table


def _code_cell(source: str) -> dict:
    lines = source.splitlines(keepends=True)
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines,
    }


def _markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def build_notebook(suite_name: str, config_file: str) -> dict:
    table_name = _table_for_suite(suite_name)
    # Embed an absolute path: the notebook's kernel cwd is play/, not repo root, so a
    # relative config_file (like the default computed in main()) would otherwise resolve
    # against the wrong directory when the notebook actually runs.
    config_file_abs = str(Path(config_file).expanduser().resolve())

    setup_source = (
        "import os\n"
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        "import great_expectations as gx\n"
        "\n"
        f"ROOT = Path({str(ROOT)!r})\n"
        "sys.path.insert(0, str(ROOT))\n"
        "os.chdir(ROOT)  # gx_consumer's config paths (e.g. csv_data_dir) are cwd-relative,\n"
        "                # matching how gx_generator.py/gx_consumer.py are always run from repo root\n"
        "import gx_consumer\n"
        "\n"
        f"gx_consumer.load_config({config_file_abs!r})\n"
        "\n"
        f"SUITE_NAME = {suite_name!r}\n"
        f"TABLE_NAME = {table_name!r}\n"
        "\n"
        "context = gx.get_context(context_root_dir=Path(gx_consumer.CONFIG[\"gx_root_dir\"]))\n"
        "suite = context.suites.get(name=SUITE_NAME)\n"
        "df = gx_consumer.load_dataframe(TABLE_NAME, gx_consumer.CONFIG[\"csv_data_dir\"])\n"
        "\n"
        "# A datasource/asset scoped to this editing session only -- distinct from\n"
        "# gx_consumer's tabular_pandas/tabular_df so a real gx_consumer run happening\n"
        "# elsewhere can't collide with (or be disrupted by) this notebook. (A second,\n"
        "# separate DataContext -- e.g. gx.get_context(mode=\"ephemeral\") -- would keep this\n"
        "# off `context` entirely, but a second get_context() call in the same process\n"
        "# corrupts this one's suites store in GX 1.12.3; see the Cleanup cell at the\n"
        "# bottom for how this notebook avoids leaving `suite_editor` behind instead.)\n"
        "datasource = context.data_sources.add_or_update_pandas(name=\"suite_editor\")\n"
        "asset = datasource.add_dataframe_asset(name=\"editor_df\")\n"
        "batch_definition = asset.add_batch_definition_whole_dataframe(name=f\"edit_{SUITE_NAME}\")\n"
        "batch = batch_definition.get_batch(batch_parameters={\"dataframe\": df})\n"
        "\n"
        "print(\n"
        "    f\"Loaded suite {SUITE_NAME!r} ({len(suite.expectations)} expectations) \"\n"
        "    f\"against table {TABLE_NAME!r} ({df.shape[0]} rows, {df.shape[1]} cols)\"\n"
        ")\n"
    )

    cells = [
        _markdown_cell(
            f"# Editing suite `{suite_name}`\n"
            "\n"
            "This notebook is **disposable** -- it is not the source of truth for the "
            f"suite. `{suite_name}` (in `expectations/{suite_name}.json`) is. This "
            "notebook is just a scratch space to try expectations against real data "
            "before committing them to that file.\n"
            "\n"
            "Replaces the removed `great_expectations suite edit "
            f"{suite_name}` CLI command (GX 1.x dropped the CLI; Data Docs' \"How to "
            "Edit This Suite\" button still quotes it). Delete this notebook (and its "
            "whole `play/` directory) whenever -- nothing here persists except what you "
            "explicitly save back to the suite below.\n"
        ),
        _code_cell(setup_source),
        _markdown_cell(
            "## Current state\n\nRun the suite as it exists on disk right now, against "
            "the real data, to see what's currently passing/failing."
        ),
        _code_cell("current_results = batch.validate(suite)\ncurrent_results\n"),
        _markdown_cell(
            "## Try a new expectation\n\nBuild a candidate expectation and validate it "
            "by itself first -- this does **not** touch the suite on disk, so iterate "
            "freely."
        ),
        _code_cell(
            "candidate = gx.expectations.ExpectColumnValuesToNotBeNull(column=\"FIRST_NAME\")\n"
            "preview = batch.validate(candidate)\n"
            "preview\n"
        ),
        _markdown_cell(
            "## Commit it\n\nHappy with the preview above? Add it to the suite and save. "
            "This is the one cell in this notebook with a durable side effect -- everything "
            "above only ran against an in-memory batch."
        ),
        _code_cell(
            "suite.add_expectation(candidate)\n"
            "context.suites.add_or_update(suite=suite)\n"
            "print(f\"Saved. Suite now has {len(suite.expectations)} expectations.\")\n"
        ),
        _markdown_cell(
            "## Re-run the full suite\n\nConfirm the saved suite still runs end to end "
            "against the same data."
        ),
        _code_cell(
            "final_results = batch.validate(suite)\n"
            "final_results.success, len(final_results.results)\n"
        ),
        _markdown_cell(
            "## Cleanup\n\nThe setup cell registered a scratch `suite_editor` "
            "datasource on `context` so `batch.validate(...)` above had something to "
            "run against -- GX persists that registration into `great_expectations.yml` "
            "immediately, so without this cell it would stick around as permanent, "
            "unwanted project config every time this notebook runs. `context.data_sources"
            ".delete(...)` *looks* like the fix but silently doesn't rewrite the file in "
            "GX 1.12.3 (its in-memory removal isn't followed by a real save), so this "
            "edits `great_expectations.yml` directly instead."
        ),
        _code_cell(
            "import yaml\n"
            "\n"
            "yml_path = Path(gx_consumer.CONFIG[\"gx_root_dir\"]) / \"great_expectations.yml\"\n"
            "cfg = yaml.safe_load(yml_path.read_text())\n"
            "cfg.get(\"fluent_datasources\", {}).pop(\"suite_editor\", None)\n"
            "if not cfg.get(\"fluent_datasources\"):\n"
            "    cfg.pop(\"fluent_datasources\", None)\n"
            "yml_path.write_text(yaml.safe_dump(cfg, sort_keys=False, default_flow_style=False))\n"
            "print(\"Removed scratch datasource from great_expectations.yml\")\n"
        ),
    ]

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate (and launch) a disposable notebook for editing one GX suite."
    )
    parser.add_argument("suite_name", help="Suite to edit, e.g. CUSTOMERS")
    parser.add_argument(
        "--config-file", default=str(ROOT / "configs" / "demo_weather.yaml"),
        help="Config file to resolve gx_root_dir/csv_data_dir from (default: demo_weather).",
    )
    parser.add_argument(
        "--no-launch", action="store_true",
        help="Only write the notebook; don't open Jupyter.",
    )
    args = parser.parse_args()

    gx_consumer.load_config(args.config_file)
    notebook = build_notebook(args.suite_name, args.config_file)

    PLAY_DIR.mkdir(exist_ok=True)
    out_path = PLAY_DIR / f"edit_{args.suite_name}.ipynb"
    out_path.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")

    if not args.no_launch:
        subprocess.run(
            [sys.executable, "-m", "jupyter", "notebook", str(out_path)],
            cwd=ROOT,
        )


if __name__ == "__main__":
    main()

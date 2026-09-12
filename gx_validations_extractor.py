"""Extract data from GX Validations JSON files into tabular (e.g., CSV, Excel, SQL databases) or other formats (e.g., different JSON for ingestion by a data-catalog API)."""

import argparse
import csv
import logging
import json
import sys
from pathlib import Path

import extractor_common as _common

ROOT = Path(__file__).resolve().parent   # repo root: every path resolves against this, never cwd
DEFAULT_CONFIG_FILE = ROOT / "configs" / "TEMPLATE.yaml"
_PROGRAM = "gx_validations_extractor"    # section read from the config file
logger = logging.getLogger(_PROGRAM)

sys.path.insert(0, str(ROOT))
import common

# Repo layout is derived, never configured: it is identical in every environment.
# gx_root_dir and output_root_dir are the two portable anchors (see configs/TEMPLATE.yaml).
_LAYOUT = {
    "gx_root_dir": ROOT / "gx",
    "output_root_dir": ROOT / "output",
}
_DERIVED_FROM_GX_ROOT = {"validations_dir": "uncommitted/validations"}
_DERIVED_FROM_OUTPUT_ROOT = {"output_directory": "", "log_dir": "logs"}  # output_directory: writes CSVs directly under output_root_dir

CONFIG: dict = {}                        # mutated in place by load_config(); never rebound

_DEFAULT_DETAILS_CAP = 50                 # rows exploded per expectation before sampling kicks in


def load_config(path=None) -> dict:
    """Populate CONFIG from `path` (default: configs/TEMPLATE.yaml). See common.load_config
    for the full precedence rule."""
    return common.load_config(
        CONFIG, _PROGRAM, _LAYOUT, ROOT, DEFAULT_CONFIG_FILE, path,
        derived_from_gx_root=_DERIVED_FROM_GX_ROOT,
        derived_from_output_root=_DERIVED_FROM_OUTPUT_ROOT,
    )


load_config()                            # importers get the checked-in default


def write_csv(path: Path, rows: list[dict]) -> None:
    """Helper to write a list of dictionaries to a CSV file.

    Uses the union of keys across every row (not just rows[0]) as the header: a suite's
    detail rows can legitimately differ in shape -- e.g. an exploded per-value row next to
    a fallback row for a column that errored instead of failing -- so a fixed rows[0]-only
    header would raise on the first row carrying an extra key.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.touch()
        return

    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


_DETAIL_LEADING = ("source", "environment_name", "table", "expectation_type", "column")
_DETAIL_TRAILING = (
    "bad_value", "bad_value_a", "bad_value_b", "exception_message",
    "observed_value", "unexpected_count", "exploded_count", "has_sample_value", "run_date",
)


def _flatten_for_csv(row: dict) -> dict:
    """Expand a detail row's `key_columns` dict into real, named columns for spreadsheet/DB
    lookup use (e.g. natural key columns from common.join_keys). Falls back to the raw
    `row_key` when no named columns could be resolved for that row.
    """
    key_columns = row.get("key_columns")
    middle = key_columns if key_columns else ({"row_key": row["row_key"]} if row.get("row_key") else {})
    return {
        **{k: row[k] for k in _DETAIL_LEADING},
        **middle,
        **{k: row[k] for k in _DETAIL_TRAILING},
    }


def process_validations() -> None:
    # Read inside the function, not at import: end_to_end propagates --config-file by
    # calling load_config() after import, so module-level values would miss it.
    output_base_dir = Path(CONFIG["output_directory"])
    join_keys = CONFIG.get("join_keys", {}) or {}
    details_cap = int(CONFIG.get("details_cap", _DEFAULT_DETAILS_CAP))
    environment_name = CONFIG.get("environment_name", "default")

    # 1. Extract information from the most recent run of each expectation suite
    json_paths = _common.latest_json_paths(Path(CONFIG["validations_dir"]))

    for name, json_path in json_paths:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        results = data.get("results", [])
        if not results:
            continue

        run_date = data.get("meta", {}).get("validation_time")
        out_dir = output_base_dir / name

        # 2a. Summary Statistics -- every result, pass or fail
        summary_rows = [
            _common.build_summary_row(
                r, name, _common.table_for_result(r), run_date, environment_name=environment_name
            )
            for r in results
        ]

        # 2b. Detailed Failures -- exploded per offending value (capped), or a single
        # fallback row for exceptions/aggregate expectation types
        failures = (r for r in results if not r.get("success", True))
        details_rows = [
            _flatten_for_csv(row)
            for r in failures
            for row in _common.build_detail_rows(
                r, name, _common.table_for_result(r), run_date, join_keys, cap=details_cap,
                environment_name=environment_name,
            )
        ]

        # 3. Outputs each pair of CSVs to the appropriate directory
        write_csv(out_dir / f"{name}_summary.csv", summary_rows)
        write_csv(out_dir / f"{name}_details.csv", details_rows)
        logger.info("Extracted results for suite '%s' to %s", name, out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flatten GX validation results into CSVs")
    parser.add_argument(
        "--config-file",
        default=None,   # None, not DEFAULT_CONFIG_FILE: import already loaded the default, so
                        # leaving this None keeps a caller's CONFIG override intact.
        help=f"Unified config file for this test environment. Default: {DEFAULT_CONFIG_FILE}",
    )
    parser.add_argument(
        "--details-cap",
        type=int,
        default=None,
        help=(
            "Max exploded detail rows per expectation before sampling kicks in "
            f"(every row still carries the true unexpected_count). Default: {_DEFAULT_DETAILS_CAP}, "
            "or details_cap in the config file."
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging verbosity for this run (file and console). Default: INFO, "
             "or log_level in the config file.",
    )
    args = parser.parse_args()
    if args.config_file:
        load_config(args.config_file)
    common.configure(_PROGRAM, CONFIG, cli_log_level=args.log_level)
    if args.details_cap is not None:
        CONFIG["details_cap"] = args.details_cap

    process_validations()

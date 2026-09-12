"""Run the full metadata-driven GX pipeline end to end: generate suites, validate CSV
data against them, extract results to CSV, and (optionally) reset the GX store first."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent   # repo root: every path resolves against this, never cwd
DEFAULT_CONFIG_FILE = ROOT / "configs" / "TEMPLATE.yaml"
_PROGRAM = "end_to_end"                  # section read from the config file
logger = logging.getLogger(_PROGRAM)

sys.path.insert(0, str(ROOT))
import common

# output_root_dir is the portable anchor for this run's own log file (see configs/TEMPLATE.yaml).
_LAYOUT = {"output_root_dir": ROOT / "output"}
_DERIVED_FROM_OUTPUT_ROOT = {"log_dir": "logs"}

CONFIG: dict = {}                        # mutated in place by load_config(); never rebound


def load_config(path=None) -> dict:
    """Populate CONFIG from `path` (default: configs/TEMPLATE.yaml). See common.load_config
    for the full precedence rule."""
    return common.load_config(
        CONFIG, _PROGRAM, _LAYOUT, ROOT, DEFAULT_CONFIG_FILE, path,
        derived_from_output_root=_DERIVED_FROM_OUTPUT_ROOT,
    )


load_config()

import gx_generator as gen
import gx_consumer as con
import gx_validations_extractor as ext
import clear_old_gx_validations as cogv


def run_pipeline(
    config_file=None,
    csv_dir=None,
    suites=None,
    clean=False,
    log_level=None,
) -> None:
    """Run every pipeline stage using one shared configuration.

    This is the reusable entry point for the CLI and the educational notebook. Each
    stage remains responsible for its own work; this function only coordinates them.
    """
    if config_file:
        cfg = str(Path(config_file).expanduser().resolve())
        load_config(cfg)
        for module in (gen, con, ext, cogv):
            module.load_config(cfg)

    common.configure(_PROGRAM, CONFIG, cli_log_level=log_level)

    selected_csv_dir = csv_dir or con.CONFIG.get("csv_data_dir")
    selected_suites = suites or CONFIG.get("suites") or "*"
    if not selected_csv_dir:
        raise ValueError(
            "csv_dir is required (or set csv_data_dir under `gx_consumer:` in the config file)"
        )

    cogv.run("all" if clean else None)
    gen.generate_all()
    con.run_validation_multiple(selected_csv_dir, selected_suites)

    try:
        ext.process_validations()
    except Exception:
        logger.exception("Stage 'gx_validations_extractor' failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full metadata-driven GX pipeline end to end")
    parser.add_argument(
        "--csv-dir",
        default=None,
        help="Directory of CSV/delimited files, one per table. Or set csv_data_dir under gx_consumer: in the config file.",
    )
    parser.add_argument(
        "--suites",
        default=None,
        help='Glob pattern for suite selection, matched against suite file stems (e.g. "ORDERS*"). Default: "*" (all suites).',
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Force a full reset (clear_old_gx_validations, quantity 'all') before running, "
             "regardless of what this environment's config file has quantity set to.",
    )
    parser.add_argument(
        "--config-file",
        default=None,
        help=f"Unified config file for this test environment, propagated to every stage. "
             f"Default: {DEFAULT_CONFIG_FILE}",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging verbosity for this run (file and console). Default: INFO, "
             "or log_level in the config file.",
    )
    args = parser.parse_args()

    try:
        run_pipeline(
            config_file=args.config_file,
            csv_dir=args.csv_dir,
            suites=args.suites,
            clean=args.clean,
            log_level=args.log_level,
        )
    except ValueError as exc:
        parser.error(str(exc))

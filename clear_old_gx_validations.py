"""Delete old timestamped GX validation result directories from gx/uncommitted/validations,
or (quantity "all") reset this environment's entire GX store and output tree."""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent   # repo root: every path resolves against this, never cwd
DEFAULT_CONFIG_FILE = ROOT / "configs" / "TEMPLATE.yaml"
_PROGRAM = "clear_old_gx_validations"    # section read from the config file
logger = logging.getLogger(_PROGRAM)

sys.path.insert(0, str(ROOT))
import common

# Repo layout is derived, never configured: it is identical in every environment.
# gx_root_dir is the portable anchor (see configs/TEMPLATE.yaml).
_LAYOUT = {
    "gx_root_dir": ROOT / "gx",
    "output_root_dir": ROOT / "output",
}
_DERIVED_FROM_GX_ROOT = {"validations_dir": "uncommitted/validations"}
_DERIVED_FROM_OUTPUT_ROOT = {"log_dir": "logs"}

CONFIG: dict = {}                        # mutated in place by load_config(); never rebound


def load_config(path=None) -> dict:
    """Populate CONFIG from `path` (default: configs/TEMPLATE.yaml). See common.load_config
    for the full precedence rule."""
    return common.load_config(
        CONFIG, _PROGRAM, _LAYOUT, ROOT, DEFAULT_CONFIG_FILE, path,
        derived_from_gx_root=_DERIVED_FROM_GX_ROOT,
        derived_from_output_root=_DERIVED_FROM_OUTPUT_ROOT,
    )


load_config()                            # importers get the checked-in default

USAGE = """\
Usage: clear_old_gx_validations.py [<quantity>]

Arguments:
  all      Full environment reset: delete every generated GX artifact (suite,
           checkpoint, and validation_definition JSON, plus the rendered data docs
           and validation-run history under gx/uncommitted/) and everything under
           output/ except output/logs/ (this and prior runs' own audit trail).
           Use before a from-scratch re-run, or when a suite has been retired --
           a removed suites/*.csv stops it being regenerated, but not by itself
           this environment's already-materialized GX artifacts, which is what
           keeps stale suites showing up (and taking real full-table-scan time)
           in a run long after their metadata CSV is gone: gx_consumer discovers
           suites by scanning gx/expectations/*.json directly, not by reading CSVs.
  <number> Delete the oldest <number> timestamped result directories from each
           suite under gx/uncommitted/validations. Newer results are left
           untouched. If <number> exceeds the available results for a suite,
           all results for that suite are cleared, leaving its __none__
           directory empty.

  If omitted, falls back to `quantity` in the config file's own section
  (see configs/TEMPLATE.yaml) -- this is what lets end_to_end.py run this as an
  ordinary config-driven stage instead of requiring a separate manual invocation.
  With neither a CLI quantity nor a configured one, this is a no-op.

Options:
  --config-file <path>  Unified config file for this test environment.
                        Default: configs/TEMPLATE.yaml
  --log-level <level>   Logging verbosity for this run (file and console):
                        DEBUG, INFO, WARNING, or ERROR. Default: INFO, or
                        log_level in the config file.

Examples:
  python clear_old_gx_validations.py all
  python clear_old_gx_validations.py 2
  python clear_old_gx_validations.py 2 --config-file ../configs/my-project.yaml
"""


def suite_dirs(validations_dir: Path) -> list[Path]:
    return sorted(d for d in validations_dir.iterdir() if d.is_dir())


def timestamped_dirs(suite_dir: Path) -> list[Path]:
    run_parent = suite_dir / "__none__"
    if not run_parent.is_dir():
        return []
    return sorted(d for d in run_parent.iterdir() if d.is_dir())


def clear_oldest(validations_dir: Path, quantity: int) -> None:
    total_removed = 0
    for suite_dir in suite_dirs(validations_dir):
        runs = timestamped_dirs(suite_dir)
        for run_dir in runs[:quantity]:
            shutil.rmtree(run_dir)
            print(f"  Removed: {suite_dir.name}/{run_dir.name}")
            total_removed += 1
    print(f"\nRemoved {total_removed} run director{'y' if total_removed == 1 else 'ies'}.")


def clear_generated(gx_root_dir: Path) -> int:
    """Delete every regenerable GX artifact under gx_root_dir: suite, checkpoint, and
    validation_definition JSON (these are what gx_consumer.discover_suite_names()
    actually iterates -- a retired suites/*.csv alone does not stop it running), plus the
    rendered data docs and the full validation-run history. Returns the JSON file count removed."""
    removed = 0
    for sub in ("expectations", "checkpoints", "validation_definitions"):
        for p in (gx_root_dir / sub).glob("*.json"):
            p.unlink()
            removed += 1
    for sub in ("uncommitted/validations", "uncommitted/data_docs"):
        shutil.rmtree(gx_root_dir / sub, ignore_errors=True)
    return removed


def clear_output(output_root_dir: Path) -> int:
    """Delete everything under output_root_dir except logs/ (this and prior runs' own audit
    trail, not regenerable output). Returns the entry count removed."""
    removed = 0
    for p in output_root_dir.iterdir():
        if p.name == "logs":
            continue
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        removed += 1
    return removed


def run(quantity: Optional[str] = None) -> None:
    """Do the configured clear. `quantity` (falls back to CONFIG["quantity"]) is "all", a
    positive integer string, or unset -- unset is a no-op, which is what lets this run
    unconditionally as an end_to_end stage without affecting environments that haven't
    opted in."""
    quantity = (quantity or CONFIG.get("quantity") or "").strip()
    if not quantity:
        logger.info("No quantity configured; skipping clear_old_gx_validations.")
        return

    validations_dir = Path(CONFIG["validations_dir"])
    if quantity == "all":
        gx_root_dir = Path(CONFIG["gx_root_dir"])
        output_root_dir = Path(CONFIG["output_root_dir"])
        print(f"Full reset: clearing generated GX artifacts under:\n  {gx_root_dir}\n")
        artifact_count = clear_generated(gx_root_dir)
        print(f"Removed {artifact_count} suite/checkpoint/validation_definition JSON file(s), "
              f"plus uncommitted/validations and uncommitted/data_docs.")
        print(f"\nClearing output under:\n  {output_root_dir}\n(logs/ preserved)\n")
        output_count = clear_output(output_root_dir)
        print(f"Removed {output_count} entr{'y' if output_count == 1 else 'ies'}.")
    elif quantity.isdigit() and int(quantity) > 0:
        n = int(quantity)
        print(f"Clearing the oldest {n} run(s) from each suite under:\n  {validations_dir}\n")
        clear_oldest(validations_dir, n)
    else:
        raise ValueError(f"Invalid quantity: '{quantity}'.")


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("quantity", nargs="?")
    parser.add_argument("--config-file", default=None)
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default=None)
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()

    if args.help:
        print(USAGE)
        return
    if args.config_file:
        load_config(args.config_file)
    common.configure(_PROGRAM, CONFIG, cli_log_level=args.log_level)

    quantity = (args.quantity or CONFIG.get("quantity") or "").strip()
    if not quantity:
        print("No quantity specified (CLI or config). You must provide one.\n")
        print(USAGE)
        sys.exit(1)

    try:
        run(quantity)
    except ValueError as e:
        print(f"{e}\n")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()

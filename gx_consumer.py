"""Consume gx expectation suites against tabular data and persist results."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import great_expectations as gx
import great_expectations.checkpoint.actions as gx_actions
import pandas as pd

ROOT = Path(__file__).resolve().parent   # repo root: every path resolves against this, never cwd
DEFAULT_CONFIG_FILE = ROOT / "configs" / "TEMPLATE.yaml"
_PROGRAM = "gx_consumer"                 # section read from the config file
logger = logging.getLogger(_PROGRAM)

sys.path.insert(0, str(ROOT))
import common

# Repo layout is derived, never configured: it is identical in every environment.
# gx_root_dir is the one portable anchor (see configs/TEMPLATE.yaml) -- everything GX
# itself manages (checkpoints/, validation_definitions/, uncommitted/) moves with it
# automatically since those store paths are relative to context_root_dir.
# expectations_dir is OUR OWN direct filesystem read (discover_suite_names/
# _build_suite_table_map bypass the GX context object), so it must be derived
# explicitly.
_LAYOUT = {
    "gx_root_dir": ROOT / "gx",
    "output_root_dir": ROOT / "output",
}
_DERIVED_FROM_GX_ROOT = {"expectations_dir": "expectations"}
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

_df_cache: Dict[str, pd.DataFrame] = {}  # keyed by table name; survives across runs

# GX's fluent Batch._create_id() joins Data Source name + Data Asset name verbatim into the
# on-disk validation filename. These stay constant across every suite in a run (the suite name
# already disambiguates the parent folder), so the filename never grows with table/suite length.
_GX_DATASOURCE_NAME = "tabular_pandas"
_GX_ASSET_NAME = "tabular_df"


def discover_suite_names(suites_glob: str = "*") -> List[str]:
    """
    Discover expectation suite names from the configured directory.

    Args:
        suites_glob: Glob pattern matched against suite file stems, e.g. "ORDERS*". Default "*" selects all.

    Returns:
        List[str]: A list of expectation suite names.

    Raises:
        RuntimeError: If the expectations directory is not found or the pattern matches no suites.
    """
    expectations_dir = Path(CONFIG["expectations_dir"]).expanduser()

    if not expectations_dir.exists():
        raise RuntimeError(f"Expectations directory not found: {expectations_dir}")

    suite_files = sorted(expectations_dir.glob(f"{suites_glob}.json"))

    if not suite_files:
        raise RuntimeError(
            f"No expectation suites matching '{suites_glob}' found in {expectations_dir}"
        )

    return [p.stem for p in suite_files]


_CSV_EXTENSIONS = ("csv", "txt", "psv", "tsv", "dat")


def load_dataframe(table_name: str, csv_dir: str) -> pd.DataFrame:
    """Load the data to validate for `table_name`.

    This is CSV/delimited-file based today -- the only function in this whole
    subproject that talks to a data source. To validate against a real database
    instead, this is the one place to change: replace the body below with a query
    against your database (e.g. `pd.read_sql_query(f"SELECT * FROM {table_name}", conn)`),
    keep the same signature and return type, and nothing else in this file needs to know
    the difference.
    """
    base = Path(csv_dir).expanduser()
    path = next(
        (base / f"{table_name}.{ext}" for ext in _CSV_EXTENSIONS
         if (base / f"{table_name}.{ext}").exists()),
        None,
    )
    if path is None:
        raise FileNotFoundError(
            f"No file for '{table_name}' in {csv_dir!r}; "
            f"tried: {', '.join(f'{table_name}.{e}' for e in _CSV_EXTENSIONS)}"
        )
    if table_name in _df_cache:
        logger.debug("Reusing cached DataFrame for '%s'", table_name)
        return _df_cache[table_name]
    logger.debug("Loading DataFrame from %s", path)
    df = pd.read_csv(path, sep=None, engine="python")

    # Optional: give failing rows a human-readable identity. If this table has natural
    # key columns configured (common.join_keys in the config file), build a pipe-joined
    # index from them so GX's unexpected_index_list echoes back e.g. "1042|3" instead of
    # a bare positional row number -- gx_validations_extractor can then split that same
    # string back into named columns for its output. Entirely optional; omit join_keys
    # for this table (or altogether) and GX just uses the default positional index.
    key_cols = CONFIG.get("join_keys", {}).get(table_name, [])
    if key_cols and all(col in df.columns for col in key_cols):
        df.index = df[key_cols].astype(str).agg("|".join, axis=1)

    _df_cache[table_name] = df
    return df


def run_expectation_suite(suite_name: str, df: pd.DataFrame):
    """
    Run a gx expectation suite against the provided DataFrame and return results as dict.

    Args:
        suite_name (str): The name of the expectation suite to run.
        df (pd.DataFrame): The DataFrame to validate.
    """
    logger.info(f"Running suite: {suite_name}, DataFrame shape: {df.shape}")
    GX_ROOT_DIR = Path(CONFIG["gx_root_dir"]).expanduser()
    context = gx.get_context(context_root_dir=GX_ROOT_DIR)

    # local_site is (re)created once per run in run_validation_multiple, not here: this used to
    # delete_data_docs_site/add_data_docs_site/build_data_docs on every suite, which forced a full
    # data-docs rebuild (scanning every validation result stored so far in the run) once per suite
    # instead of once per run. Each suite's checkpoint action (UpdateDataDocsAction below) already
    # keeps the site incrementally current, so nothing here needs the site freshly rebuilt.
    datasource = context.data_sources.add_or_update_pandas(name=_GX_DATASOURCE_NAME)

    try:
        datasource.delete_asset(_GX_ASSET_NAME)
    except Exception:
        pass

    asset = datasource.add_dataframe_asset(name=_GX_ASSET_NAME)

    try:
        asset.delete_batch_definition(suite_name)
    except Exception:
        pass

    batch_definition = asset.add_batch_definition_whole_dataframe(name=suite_name)
    suite = context.suites.get(name=suite_name)
    validation_definition = context.validation_definitions.add_or_update(
        gx.ValidationDefinition(data=batch_definition, suite=suite, name=suite_name)
    )
    # NOT context.validation_definitions.all(): every suite shares one dataframe asset/datasource
    # name (_GX_ASSET_NAME/_GX_DATASOURCE_NAME), which is deleted and recreated fresh per suite
    # (see delete_asset above), so only the validation_definition just added above resolves against
    # it -- every other one already in the store fails GX's own deserialization (its batch_definition
    # name doesn't exist on the freshly-recreated asset) and gets silently dropped, but not before
    # the store attempts and logs each failure. Passing only this suite's own validation_definition
    # sidesteps an "attempt every stored one, keep the one that resolves" churn that otherwise grows
    # linearly with how many suites/checkpoints/validation_definitions have ever been run and never
    # pruned -- see clear_old_gx_validations for a way to reset that store between runs.
    checkpoint = context.checkpoints.add_or_update(
        gx.Checkpoint(
            name=suite_name,
            validation_definitions=[validation_definition],
            actions=[gx_actions.UpdateDataDocsAction(name="local_site")],
            result_format={"result_format": "COMPLETE"},
        )
    )
    context.variables.save()
    checkpoint.run(batch_parameters={"dataframe": df})
    logger.info("Suite '%s' validated", suite_name)


def _table_from_meta(suite_path: Path) -> Optional[str]:
    """Return the table declared in a suite's expectation `meta.table`, or None."""
    try:
        suite_json = json.loads(suite_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for exp in suite_json.get("expectations", []):
        table = (exp.get("meta") or {}).get("table")
        if table:
            return table
    return None


def _build_suite_table_map() -> Dict[str, str]:
    """
    Build a mapping from expectation suite name (file stem) to source table name.

    The table is read from the suite's expectation `meta.table` (stamped by
    gx_generator on every expectation it builds -- see its README).

    Raises:
        RuntimeError: If a suite has no `meta.table` on any expectation.
    """
    expectations_dir = Path(CONFIG["expectations_dir"]).expanduser()
    suite_table: Dict[str, str] = {}

    for p in expectations_dir.glob("*.json"):
        table_name = _table_from_meta(p)
        if not table_name:
            raise RuntimeError(
                f"Could not determine table for suite '{p.name}': no expectation has "
                f"meta.table set. Regenerate this suite with gx_generator."
            )

        suite_table[p.stem] = table_name
        logger.debug("Resolved table '%s' for suite '%s'", table_name, p.stem)

    return suite_table


def _ensure_data_docs_site():
    """(Re)create the local_site data-docs site once per run. Each suite's checkpoint
    incrementally updates it afterward (see UpdateDataDocsAction in run_expectation_suite) --
    this just needs to exist before the first checkpoint runs."""
    GX_ROOT_DIR = Path(CONFIG["gx_root_dir"]).expanduser()
    context = gx.get_context(context_root_dir=GX_ROOT_DIR)

    try:
        context.delete_data_docs_site("local_site")
    except Exception:
        pass

    context.add_data_docs_site(
        site_name="local_site",
        site_config={
            "class_name": "SiteBuilder",
            "site_index_builder": {"class_name": "DefaultSiteIndexBuilder"},
            "store_backend": {
                "class_name": "TupleFilesystemStoreBackend",
                # Relative, so GX resolves it against context_root_dir. Writing an
                # absolute path here persists this machine's checkout into the committed
                # great_expectations.yml, which is how that file can accumulate other
                # developers' home directories if it's ever written with an absolute path.
                "base_directory": "uncommitted/data_docs/local_site/",
            },
        },
    )
    context.build_data_docs(["local_site"])


def run_validation_multiple(csv_dir: str, suites_glob: str = "*"):
    """
    Run validation for multiple expectation suites, one table load per distinct table.

    Args:
        csv_dir (str): Directory of CSV/delimited files, one per table (see load_dataframe).
        suites_glob (str): Glob pattern for suite file stems, e.g. "ORDERS*". Default "*" runs all.
    """
    suite_names = discover_suite_names(suites_glob)
    suite_table_map = _build_suite_table_map()

    _ensure_data_docs_site()

    current_table = None
    for name in suite_names:
        table_name = suite_table_map.get(name)
        if not table_name:
            logger.info("Skipping suite '%s': no table name mapping found", name)
            continue

        # _df_cache only needs to survive across one table's own batch of suites (that's
        # what makes the "load the table once, reuse for every suite targeting it" design
        # work) -- not for the life of the whole run. Evicting on table boundaries keeps
        # every prior table's DataFrame from staying permanently resident for a run with
        # many large tables.
        if table_name != current_table:
            _df_cache.clear()
            current_table = table_name

        try:
            df = load_dataframe(table_name, csv_dir)
        except Exception as exc:
            logger.error("Skipping suite '%s': failed to load DataFrame for table '%s': %s", name, table_name, exc)
            continue

        try:
            run_expectation_suite(name, df)
        except Exception as exc:
            logger.error("Skipping suite '%s': failed to run expectation suite: %s", name, exc)
            continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run gx validations against CSV/delimited data")
    parser.add_argument(
        "--csv-dir",
        default=None,
        help=(
            "Directory containing CSV/delimited files, one per table (e.g. ORDERS.csv). "
            "Also configurable via csv_data_dir in the config file."
        ),
    )
    parser.add_argument(
        "--suites",
        default=None,
        help='Glob pattern for suite names (file stems), e.g. "ORDERS*". Default: "*" (all suites).',
    )
    parser.add_argument(
        "--config-file",
        default=None,   # None, not DEFAULT_CONFIG_FILE: import already loaded the default, so
                        # leaving this None keeps a caller's CONFIG override intact.
        help=f"Unified config file for this test environment. Default: {DEFAULT_CONFIG_FILE}",
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
    common.configure(_PROGRAM, CONFIG, cli_log_level=args.log_level, suppress_gx=True)

    csv_dir = args.csv_dir or CONFIG.get("csv_data_dir") or None
    suites = args.suites or CONFIG.get("suites") or "*"
    if not csv_dir:
        parser.error(
            "--csv-dir (or csv_data_dir in the config file) is required."
        )
    run_validation_multiple(csv_dir, suites)

"""Generate Great Expectations suites from CSV specifications."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

import great_expectations as gx
import pandas as pd

ROOT = Path(__file__).resolve().parent   # repo root: every path resolves against this, never cwd
DEFAULT_CONFIG_FILE = ROOT / "configs" / "TEMPLATE.yaml"
_PROGRAM = "gx_generator"                # section read from the config file
logger = logging.getLogger(_PROGRAM)

sys.path.insert(0, str(ROOT))
import common

# Repo layout is derived, never configured: it is identical in every environment.
_LAYOUT = {
    "gx_root_dir": ROOT / "gx",
    "suites_dir": ROOT / "suites",
    "metadata_file": ROOT / "core-expectations-types-and-args.csv",
    "output_root_dir": ROOT / "output",
}
_DERIVED_FROM_OUTPUT_ROOT = {"log_dir": "logs"}

CONFIG: dict = {}                        # mutated in place by load_config(); never rebound

# Data-docs validation paths are built as:
#   <base>/data_docs/<site>/validations/<suite_name>/<run_name>/<run_time>/<datasource>-<asset>.html
# The base path is environment-dependent, run_name/run_time are fixed-length, and datasource/asset
# are short constants (see gx_consumer.py). suite_name is the one length lever left
# under our control here, so warn early if a suite name would leave too little margin under
# Windows' 260-char MAX_PATH once a reasonably long base path is added.
_ASSUMED_BASE_PATH_LEN = 100  # generous budget for <repo>/gx/uncommitted/data_docs/<site>/validations
_FIXED_PATH_TAIL_LEN = 70     # "\<run_name>\<24-char run_time>\<datasource>-<asset>.html"
_SAFE_PATH_BUDGET = 240       # leaves margin under the 260-char Windows MAX_PATH


def _warn_if_suite_name_too_long(suite_key: str) -> None:
    """Warn if suite_key risks exceeding Windows' MAX_PATH in generated data-docs output."""
    worst_case = _ASSUMED_BASE_PATH_LEN + len(suite_key) + _FIXED_PATH_TAIL_LEN
    if worst_case > _SAFE_PATH_BUDGET:
        logger.warning(
            "Suite name '%s' (%d chars) may exceed Windows' 260-char path limit in data-docs "
            "output (worst-case estimate: %d chars). Consider a shorter table or expectation "
            "name.",
            suite_key, len(suite_key), worst_case,
        )


def load_config(path=None) -> dict:
    """Populate CONFIG from `path` (default: configs/TEMPLATE.yaml). See common.load_config
    for the full precedence rule."""
    return common.load_config(
        CONFIG, _PROGRAM, _LAYOUT, ROOT, DEFAULT_CONFIG_FILE, path,
        derived_from_output_root=_DERIVED_FROM_OUTPUT_ROOT,
    )


load_config()                            # importers get the checked-in default


# ---------------------------------------------------------------------------
# Helpers (coercion and parsing)
# ---------------------------------------------------------------------------


def _is_blank(v: Any) -> bool:
    """
    Check if a value is blank (empty string, whitespace, or NaN).

    Args:
        v: The value to check.

    Returns:
        True if the value is blank, False otherwise.
    """
    return (isinstance(v, str) and not v.strip()) or pd.isna(v)


def _coerce_int(
    v: Any, field: str, rownum: int, default: Optional[int] = None
) -> Optional[int]:
    """
    Coerce a value to an integer, handling blanks and logging errors.

    Args:
        v: The value to coerce.
        field: The name of the field being coerced.
        rownum: The row number for logging purposes.
        default: The default value to return if coercion fails.

    Returns:
        The coerced integer or the default value.
    """
    try:
        return None if _is_blank(v) else int(v)
    except Exception as exc:
        logger.warning("Row %s: field '%s' must be an integer. %s", rownum, field, exc)
        return default


def _coerce_float(
    v: Any, field: str, rownum: int, default: Optional[float] = None
) -> Optional[float]:
    """
    Coerce a value to a float, handling blanks and logging errors.

    Args:
        v: The value to coerce.
        field: The name of the field being coerced.
        rownum: The row number for logging purposes.
        default: The default value to return if coercion fails.

    Returns:
        The coerced float or the default value.
    """
    try:
        return None if _is_blank(v) else float(v)
    except Exception as exc:
        logger.warning("Row %s: field '%s' must be a float. %s", rownum, field, exc)
        return default


_TRUE_STRINGS = {"true", "1", "yes", "y"}


def _coerce_bool(v: Any, default: bool = False) -> bool:
    """Coerce a CSV cell to a real bool, for flags like strict_min/strict_max/exact_match.

    A blank cell means "not set" and returns `default` -- NOT `bool(v)`: pandas represents
    a blank object-dtype cell as NaN, a non-zero (truthy!) float, and any non-empty string
    is also truthy regardless of its text -- so naive `bool(v)` can never produce False,
    silently forcing every such flag on (e.g. every ExpectColumnValuesToBeBetween row
    getting strict, exclusive bounds whether its CSV row asked for that or not).
    """
    if _is_blank(v):
        return default
    return str(v).strip().lower() in _TRUE_STRINGS


def _coerce_value(v: Any) -> Optional[Any]:
    """Coerce to int or float if possible, otherwise return the raw string."""
    if _is_blank(v):
        return None
    s = str(v).strip()
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_list(v: Any, field: str, rownum: int) -> Optional[List]:
    """
    Parse a value as a list, handling blanks and logging errors.

    Args:
        v: The value to parse.
        field: The name of the field being parsed.
        rownum: The row number for logging purposes.

    Returns:
        The parsed list or None if parsing fails.
    """
    if _is_blank(v):
        return None

    if isinstance(v, (list, tuple, set)):
        return list(v)

    if not isinstance(v, str):
        return [v]

    s = v.strip()

    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = json.loads(s)

            if isinstance(parsed, list):
                return parsed

            raise ValueError
        except Exception as exc:
            logger.warning(
                "Row %s: field '%s' contains invalid JSON list. %s", rownum, field, exc
            )
            return None

    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts if parts else None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ExpectationMetadataRow:
    expectation: str
    expectation_type: str
    arg_keys: tuple[str, ...] = tuple()


@dataclass
class ExpectationRow:
    table: str
    column: str
    expectation: str
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    value_set: Optional[list] = None
    mostly: Optional[float] = None
    column_list: Optional[list] = None
    regex: Optional[str] = None
    severity: Optional[str] = "warning"
    meta: Optional[dict[str, Any]] = None
    test_category: Optional[str] = None
    allow_relative_error: Optional[bool] = None
    column_A: Optional[str] = None
    column_B: Optional[str] = None
    column_index: Optional[int] = None
    column_set: Optional[list] = None
    exact_match: Optional[bool] = None
    json_schema: Optional[str] = None
    like_pattern: Optional[str] = None
    like_pattern_list: Optional[list] = None
    or_equal: Optional[str] = None
    other_table_name: Optional[str] = None
    partition_object: Optional[str] = None
    quantile_ranges: Optional[str] = None
    regex_list: Optional[list] = None
    strftime_format: Optional[str] = None
    strict_max: Optional[bool] = None
    strict_min: Optional[bool] = None
    sum_total: Optional[float] = None
    threshold: Optional[float] = None
    ties_ok: Optional[bool] = None
    type_: Optional[str] = None
    type_list: Optional[list] = None
    value: Optional[int] = None
    value_pairs_set: Optional[list] = None
    unexpected_rows_query: Optional[str] = None
    row_condition: Optional[str] = None
    condition_parser: Optional[str] = None


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def load_metadata_csv(path: Path) -> List[ExpectationMetadataRow]:
    """
    Load expectation metadata from a CSV file.

    Args:
        path (Path): The path to the CSV file.

    Returns:
        List[ExpectationMetadataRow]: A list of expectation metadata rows.
    """
    rows: List[ExpectationMetadataRow] = []
    df = pd.read_csv(path, dtype="object", keep_default_na=True, index_col=False)
    required = {"expectation", "expectation_type", "arg_keys"}
    missing = required - set(df.columns)

    if missing:
        logger.error(
            "Metadata CSV '%s' is missing required columns: %s", path, missing
        )
        raise ValueError(f"Missing metadata columns {missing}")

    # rownum = physical CSV row number; header=1, first data row=2
    for rownum, (_, r) in enumerate(df.iterrows(), start=2):
        expectation_val = r.get("expectation")
        expectation_type_val = r.get("expectation_type")
        arg_keys_val = r.get("arg_keys")
        # _parse_list returns Optional[list]
        keys_list = _parse_list(arg_keys_val, field="arg_keys", rownum=rownum)

        # Normalize to a tuple of strings (possibly empty)
        if keys_list is None:
            keys: tuple[str, ...] = tuple()
        else:
            keys = tuple(str(k).strip() for k in keys_list)

        rows.append(
            ExpectationMetadataRow(
                expectation=(
                    str(expectation_val).strip() if expectation_val is not None else ""
                ),
                expectation_type=(
                    str(expectation_type_val).strip()
                    if expectation_type_val is not None
                    else ""
                ),
                arg_keys=keys,
            )
        )

    return rows


def load_spec_csv(path: Path) -> List[ExpectationRow]:
    """
    Load expectation specifications from a CSV file.

    Args:
        path (Path): The path to the CSV file.

    Returns:
        List[ExpectationRow]: A list of expectation rows.
    """
    rows: List[ExpectationRow] = []
    df = pd.read_csv(path, dtype="object", keep_default_na=True, index_col=False)
    required = {"table", "column", "expectation"}
    missing = required - set(df.columns)

    if missing:
        logger.error("Spec CSV '%s' is missing required columns: %s", path, missing)
        raise ValueError(f"Missing required columns {missing}")

    # rownum reflects the physical CSV line number: header = 1, first data row = 2
    for rownum, (_, r) in enumerate(df.iterrows(), start=2):
        table_val = r.get("table")
        column_val = r.get("column")
        expectation_val = r.get("expectation")
        min_value_val = r.get("min_value")
        max_value_val = r.get("max_value")
        mostly_val = r.get("mostly")
        value_set_val = r.get("value_set")
        column_list_val = r.get("column_list")
        regex_val = r.get("regex")
        severity_val = r.get("severity")
        meta_val = r.get("meta")
        test_category_val = r.get("test_category")
        allow_relative_error_val = r.get("allow_relative_error")
        column_A_val = r.get("column_A")
        column_B_val = r.get("column_B")
        column_index_val = r.get("column_index")
        column_set_val = r.get("column_set")
        exact_match_val = r.get("exact_match")
        json_schema_val = r.get("json_schema")
        like_pattern_val = r.get("like_pattern")
        like_pattern_list_val = r.get("like_pattern_list")
        or_equal_val = r.get("or_equal")
        other_table_name_val = r.get("other_table_name")
        partition_object_val = r.get("partition_object")
        quantile_ranges_val = r.get("quantile_ranges")
        regex_list_val = r.get("regex_list")
        strftime_format_val = r.get("strftime_format")
        strict_max_val = r.get("strict_max")
        strict_min_val = r.get("strict_min")
        sum_total_val = r.get("sum_total")
        threshold_val = r.get("threshold")
        ties_ok_val = r.get("ties_ok")
        type__val = r.get("type_")
        type_list_val = r.get("type_list")
        value_val = r.get("value")
        value_pairs_set_val = r.get("value_pairs_set")
        unexpected_rows_query_val = r.get("unexpected_rows_query")
        row_condition_val = r.get("row_condition")
        condition_parser_val = r.get("condition_parser")

        rows.append(
            ExpectationRow(
                table=str(table_val).strip() if not _is_blank(table_val) else "",
                column=str(column_val).strip() if not _is_blank(column_val) else "",
                expectation=(
                    str(expectation_val).strip()
                    if not _is_blank(expectation_val)
                    else ""
                ),
                min_value=_coerce_value(min_value_val),
                max_value=_coerce_value(max_value_val),
                mostly=_coerce_float(mostly_val, "mostly", rownum, default=1.0),
                value_set=_parse_list(value_set_val, "value_set", rownum),
                column_list=_parse_list(column_list_val, "column_list", rownum),
                regex=None if _is_blank(regex_val) else str(regex_val).strip(),
                severity=str(severity_val or "warning").lower(),
                meta=None if _is_blank(meta_val) else json.loads(str(meta_val)),
                test_category=(
                    None
                    if _is_blank(test_category_val)
                    else str(test_category_val).strip().upper()
                ),
                allow_relative_error=_coerce_bool(allow_relative_error_val),
                column_A=None if _is_blank(column_A_val) else str(column_A_val).strip(),
                column_B=None if _is_blank(column_B_val) else str(column_B_val).strip(),
                column_index=_coerce_int(column_index_val, "column_index", rownum),
                column_set=_parse_list(column_set_val, "column_set", rownum),
                exact_match=_coerce_bool(exact_match_val),
                json_schema=(
                    None if _is_blank(json_schema_val) else str(json_schema_val).strip()
                ),
                like_pattern=(
                    None
                    if _is_blank(like_pattern_val)
                    else str(like_pattern_val).strip()
                ),
                like_pattern_list=_parse_list(
                    like_pattern_list_val, "like_pattern_list", rownum
                ),
                or_equal=None if _is_blank(or_equal_val) else str(or_equal_val).strip(),
                other_table_name=(
                    None
                    if _is_blank(other_table_name_val)
                    else str(other_table_name_val).strip()
                ),
                partition_object=(
                    None
                    if _is_blank(partition_object_val)
                    else str(partition_object_val).strip()
                ),
                quantile_ranges=(
                    None
                    if _is_blank(quantile_ranges_val)
                    else str(quantile_ranges_val).strip()
                ),
                regex_list=_parse_list(regex_list_val, "regex_list", rownum),
                strftime_format=(
                    None
                    if _is_blank(strftime_format_val)
                    else str(strftime_format_val).strip()
                ),
                strict_max=_coerce_bool(strict_max_val),
                strict_min=_coerce_bool(strict_min_val),
                sum_total=_coerce_float(
                    sum_total_val, "sum_total", rownum, default=0.0
                ),
                threshold=_coerce_float(
                    threshold_val, "threshold", rownum, default=0.0
                ),
                ties_ok=_coerce_bool(ties_ok_val),
                type_=None if _is_blank(type__val) else str(type__val).strip(),
                type_list=_parse_list(type_list_val, "type_list", rownum),
                value=_coerce_int(value_val, "value", rownum),
                value_pairs_set=_parse_list(
                    value_pairs_set_val, "value_pairs_set", rownum
                ),
                unexpected_rows_query=(
                    None
                    if _is_blank(unexpected_rows_query_val)
                    else str(unexpected_rows_query_val).strip()
                ),
                row_condition=(
                    None if _is_blank(row_condition_val) else str(row_condition_val).strip()
                ),
                condition_parser=(
                    None
                    if _is_blank(condition_parser_val)
                    else str(condition_parser_val).strip()
                ),
            )
        )

    return rows


def build_expectation_suite(rows, suite_name, metadata):
    """
    Build a Great Expectations suite from expectation rows and metadata.

    Args:
        rows: A list of ExpectationRow objects containing expectation specifications.
        suite_name: The name of the expectation suite to create.
        metadata: A dictionary mapping expectation names to ExpectationMetadataRow objects.
    """
    context = gx.get_context(context_root_dir=Path(CONFIG["gx_root_dir"]).expanduser())
    suites_by_table = {}

    for row in rows:
        table = row.table.strip()
        expectation = row.expectation.strip()

        meta_row = metadata.get(expectation)
        if not meta_row:
            logger.warning(f"Unknown expectation {expectation}")
            continue

        kwargs = {}
        missing = []

        for key in meta_row.arg_keys:
            if not hasattr(row, key):
                missing.append(key)
                continue
            value = getattr(row, key)
            if value is None:
                missing.append(key)
                continue
            kwargs[key] = value

        if missing:
            logger.warning(f"Missing args {missing} for {expectation}")

        # row_condition/condition_parser scope an expectation to a subset of rows (e.g. one
        # region's row in a rolled-up aggregate frame) -- supported by every core
        # expectation type via gx's domain_keys, but deliberately not listed in any
        # arg_keys row: adding them there would make the "Missing args" warning above fire
        # on every existing suite that doesn't set them.
        if row.row_condition:
            kwargs["row_condition"] = row.row_condition
        if row.condition_parser:
            kwargs["condition_parser"] = row.condition_parser

        if row.severity is not None:
            kwargs["severity"] = row.severity
        kwargs["result_format"] = "COMPLETE"
        kwargs["catch_exceptions"] = True

        try:
            cls = getattr(gx.expectations, expectation)
            ge_exp = cls(**kwargs)
        except Exception as exc:
            logger.warning(f"Cannot instantiate {expectation}: {exc}")
            continue

        # GX Pydantic models ignore meta passed as a constructor kwarg; set it post-construction.
        if row.meta is not None:
            ge_exp.meta = row.meta

        # Table-level expectations (e.g. ExpectTableRowCountToBeBetween) don't take "column"
        # as a kwarg, so the CSV's column would otherwise be lost before it reaches the
        # validation result JSON; stash it in meta so the extractor can still recover it.
        if row.column and "column" not in meta_row.arg_keys:
            if ge_exp.meta is None:
                ge_exp.meta = {}
            ge_exp.meta["column"] = row.column

        # test_category is a business classification independent of how the expectation was
        # authored (hand-written vs. generated, one-off vs. standing rule) -- default to "DQ"
        # (data quality) so every expectation gets an explicit value even when the CSV
        # doesn't set one. Use whatever categories make sense for your own project.
        if ge_exp.meta is None:
            ge_exp.meta = {}
        ge_exp.meta["test_category"] = row.test_category or "DQ"

        # Table-level expectations don't take "column" as a kwarg, so meta.table lets the
        # consumer/extractor recover which table this expectation targets even without one.
        ge_exp.meta["table"] = table

        # suite_name (the CSV stem) already starts with the table name for auto-generated
        # per-table CSVs (e.g. "ORDERS_ExpectColumnValuesToBeInSet"); only append it for
        # hand-authored multi-table CSVs where it doesn't.
        suite_key = suite_name if suite_name.startswith(table) else f"{suite_name}_{table}"
        suite = suites_by_table.get(suite_key)

        if suite is None:
            _warn_if_suite_name_too_long(suite_key)
            try:
                suite = context.suites.get(suite_key)
            except Exception:
                suite = gx.ExpectationSuite(suite_key)
            suites_by_table[suite_key] = suite

        suite.add_expectation(ge_exp)

    for key, suite in suites_by_table.items():
        context.suites.add_or_update(suite=suite)

    try:
        context.variables.save()
    except Exception as exc:
        logger.warning(
            "Exception while saving suites. If using a filesystem store, this may be due to concurrent writes. %s",
            exc,
        )
        pass


def generate_all():
    """
    Generate Great Expectations suites for all CSV specifications in the configured directory.
    """
    metadata_file = Path(CONFIG["metadata_file"])
    metadata_rows = load_metadata_csv(metadata_file)
    metadata = {m.expectation: m for m in metadata_rows}
    SUITES_DIR = Path(CONFIG["suites_dir"])
    csv_files = sorted(SUITES_DIR.glob("*.csv"))

    if not csv_files:
        logger.warning(f"No CSV files in {SUITES_DIR}")
        return

    for csv_path in csv_files:
        suite_name = csv_path.stem
        rows = load_spec_csv(csv_path)
        logger.info(f"Generating suite '{suite_name}' from {csv_path.name}")
        build_expectation_suite(rows, suite_name, metadata)

    logger.info("All suites generated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile suites/*.csv specs into GX JSON suites")
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

    generate_all()

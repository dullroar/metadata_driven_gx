"""Row-shaping logic shared by every extractor output format.

Kept as its own module so a second output target (a database load, a different file
format, ...) can reuse the same row-shaping instead of duplicating (and inevitably
drifting from) it.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Kwargs that are constant/never useful in expectation_kwargs (everything else -- min_value,
# max_value, value_set, mostly, column_list, ... -- is exactly the "why did this fail" context
# that would otherwise only be visible by opening the suite JSON directly).
_KWARGS_DROP_KEYS = ("batch_id", "result_format")

_tables_without_join_keys_warned: set = set()

_NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?$")

DETAIL_ROW_KEYS = (
    "source", "table", "expectation_type", "column", "row_key", "key_columns",
    "bad_value", "bad_value_a", "bad_value_b", "exception_message", "observed_value",
    "unexpected_count", "exploded_count", "has_sample_value", "run_date",
)


def latest_json_paths(validations_dir: Path):
    """Yield (suite_name, json_path) pairs from only the most recent run directory of each suite.

    The suite name comes from suite_dir, not the JSON file's own stem: GX names every
    validation-result file after the constant Data Source + Data Asset id, so the file
    name alone can't tell suites apart.
    """
    for suite_dir in sorted(validations_dir.iterdir()):
        run_parent = suite_dir / "__none__"
        if not run_parent.is_dir():
            continue
        run_dirs = sorted(d for d in run_parent.iterdir() if d.is_dir())
        if run_dirs:
            for json_path in run_dirs[-1].glob("*.json"):
                yield suite_dir.name, json_path


def get_col(kwargs: dict) -> str:
    """Column name for an expectation: a single column, a comma-joined column_list
    (multi-column expectations like expect_compound_columns_to_be_unique), or a
    "colA / colB" pair for column_A/column_B expectations."""
    column_list = kwargs.get("column_list")
    if column_list:
        return ", ".join(str(c) for c in column_list)
    return kwargs.get("column") or " / ".join(
        str(kwargs[k]) for k in ("column_A", "column_B") if kwargs.get(k)
    )


def extract_exception(exc_info: dict) -> str:
    """Extracts exception messages, handling nested dynamic keys from GX."""
    if not exc_info:
        return ""
    if exc_info.get("exception_message"):
        return exc_info["exception_message"]
    return next((v.get("exception_message", "") for v in exc_info.values() if isinstance(v, dict)), "")


def key_columns_to_where(key_columns: dict) -> str:
    """Render a {col: value} dict as a SQL WHERE-clause snippet, e.g. `COL_A = 1 AND COL_B = 'X'`,
    meant to be pasted straight into a query against whichever database/table this
    validation run's data actually came from -- the extractor doesn't know that connection
    or even which environment it'll be queried from, since that's run-time config, not
    available at extraction time -- so this can't build a full SELECT, only the WHERE half.

    A value is left unquoted only if it's purely numeric (int/float, or a string that looks
    like one); everything else -- codes, IDs with leading zeros, dates -- is single-quoted,
    with embedded quotes doubled per SQL's escaping convention. None becomes `IS NULL`.
    """
    clauses = []
    for col, value in key_columns.items():
        if value is None:
            clauses.append(f"{col} IS NULL")
        elif isinstance(value, (int, float)) or _NUMERIC_RE.match(str(value)):
            clauses.append(f"{col} = {value}")
        else:
            escaped = str(value).replace("'", "''")
            clauses.append(f"{col} = '{escaped}'")
    return " AND ".join(clauses)


def table_for_result(r: dict):
    """The table this result's expectation targets, from meta.table (stamped by gx_generator)."""
    return (r.get("expectation_config", {}).get("meta") or {}).get("table")


def _raised_exception(exc_info: dict) -> bool:
    """True if `exc_info` (top-level or nested under GX's dynamic per-metric keys -- see
    extract_exception()) flags raised_exception=True anywhere."""
    if not exc_info:
        return False
    if exc_info.get("raised_exception"):
        return True
    return any(
        isinstance(v, dict) and v.get("raised_exception") for v in exc_info.values()
    )


def get_result_type(r: dict) -> str:
    """'error' if the expectation raised an exception instead of failing cleanly, else
    'success'/'failure' from GX's own success flag.

    GX conflates both outcomes into success=False -- an all-null stat row can mean either
    "this is a passing aggregate type that never reports these stats" or "this errored"
    (e.g. a missing column), and only exception_info distinguishes them.
    """
    if _raised_exception(r.get("exception_info") or {}):
        return "error"
    return "success" if r.get("success", False) else "failure"


def get_rule_kind(kwargs: dict) -> str:
    """Coarse category of what shape of check this is, so callers don't have to infer it
    from which of column/column_A+B/bad_value_a+b happens to be populated."""
    if kwargs.get("column_list"):
        return "compound_key"
    if kwargs.get("column_A") or kwargs.get("column_B"):
        return "pair_comparison"
    if kwargs.get("column"):
        return "single_column"
    return "aggregate"


def build_summary_row(r: dict, source: str, table, run_date, environment_name: str = None) -> dict:
    """One summary row per validation result: pass/fail plus whatever stats GX returned.

    element_count/missing_count/unexpected_count are null for aggregate expectation types
    (row-count, unique-count, sum) because GX itself never returns them for those types --
    that's not a bug to patch by inventing numbers. expectation_kwargs shows the configured
    bound/set instead, which is the actual missing context for "why did this fail".

    environment_name identifies which config file's run produced this row -- see
    configs/TEMPLATE.yaml's environment_name comment. Defaults to None and is OMITTED from
    the returned dict when not given, so a caller with a fixed downstream schema that has
    no such column can still call this function unchanged.
    """
    config = r.get("expectation_config", {})
    kwargs = config.get("kwargs", {})
    result = r.get("result", {})
    trimmed_kwargs = {k: v for k, v in kwargs.items() if k not in _KWARGS_DROP_KEYS}
    row = {
        "source": source,
        "expectation_type": config.get("type"),
        "column": get_col(kwargs) or (config.get("meta") or {}).get("column"),
        "table": table,
        "severity": config.get("severity"),
        "test_category": (config.get("meta") or {}).get("test_category") or "DQ",
        "success": r.get("success", False),
        "result_type": get_result_type(r),
        "rule_kind": get_rule_kind(kwargs),
        "element_count": result.get("element_count"),
        "missing_count": result.get("missing_count"),
        "missing_percent": result.get("missing_percent"),
        "unexpected_count": result.get("unexpected_count"),
        "unexpected_percent": result.get("unexpected_percent"),
        "unexpected_percent_total": result.get("unexpected_percent_total"),
        "observed_value": result.get("observed_value"),
        "expectation_kwargs": json.dumps(trimmed_kwargs) if trimmed_kwargs else None,
        "run_date": run_date,
    }
    if environment_name is not None:
        row["environment_name"] = environment_name
    return row


def _split_row_key(row_key: str, key_cols: list, table):
    """Split a pipe-joined index string into {key_col: value}, or None if the count mismatches.

    A mismatch (join_keys configured, but the index string doesn't split into that many
    parts) would otherwise silently mislabel values under the wrong column headers in an
    audit artifact, so it falls back to no named columns rather than guessing.
    """
    parts = row_key.split("|") if row_key else []
    if len(parts) != len(key_cols):
        logger.debug(
            "row_key %r splits into %d parts but table '%s' has %d configured join_keys; "
            "falling back to raw row_key for this suite.", row_key, len(parts), table, len(key_cols),
        )
        return None
    return dict(zip(key_cols, parts))


def build_detail_rows(r: dict, source: str, table, run_date, join_keys: dict, cap: int = 50,
                       environment_name: str = None):
    """Yield one dict per offending row (up to `cap`), or a single fallback row.

    environment_name: see build_summary_row()'s docstring -- same purpose and same
    None-means-omit-the-key contract.

    Every row has the same keys (DETAIL_ROW_KEYS) regardless of branch, so callers can write
    a suite's rows without a union-of-fieldnames dance. `key_columns` is a dict -- named
    join-key columns split from the DataFrame index GX echoes back as `unexpected_index_list`
    (see gx_consumer.load_dataframe's optional join_keys support), or (for
    expect_compound_columns_to_be_unique, whose unexpected entries are themselves a dict of
    the violating columns -- typically a different column set than the table's join_keys)
    the violation's own columns -- or None when it can't be determined. Callers that want
    literal named columns (this module's CSV caller) can flatten it themselves; callers that
    need a fixed schema can render it as a WHERE-clause snippet via key_columns_to_where().

    GX's own `unexpected_list` (the actual offending value/columns) is silently capped at
    200 entries internally, regardless of result_format/`cap` -- but `unexpected_index_list`
    (which rows failed) is not. So rows beyond the 200th still get a real `key_columns`/
    `row_key` identity here (up to `cap`), just with `bad_value*`/violation columns null;
    `has_sample_value` says which is which.
    """
    config = r.get("expectation_config", {})
    kwargs = config.get("kwargs", {})
    expectation_type = config.get("type")
    column = get_col(kwargs) or (config.get("meta") or {}).get("column")
    result = r.get("result", {})
    index_list = result.get("unexpected_index_list")
    unexpected_list = result.get("unexpected_list")

    if not index_list:
        # Fallback: a table-level aggregate expectation (row-count/unique-count/sum/...), or
        # an errored/exception expectation -- neither has a per-row unexpected_index_list.
        fallback_row = {
            "source": source,
            "table": table,
            "expectation_type": expectation_type,
            "column": column,
            "row_key": None,
            "key_columns": None,
            "bad_value": None,
            "bad_value_a": None,
            "bad_value_b": None,
            "exception_message": extract_exception(r.get("exception_info", {})),
            "observed_value": result.get("observed_value"),
            "unexpected_count": None,
            "exploded_count": None,
            "has_sample_value": False,
            "run_date": run_date,
        }
        if environment_name is not None:
            fallback_row["environment_name"] = environment_name
        yield fallback_row
        return

    total = result.get("unexpected_count") or len(index_list)
    key_cols = join_keys.get(table) if table else None
    if table and not key_cols and table not in _tables_without_join_keys_warned:
        logger.debug("No join_keys configured for table '%s'; emitting raw row_key only.", table)
        _tables_without_join_keys_warned.add(table)

    # unexpected_index_list (every failing row's identity) is never truncated by GX, but
    # unexpected_list (the actual offending value/columns) is capped at 200 internally by
    # GX itself (independent of result_format/details_cap) -- so past index n_sampled we
    # still know *which* row failed, just not what its value was.
    n_sampled = len(unexpected_list) if unexpected_list else 0

    rows = []
    for row_key in index_list:
        if len(rows) >= cap:
            break
        i = len(rows)
        entry = unexpected_list[i] if i < n_sampled else None

        if isinstance(entry, dict):
            # Compound-uniqueness: the entry already names its own offending columns --
            # don't also split row_key, which is a different column set (the table's join_keys).
            key_columns = entry
            bad_value = bad_value_a = bad_value_b = None
        else:
            key_columns = _split_row_key(row_key, key_cols, table) if key_cols else None
            if isinstance(entry, (list, tuple)) and len(entry) == 2:
                bad_value, bad_value_a, bad_value_b = None, entry[0], entry[1]
            else:
                bad_value, bad_value_a, bad_value_b = entry, None, None

        rows.append({
            "source": source,
            "table": table,
            "expectation_type": expectation_type,
            "column": column,
            "row_key": row_key,
            "key_columns": key_columns,
            "bad_value": bad_value,
            "bad_value_a": bad_value_a,
            "bad_value_b": bad_value_b,
            "exception_message": None,
            "observed_value": None,
            "unexpected_count": total,
            "exploded_count": None,  # patched below once the true count is known
            "has_sample_value": entry is not None,
            "run_date": run_date,
        })

    exploded_count = len(rows)
    for row in rows:
        row["exploded_count"] = exploded_count
        if environment_name is not None:
            row["environment_name"] = environment_name
        yield row

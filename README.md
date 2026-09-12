# metadata-driven-gx

A demonstration of how to build a **metadata-driven** data-quality testing stack on top
of [Great Expectations](https://docs.greatexpectations.io/docs/core/introduction/) (GX):
expectations described as rows in a CSV, compiled into GX suites, run against your data,
and flattened back into CSVs a human (or a dashboard) can actually read.

This is the extracted, database-agnostic core of a much larger internal tool built for
one bank's mainframe database -- everything specific to that database, that bank, or its
infrastructure has been removed. What's left is the pattern and the hard-won lessons,
demonstrated against plain CSV files, ready to point at your own data source.

By Jim Lehmer and Contributors.

## Why metadata-driven?

Hand-writing GX suites in Python scales fine for a handful of tables. It stops scaling
once you have dozens of tables and hundreds of column-level rules: every rule looks
almost identical to the last, and the interesting part -- *which* columns need *which*
checks, and why -- gets buried in boilerplate. Describing each expectation as one CSV row
instead keeps the interesting part front and center, lets it live in source control with
a meaningful diff and commit history, and lets a non-Python analyst own it directly
without touching a line of code.

## Architecture

```
suites/*.csv  --[gx_generator.py]-->  gx/expectations/*.json (GX suites)
                                              |
                                              v
your CSV data  --[gx_consumer.py]-->  gx/uncommitted/{validations,data_docs}/
                                              |
                                              v
                       [gx_validations_extractor.py]  -->  output/<suite>/*.csv
```

Everything is a plain Python script in the repo root -- there's no package structure to
navigate, because there's no real module boundary to express: each stage is a single
file that reads its own config section and talks to the others only through files
(CSVs in, `gx/` in the middle, CSVs out). That's what lets you swap `gx_consumer.py`'s
CSV reader for a database query, or drop in a different suite generator, without
anything else in the pipeline noticing.

| File | Role |
|---|---|
| `gx_generator.py` | Compiles `suites/*.csv` into GX expectation suite JSON under `gx/expectations/`. |
| `gx_consumer.py` | Runs those suites against your data (CSV out of the box -- see below for pointing it at a database instead) and builds GX's `data_docs` static site. |
| `gx_validations_extractor.py` / `extractor_common.py` | Flattens the latest validation run of every suite into tabular summary/detail CSVs. |
| `clear_old_gx_validations.py` | Resets the GX store between runs (full reset, or pruning old run history). |
| `end_to_end.py` | Runs the three stages above in order, in one command. |
| `common.py` | Shared config-loading and logging bootstrap every script imports. |
| `edit_suite.py` | Generates (and launches) a disposable notebook for interactively editing one suite -- see below. |

Every script is runnable on its own (`python gx_generator.py --config-file ...`);
`end_to_end.py` is a convenience, not a requirement.

## The CSV metadata format (`suites/*.csv`)

One row per expectation. Column names in the CSV match the constructor argument names of
the corresponding GX expectation class, so an analyst who knows GX's own docs already
knows the column names. Only `table`, `column`, and `expectation` are required; every
other column is read only if the target expectation type actually uses it (see
`core-expectations-types-and-args.csv`, which maps each supported `Expectation...` class
name to its GX snake_case type and the argument keys it accepts).

```csv
table,column,expectation,min_value,max_value,mostly,severity,meta
ORDERS,ORDER_TOTAL,ExpectColumnValuesToBeBetween,0,100000,0.99,warning,"{""notes"": ""sanity bound""}"
```

A few conventions worth knowing:

- `meta` is a JSON object merged onto the expectation verbatim -- put anything you want
  to see later in the extractor's output there (an owner, a ticket link, a note to a
  future reader).
- `test_category` (default `"DQ"`) is a free-form classification, not read by GX itself
  -- use it however makes sense for your project (e.g. `"DQ"` for a standing rule vs.
  `"SMOKE"` for a one-off migration check).
- `row_condition`/`condition_parser` scope an expectation to a subset of rows (any GX
  core expectation type supports this via `domain_keys`, even though it isn't listed in
  `arg_keys` for any type in `core-expectations-types-and-args.csv`).
- `gx_generator.py` stamps `meta.table` onto every expectation automatically (from the
  CSV's own `table` column) -- `gx_consumer.py` and `gx_validations_extractor.py` both
  rely on this to recover which table an expectation targets, since table-level
  expectations (e.g. `ExpectTableRowCountToBeBetween`) have no `column` kwarg of their own.
- A suite's file name doesn't have to match its table name, only its content: the
  generator groups rows by their own `table` column, not by the CSV's file name (a
  hand-authored, multi-table CSV works fine).

`generator-tests/` has two small fixture CSVs -- one that should generate cleanly, one
where every row is intentionally invalid -- see `generator-tests/TESTS.md` for exactly
what each row proves, useful for confirming your Python environment and GX version work
before pointing anything at real data.

## Interactively editing a suite: `edit_suite.py`

Great Expectations' CLI used to scaffold a disposable Jupyter notebook for editing one
suite at a time (`great_expectations suite edit <SUITE>`) -- profile the suite against
real data, tweak expectations, re-run, save. GX 1.x removed the CLI entirely, but Data
Docs' own "How to Edit This Suite" button still quotes that dead command (it's baked
into a template inside the `great_expectations` package that nobody updated). This
repo's `edit_suite.py` reproduces the same disposable-notebook workflow on GX's current
fluent (`Batch.validate`) API instead of the removed one:

```bash
python edit_suite.py CUSTOMERS --config-file configs/demo_weather.yaml
```

This writes `play/edit_<SUITE>.ipynb` (`play/` is gitignored -- the notebook is genuinely
disposable) and opens it in Jupyter; pass `--no-launch` to only generate the file. The
notebook loads the named suite and its real data through this repo's own conventions
(the same `load_dataframe()` `gx_consumer.py` uses), runs the suite as-is so you can see
what's currently failing, lets you build and preview a candidate expectation against the
data with zero side effects, and -- in one clearly marked cell -- saves it into
`expectations/<SUITE>.json` for real, only once you're happy with the preview.

Needs `jupyter`/`ipykernel` in your `.venv` -- deliberately not in `requirements.txt`,
since it's a dev tool for editing suites, not a pipeline runtime dependency:

```bash
.venv/bin/pip install jupyter ipykernel
```

See `edit_suite.py`'s own module docstring for two GX 1.12.3 quirks its generated
notebook works around: a fluent datasource registration that GX's own `.delete()`
doesn't actually persist the removal of, and a second `get_context()` call in the same
process corrupting the first context's suites store.

## The one-seam design

Everything in this repo except one function is agnostic to where your data actually
lives. **`gx_consumer.py`'s `load_dataframe()` is the single seam:** read CSVs today,
swap in a database query tomorrow (e.g. `pd.read_sql_query(f"SELECT * FROM {table_name}",
conn)`), keep the same signature and return type, and nothing else -- suite discovery,
checkpoint execution, data-docs rendering, the extractor -- has to change.

## Readable failing rows: `join_keys`

By default GX identifies a failing row by its plain positional index (0, 1, 2, ...) --
not very useful once you're looking at real-sized data. Set `common.join_keys` in your
config file to a `{table: [key_col, ...]}` mapping of natural key columns, and
`gx_consumer.py` builds a pipe-joined index from them instead (e.g. `"1042|3"`);
`gx_validations_extractor.py` then splits that same string back into named columns in its
own output. Entirely optional; omit it and GX just uses the default positional index.

## Configuration

One YAML file per environment/project, in `configs/`. Never commit real secrets to
one -- if your own data source needs credentials, read them from an environment variable
or a secrets manager inside your `load_dataframe()` replacement, not from this file.

```
common:            # values read by more than one program
  gx_root_dir: "gx"
  output_root_dir: "output"
  environment_name: "my-project"
  join_keys: {}     # optional: table -> natural key columns, for readable failing rows

<program>:          # one section per script, wins over common:
  ...
```

Precedence, lowest to highest: derived repo layout &rarr; `common:` &rarr; `<program>:`
&rarr; CLI flag. Copy `configs/TEMPLATE.yaml` to start a new one -- see
[GETTING_STARTED.md](GETTING_STARTED.md).

## Repo layout

```
common.py                        shared config/logging bootstrap
gx_generator.py                  suites/*.csv -> gx/expectations/*.json
gx_consumer.py                   gx/expectations/*.json + your data -> validation results
gx_validations_extractor.py      validation results -> output/*.csv
extractor_common.py              row-shaping logic shared by the extractor
clear_old_gx_validations.py      GX store maintenance
end_to_end.py                    runs the above in order
edit_suite.py                    generates a disposable notebook for interactively editing one suite
core-expectations-types-and-args.csv   GX expectation vocabulary the generator understands
generator-tests/                 fixture CSVs proving the generator works
setup_venv.ps1                   creates/refreshes this repo's .venv
requirements.txt                 the repo's one set of Python dependencies

configs/TEMPLATE.yaml             copy this to start a new environment/project
suites/                          your expectation metadata CSVs (empty here -- add your own)
gx/                              the GX context: committed suite JSON + config; uncommitted run history
output/                          extractor CSVs + log files (gitignored)
play/                            edit_suite.py's generated notebooks (gitignored -- scratch only)

environments/demo_weather/       a fully worked, committed example -- see GETTING_STARTED.md
```

## Re-running the demo produces a noisy diff (and that's fine)

`environments/demo_weather/` ships with GX's own output already generated and committed,
so you can look at a finished result without running anything. If you *do* re-run
`python end_to_end.py --config-file configs/demo_weather.yaml` (or any single stage) against
that same environment, `git diff` will show changes even though nothing about the demo
itself changed:

- Every GX suite/checkpoint/validation-definition JSON under `gx/` carries an `"id"` field
  -- a GUID GX assigns fresh each time that object is (re)created.
- Every row the extractor writes to `output/*/*.csv` carries a `run_date` column -- the
  wall-clock time the validation actually ran.

Neither is meaningful content; they're just GX's own bookkeeping and the current
timestamp, not something an analyst or reviewer needs to see in a diff. See
[CLAUDE.md](CLAUDE.md)/[AGENTS.md](AGENTS.md) for what an AI coding agent working in this
repo should do when it runs into this.

## Hard lessons, kept on purpose

A few things this repo's design encodes because they were learned the expensive way in
production, not because they were obvious in advance:

- **Object-dtype numeric columns silently break `_between` comparisons.** GX only takes
  its fast, vectorized comparison path when a column's pandas dtype is `int`/`float`;
  otherwise a value like `Decimal('0.065')` compared against a float boundary can fail an
  exact bound it should have passed, because of ordinary floating-point representation
  error. If your own `load_dataframe()` replacement pulls numeric columns back as
  `decimal.Decimal` or another non-native-numeric Python object (several ODBC drivers do
  this for `DECIMAL`/`NUMERIC` columns), coerce that column to `float64` (e.g.
  `pd.to_numeric(df[col], errors="coerce")`) before validating it.
- **Rebuild `data_docs` incrementally, not once per suite.** Rebuilding the whole static
  site after every single suite scales with the *total* number of validations ever
  stored, not the size of the current run -- GX's per-checkpoint
  `UpdateDataDocsAction` already keeps the site current incrementally; a full rebuild is
  only needed once, before the first checkpoint of a run.
- **Don't let a GX store accumulate validation_definitions forever.** Every suite in a
  run that shares one dataframe asset/datasource name (recreated fresh per suite) makes
  GX attempt to deserialize *every* validation_definition ever stored against that asset,
  not just the one this run just added -- discard the ones you don't need, or the churn
  grows without bound. `clear_old_gx_validations.py` exists for this; see the comment on
  `run_expectation_suite()` in `gx_consumer.py`.
- **Windows' 260-character `MAX_PATH` is a real constraint on GX's own output paths.**
  Data-docs validation result paths embed the suite name; `gx_generator.py` warns early
  if a suite name risks tipping a deep base path over the limit, rather than failing
  obscurely deep into a run.
- **A failing row's identity is worth more than its positional index.** See `join_keys`
  above -- a failure reads as `ORDER_ID=1042` rather than a row number nobody can map
  back to anything.
- **`success: false` means two different things and GX doesn't tell you which.** A
  failing expectation and one that raised an exception (e.g. against a missing column)
  both come back with `success: false`; only `exception_info` tells them apart.
  `extractor_common.py`'s `result_type` (`success`/`failure`/`error`) does that
  disambiguation once so nobody has to read exception text by hand to find out whether a
  suite is broken versus the data actually being bad.
- **A blank CSV cell is not the same as `False`.** pandas represents a blank
  object-dtype cell as `NaN` -- a non-zero, and therefore *truthy*, float -- and any
  non-empty string is also truthy regardless of its text. Coercing a boolean flag
  (`strict_min`, `strict_max`, `exact_match`, ...) with plain `bool(cell)` means it can
  only ever come out `True`; `gx_generator.py`'s `_coerce_bool()` treats a blank cell as
  "not set" (a real default, usually `False`) and only text like `true`/`1`/`yes` as
  actually `True`.
- **pandas silently nulls out sentinel-looking strings by default.** `pd.read_csv`
  treats `N/A`, `NA`, `NULL`, `None`, `nan`, and a few others as missing values
  out of the box, converting them to a real null before GX (or your own code) ever sees
  the column. A malformed-value test using one of those strings on purpose actually
  becomes a null test -- not what it looks like on the page. See
  `environments/demo_weather/generate_data.py` for where this bit the demo data itself.

## Release notes

See [RELEASE_NOTES.md](RELEASE_NOTES.md) for what changed in each version.

## License

MIT -- see [LICENSE](LICENSE).

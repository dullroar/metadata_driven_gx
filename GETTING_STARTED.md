# Getting Started

## 1. Prerequisites

Python 3.10+ on your PATH. This repo is a flat set of Python scripts and notebooks
sharing one `requirements.txt` -- there's no package structure to install, just one
`.venv`.

## 2. Create the virtual environment

On Windows, from the repo root:

```powershell
.\setup_venv.ps1
```

On another OS, do the equivalent by hand:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Activate it, then run everything below from the repo root (paths in
`configs/*.yaml` resolve either against the repo root or your current directory --
running from the repo root is the simplest way to keep both consistent).

## 3. See it work first: the `demo_weather` example

For the interactive, notebook-oriented version of this walkthrough, see
[`dbx_notebooks/README.md`](dbx_notebooks/README.md) and
[`dbx_notebooks/end_to_end.ipynb`](dbx_notebooks/end_to_end.ipynb). The notebook and CLI
call the same pipeline code; choose whichever presentation suits your workflow.

Before building your own project, look at the one that's already here.
`environments/demo_weather/` is a fully worked, **committed** example: a fictional home
weather station company's CRM + sensor-log data (6 tables, 50 expectations, 12 different
GX expectation types), with real problems planted in the data and already-generated
results committed alongside it. Read `environments/demo_weather/README.md` for the full
map of what was planted and what catches it, or just re-run it yourself:

```bash
python end_to_end.py --config-file configs/demo_weather.yaml
```

Then open `environments/demo_weather/gx/uncommitted/data_docs/local_site/index.html` in a
browser, or look at `environments/demo_weather/output/CUSTOMERS/CUSTOMERS_summary.csv`
(and the other five tables) to see the flattened pass/fail results. This is the fastest
way to build a mental model of what the pipeline actually produces before you commit to
designing your own suites.

## 4. Create your own environment config

```bash
cp configs/TEMPLATE.yaml configs/my-project.yaml
```

Edit `configs/my-project.yaml`:

- `common.environment_name`: any short, unique label for this project/environment.
- `gx_consumer.csv_data_dir`: the directory where your `<table>.<ext>` CSV files live
  (see step 6).
- Everything else can stay at its default to start.

Commit this file once it's real -- that's the point of a config-per-environment model:
`git log configs/my-project.yaml` answers "what were we testing, and when did it change?"

If you'd rather keep your project's suites, data, and results isolated from the root
`gx/`/`output/`/`suites/` trees the way `demo_weather` does (recommended once you're past
experimenting), point `gx_root_dir`, `output_root_dir`, `suites_dir`, and `csv_data_dir`
at your own `environments/my-project/` subtree instead -- see
`configs/demo_weather.yaml` for a working example of that pattern.

## 5. Write your first expectations

Expectations live as rows in CSVs under `suites/`. Start simple -- one CSV, one table:

```csv
table,column,expectation,min_value,max_value,mostly,severity,meta
ORDERS,ORDER_TOTAL,ExpectColumnValuesToBeBetween,0,100000,0.99,warning,"{""notes"": ""sanity bound""}"
ORDERS,ORDER_ID,ExpectColumnValuesToNotBeNull,,,,critical,"{""notes"": ""primary key""}"
```

Save this as `suites/ORDERS_basic.csv`. See the root [README.md](README.md)'s "The CSV
metadata format" section for the full format, and `core-expectations-types-and-args.csv`
for every supported expectation type and the columns it reads.

**Watch out for blank boolean cells.** `strict_min`, `strict_max`, `exact_match`,
`ties_ok`, and `allow_relative_error` all default to `false` when their cell is blank --
but a *non-empty* cell is only ever treated as `true` unless its text (case-insensitive)
is one of `true`/`1`/`yes`/`y`. Write `false` explicitly rather than leaving the cell
blank if you want to be unambiguous, especially for `strict_min`/`strict_max` on an
`ExpectColumnValuesToBeBetween` row where a real value can legitimately sit exactly on
the boundary (e.g. a percentage that's legitimately `0` or `100`).

## 6. Provide some data

Put a CSV named after each table your suites reference in the directory you set as
`csv_data_dir` -- e.g. `<csv_data_dir>/ORDERS.csv` with an `ORDER_TOTAL` and an
`ORDER_ID` column, some passing rows and (to see a failure) a row or two that violates a
rule.

**Watch out for pandas' default null-sentinel strings.** `pd.read_csv` (what
`gx_consumer.py` uses to load your data) treats `N/A`, `NA`, `NULL`, `None`, `nan`, and a
few others as missing values by default, converting them to a real null *before* GX ever
sees the column -- so a literal `N/A` you intended as "a garbled value" instead becomes
"no value provided," which a not-null check catches but a format check (e.g.
`ExpectColumnValuesToBeDateutilParseable`) will not. If you want to test a malformed
string on purpose, use something that isn't on that list (e.g. `"not-a-date"` rather than
`"N/A"`) -- see `environments/demo_weather/generate_data.py`'s own note on exactly this.

## 7. Run it

One command:

```bash
python end_to_end.py --config-file configs/my-project.yaml
```

Or run each stage by hand:

```bash
python gx_generator.py --config-file configs/my-project.yaml
python gx_consumer.py  --config-file configs/my-project.yaml
python gx_validations_extractor.py --config-file configs/my-project.yaml
```

## 8. Look at the results

- **Data docs** (GX's own human-readable report): open
  `gx/uncommitted/data_docs/local_site/index.html` in a browser.
- **Flattened CSVs**: `output/<suite_name>/<suite_name>_summary.csv` and `_details.csv`.

## 9. Iterate

Edit `suites/*.csv`, re-run `gx_generator.py`, re-run `gx_consumer.py`. When a suite is
retired (its CSV deleted), also run `clear_old_gx_validations.py all` (or
`end_to_end.py --clean`) -- otherwise its already-generated suite JSON keeps being
discovered and run even though its source CSV is gone.

## 10. Edit a suite interactively

Editing `suites/*.csv` by hand and re-running `gx_generator.py` works, but sometimes you
want to try an expectation against real data before committing to it. Great
Expectations used to ship a `great_expectations suite edit <SUITE>` CLI command for
exactly that; GX 1.x removed the CLI entirely (Data Docs' own "How to Edit This Suite"
button still quotes that now-dead command). `edit_suite.py` is this repo's replacement:

```bash
python edit_suite.py CUSTOMERS --config-file configs/demo_weather.yaml
```

This generates a disposable notebook at `play/edit_CUSTOMERS.ipynb` (gitignored) and
opens it in Jupyter (pass `--no-launch` to only generate it). Run its cells top to
bottom: it loads the suite and the real data, runs the suite as-is so you can see what's
currently failing, lets you preview a candidate expectation against the data with zero
side effects, and -- one clearly marked cell -- saves it into `expectations/<SUITE>.json`
for real once you're happy with it.

Needs `jupyter`/`ipykernel` in your `.venv` (a dev tool, not a pipeline dependency, so
it's deliberately not in `requirements.txt`):

```bash
.venv/bin/pip install jupyter ipykernel
```

## 11. Sanity-check the generator alone

`generator-tests/` has two small fixture CSVs -- one that should generate cleanly, one
where every row is intentionally invalid -- useful for confirming your Python environment
and GX version are working before you point anything at real data. See
`generator-tests/TESTS.md`.

## 12. Point it at a real database

Everything above validates CSV files. To validate a live database table instead, read the
root [README.md](README.md)'s "The one-seam design" section -- `gx_consumer.py`'s
`load_dataframe()` is the only function you need to change.

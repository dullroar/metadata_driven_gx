# demo_weather

A fully worked, **committed** example environment for this repo, so you can see what a
real run produces without having to build your own dataset first. Everything here is
synthetic and generated for this repo -- it does not describe any real company, person,
or database.

**"Nimbus Home Weather Co."** is a fictional company that sells home weather stations.
This environment validates its (fake) CRM data -- customers, addresses, phone numbers,
email addresses -- plus a numeric-heavy sensor-log dataset from the weather stations
themselves. 6 tables, 50 expectations across 12 different GX expectation types, 29 of
which currently fail -- **on purpose**. Every failure here was deliberately planted so you
can see exactly what each expectation type catches; see [Data model](#data-model) and
[Deliberately planted problems](#deliberately-planted-problems) below for the full map
from implanted problem to the expectation that catches it.

## Why this is isolated from the root `gx/`/`output/`

This environment sets its own `gx_root_dir`, `output_root_dir`, `suites_dir`, and
`csv_data_dir` (see `configs/demo_weather.yaml`), all under this directory. That keeps
the root `gx/`/`output/`/`suites/` trees an untouched, empty template for **your own**
project, while this one worked example lives self-contained and fully committed
(including its generated results) alongside it.

## Running it

From the repo root:

```
python end_to_end.py --config-file configs/demo_weather.yaml
```

or stage by stage:

```
python gx_generator.py --config-file configs/demo_weather.yaml
python gx_consumer.py  --config-file configs/demo_weather.yaml
python gx_validations_extractor.py --config-file configs/demo_weather.yaml
```

Then open `environments/demo_weather/gx/uncommitted/data_docs/local_site/index.html` in a
browser, or look at `environments/demo_weather/output/<TABLE>/<TABLE>_summary.csv` and
`_details.csv`.

**A note on diffs after you re-run this.** `gx/great_expectations.yml` gets a fresh
`data_context_id` and re-derived `fluent_datasources` block every time `gx_consumer.py`
runs (GX manages both; neither is meaningful to a reader), and `output/*/run_date`
columns/log filenames are always today's timestamp -- an incidental diff there is normal
and not worth chasing down. `gx/expectations/*.json` (the suites themselves), by
contrast, stays byte-for-byte stable across ordinary re-runs -- GX reuses each existing
expectation's id when its type+kwargs haven't changed. Only an explicit full reset
(`clear_old_gx_validations.py all` / `end_to_end.py --clean`) followed by regeneration
assigns fresh ids there.

## Regenerating the data and suites from scratch

Both are scripted and deterministic (fixed random seed):

```
python environments/demo_weather/generate_data.py     # writes data/*.csv
python environments/demo_weather/generate_suites.py   # writes suites/*.csv
```

Read them if you want to see exactly how a problem was planted, or to model your own
fake dataset on this one.

## Data model

Six tables, with the FK relationships you'd expect from a real CRM + IoT device fleet
(none of these are enforced by GX itself across tables -- see the note in
[Deliberately planted problems](#deliberately-planted-problems)):

```
CUSTOMERS (26 rows, 1 duplicate CUSTOMER_ID)
  |-- ADDRESSES (25 rows)   CUSTOMER_ID FK
  |-- PHONES    (36 rows)   CUSTOMER_ID FK
  |-- EMAILS    (25 rows)   CUSTOMER_ID FK
  '-- STATIONS  (16 rows, 1 duplicate STATION_ID)   CUSTOMER_ID FK
        '-- READINGS (151 rows)   STATION_ID FK
```

| Table | Columns |
|---|---|
| `CUSTOMERS` | `CUSTOMER_ID`, `FIRST_NAME`, `LAST_NAME`, `SIGNUP_DATE`, `STATE_CD`, `ACCOUNT_STATUS`, `LOYALTY_POINTS` |
| `ADDRESSES` | `ADDRESS_ID`, `CUSTOMER_ID`, `STREET`, `CITY`, `STATE_CD`, `BILLING_STATE_CD`, `ZIP_CODE`, `COUNTRY_CD` |
| `PHONES` | `PHONE_ID`, `CUSTOMER_ID`, `PHONE_TYPE`, `PHONE_NUMBER`, `IS_PRIMARY` |
| `EMAILS` | `EMAIL_ID`, `CUSTOMER_ID`, `EMAIL_ADDRESS`, `IS_VERIFIED` |
| `STATIONS` | `STATION_ID`, `CUSTOMER_ID`, `MODEL_CD`, `INSTALL_DATE`, `WARRANTY_START_DATE`, `WARRANTY_END_DATE`, `IS_ACTIVE` |
| `READINGS` | `READING_ID`, `STATION_ID`, `READING_TS`, `TEMPERATURE_F`, `HUMIDITY_PCT`, `PRESSURE_HPA`, `WIND_SPEED_MPH`, `RAINFALL_IN`, `BATTERY_PCT` |

## Deliberately planted problems

Every row below is a **real, distinct problem planted in `data/*.csv`**, and the
expectation (in `suites/*.csv`) that catches it. All natural keys (`CUSTOMER_ID`,
`READING_ID`, ...) are wired up as `join_keys` in `configs/demo_weather.yaml`, so
`output/<table>/<table>_details.csv` names the exact offending row by its real key
column, not a bare position.

| Table | Key | Problem planted | Expectation that catches it |
|---|---|---|---|
| CUSTOMERS | 10 (dup) | a row with `CUSTOMER_ID` 10 appended a second time | `ExpectColumnValuesToBeUnique` |
| CUSTOMERS | 5 | blank `LAST_NAME` | `ExpectColumnValuesToNotBeNull` |
| CUSTOMERS | 8 | `STATE_CD` = `"ZZ"` (not a real state) | `ExpectColumnValuesToBeInSet` |
| CUSTOMERS | 11 | `LOYALTY_POINTS` = `-150` | `ExpectColumnValuesToBeBetween` |
| CUSTOMERS | 14 | `SIGNUP_DATE` = `"sometime last spring"` | `ExpectColumnValuesToBeDateutilParseable` |
| CUSTOMERS | 17 | `ACCOUNT_STATUS` = `"CANCELLED"` (not an allowed status) | `ExpectColumnValuesToBeInSet` |
| ADDRESSES | 13 | blank `STREET` | `ExpectColumnValuesToNotBeNull` |
| ADDRESSES | 3 | `ZIP_CODE` = `"123"` (wrong length) | `ExpectColumnValueLengthsToEqual` + `ExpectColumnValuesToMatchRegex` |
| ADDRESSES | 10 | `COUNTRY_CD` = `"USA"` (not `"US"`) | `ExpectColumnValuesToBeInSet` |
| ADDRESSES | 7 | `STATE_CD` != `BILLING_STATE_CD` | `ExpectColumnPairValuesToBeEqual` |
| PHONES | 4 (dup) | a row with `PHONE_ID` 4 appended a second time | `ExpectColumnValuesToBeUnique` |
| PHONES | 10 | `PHONE_TYPE` = `"FAX"` (not supported) | `ExpectColumnValuesToBeInSet` |
| PHONES | 5 | `PHONE_NUMBER` = `"555.12.34"` (wrong format) | `ExpectColumnValuesToMatchRegex` |
| EMAILS | 16 | blank `EMAIL_ADDRESS` | `ExpectColumnValuesToNotBeNull` |
| EMAILS | 6 | `EMAIL_ADDRESS` = `"not-an-email"` | `ExpectColumnValuesToMatchRegex` |
| EMAILS | 21 (dup of 3) | same `EMAIL_ADDRESS` as EMAIL_ID 3 | `ExpectColumnValuesToBeUnique` (on `EMAIL_ADDRESS`, not `EMAIL_ID`) |
| STATIONS | 2 (dup) | a row with `STATION_ID` 2 appended a second time | `ExpectColumnValuesToBeUnique` |
| STATIONS | 8 | `MODEL_CD` = `"WX50"` (discontinued/unknown model) | `ExpectColumnValuesToBeInSet` |
| STATIONS | 4 | `WARRANTY_END_DATE` == `WARRANTY_START_DATE` (zero-length warranty) | `ExpectColumnPairValuesAToBeGreaterThanB` |
| READINGS | 101 | `READING_TS` = `"not-a-timestamp"` | `ExpectColumnValuesToBeDateutilParseable` |
| READINGS | 13 | `HUMIDITY_PCT` = `142.0` (> 100%) | `ExpectColumnValuesToBeBetween` |
| READINGS | 28 | `TEMPERATURE_F` = `-999.0` (dead-sensor sentinel) | `ExpectColumnValuesToBeBetween` **and** `ExpectColumnStdevToBeBetween` (the same bad reading blows out the whole day's spread, not just its own bound -- a nice example of two independent expectation types catching one root cause) |
| READINGS | 41 | blank `PRESSURE_HPA` | `ExpectColumnValuesToNotBeNull` |
| READINGS | 56 | `WIND_SPEED_MPH` = `-5.0` | `ExpectColumnValuesToBeBetween` |
| READINGS | 86 | `RAINFALL_IN` = `-0.1` | `ExpectColumnValuesToBeBetween` |
| READINGS | 71 | `BATTERY_PCT` = `137` (> 100%) | `ExpectColumnValuesToBeBetween` |
| READINGS | 151 (dup of 6) | same `(STATION_ID, READING_TS)` as READING_ID 6 | `ExpectCompoundColumnsToBeUnique` |

That's 27 distinct planted problems; the summary CSVs show 29 failing expectation
*results* because two of them (the malformed ZIP code, the dead-sensor temperature
reading) are independently caught by more than one expectation, on purpose -- real
data-quality suites overlap like this too, and it's worth seeing what that looks like.

Everything else -- e.g. `STATE_CD` length, `INSTALL_DATE`/`SIGNUP_DATE` parseability for
every *other* row, the `(FIRST_NAME, LAST_NAME)` and `(CUSTOMER_ID, PHONE_TYPE)` compound
uniqueness checks, all four `ExpectTableRowCountToBeBetween` sanity bounds -- **passes**,
on real, legitimately clean rows. A demo where everything fails doesn't tell you much;
the point is to see both outcomes side by side in the same run.

Note: GX has no built-in notion of a cross-table foreign key -- every expectation here
validates one table's own dataframe. The FK relationships in the diagram above are
real (and worth knowing when you read the data), but nothing in `suites/*.csv` enforces
them across files; that would require loading a joined/merged dataframe yourself (see
`gx_consumer.py`'s `load_dataframe()` -- the same seam you'd use to point this at a real
database) before validating it.

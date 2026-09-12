"""Regenerate this environment's suites/*.csv expectation metadata from scratch, via
csv.DictWriter -- avoids hand-counting commas across many optional columns (the CSV
format documented in ../../README.md and ../../gx_generator's docstrings).

    python generate_suites.py
"""
import csv
from pathlib import Path

OUT = Path(__file__).resolve().parent / "suites"
OUT.mkdir(parents=True, exist_ok=True)

VALID_STATES = ["CA","NY","TX","WA","CO","OR","AZ","IL","MA","NC","MN","GA","UT","VA","MI"]

def write_suite(name, fieldnames, rows):
    path = OUT / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            full = {k: r.get(k, "") for k in fieldnames}
            w.writerow(full)
    print(f"wrote {path} ({len(rows)} rows)")


# ---------------------------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------------------------
customers_fields = ["table","column","expectation","column_A","column_B","min_value",
                     "max_value","strict_min","strict_max","mostly","value_set",
                     "column_list","value","severity","meta"]
customers_rows = [
    dict(table="CUSTOMERS", column="CUSTOMER_ID", expectation="ExpectColumnValuesToBeUnique",
         severity="critical", meta='{"notes": "primary key must be unique"}'),
    dict(table="CUSTOMERS", column="CUSTOMER_ID", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="critical", meta='{"notes": "primary key must be present"}'),
    dict(table="CUSTOMERS", column="LAST_NAME", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="warning",
         meta='{"notes": "a customer record with no last name is incomplete"}'),
    dict(table="CUSTOMERS", column="STATE_CD", expectation="ExpectColumnValuesToBeInSet",
         value_set=str(VALID_STATES).replace("'", '"'), mostly="1.0", severity="warning",
         meta='{"notes": "home state must be one we actually ship to"}'),
    dict(table="CUSTOMERS", column="STATE_CD", expectation="ExpectColumnValueLengthsToEqual",
         value="2", severity="warning", meta='{"notes": "state codes are always 2 letters"}'),
    dict(table="CUSTOMERS", column="ACCOUNT_STATUS", expectation="ExpectColumnValuesToBeInSet",
         value_set='["ACTIVE", "INACTIVE", "SUSPENDED"]', mostly="1.0", severity="critical",
         meta='{"notes": "no other lifecycle states exist"}'),
    dict(table="CUSTOMERS", column="LOYALTY_POINTS", expectation="ExpectColumnValuesToBeBetween",
         min_value="0", max_value="100000", strict_min="false", strict_max="false", mostly="1.0",
         severity="critical", meta='{"notes": "points can never go negative"}'),
    dict(table="CUSTOMERS", column="SIGNUP_DATE", expectation="ExpectColumnValuesToBeDateutilParseable",
         mostly="1.0", severity="warning", meta='{"notes": "must be a real date"}'),
    dict(table="CUSTOMERS", column="FIRST_NAME, LAST_NAME", expectation="ExpectCompoundColumnsToBeUnique",
         column_list='["FIRST_NAME", "LAST_NAME"]', severity="info",
         meta='{"notes": "sniff test for accidental duplicate customer records"}'),
    dict(table="CUSTOMERS", column="CUSTOMER_ID", expectation="ExpectTableRowCountToBeBetween",
         min_value="10", max_value="100", strict_min="false", strict_max="false", severity="info",
         meta='{"notes": "sanity bound on table size"}'),
]
write_suite("CUSTOMERS", customers_fields, customers_rows)

# ---------------------------------------------------------------------------
# ADDRESSES
# ---------------------------------------------------------------------------
addresses_fields = ["table","column","expectation","column_A","column_B","min_value",
                     "max_value","mostly","value_set","value","regex","severity","meta"]
addresses_rows = [
    dict(table="ADDRESSES", column="ADDRESS_ID", expectation="ExpectColumnValuesToBeUnique",
         severity="critical", meta='{"notes": "primary key must be unique"}'),
    dict(table="ADDRESSES", column="CUSTOMER_ID", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="critical", meta='{"notes": "every address must belong to a customer"}'),
    dict(table="ADDRESSES", column="STREET", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="warning",
         meta='{"notes": "a blank street line means the address is unusable"}'),
    dict(table="ADDRESSES", column="ZIP_CODE", expectation="ExpectColumnValueLengthsToEqual",
         value="5", severity="critical",
         meta='{"notes": "US ZIP codes are 5 digits in this dataset"}'),
    dict(table="ADDRESSES", column="ZIP_CODE", expectation="ExpectColumnValuesToMatchRegex",
         mostly="1.0", regex=r"^\d{5}$", severity="warning", meta='{"notes": "digits only, no letters"}'),
    dict(table="ADDRESSES", column="STATE_CD", expectation="ExpectColumnValuesToBeInSet",
         value_set=str(VALID_STATES).replace("'", '"'), mostly="1.0", severity="warning",
         meta='{"notes": "shipping state must be one we serve"}'),
    dict(table="ADDRESSES", column="COUNTRY_CD", expectation="ExpectColumnValuesToBeInSet",
         value_set='["US"]', mostly="1.0", severity="warning",
         meta='{"notes": "this dataset is US-only for now"}'),
    dict(table="ADDRESSES", column="", expectation="ExpectColumnPairValuesToBeEqual",
         column_A="STATE_CD", column_B="BILLING_STATE_CD", mostly="1.0", severity="warning",
         meta='{"notes": "home state and billing state should usually match; a mismatch is worth a human look, not necessarily wrong"}'),
    dict(table="ADDRESSES", column="ADDRESS_ID", expectation="ExpectTableRowCountToBeBetween",
         min_value="10", max_value="100", severity="info", meta='{"notes": "sanity bound on table size"}'),
]
write_suite("ADDRESSES", addresses_fields, addresses_rows)

# ---------------------------------------------------------------------------
# PHONES
# ---------------------------------------------------------------------------
phones_fields = ["table","column","expectation","min_value","max_value","mostly",
                  "value_set","column_list","regex","severity","meta"]
phones_rows = [
    dict(table="PHONES", column="PHONE_ID", expectation="ExpectColumnValuesToBeUnique",
         severity="critical", meta='{"notes": "primary key must be unique"}'),
    dict(table="PHONES", column="CUSTOMER_ID", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="critical", meta='{"notes": "every phone must belong to a customer"}'),
    dict(table="PHONES", column="PHONE_TYPE", expectation="ExpectColumnValuesToBeInSet",
         value_set='["MOBILE", "HOME", "WORK"]', mostly="1.0", severity="warning",
         meta='{"notes": "FAX is not a supported contact channel here"}'),
    dict(table="PHONES", column="PHONE_NUMBER", expectation="ExpectColumnValuesToMatchRegex",
         mostly="1.0", regex=r"^\d{3}-\d{3}-\d{4}$", severity="warning",
         meta='{"notes": "expected format: 555-123-4567"}'),
    dict(table="PHONES", column="CUSTOMER_ID, PHONE_TYPE", expectation="ExpectCompoundColumnsToBeUnique",
         column_list='["CUSTOMER_ID", "PHONE_TYPE"]', severity="info",
         meta='{"notes": "a customer should not have two phones of the same type on file"}'),
    dict(table="PHONES", column="PHONE_ID", expectation="ExpectTableRowCountToBeBetween",
         min_value="10", max_value="100", severity="info", meta='{"notes": "sanity bound on table size"}'),
]
write_suite("PHONES", phones_fields, phones_rows)

# ---------------------------------------------------------------------------
# EMAILS
# ---------------------------------------------------------------------------
emails_fields = ["table","column","expectation","min_value","max_value","mostly","regex","severity","meta"]
emails_rows = [
    dict(table="EMAILS", column="EMAIL_ID", expectation="ExpectColumnValuesToBeUnique",
         severity="critical", meta='{"notes": "primary key must be unique"}'),
    dict(table="EMAILS", column="CUSTOMER_ID", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="critical", meta='{"notes": "every email must belong to a customer"}'),
    dict(table="EMAILS", column="EMAIL_ADDRESS", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="critical",
         meta='{"notes": "a blank email cannot be used to contact the customer"}'),
    dict(table="EMAILS", column="EMAIL_ADDRESS", expectation="ExpectColumnValuesToMatchRegex",
         mostly="1.0", regex=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", severity="warning",
         meta='{"notes": "must look like a real email address"}'),
    dict(table="EMAILS", column="EMAIL_ADDRESS", expectation="ExpectColumnValuesToBeUnique",
         severity="warning",
         meta='{"notes": "two customers sharing one email is usually a data-entry mistake"}'),
    dict(table="EMAILS", column="EMAIL_ID", expectation="ExpectTableRowCountToBeBetween",
         min_value="10", max_value="100", severity="info", meta='{"notes": "sanity bound on table size"}'),
]
write_suite("EMAILS", emails_fields, emails_rows)

# ---------------------------------------------------------------------------
# STATIONS
# ---------------------------------------------------------------------------
stations_fields = ["table","column","expectation","column_A","column_B","or_equal",
                    "min_value","max_value","strict_min","strict_max","mostly","value_set","severity","meta"]
stations_rows = [
    dict(table="STATIONS", column="STATION_ID", expectation="ExpectColumnValuesToBeUnique",
         severity="critical", meta='{"notes": "primary key must be unique"}'),
    dict(table="STATIONS", column="CUSTOMER_ID", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="critical", meta='{"notes": "every station must be registered to a customer"}'),
    dict(table="STATIONS", column="MODEL_CD", expectation="ExpectColumnValuesToBeInSet",
         value_set='["WX100", "WX200", "WX300"]', mostly="1.0", severity="warning",
         meta='{"notes": "WX50 was discontinued before this product line existed"}'),
    dict(table="STATIONS", column="", expectation="ExpectColumnPairValuesAToBeGreaterThanB",
         column_A="WARRANTY_END_DATE", column_B="WARRANTY_START_DATE", or_equal="false", mostly="1.0",
         severity="warning", meta='{"notes": "a warranty must cover at least one day"}'),
    dict(table="STATIONS", column="INSTALL_DATE", expectation="ExpectColumnValuesToBeDateutilParseable",
         mostly="1.0", severity="warning", meta='{"notes": "must be a real date"}'),
    dict(table="STATIONS", column="STATION_ID", expectation="ExpectTableRowCountToBeBetween",
         min_value="5", max_value="50", strict_min="false", strict_max="false", severity="info",
         meta='{"notes": "sanity bound on table size"}'),
]
write_suite("STATIONS", stations_fields, stations_rows)

# ---------------------------------------------------------------------------
# READINGS
# ---------------------------------------------------------------------------
readings_fields = ["table","column","expectation","min_value","max_value","strict_min",
                    "strict_max","mostly","threshold","column_list","severity","meta"]
readings_rows = [
    dict(table="READINGS", column="READING_ID", expectation="ExpectColumnValuesToBeUnique",
         severity="critical", meta='{"notes": "primary key must be unique"}'),
    dict(table="READINGS", column="STATION_ID", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="critical", meta='{"notes": "a reading with no station cannot be attributed to anyone"}'),
    dict(table="READINGS", column="READING_TS", expectation="ExpectColumnValuesToBeDateutilParseable",
         mostly="1.0", severity="critical",
         meta='{"notes": "a reading with a garbled timestamp cannot be trended"}'),
    dict(table="READINGS", column="HUMIDITY_PCT", expectation="ExpectColumnValuesToBeBetween",
         min_value="0", max_value="100", strict_min="false", strict_max="false", mostly="1.0",
         severity="critical", meta='{"notes": "humidity is a percentage; it cannot exceed 100"}'),
    dict(table="READINGS", column="TEMPERATURE_F", expectation="ExpectColumnValuesToBeBetween",
         min_value="-40", max_value="130", strict_min="false", strict_max="false", mostly="1.0",
         severity="critical",
         meta='{"notes": "generous bound for any US home weather station; -999 is a dead-sensor sentinel, not a real reading"}'),
    dict(table="READINGS", column="PRESSURE_HPA", expectation="ExpectColumnValuesToNotBeNull",
         mostly="1.0", severity="warning",
         meta='{"notes": "a missing pressure reading means the barometer sensor dropped out"}'),
    dict(table="READINGS", column="PRESSURE_HPA", expectation="ExpectColumnValuesToBeBetween",
         min_value="930", max_value="1085", strict_min="false", strict_max="false", mostly="1.0",
         severity="warning",
         meta='{"notes": "outside this range the station is almost certainly malfunctioning, not measuring real weather"}'),
    dict(table="READINGS", column="WIND_SPEED_MPH", expectation="ExpectColumnValuesToBeBetween",
         min_value="0", max_value="150", strict_min="false", strict_max="false", mostly="1.0",
         severity="warning", meta='{"notes": "wind speed cannot be negative"}'),
    dict(table="READINGS", column="RAINFALL_IN", expectation="ExpectColumnValuesToBeBetween",
         min_value="0", max_value="20", strict_min="false", strict_max="false", mostly="1.0",
         severity="warning", meta='{"notes": "rainfall cannot be negative (0 itself -- no rain -- is a valid, common reading)"}'),
    dict(table="READINGS", column="BATTERY_PCT", expectation="ExpectColumnValuesToBeBetween",
         min_value="0", max_value="100", strict_min="false", strict_max="false", mostly="1.0",
         severity="warning", meta='{"notes": "battery is a percentage; 100 itself is a valid, common reading"}'),
    dict(table="READINGS", column="TEMPERATURE_F", expectation="ExpectColumnStdevToBeBetween",
         min_value="0", max_value="20", strict_min="false", strict_max="false", severity="warning",
         meta='{"notes": "flex check: a single wild sensor reading blows out the whole day\\u2019s spread, not just its own bound"}'),
    dict(table="READINGS", column="STATION_ID, READING_TS", expectation="ExpectCompoundColumnsToBeUnique",
         column_list='["STATION_ID", "READING_TS"]', severity="critical",
         meta='{"notes": "a station cannot log two different readings at the exact same timestamp"}'),
    dict(table="READINGS", column="READING_ID", expectation="ExpectTableRowCountToBeBetween",
         min_value="50", max_value="500", strict_min="false", strict_max="false", severity="info",
         meta='{"notes": "sanity bound on table size"}'),
]
write_suite("READINGS", readings_fields, readings_rows)

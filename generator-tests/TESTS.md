
# TESTS.md

## pass-tests-expectations.csv

A compact set of passing tests proving the generator is working:

* Row 1: ExpectColumnValuesToNotBeNull — valid.
* Row 2: ExpectColumnValuesToBeBetween — valid.
* Row 3: ExpectColumnValuesToBeInSet — valid.
* Row 4: ExpectColumnValueLengthsToBeBetween — valid.
* Row 5: ExpectCompoundColumnsToBeUnique — valid.
* Row 6: ExpectTableRowCountToBeBetween — valid.

## adversarial-expectations.csv

Each row is intentionally invalid.

### Row 1

* **Error:** Unknown expectation `ExpectColumnValuesToBePurple`.
* **Why:** Not found in metadata.

### Row 2

* **Error:** Invalid severity `medium`.
* **Why:** Only critical/warning/info allowed.

### Row 3

* **Error:** Invalid JSON in meta.
* **Why:** JSON not parseable.

### Row 4

* **Error:** value_set cannot be parsed into a list.
* **Why:** Format is not JSON, comma‑list, or parseable structure.

### Row 5

* **Error:** Missing required column name.
* **Why:** `column` cannot be blank for column expectations.

### Row 6

* **Error:** Missing required args for ExpectColumnValuesToBeBetween.
* **Why:** min_value and max_value required; both blank.

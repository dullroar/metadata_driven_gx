"""Run the demo CLI in a fresh copy and compare its CSVs with the sample."""

import csv
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO = Path("environments/demo_weather")


def csv_files(root):
    return {path.relative_to(root) for path in root.rglob("*.csv")}


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        columns = next(reader, [])
        if columns.count("run_date") != 1:
            raise ValueError(f"{path.name}: expected one run_date column")
        date_index = columns.index("run_date")
        rows = Counter()
        for line, row in enumerate(reader, start=2):
            if len(row) != len(columns):
                raise ValueError(f"{path.name}:{line}: row does not match the header")
            rows[tuple(row[:date_index] + row[date_index + 1 :])] += 1
        return columns, rows


def compare_outputs(reference, output):
    expected_files = csv_files(reference)
    actual_files = csv_files(output)
    if not expected_files or expected_files != actual_files:
        missing = sorted(str(path) for path in expected_files - actual_files)
        extra = sorted(str(path) for path in actual_files - expected_files)
        raise ValueError(f"CSV file set differs. Missing: {missing}. Extra: {extra}.")

    errors = []
    for path in sorted(expected_files):
        expected_columns, expected_rows = read_csv(reference / path)
        actual_columns, actual_rows = read_csv(output / path)
        if actual_columns != expected_columns:
            errors.append(f"{path}: column names or order differ")
        if actual_rows != expected_rows:
            missing = sum((expected_rows - actual_rows).values())
            extra = sum((actual_rows - expected_rows).values())
            errors.append(
                f"{path}: {expected_rows.total()} expected rows, "
                f"{actual_rows.total()} actual rows, {missing} missing, {extra} extra"
            )
    if errors:
        raise ValueError("\n".join(errors))
    print(f"Demo matches all {len(expected_files)} sample CSVs.")


def main():
    with tempfile.TemporaryDirectory(prefix="metadata-driven-gx-demo-") as temp:
        work = Path(temp) / "source"
        shutil.copytree(
            ROOT, work, ignore=shutil.ignore_patterns(".git", "output", "uncommitted")
        )
        subprocess.run(
            [sys.executable, "end_to_end.py", "--config-file", "configs/demo_weather.yaml"],
            cwd=work,
            check=True,
        )
        compare_outputs(ROOT / DEMO / "output", work / DEMO / "output")


if __name__ == "__main__":
    main()

# DESIGN.md

# metadata-driven-gx Design

## Boundary

The project turns tabular validation metadata into Great Expectations suites, executes them against supplied data, and flattens results into reviewable tables. README.md explains the runnable workflow; this document records the deliberate seams.

## Core decisions

- Describe expectations as rows in CSV files. This makes validation intent editable, diffable, and generatable without requiring Python edits for each suite.
- Separate generation, consumption, and extraction: `gx_generator.py` creates suites, `gx_consumer.py` runs them, and `gx_validations_extractor.py` produces flat results. The stages can be inspected or run independently.
- Treat an environment directory as the configuration seam: it groups metadata, source data, GX artifacts, and extracted output for one target.
- Keep generated GX definitions and flattened results available for white-box review, even though GX regenerates GUIDs and each run records a timestamp.
- Use `join_keys` to make failed rows readable and attributable rather than presenting only aggregate expectation failures.

## Constraints

This repository is a metadata-driven validation harness, not a replacement for Great Expectations or a generic ETL platform. Generated GUID/timestamp-only diffs are operational noise and must not be mistaken for semantic changes.



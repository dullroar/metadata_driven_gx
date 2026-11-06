---
gist: "Read when: changing how expectations are described or generated, the CSV metadata schema, or whether a suite change requires Python edits."
---

# Expectations are rows in CSV files

**Decision.** Validation intent is described as rows in CSV files, which makes it editable, diffable, and generatable without Python edits for each suite.

**Boundary.** A metadata-driven validation harness, not a replacement for Great Expectations or a generic ETL platform.

---
gist: "Read when: changing the repository's design, boundaries or dependencies, or before simplifying a deliberate seam."
---

# Architecture premises

One durable design decision per file: the constraint, the choice, why, and what would contradict it. Open only the premise whose **Read when** line matches the task.

<!-- BEGIN GENERATED CONTEXT INDEX -->

* [expectations-as-csv-metadata.md](./expectations-as-csv-metadata.md).
  Read when: changing how expectations are described or generated, the CSV metadata schema, or whether a suite change requires Python edits.
* [generate-consume-extract-stages.md](./generate-consume-extract-stages.md).
  Read when: changing gx_generator.py, gx_consumer.py or gx_validations_extractor.py, merging the stages, or altering the environment-directory layout.
* [reviewable-artifacts-and-join-keys.md](./reviewable-artifacts-and-join-keys.md).
  Read when: deciding whether to gitignore generated GX output, interpreting GUID or timestamp diffs, or changing how failed rows are reported (join_keys).

<!-- END GENERATED CONTEXT INDEX -->

---
gist: "Read when: changing gx_generator.py, gx_consumer.py or gx_validations_extractor.py, merging the stages, or altering the environment-directory layout."
---

# Separate generation, consumption and extraction

**Decision.** `gx_generator.py` creates suites, `gx_consumer.py` runs them, and `gx_validations_extractor.py` produces flat results, so each stage can be inspected or run independently. An environment directory is the configuration seam: it groups metadata, source data, GX artifacts and extracted output for one target.

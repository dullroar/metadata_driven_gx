---
gist: "Read when: deciding whether to gitignore generated GX output, interpreting GUID or timestamp diffs, or changing how failed rows are reported (join_keys)."
---

# Reviewable generated artifacts and attributable failures

**Decision.** Generated GX definitions and flattened results stay available for white-box review, even though GX regenerates GUIDs and each run records a timestamp. Generated GUID/timestamp-only diffs are operational noise and must not be mistaken for semantic changes (see AGENTS.md for handling). `join_keys` make failed rows readable and attributable rather than presenting only aggregate expectation failures.

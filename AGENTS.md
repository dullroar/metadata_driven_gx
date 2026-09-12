# Instructions for AI coding agents working in this repo

This file and [AGENTS.md](AGENTS.md) are kept identical on purpose, for whichever
convention your tool looks for.

## GX regenerates GUIDs and timestamps on every run -- don't treat that as a real diff

`environments/demo_weather/` is a committed, fully worked example: its GX suite JSON,
checkpoints, and flattened `output/*/*.csv` results are already generated and checked in.
If you (or the user, while you're watching) re-run `end_to_end.py` or any individual
stage (`gx_generator.py`, `gx_consumer.py`, `gx_validations_extractor.py`) against that
same environment, or against any other environment whose output is committed, expect
`git status`/`git diff` to show files as changed even though nothing about the demo
itself changed:

- Every suite/checkpoint/validation-definition JSON under a `gx/` tree carries an `"id"`
  field -- a GUID Great Expectations assigns fresh each time that object is (re)created.
  Re-running the generator or consumer reshuffles these even when every expectation's
  actual content (table, column, expectation type, kwargs) is identical to what's already
  committed.
- Every row in `output/*/*.csv` (written by `gx_validations_extractor.py`) carries a
  `run_date` column -- the wall-clock time that particular validation run happened.
- Data-docs HTML under `gx/uncommitted/` is gitignored already, so it shouldn't show up
  at all -- but if you ever see it staged, that's also churn, not content.
- Plain filesystem modified-times on unchanged files are not something git tracks or
  something you need to reason about at all -- only file *content* matters here.

**What to do about it:**

- Before staging or committing anything in this area, run `git diff` (not just
  `git status`) on any changed file under a `gx/` or `output/` tree and actually look at
  it. If the only lines that changed are `"id": "<guid>"` values and/or a `run_date` /
  timestamp column, that file has no real change -- `git checkout -- <path>` it (or leave
  it unstaged) rather than committing regenerated noise, and don't report it to the user
  as a meaningful change.
- If a file's diff mixes that kind of churn with an actual content change (a different
  `success`/`unexpected_count`/`observed_value`, a new or removed expectation, a changed
  kwarg, an added row), treat the whole file as genuinely changed and let it through
  normally -- don't try to hand-filter out just the GUID/timestamp lines from a real
  change, and don't hide the real change from the user.
- If the user explicitly asks you to regenerate and commit fresh demo output on purpose,
  that's a normal, intentional commit -- this guidance is about not mistaking routine
  regeneration for something worth flagging or committing when nothing substantive moved,
  not about refusing to ever update the committed example.

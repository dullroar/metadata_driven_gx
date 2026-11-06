# Agent contract

Turns tabular validation metadata (CSV rows) into Great Expectations suites, runs them against supplied data, and flattens results into reviewable tables.

## Load context in this order

1. Read this file.
2. Read the short indexes in full: `README.md`, `docs/README.md`, `memory/README.md`, `scripts/README.md`.
3. Match the task against each index's **Read when** entries and open only matching documents.
4. For a large file, search its headings and read only the relevant ranges.
5. Stop loading when the decision, intended files, constraints and validation method are known.

User instructions take precedence over repository guidance. When sources conflict, prefer: user
instruction, this file, `docs/design/`, the named plan, domain documentation and references,
`memory/`, implementation and tests, historical notes.

## Context ownership

- Universal rules belong here.
- Architectural reasons belong in `docs/design/` (one premise per file).
- Non-obvious findings that cost time to discover belong in `memory/` (one topic per file; edit the existing topic, do not append a rival).
- Execution state belongs in `plans/`; deterministic automation in `scripts/`.
- Every routed Markdown file starts with `gist: "Read when: ..."` front matter. Do not hand-edit the generated section of an index; run `python scripts/build_context_indexes.py`.

Do not duplicate a fact across layers. Correct its canonical source.

## Planned work (spec-driven)

- Work only on a named plan in `plans/<plan>/` (`spec.md` plus `steps/`) or an explicitly identified off-plan task. Copy `plans/TEMPLATE/` to start one.
- Once its spec is approved, proceed through the steps without asking permission for routine work. Failed tests and dead ends inside scope: diagnose, repair, continue. Return to the user only for a new decision: contradictory requirements, scope expansion, or an action outside the spec's delegated authority.
- Acceptance checks named in the spec are protected. Never weaken, skip or delete one to get green; if one cannot pass as written, escalate.
- Parallel steps must have no dependency between them and no overlapping `touches`; if independence is uncertain, serialize. After parallel steps merge, run the spec's combined validation.
- A step is done only with recorded evidence. Report unavailable verification honestly.
- Retiring a rule, correcting documentation, and tolerating a known violation are different outcomes; record which one (see `plans/TEMPLATE/spec.md`).

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

## Update RELEASE_NOTES.md in the same commit as whatever it describes

This repo tracks its version in commit message prefixes (`vX.Y.Z: <summary>`, no git
tags) and in [RELEASE_NOTES.md](RELEASE_NOTES.md). Whenever you make a change worth its
own version bump -- the user says so explicitly, or you're about to commit something a
future reader would want called out (a new script, a behavior change, a fix to
something documented elsewhere in this repo) -- add an entry to the top of
RELEASE_NOTES.md in that same commit, and use the matching `vX.Y.Z:` prefix on the
commit message itself. Don't wait to be asked a second time; this instruction is the
standing ask.

## Validation

Run the smallest check that proves the change, then `python scripts/check_context.py` for any change to context files.

## Safety

Do not commit credentials, personal data, personal filesystem paths or sensitive record-level examples. Use placeholders and aggregate evidence. Do not push, publish, force-push or add a remote without authorization.

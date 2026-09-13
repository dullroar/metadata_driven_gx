# Testing with GX: environments as a universal whitebox output harness

This repo was built to solve one problem -- turn a spreadsheet of data-quality rules into
Great Expectations suites without hand-writing Python for every column -- but the shape it
ended up with solves a second, more general problem almost by accident: **it is a
ready-made harness for whitebox-testing the output of any other codebase**, without
writing a line of test code in that codebase.

This document is about that second use, aimed specifically at an AI coding agent deciding
whether to reach for it.

## The unit that makes this work: an environment

Nothing in `gx_generator.py`, `gx_consumer.py`, or `gx_validations_extractor.py` knows or
cares what produced the CSV files it reads. Each script reads one config section, does its
one job, and hands off through files -- `suites/*.csv` in, `gx/expectations/*.json` in the
middle, `output/*/*.csv` out (see the architecture diagram in [README.md](README.md)).
`environments/demo_weather/` already demonstrates the consequence of that decoupling: a
config file (`configs/demo_weather.yaml`) that points every one of `gx_root_dir`,
`output_root_dir`, `suites_dir`, and `csv_data_dir` at its own subtree instead of the
root-level defaults, so one repo can host any number of self-contained, isolated test
environments side by side.

An "environment," in other words, is nothing more than:

1. a YAML config file naming four directories,
2. a directory of CSV data to validate,
3. a directory of CSV rows describing what "correct" looks like for that data, and
4. the two directories GX and the extractor write their output into.

That's a small, mechanical, *declarative* unit -- exactly the shape of thing an AI agent
is good at generating. Steps 3 and 4 are the ones worth dwelling on.

## Why an AI agent can generate the metadata directly

`suites/*.csv` rows aren't a Python API to learn -- they're `table,column,expectation,...`
tuples whose column names match GX's own constructor arguments, drawn from a closed,
documented vocabulary (`core-expectations-types-and-args.csv`: every supported
`Expectation...` class, its snake_case type, and the exact kwargs it reads). That closure
is what makes this tractable for an LLM in a way that "go write pytest assertions against
this pipeline's internals" is not: an agent reading a target codebase's schema, docs, or
sample output doesn't need to understand GX's Python API, invent a test harness, or decide
where fixtures live. It needs to map "this column should never be null" to
`ExpectColumnValuesToNotBeNull`, "this code should only ever be one of these five values"
to `ExpectColumnValuesToBeInSet`, and so on -- a lookup, not a design decision. The whole
`demo_weather` suite (50 expectations, 12 expectation types) exists as a worked example of
exactly that mapping, planted deliberately so both a human and an agent can see cause and
effect for every row.

The practical loop for an agent asked to whitebox-test some other codebase's output looks
like this:

1. Read the target codebase's output contract -- its schema, its docs, sample files,
   whatever tells you what a *correct* row looks like (non-null keys, value sets, numeric
   ranges, formats, cross-column relationships).
2. Write that contract as `suites/*.csv` rows, using
   `core-expectations-types-and-args.csv` as the vocabulary.
3. Write a small `configs/<target>.yaml` pointing at the target's own directories (see
   below for *which* directories).
4. Run `python end_to_end.py --config-file configs/<target>.yaml`.
5. Read `output/<table>/<table>_summary.csv`/`_details.csv` -- or the generated data
   docs -- for a pass/fail report with a readable failing-row identity, if `join_keys` is
   set.

No custom test framework, no fixtures, no assertions written in the target codebase's own
language. As the pitch line for this goes:

> "Here is an easy way to test this code from an output POV without having to build custom
> test code here."

## Why "rectangular output" is the right target

This only works because of the one deliberate seam this repo is built around:
`gx_consumer.py`'s `load_dataframe()` is the single place that knows how to get data in
(see "The one-seam design" in [README.md](README.md)), and out of the box that seam reads
plain CSV files, one per table. Almost anything that could be called a codebase eventually
produces *some* tabular artifact on its way out -- a report, an extract, a batch job's
output file, a materialized view dumped for review, a test fixture, a data pipeline's
final Parquet-to-CSV export. If it's rows and columns, it's testable here, regardless of
what language or framework produced it. The target codebase doesn't need to *be* Python,
doesn't need a `.venv`, doesn't need to know this repo exists at runtime -- it just needs
to leave a rectangular file somewhere on disk, which most such systems already do or can
be made to do trivially (a debug/export flag, a `--dump-csv`, a temp-table unload).

That's the whitebox part: the expectations an agent writes encode real knowledge of the
target's *intended* internal contract -- not "did it crash," but "does column X actually
respect the invariant the target codebase's own logic is supposed to guarantee." The
target's output is the observation point; the suite is the whitebox knowledge made
explicit and checkable by a tool that was never told anything about how that output was
produced.

## Where the generated artifacts should actually live

Here's the part worth being deliberate about, and the reason `common.py`'s config
resolution matters: `load_config()` resolves every layout key (`gx_root_dir`,
`output_root_dir`, and everything derived from them) as `root / Path(value)`, where `root`
is *this* repo's own directory, not the current working directory and not the config
file's own location. Pathlib's `/` operator has a convenient property here: when the
right-hand side is already an absolute path, the left side is discarded entirely
(`Path("/anything") / Path("/elsewhere")` is just `Path("/elsewhere")`). So an **absolute**
path in `gx_root_dir`, `output_root_dir`, `suites_dir`, or `csv_data_dir` sends that tree
anywhere on disk -- including into the target codebase's own repository. A **relative**
one, by contrast, always resolves against *this* repo's root, no matter where the config
file itself sits or where you ran the command from -- a real gotcha worth remembering
before pointing a config at a sibling repo.

Which means, concretely: nothing stops `configs/<target>.yaml` from looking like this --

```yaml
common:
  gx_root_dir: "/abs/path/to/target-repo/gx_tests/gx"
  output_root_dir: "/abs/path/to/target-repo/gx_tests/output"
  environment_name: "target-repo-output-contract"
  join_keys:
    SOME_TABLE: ["SOME_KEY_COLUMN"]

gx_generator:
  suites_dir: "/abs/path/to/target-repo/gx_tests/suites"

gx_consumer:
  csv_data_dir: "/abs/path/to/target-repo/gx_tests/data"
```

Run it once and GX's own `get_context(context_root_dir=...)` materializes the whole `gx/`
scaffold at that location -- there's nothing to pre-create. From that point on, every
substantive artifact this pipeline produces -- the hand/AI-authored `suites/*.csv`
metadata, the compiled `gx/expectations/*.json` suites, the flattened
`output/*/*.csv` results, even the data docs -- lives *inside the target repo's own
working tree*. It commits to the target repo's own history, shows up in the target repo's
own `git diff`, and gets reviewed by whoever reviews that repo's PRs. `metadata_driven_gx`
itself holds nothing about the target codebase except the four-line pointer config, and
even that config doesn't strictly need to live here either -- `--config-file` accepts any
path, so the config itself could live inside the target repo too, provided every path
*inside* it stays absolute for the reason above.

That split is the point: this repo stays the small, reusable *engine* (the four pipeline
scripts, the expectation vocabulary, the orchestration), while every environment's
*content* -- what's being tested, and the record of whether it currently passes -- lives
and version-controls with the thing it's actually testing. A reviewer looking at the
target repo's history sees "we added an output-contract check for this column" the same
way they'd see any other test added to that repo, without needing to know
`metadata_driven_gx` exists to understand *what* changed, only *how to re-run it*.

## What the target repo's own README needs

Since the target repo now depends on this one only as an external, callable tool (not a
library it imports), all its own README needs is a pointer:

```markdown
## Output validation

This repo's output contract is whitebox-tested against `metadata_driven_gx`, an external
tool -- see `gx_tests/` in this repo for the expectation suites (`suites/*.csv`) and the
generated results (`gx/expectations/*.json`, `output/*/*.csv`).

    python /path/to/metadata_driven_gx/end_to_end.py \
      --config-file /path/to/metadata_driven_gx/configs/<this-repo>.yaml
```

That's genuinely the whole integration surface. The target repo carries no dependency on
GX, pandas, or this repo's `requirements.txt`; it only needs `metadata_driven_gx` checked
out somewhere reachable at test time (a sibling clone, a git submodule, a pinned path in
CI) -- the same way you'd document any other external CLI tool a repo's tests shell out
to.

## Caveats worth carrying over

A few lessons already documented elsewhere in this repo apply with extra force once the
output tree lives inside someone else's repo, not this one:

- **The GUID/timestamp churn described in [CLAUDE.md](CLAUDE.md)/[AGENTS.md](AGENTS.md)
  now happens in the target repo's diffs, not this one.** Whoever maintains the target
  repo (human or agent) needs the same rule: an `"id"` GUID or a `run_date` column
  changing on an otherwise-identical re-run isn't a real diff worth committing or
  flagging. Worth copying that guidance into the target repo's own CLAUDE.md/AGENTS.md if
  it has one.
- **`gx/uncommitted/` is exactly that -- uncommitted.** The target repo's `.gitignore`
  should exclude it the same way this repo's does, so data docs and raw validation run
  history don't get committed as noise; only `gx/expectations/*.json` (the suites
  themselves) and the extractor's flattened `output/*/*.csv` need to be tracked.
- **Relative paths in the config resolve against this repo, not the target's.** Covered
  above, but easy to get wrong once: always use absolute paths (or a small amount of
  path-joining logic an agent writes once, anchored on a known constant) when a config is
  meant to point outside `metadata_driven_gx`.
- **This only tests the output, not the code that produced it.** That's the deal, not a
  limitation to work around: it's precisely what makes it possible to test *any* other
  codebase, in any language, without writing code in it. Pair it with that codebase's own
  unit/integration tests where those already exist; this fills the gap where they don't,
  or where "does the final table actually look right" is a question no unit test answers
  on its own.

## Summary

`environments/` was already the right abstraction for isolating one project's suites from
another's within this repo. Pointing an environment's four directories outside this repo
entirely is not a hack on top of that design -- it's the same design, used at its natural
boundary. An AI agent can read a target codebase's output contract, express it as
`suites/*.csv` rows against a small, closed expectation vocabulary, and hand the whole
result back to that codebase's own repository to own and version -- while this repo stays
what it always was: the engine that compiles metadata into suites, runs them, and reports
what it found, nothing more, nothing target-specific baked in.

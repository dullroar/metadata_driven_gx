---
gist: "Read me when: you need to know how this repository runs the pinned deterministic-controls library, how the adoption was made, or where the tools did not fit."
---

# Controls adoption

This repository runs the pinned `deterministic-controls` library in advisory mode. The `controls` CI job is not a required check yet.

## How it works

- `scripts/check_context.py` is a shim. It runs the library and prints the old lines (`ok  <script>` or `FAIL <script>`).
- The pin is in `scripts/controls-requirements.txt`. It names one full commit.
- The shim keeps a virtual environment for the pinned commit in `$XDG_CACHE_HOME/deterministic-controls/<commit>/`. The default is `~/.cache/deterministic-controls/<commit>/`.
- The first run for a commit needs the network. Later runs do not.
- Exit codes: `0` all checks pass, `1` a check fails, `2` the library cannot run. The shim never passes without a result. It never falls back to the old scripts.
- `controls.toml` lists the enabled checks.

## How the adoption was made

1. Audit: step `a01-audit` ran a read-only audit. The result is in `docs/controls-audit.json`.
2. Plan: `adopt plan` with the pinned commit gave a dry run. It was read before any change.
3. Apply: `adopt apply` wrote the shim, the pin, `controls.toml` and the `controls` CI job. Its commit is on the step branch. Then the Docker image, `AGENTS.md` and this file were edited by hand.

## Where the tools did not fit

- **Dockerfile.** The Docker run has no network (`--network none`). The shim needs the network once. So the Dockerfile now prepares the shim cache at image build time, as user `gx-test`. The cache is under the home of that user. The image also needs the `git` program, for the shim setup and for `tests/test_secret_guard.py`. The Dockerfile installs it with `apt-get` as root. The run command and `scripts/test_docker.sh` did not change.
- **Pin file.** `adopt apply` wrote a `Run me when:` line in `scripts/controls-requirements.txt`. No fix was needed.
- **Files outside the step scope.** The first `adopt apply` wrote none. The re-run for the `v0.1.2` pin also changed `scripts/install_hooks.sh` (a new `secretguard.path` fallback). That file is outside the scope, so the change was reverted. The step did not keep it.
- **Existing jobs.** `adopt apply` kept the `check` job. The new `controls` job repeats the secret guard steps. That is accepted for now.

- **Stricter index check.** With the first pin, the library reported that `memory/README.md` had no `gist` and `scripts/README.md` had no `Run me when:` line. The old `build_indexes.py --check` did not report this. Pin `v0.1.2` skips folder `README.md` files, so no file edit was needed.

## Secret guard exceptions

none

## Probes

Date of the runs (UTC): 2026-11-24.

Each probe ran in a throwaway Git clone of `HEAD`, never in the real tree. Each bad change was committed in the clone. The command was `python3 -m deterministic_controls check --root <clone> --profile ci --format json`. The rule ID comes from the JSON. The secret probe built its synthetic key at run time in the shell. The key is not in any tracked file.

| Probe | Expected rule ID | Exit code | Result |
| --- | --- | --- | --- |
| Broken relative link in a Markdown file | `markdown.local-links` | 1 | Failed with the expected rule. |
| Stale generated index (changed a `Run me when:` line, no rebuild) | `context.index-freshness` | 1 | Failed with the expected rule. |
| Plan step without `gate` | `plans.schema` | 1 | Failed with the expected rule. |
| Synthetic key in a Markdown file | `security.secrets` | 1 | Failed with the expected rule. `security.personal-data` also failed. |
| Tracked `driver.out` file | `repo.forbidden-artifacts` | 1 | Failed with the expected rule. |
| Internal error (a tracked file with mode 000) | none (the check must not pass) | 3 | Run status `error`. Not a pass. |
| Restored clone (no change) | none | 0 | Passed. All seven checks passed. |

Notes:

- `security.secrets` reads committed content. The synthetic key was found only after it was committed in the clone. Before the commit, only `security.personal-data` found it.
- The shim `python3 scripts/check_context.py` ran in the clone with the plan step that had no `gate`. Its exit code was `1`. It printed `FAIL check_plan.py`.
- The shim on the restored clone exited `0`.

## Rollback

Date of the test (UTC): 2026-11-24.

There is no earlier pin, so the rollback goes back to the pre-adoption scripts. The base commit is the parent of the `adopt apply` commit.

Test result:

- A clean clone at the base commit ran its own `python3 scripts/check_context.py`. All four old checks passed (`build_indexes.py`, `check_plan.py`, `check_links.py`, `scan_secrets.py`).
- A clean clone of `HEAD` ran the new shim. All checks passed (exit `0`).

Files of the adoption:

- Added: `controls.toml`, `scripts/controls-requirements.txt`, `docs/controls-adoption.md`, `docs/controls-audit.json`.
- Changed: `scripts/check_context.py` (now a shim), `.github/workflows/context.yml` (new `controls` job), `AGENTS.md`, `Dockerfile`, `docs/README.md`, `scripts/AGENTS.md`.
- Kept: the old check scripts, `scripts/test_docker.sh`, the `check` CI job and the demo check `tests/check_demo_weather.py`.

Steps to roll back:

1. Create a new branch.
2. Option A, change the pin: edit `scripts/controls-requirements.txt`. Put the other commit in the install line.
3. Option B, remove the adoption: run `git revert` on the adoption commits. Or restore the changed files from the base commit with `git checkout <base> -- <file>`, and delete the added files.
4. Run `python3 scripts/check_context.py`. The first run for a new pin needs the network.
5. The cache under `$XDG_CACHE_HOME/deterministic-controls/<commit>/` is safe to delete.

## Receipt

Date of the run (UTC): 2026-11-24. The command ran in a clean clone of `HEAD`:

`python3 -m deterministic_controls adopt receipt --root <clean clone> --commit 3a2e9f3d95136958c54f73c831e84b971fc9a054`

`repository` is the name of the temporary clone, not the name of this repository. `enforcement_state` is `advisory`. The `files_added` and `files_changed` lists are empty because the clone had no pending change. See the lists above for the files of the adoption.

```json
{
  "base_revision": "919302035f1be0963e00552cfbf24db9de0eb784",
  "checks_run": [
    {"check_id": "context.index-freshness", "status": "passed"},
    {"check_id": "markdown.local-links", "status": "passed"},
    {"check_id": "plans.graph", "status": "passed"},
    {"check_id": "plans.schema", "status": "passed"},
    {"check_id": "repo.forbidden-artifacts", "status": "passed"},
    {"check_id": "security.personal-data", "status": "passed"},
    {"check_id": "security.secrets", "status": "passed"}
  ],
  "commands_kept": [
    "scripts/build_context_indexes.py",
    "scripts/build_indexes.py",
    "scripts/check_links.py",
    "scripts/check_plan.py",
    "scripts/ctx_common.py",
    "scripts/scan_context_secrets.py",
    "scripts/scan_secrets.py",
    "scripts/test_docker.sh",
    "test: python3 -m unittest discover -s tests",
    "test: docker build (Dockerfile)",
    "ci-job: check"
  ],
  "control_pin": "3a2e9f3d95136958c54f73c831e84b971fc9a054",
  "date": "2026-11-24",
  "enabled_checks": [
    "context.index-freshness",
    "markdown.local-links",
    "plans.graph",
    "plans.schema",
    "repo.forbidden-artifacts",
    "security.personal-data",
    "security.secrets"
  ],
  "enforcement_state": "advisory",
  "files_added": [],
  "files_changed": [],
  "profile": "ci",
  "repository": "copy",
  "rollback": [
    "To restore the previous pin: edit scripts/controls-requirements.txt, put the previous commit in the install line, and run scripts/check_context.py once to build its environment.",
    "To remove the adoption: run 'git revert' on the adoption commit, or restore these files from the base revision 919302035f1be0963e00552cfbf24db9de0eb784 with 'git checkout 919302035f1be0963e00552cfbf24db9de0eb784 -- <file>' and delete the files that were added: scripts/check_context.py, scripts/controls-requirements.txt, controls.toml, scripts/secret_guard.py, scripts/install_hooks.sh, .github/workflows/context.yml.",
    "The cached environment is in the user cache directory under deterministic-controls/<commit>/. It is safe to delete."
  ],
  "schema_version": 1
}
```

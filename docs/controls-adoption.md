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
- **Files outside the step scope.** `adopt apply` wrote none.
- **Existing jobs.** `adopt apply` kept the `check` job. The new `controls` job repeats the secret guard steps. That is accepted for now.

- **Stricter index check.** The library reports that `memory/README.md` has no `gist` and `scripts/README.md` has no `Run me when:` line. The old `build_indexes.py --check` did not report this. Both files were outside the scope of the adoption step. The fix is open.

## Secret guard exceptions

none

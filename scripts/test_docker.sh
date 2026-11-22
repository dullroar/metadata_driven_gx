#!/usr/bin/env bash
# Run me when: I need to build the image and test the demo pipeline in Docker.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

run_dir=$(mktemp -d "${TMPDIR:-/tmp}/metadata-driven-gx.XXXXXXXXXX")
run_name=${run_dir##*/}
image="metadata-driven-gx:${run_name#metadata-driven-gx.}"
cleanup() {
    docker image rm "$image" >/dev/null 2>&1 || true
    rmdir -- "$run_dir"
}
trap cleanup EXIT

# Copy current file contents, including local edits, without host Git data or
# untracked files. Context checks can scan the complete source snapshot.
git ls-files --cached -z \
    | tar --create --file=- --null --files-from=- \
    | docker build --tag "$image" -

docker run --rm --name "$run_name" --network none "$image" \
    bash -c 'python3 scripts/check_context.py && python tests/check_demo_weather.py'

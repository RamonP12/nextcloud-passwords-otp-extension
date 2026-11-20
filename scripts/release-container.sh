#!/usr/bin/env bash
set -euo pipefail

if [[ ${1:-} == --help || $# -gt 2 ]]; then
    printf 'Usage: bash scripts/release-container.sh [git-ref [new-output-directory]]\n'
    if [[ $# -gt 2 ]]; then exit 2; fi
    exit 0
fi

repo=$(git -C "$(dirname -- "${BASH_SOURCE[0]}")/.." rev-parse --show-toplevel)
commit=$(git -C "$repo" rev-parse --verify --end-of-options "${1:-HEAD}^{commit}")
output=${2:-"$repo/.build/reproducible/$commit"}

output_parent=$(dirname -- "$output")
mkdir -p -- "$output_parent"
output_parent=$(cd -- "$output_parent" && pwd -P)
output="$output_parent/$(basename -- "$output")"
if [[ -e $output || -L $output ]]; then
    printf 'Output already exists: %s\n' "$output" >&2
    exit 1
fi

stage=$(mktemp -d "$output_parent/.otp-release.XXXXXXXX")
trap 'rm -rf -- "$stage"' EXIT

# Give the container the exact tracked source and its commit identity. A
# separate clone also works when the caller is in a linked Git worktree.
git init --quiet --bare "$stage/source.git"
git -C "$stage/source.git" fetch --quiet --no-tags "$repo" "$commit:refs/heads/source"
mkdir -- "$stage/output"

docker build --platform linux/amd64 --iidfile "$stage/image-id" "$repo/scripts/release-container"
docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" \
    --mount "type=bind,source=$stage/source.git,target=/input,readonly" \
    --mount "type=bind,source=$stage/output,target=/output" \
    --env GIT_CONFIG_GLOBAL=/dev/null \
    --env npm_config_cache=/tmp/otp-npm-cache \
    "$(cat "$stage/image-id")" sh -eu -c '
        git clone --quiet --no-local --single-branch --branch source /input /tmp/otp-source
        cd /tmp/otp-source
        test "$(git rev-parse HEAD)" = "$1"
        npm ci --include=dev --include=optional --no-audit --no-fund
        npm run build
        python3 scripts/release.py /output/package
    ' sh "$commit"

# Both paths are on the same filesystem. Refuse to replace an output from a
# concurrent run, including on coreutils versions that return 0 for a skip.
mv -T --no-clobber -- "$stage/output/package" "$output"
if [[ -e $stage/output/package ]]; then
    printf 'Output was created by another process: %s\n' "$output" >&2
    exit 1
fi
printf 'REPRODUCIBLE_PACKAGE_PASS source=%s output=%s\n' "$commit" "$output"

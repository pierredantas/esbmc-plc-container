#!/usr/bin/env bash
# Rebuild the GitHub-mined LD corpus and rerun its translation validation.
# Needs an authenticated `gh` (fetch.py reads blobs through the GitHub API) and an ESBMC built at
# fork commit 1d7ad4332b: docker build --build-arg ESBMC_COMMIT=1d7ad4332b60a32d69354af2abc1b4af50ee253e .
# Usage: reproduce.sh ESBMC [OUT]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ESBMC=$1; OUT=${2:-$HERE/out}
mkdir -p "$OUT/raw"
python3 -I "$HERE/scripts/fetch.py" "$HERE/results/hits.json" "$OUT/raw" "$OUT/manifest.json"
python3 -I "$HERE/scripts/dedup.py" "$OUT/manifest.json" "$OUT/raw" "$OUT/programs.json"
python3 -I "$HERE/scripts/tp_run.py" --esbmc "$ESBMC" --programs "$OUT/programs.json" --raw "$OUT/raw" --out "$OUT/run"

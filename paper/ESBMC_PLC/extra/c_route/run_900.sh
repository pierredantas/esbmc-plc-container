#!/usr/bin/env bash
# RQ3, tuning the C route: ESBMC k-induction on MATIEC's C at 900 s, on the variants the 120 s run did not prove.
#   ESBMC=... SUITE=... extra/c_route/run_900.sh ROUTES_DIR OUT_DIR [JOBS]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
ROUTES=$1; OUT=$2; JOBS=${3:-6}
: "${ESBMC:?set ESBMC}" "${SUITE:?set SUITE}"
mkdir -p "$OUT"
python3 "$HERE/names_from_routes.py" "$ROUTES" > "$OUT/names.txt"
python3 "$ROOT/run/viac_uniform.py" --esbmc "$ESBMC" --suite "$SUITE" --names "$OUT/names.txt" --out "$OUT" \
  --timeout 900 --jobs "$JOBS" --jsonl viac900.jsonl > "$OUT/viac900.log" 2>&1

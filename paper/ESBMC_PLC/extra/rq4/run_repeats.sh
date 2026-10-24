#!/usr/bin/env bash
# RQ4 repetitions: the scaling experiments s4, s2, s3, s1 of ws2/l1/scale_l1.py, REPS times, one ESBMC at a time.
#   ESBMC=... extra/rq4/run_repeats.sh OUT_DIR [REPS]
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
OUT=$1; REPS=${2:-5}; : "${ESBMC:?set ESBMC}"
mkdir -p "$OUT"
for r in $(seq 1 "$REPS"); do
  for spec in "s4 300" "s2 300" "s3 600" "s1 300"; do
    set -- $spec
    python3 "$ROOT/ws2/l1/scale_l1.py" "$OUT/rep$r" "$ESBMC" "$1" "$2" > "$OUT/rep${r}_$1.log" 2>&1
  done
done
python3 "$HERE/summary.py" "$OUT" > "$OUT/summary.txt"

#!/usr/bin/env bash
# Rerun every experiment behind the TOSEM paper's numbers inside the image.
#   docker run --rm -v "$PWD/out:/out" <image> reproduce-paper [OUT]
# Writes OUT/paper (the paper run: suite records, translation validation, vacuity, input
# tiers, timer experiments) and OUT/referee (uniform k-induction and the MATIEC C route).
# A full run takes several hours on 8 cores; the C route alone is about one hour.
set -uo pipefail
OUT=${1:-/out}
ROOT=/opt/paper/ESBMC_PLC
export ESBMC=${ESBMC:-/opt/esbmc/build/src/esbmc/esbmc}
export SUITE=${SUITE:-/opt/suite}
export MATIEC=${MATIEC:-/opt/plc-tools/matiec}
export PLC_TOOLS=${PLC_TOOLS:-/opt/plc-tools}
JOBS=${JOBS:-$(nproc)}
mkdir -p "$OUT/referee"

JOBS=$JOBS "$ROOT/run/paper_run.sh" "$OUT/paper"
python3 "$ROOT/run/summarize_suite.py" "$OUT/paper" "$SUITE" > "$OUT/paper/suite_tables.txt"

python3 -c "import json,sys; print('\n'.join(r['record'] for r in json.load(open(sys.argv[1]))))" \
  "$OUT/paper/suite_summary.json" > "$OUT/referee/names.txt"
python3 "$ROOT/run/uniform_ld.py" --esbmc "$ESBMC" --suite "$SUITE" --out "$OUT/referee/uniform_ld" \
  --timeout 120 --jobs "$JOBS" > "$OUT/referee/uniform_ld.log" 2>&1
python3 "$ROOT/run/viac_uniform.py" --esbmc "$ESBMC" --suite "$SUITE" --names "$OUT/referee/names.txt" \
  --out "$OUT/referee/viac" --timeout 120 --jobs "$JOBS" > "$OUT/referee/viac.log" 2>&1
echo "done; compare with the archived results as listed in /opt/paper/CLAIMS.md"

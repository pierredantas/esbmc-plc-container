#!/usr/bin/env bash
# The single evaluation run of PLAN_SHORT.md, week 1: every number in the paper comes from here.
# Usage: run/paper_run.sh [OUT]   (default: results/paper-pin-2026-10-13)
set -uo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd)
ESBMC=${ESBMC:-$HOME/Claude/esbmc-pin/build/src/esbmc/esbmc}
SUITE=${SUITE:-$HOME/Claude/suite-paper-run}
MATIEC=${MATIEC:-$HOME/Claude/5_ESBMC-PLC Toolkit/ESBMC-Arduino Research/ACM/experiments/tools/matiec}
OUT=${1:-$HERE/results/paper-pin-2026-10-13}
JOBS=${JOBS:-6}
mkdir -p "$OUT/logs"

step() {
  local name=$1; shift
  local t0=$(date +%s)
  echo "== $name ($(date '+%H:%M:%S'))"
  "$@" > "$OUT/logs/$name.log" 2>&1
  local rc=$?
  echo "   $name: exit $rc, $(( $(date +%s) - t0 )) s"
}

{
  echo "date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "esbmc: $ESBMC"
  "$ESBMC" --version 2>&1 | head -1
  echo "esbmc commit: $(git -C "$(dirname "$ESBMC")/../../.." rev-parse HEAD)"
  echo "suite commit: $(git -C "$SUITE" rev-parse HEAD)"
  echo "machine: $(sysctl -n machdep.cpu.brand_string) / $(sysctl -n hw.ncpu) cores / $(sw_vers -productVersion) build $(sw_vers -buildVersion)"
} > "$OUT/PROVENANCE.txt"

W1="$HERE/ws1"; L1="$HERE/ws2/l1"
step suite_records  python3 "$SUITE/runner/record_all.py" --tool "paper-pin=$ESBMC" --timeout 120
cp -R "$SUITE/results/records" "$OUT/suite_records" 2>/dev/null
step tv             python3 "$W1/tv_corpus.py" --esbmc "$ESBMC" --suite "$SUITE" --out "$OUT/tv" --jobs "$JOBS"
step tv_control     python3 "$W1/tv_corpus.py" --esbmc "$ESBMC" --suite "$SUITE" --out "$OUT/tv_control" --jobs "$JOBS" --control
step vacuity        python3 "$W1/vacuity.py" --esbmc "$ESBMC" --suite "$SUITE" --out "$OUT/vacuity" --jobs "$JOBS"
step io_tiers       python3 "$W1/io_tiers.py" --esbmc "$ESBMC" --suite "$SUITE" --out "$OUT/io_tiers.json" --jobs "$JOBS"
step l1_gen         python3 "$L1/gen_l1.py" "$OUT/l1_cases"
step l1_tool        python3 "$L1/run_l1.py" "$OUT/l1_cases" "$ESBMC"
step l1_oracle_a    python3 "$L1/oracle_a.py" "$OUT/l1_cases" "$MATIEC" 200
step counters       python3 "$L1/counters.py" "$OUT/counters" "$ESBMC" "$MATIEC"
step neg_controls   python3 "$L1/neg_controls.py" "$OUT/neg_controls" "$ESBMC" "$MATIEC"
step stairs_s0      python3 "$L1/s0.py" "$OUT/s0" "$ESBMC"
step scale_s4       python3 "$L1/scale_l1.py" "$OUT/scale" "$ESBMC" s4 300
step scale_s2       python3 "$L1/scale_l1.py" "$OUT/scale" "$ESBMC" s2 300
step scale_s3       python3 "$L1/scale_l1.py" "$OUT/scale" "$ESBMC" s3 600
step scale_s1       python3 "$L1/scale_l1.py" "$OUT/scale" "$ESBMC" s1 300
echo "done $(date '+%H:%M:%S')"

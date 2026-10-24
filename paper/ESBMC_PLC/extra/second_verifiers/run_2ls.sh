#!/usr/bin/env bash
# Appendix E, second C verifiers: 2LS k-induction on exported harnesses (harness.i), 120 s by watchdog.
#   TWOLS=<2ls binary> extra/second_verifiers/run_2ls.sh HARNESS_DIR OUT_DIR
# HARNESS_DIR is the harnesses/ folder of extra/c_route/viac_export.py: run it on the names of
# extra/c_route/names_from_routes.py for the SAFE check, and on the LD-route VIOLATION variants for the soundness
# check. 2LS has no time limit of its own.
set -uo pipefail
H=$1; OUT=$2; : "${TWOLS:?set TWOLS}"
export TWOLS OUT LIMIT=${LIMIT:-120}
mkdir -p "$OUT/logs"
one() {
  local d=$1 n t0 pid dog r
  n=$(basename "$d"); t0=$(date +%s); rm -f "$OUT/logs/$n.killed"
  "$TWOLS" "$d/harness.i" --k-induction > "$OUT/logs/$n.log" 2>&1 & pid=$!
  ( sleep "$LIMIT"; kill -9 $pid 2>/dev/null && touch "$OUT/logs/$n.killed" ) > /dev/null 2>&1 & dog=$!
  wait $pid; pkill -P $dog 2>/dev/null; kill $dog 2>/dev/null; wait $dog 2>/dev/null
  if [ -f "$OUT/logs/$n.killed" ]; then r="timeout"
  elif grep -q "Invariant check failed" "$OUT/logs/$n.log"; then r="2LS crash: $(grep -m1 '^Condition:' "$OUT/logs/$n.log")"
  else r=$(grep -oE "VERIFICATION (SUCCESSFUL|FAILED|INCONCLUSIVE)" "$OUT/logs/$n.log" | tail -1); [ -z "$r" ] && r="no verdict"; fi
  printf '%s\t%s s\t%s\n' "$n" "$(( $(date +%s) - t0 ))" "$r"
}
export -f one
ls -d "$H"/*/ | xargs -P "${JOBS:-6}" -I{} bash -c 'one "$1"' _ {} > "$OUT/results.tsv"

#!/usr/bin/env bash
# RQ3, tuning the C route: ESBMC k-induction at 120 s on MATIEC's C with facts about MATIEC's records.
#   ESBMC=... SUITE=... PLC_TOOLS=... extra/c_route/run_facts.sh NAMES OUT_DIR [JOBS]
# Per variant: the force-flag facts first (harness_inv.c); if not proved, the counter facts (harness_inv_counters.c)
# and the timer and counter facts (harness_inv_timers_counters.c). Each fact is assumed at the head of the scan loop
# and asserted at its end. A watchdog kills ESBMC 30 s after its own limit, which it does not always honour.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
NAMES=$1; OUT=$2; JOBS=${3:-6}
: "${ESBMC:?set ESBMC}" "${SUITE:?set SUITE}"
export ESBMC LIMIT=${LIMIT:-120} L="${PLC_TOOLS:-$HOME/plc-tools}/matiec/lib/C"
mkdir -p "$OUT"
python3 "$HERE/viac_export.py" --suite "$SUITE" --names "$NAMES" --out "$OUT/harnesses" --jobs "$JOBS" > "$OUT/export.log" 2>&1
for d in "$OUT"/harnesses/*/; do
  [ -f "$d/harness.c" ] || continue
  python3 "$HERE/viac_invariants.py" "$d" > /dev/null
  python3 "$HERE/viac_invariants.py" "$d" --counters > /dev/null
  python3 "$HERE/viac_invariants.py" "$d" --timers --counters > /dev/null
done
one() {
  local d=$1 f r pid dog
  for f in harness_inv.c harness_inv_counters.c harness_inv_timers_counters.c; do
    r=$(cd "$d" && { rm -f "killed_$f"
          "$ESBMC" "$f" -I "$L" -I . --k-induction --timeout "${LIMIT}s" > "esbmc_$f.log" 2>&1 & pid=$!
          ( sleep $((LIMIT + 30)); kill -9 $pid 2>/dev/null && touch "killed_$f" ) > /dev/null 2>&1 & dog=$!
          wait $pid; pkill -P $dog 2>/dev/null; kill $dog 2>/dev/null; wait $dog 2>/dev/null
          [ -f "killed_$f" ] && echo "Timed out (external limit)" >> "esbmc_$f.log"
          grep -E "VERIFICATION|Timed out|ERROR|inductive step \(k = [0-9]+\)" "esbmc_$f.log" | tail -2 | tr '\n' ' '; })
    printf '%s\t%s\t%s\n' "$(basename "$d")" "$f" "$r"
    [[ $r == *SUCCESSFUL* ]] && return
  done
}
export -f one
ls -d "$OUT"/harnesses/*/ | xargs -P "$JOBS" -I{} bash -c 'one "$1"' _ {} > "$OUT/results.tsv"

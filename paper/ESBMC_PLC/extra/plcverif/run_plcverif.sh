#!/usr/bin/env bash
# RQ3, an independent PLC verifier: PLCverif with NuSMV on the LD variants within Theorem 1's scope.
#   SUITE=... PLCVERIF=<CLI dir> NUSMV=<NuSMV binary> JAVA=<java 25+> BUILTIN=<builtin.scl> \
#     extra/plcverif/run_plcverif.sh ROUTES_DIR OUT_DIR
# Per variant: Beremiz ST -> SCL with the properties as assertions (results.tsv), then the `reachable` properties as
# witness runs (witness.tsv, VIOLATED = the required state is reachable). summarize.py combines both.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROUTES=$1; OUT=$2
: "${SUITE:?set SUITE}" "${PLCVERIF:?set PLCVERIF}" "${NUSMV:?set NUSMV}" "${JAVA:?set JAVA}" "${BUILTIN:?set BUILTIN}"
LAUNCHER=$(ls "$PLCVERIF"/plugins/org.eclipse.equinox.launcher_*.jar | head -1)
mkdir -p "$OUT/scl" "$OUT/logs" "$OUT/out"
python3 "$HERE/select_variants.py" "$ROUTES" > "$OUT/names.txt"
python3 "$HERE/../c_route/viac_export.py" --suite "$SUITE" --names "$OUT/names.txt" --out "$OUT/harnesses" --jobs 6 \
  > "$OUT/export.log" 2>&1
pv() {  # pv ID SCL ENTRY LOG
  (cd "$PLCVERIF" && "$JAVA" -Xss5m -Dlog4j2.statusLoggerLevel=OFF --enable-native-access=ALL-UNNAMED -jar "$LAUNCHER" \
    -id="$1" -job=verif -lf=step7 -sourcefiles.0="$2" -sourcefiles.1="$BUILTIN" -sourcefiles.2="$HERE/iec_blocks.scl" \
    -lf.entry="$3" -job.backend=nusmv -job.backend.binary_path="$NUSMV" -job.backend.timeout=120 -job.req=assertion \
    -job.reporters.0=plaintext -output="$OUT/out/$1") > "$4" 2>&1
  grep -m1 -oE 'Result: the requirement is [A-Z]+' "$4" | awk '{print $NF}'
}
: > "$OUT/results.tsv"; : > "$OUT/witness.tsv"
for n in $(cat "$OUT/names.txt"); do
  h="$OUT/harnesses/$n/harness.c"
  if [ ! -f "$h" ] || ! entry=$(python3 "$HERE/st_to_scl.py" "$SUITE" "$n" "$OUT/scl/$n.scl" "$h" 2>"$OUT/logs/$n.convert.err"); then
    printf '%s\t-\tnot converted\n' "$n" >> "$OUT/results.tsv"; continue
  fi
  t0=$(date +%s); r=$(pv "$n" "$OUT/scl/$n.scl" "$entry" "$OUT/logs/$n.log")
  printf '%s\t%s s\t%s\n' "$n" "$(( $(date +%s) - t0 ))" "${r:-ERROR}" >> "$OUT/results.tsv"
  if entry=$(python3 "$HERE/st_to_scl.py" "$SUITE" "$n" "$OUT/scl/$n.witness.scl" "$h" --witness 2>/dev/null); then
    r=$(pv "w_$n" "$OUT/scl/$n.witness.scl" "$entry" "$OUT/logs/$n.witness.log")
    printf '%s\t%s\n' "$n" "${r:-ERROR}" >> "$OUT/witness.tsv"
  fi
done
python3 "$HERE/summarize.py" "$ROUTES" "$OUT" | tee "$OUT/summary.txt"

#!/usr/bin/env bash
# Check iec_blocks.scl: each block meets one property (*_ok, expect SATISFIED) and breaks one (*_bad, expect VIOLATED).
#   PLCVERIF=... NUSMV=... JAVA=... extra/plcverif/run_blocktests.sh OUT_DIR
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); OUT=$1
: "${PLCVERIF:?set PLCVERIF}" "${NUSMV:?set NUSMV}" "${JAVA:?set JAVA}"
LAUNCHER=$(ls "$PLCVERIF"/plugins/org.eclipse.equinox.launcher_*.jar | head -1)
mkdir -p "$OUT"
for b in RT FT CU CD; do
  for k in ok bad; do
    (cd "$PLCVERIF" && "$JAVA" -Xss5m -Dlog4j2.statusLoggerLevel=OFF --enable-native-access=ALL-UNNAMED -jar "$LAUNCHER" \
      -id="${b}_$k" -job=verif -lf=step7 -sourcefiles.0="$HERE/blocktests/${b}_$k.scl" -sourcefiles.1="$HERE/iec_blocks.scl" \
      -lf.entry="${b}_TEST" -job.backend=nusmv -job.backend.binary_path="$NUSMV" -job.backend.timeout=120 \
      -job.req=assertion -job.reporters.0=plaintext -output="$OUT/out_${b}_$k") > "$OUT/${b}_$k.log" 2>&1
    r=$(grep -m1 -oE 'Result: the requirement is [A-Z]+' "$OUT/${b}_$k.log" | awk '{print $NF}')
    exp=$([ $k = ok ] && echo SATISFIED || echo VIOLATED)
    printf '%-3s %-4s expected %-9s got %s %s\n' $b $k $exp "${r:-ERROR}" "$([ "$r" = "$exp" ] && echo OK || echo MISMATCH)"
  done
done | tee "$OUT/results.txt"

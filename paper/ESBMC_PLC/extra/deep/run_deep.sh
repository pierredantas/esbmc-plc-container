#!/usr/bin/env bash
# RQ6: the delay-chain and dual-counter families with ESBMC-PLC and with PLCverif + NuSMV (Table 9).
#   ESBMC=... SUITE=... [PLCVERIF=... NUSMV=... JAVA=...] extra/deep/run_deep.sh OUT_DIR
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); OUT=$1
: "${ESBMC:?set ESBMC}" "${SUITE:?set SUITE}"
export SUITE
mkdir -p "$OUT"
python3 "$HERE/gen_dual_chain.py" "$OUT/benchmarks" 2 3 4 6 8 12 16 > /dev/null
python3 "$HERE/gen_dual_counter.py" "$OUT/benchmarks_counter" 2 4 8 16 24 > /dev/null
python3 "$HERE/run_esbmc_plc.py" "$OUT/benchmarks" "$ESBMC" "$OUT/esbmc_plc_dual_chain.jsonl" 300
python3 "$HERE/run_esbmc_plc.py" "$OUT/benchmarks_counter" "$ESBMC" "$OUT/pinned_dual_counter.jsonl" 300
python3 "$HERE/run_esbmc_plc.py" "$OUT/benchmarks_counter" "$ESBMC" "$OUT/fbinv_dual_counter.jsonl" 300 --ld-fb-invariants
# PLCverif needs Java 25+ and NuSMV, which the image does not carry (README, "Outside the image").
[ -n "${PLCVERIF:-}" ] || exit 0
: "${NUSMV:?set NUSMV}" "${JAVA:?set JAVA}"
python3 "$HERE/gen_scl.py" "$OUT/benchmarks" "$OUT/scl" > "$OUT/scl_chain.txt"
python3 "$HERE/gen_scl.py" "$OUT/benchmarks_counter" "$OUT/scl" > "$OUT/scl_counter.txt"
LAUNCHER=$(ls "$PLCVERIF"/plugins/org.eclipse.equinox.launcher_*.jar | head -1)
cat "$OUT/scl_chain.txt" "$OUT/scl_counter.txt" | while read -r family variant entry; do
  t0=$(date +%s); log="$OUT/scl/${family}__$variant.log"
  (cd "$PLCVERIF" && "$JAVA" -Xss5m -Dlog4j2.statusLoggerLevel=OFF --enable-native-access=ALL-UNNAMED -jar "$LAUNCHER" \
    -id="${family}_$variant" -job=verif -lf=step7 -sourcefiles.0="$OUT/scl/${family}__$variant.scl" \
    -sourcefiles.1="$HERE/../plcverif/iec_blocks.scl" -lf.entry="$entry" -job.backend=nusmv \
    -job.backend.binary_path="$NUSMV" -job.backend.timeout=300 -job.req=assertion -job.reporters.0=plaintext \
    -output="$OUT/scl/out_${family}_$variant") > "$log" 2>&1
  printf '%s\t%s\t%s\t%s s\n' "$family" "$variant" \
    "$(grep -m1 -oE 'Result: the requirement is [A-Z]+' "$log" | awk '{print $NF}')" "$(( $(date +%s) - t0 ))"
done > "$OUT/plcverif_results.tsv"

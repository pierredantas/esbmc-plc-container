#!/usr/bin/env bash
# Validate the image: the LD unit and regression tests, the twelve WS0
# reproducers, and one program through each route of the benchmark suite.
set -uo pipefail
fail=0
step() { printf '== %s\n' "$1"; }

step "versions"
esbmc --version | head -1
for d in /opt/esbmc /opt/suite /opt/plc-tools/beremiz /opt/plc-tools/matiec; do
  printf '  %-24s %s\n' "$(basename "$d")" "$(git -C "$d" rev-parse HEAD)"
done

step "LD unit tests"
for t in ld_parser_test ld_property_test ld_ir_gen_test; do
  /opt/esbmc/build/unit/ld-frontend/$t >/dev/null || { echo "  FAIL $t"; fail=1; }
done

step "regression/ld and ld-verify"
ctest --test-dir /opt/esbmc/build -j"$(nproc)" --timeout 300 \
  -L '^ld/$|^ld-verify$' | grep -E 'tests passed|\*\*\*' || fail=1

step "WS0 reproducers"
out=$(mktemp -d)
(cd /opt/ws0 && ./run_repro.sh "$out") >/dev/null 2>&1
if awk 'NR>1 && $NF!="yes"{bad=1} END{exit bad}' "$out/summary.tsv"; then
  echo "  $(($(wc -l <"$out/summary.tsv") - 1)) of 12 match"
else
  cat "$out/summary.tsv"; fail=1
fi

step "benchmark suite: one program through both routes"
# g_building_lighting/clean is SAFE by its label, and both routes agreed on it.
prog=benchmarks/building_automation/g_building_lighting/clean.xml
props=benchmarks/building_automation/g_building_lighting/props.yaml
cp "/opt/suite/$prog" "$out/clean.ld"
ld=$(cd /opt/suite && python3 runner/record.py --source "$prog" --tool ws0="$ESBMC" \
  "$out/clean.ld" "$props" true -o "$out/ld.json" 2>&1)
viac=$(cd /opt/suite && python3 runner/record_via_c.py --tool ws0="$ESBMC" \
  "$prog" "$props" true -o "$out/viac.json" 2>&1)
for r in "LD route:$ld" "via-C route:$viac"; do
  case "$r" in
  *ws0:SAFE*) echo "  ${r%%:*}: SAFE" ;;
  *) echo "  FAIL ${r%%:*}: ${r#*:}" | tail -3; fail=1 ;;
  esac
done

[ $fail = 0 ] && echo "image OK" || { echo "image FAILED"; exit 1; }

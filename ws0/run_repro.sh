#!/usr/bin/env bash
# Run each WS0 reproducer and compare the verdict with the expected one.
# Usage: ESBMC=/path/to/esbmc ./run_repro.sh [out_dir]
#
# A SAFE or VIOLATION verdict counts only if every identifier in the property file
# is assigned inside the scan loop; otherwise the run is reported VACUOUS, because a
# property over a never-assigned variable is checked against its zero initializer.
set -u
cd "$(dirname "$0")"
SUITE=${SUITE:-"$(cd ../../ESBMC-Benchmark-Suite && pwd)"}
ESBMC=${ESBMC:-$HOME/Claude/esbmc/build/src/esbmc/esbmc}
OUT=${1:-results/$(git -C "$(dirname "$ESBMC")" rev-parse --short HEAD 2>/dev/null || echo unknown)}
mkdir -p "$OUT"
printf 'id\tdefect\texpected\tobserved\tmatch\n' > "$OUT/summary.tsv"

unassigned_props() { # $1 props.yaml, $2 goto dump
  python3 - "$1" "$2" <<'EOF'
import re, sys, yaml
props = yaml.safe_load(open(sys.argv[1]))["properties"]
goto = open(sys.argv[2]).read()
body = goto[goto.find("scan_loop"):]
ids = set()
for p in props:
    ids.update(p.get("variables", []))
    for key in ("expression", "trigger", "response"):
        ids.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(p.get(key, ""))))
ids -= {"true", "false", "TRUE", "FALSE"}
missing = sorted(i for i in ids if not re.search(rf"ASSIGN {re.escape(i)}\s*=", body))
print(" ".join(missing))
EOF
}

while IFS=$'\t' read -r id defect prog props expected _src; do
  [[ $id == \#* || -z $id ]] && continue
  # The front end reads PLCopen XML only, selected by the .ld extension; the suite's
  # plain-text rung DSL goes through its own converter first.
  if [[ $(head -c 5 "$prog") != "<?xml" ]]; then
    (cd "$SUITE" && python3 -m tools.ld_text_to_xml "$OLDPWD/$prog") > "$OUT/$id.ld"
    prog="$OUT/$id.ld"
  fi
  "$ESBMC" "$prog" --goto-functions-only > "$OUT/$id.goto.txt" 2>&1
  if [[ $expected == VIOLATION ]]; then mode=(--incremental-bmc)
  else mode=(--k-induction --unlimited-k-steps); fi
  "$ESBMC" "$prog" --ld-props "$props" "${mode[@]}" --timeout 300s > "$OUT/$id.log" 2>&1
  if grep -q '^VERIFICATION SUCCESSFUL' "$OUT/$id.log"; then obs=SAFE
  elif grep -q '^VERIFICATION FAILED' "$OUT/$id.log"; then obs=VIOLATION
  elif grep -q 'ERROR' "$OUT/$id.log"; then obs=ERROR
  else obs=UNKNOWN; fi
  if [[ $obs == SAFE || $obs == VIOLATION ]]; then
    missing=$(unassigned_props "$props" "$OUT/$id.goto.txt")
    [[ -n $missing ]] && obs="VACUOUS($missing)"
  fi
  [[ $obs == "$expected" ]] && m=yes || m=NO
  printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$defect" "$expected" "$obs" "$m" | tee -a "$OUT/summary.tsv"
done < cases.tsv

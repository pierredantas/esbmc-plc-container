#!/usr/bin/env bash
# Rerun the remaining ESBMC experiments of the paper, inside the image, after reproduce-paper.
#   docker run --rm -v "$PWD/out:/out" <image> reproduce-extra [OUT]
# Needs OUT/routes from reproduce-paper. Writes OUT/viac-900 (RQ3, about 4.5 h on 6 jobs), OUT/viac-facts (RQ3),
# OUT/deep (RQ6, ESBMC-PLC part), and OUT/rq4-repeats (RQ4, about 3.5 h). PLCverif, NuSMV, and 2LS run outside the
# image (README).
set -uo pipefail
OUT=${1:-/out}
REV=/opt/paper/ESBMC_PLC/extra
export ESBMC=${ESBMC:-/opt/esbmc/build/src/esbmc/esbmc} SUITE=${SUITE:-/opt/suite} PLC_TOOLS=${PLC_TOOLS:-/opt/plc-tools}
JOBS=${JOBS:-6}
[ -d "$OUT/routes/viac" ] || { echo "run reproduce-paper first"; exit 1; }
"$REV/c_route/run_900.sh" "$OUT/routes" "$OUT/viac-900" "$JOBS"
python3 "$REV/c_route/names_from_routes.py" "$OUT/routes" > "$OUT/facts-names.txt"
"$REV/c_route/run_facts.sh" "$OUT/facts-names.txt" "$OUT/viac-facts" "$JOBS"
"$REV/deep/run_deep.sh" "$OUT/deep"
"$REV/rq4/run_repeats.sh" "$OUT/rq4-repeats" 5
echo "done; compare with the archived results as listed in /opt/paper/CLAIMS.md"

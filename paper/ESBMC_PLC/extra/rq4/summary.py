"""Median, IQR, and verdict agreement per RQ4 case across repetitions: rq4_summary.py OUT_DIR"""
import json, pathlib, statistics, sys
from collections import defaultdict
KEYS = ("exp", "kind", "pt", "range", "side", "invariants", "m", "claim")
cases = defaultdict(list)
for f in sorted(pathlib.Path(sys.argv[1]).glob("rep*/s*.json")):
    for row in json.loads(f.read_text()):
        cases[tuple((k, row.get(k)) for k in KEYS if k in row)].append(row)
def quart(xs):
    q = statistics.quantiles(xs, n=4, method="inclusive") if len(xs) > 1 else [xs[0]] * 3
    return q[0], statistics.median(xs), q[2]
split = 0
for key, rows in sorted(cases.items(), key=str):
    verdicts = {r["verdict"] for r in rows}
    split += len(verdicts) > 1
    lo, med, hi = quart([r["sec"] for r in rows])
    print(f"{dict(key)}  n={len(rows)}  verdicts={sorted(verdicts)}  k={sorted({r['k'] for r in rows}, key=str)}  "
          f"sec median {med:.2f} IQR {lo:.2f}-{hi:.2f}")
print(f"cases {len(cases)}, with differing verdicts across reps: {split}")

#!/usr/bin/env python3
"""Combine PLCverif's assertion and witness runs and compare with the labels and ESBMC-PLC (Table 8):
summarize.py ROUTES_DIR OUT_DIR

A variant is SAFE for PLCverif when its assertions hold and every required witness is reachable (VIOLATED).
"""
import collections
import json
import pathlib
import sys

routes, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
recs = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in (routes / "uniform_ld/records").glob("*.json")}
witness = dict(l.split("\t") for l in (out / "witness.tsv").read_text(encoding="utf-8").splitlines() if l)
counts, disagree, excluded = collections.Counter(), [], []
for line in (out / "results.tsv").read_text(encoding="utf-8").splitlines():
    name, _, result = line.split("\t")
    if result not in ("SATISFIED", "VIOLATED"):
        excluded.append((name, result))
        continue
    verdict = "VIOLATION" if result == "VIOLATED" or witness.get(name) == "SATISFIED" else "SAFE"
    expected, ld = recs[name]["expected_verdict"], recs[name]["runs"]["uniform"]["verdict"]
    counts[(expected, verdict)] += 1
    if verdict != expected or verdict != ld:
        disagree.append((name, expected, ld, verdict))
print("expected -> PLCverif:", dict(counts))
print("disagreements with the label or ESBMC-PLC:", disagree)
print("not checked:", excluded)

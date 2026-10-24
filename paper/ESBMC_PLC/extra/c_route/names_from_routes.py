#!/usr/bin/env python3
"""List the variants the LD route proves SAFE and the C route does not: names_from_routes.py ROUTES_DIR > names.txt

ROUTES_DIR is the routes/ folder that reproduce.sh writes (uniform_ld/records/ and viac/viac.jsonl). These are the
variants of the tuned C-route runs: the 900 s limit and the MATIEC facts.
"""
import json
import pathlib
import sys

routes = pathlib.Path(sys.argv[1])
ld = {f.stem: json.loads(f.read_text(encoding="utf-8"))["runs"]["uniform"]["verdict"]
      for f in (routes / "uniform_ld/records").glob("*.json")}
c = {r["name"]: r["verdict"] for r in map(json.loads, (routes / "viac/viac.jsonl").read_text(encoding="utf-8").splitlines())}
print("\n".join(sorted(n for n, v in ld.items() if v == "SAFE" and c.get(n) in ("timeout", "unknown"))))

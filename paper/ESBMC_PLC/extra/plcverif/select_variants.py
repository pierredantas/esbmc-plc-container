#!/usr/bin/env python3
"""List the LD variants within Theorem 1's scope: select_variants.py ROUTES_DIR > names.txt

Those the frontend accepts (uniform run status other than error) and that call no user function block.
"""
import json
import pathlib
import sys

records = pathlib.Path(sys.argv[1]) / "uniform_ld/records"
names = []
for f in sorted(records.glob("*.json")):
    r = json.loads(f.read_text(encoding="utf-8"))
    if r["runs"]["uniform"]["status"] != "error" and not r["user_function_blocks"]:
        names.append(f.stem)
print("\n".join(names))

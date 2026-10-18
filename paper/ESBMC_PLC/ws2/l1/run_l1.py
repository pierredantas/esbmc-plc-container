#!/usr/bin/env python3
"""Run ESBMC on every L1 case at the predicted worst case (must verify) and one below (must fail).

Usage: run_l1.py CASEDIR ESBMC
"""
import json, pathlib, re, subprocess, sys

def verdict(esbmc, case, props, info):
    cmd = [esbmc, "--ld-props", props, "--ld-cycle-time", f"{info['tmin']}:{info['tmax']}",
           "--unwind", str(info["unwind"]), "--no-unwinding-assertions", "prog.ld"]
    p = subprocess.run(cmd, cwd=case, capture_output=True, text=True)
    m = re.search(r"VERIFICATION (\w+)", p.stdout + p.stderr)
    return m.group(1) if m else "ERROR"

def main(root, esbmc):
    bad, rows = 0, []
    for case in sorted(pathlib.Path(root).iterdir()):
        info = json.loads((case / "case.json").read_text())
        got = {p: verdict(esbmc, case, p, info) for p in info["expect"]}
        ok = got == info["expect"]
        bad += not ok
        rows.append((info["id"], info["worst_ms"], info["scans_to_worst"], got["props_pass.yaml"], got["props_fail.yaml"], "ok" if ok else "MISMATCH"))
    print(f"{'case':26} {'worst':>6} {'scans':>5}  {'at worst':10} {'one below':10}")
    for r in rows:
        print(f"{r[0]:26} {r[1]:>6} {r[2]:>5}  {r[3]:10} {r[4]:10} {r[5]}")
    print(f"{len(rows) - bad} of {len(rows)} cases agree with the model")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

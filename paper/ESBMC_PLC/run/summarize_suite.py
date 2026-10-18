#!/usr/bin/env python3
"""Summarize the paper-pin suite records: outcome by program provenance, label status and scope, CPU time, refusals.

Scope separates programs inside Theorem 1's subset from those with a user function block (outside it, H6), and
`h1` is the overflow run a SAFE verdict now gets (no arithmetic / no overflow to depth 20 / overflow).

Usage: summarize_suite.py RESULTS_DIR SUITE_DIR   (writes RESULTS_DIR/suite_summary.json and prints tables)
"""
import collections, json, pathlib, re, statistics, sys, yaml

res, suite = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
rows = []
for f in sorted((res / "suite_records").glob("*.json")):
    d = json.loads(f.read_text())
    run = d.get("runs", {}).get("paper-pin")
    if not run:
        continue
    prog = pathlib.Path(d["program"])
    bdir = suite / "benchmarks" / prog.parts[-3] / prog.parts[-2]
    meta = yaml.safe_load((bdir / "benchmark.yml").read_text())
    origin = (meta.get("source") or {}).get("origin", "?")
    err = ""
    if run.get("status") == "error" or run.get("verdict") in (None, "error"):
        m = re.search(r"(UnsupportedConstruct\([^)]*\)|ERROR: [^\n]*)", json.dumps(run))
        err = m.group(1)[:90] if m else run.get("status", "")
    user_fb = d.get("user_function_blocks")
    if user_fb is None:  # records made before the runner wrote the field
        user_fb = 'pouType="functionBlock"' in (suite / d["program"].split("suite-paper-run/")[-1]).read_text()
    rows.append({"record": f.stem, "task": bdir.name, "origin": origin,
                 "scope": "user FB" if user_fb else "subset", "h1": (run.get("h1") or {}).get("verdict"),
                 "provenance": "authored" if origin == "authored" else "third-party",
                 "label": meta.get("validation_status", "?"), "expected": d.get("expected_verdict"),
                 "verdict": run.get("verdict"), "status": run.get("status"), "cpu_s": run.get("cpu_time_s"), "error": err})

def table(key):
    t = collections.Counter((r[key], r["status"]) for r in rows)
    keys = sorted({r[key] for r in rows}); sts = sorted({r["status"] for r in rows})
    print(f"\n{key:12} " + " ".join(f"{s:>10}" for s in sts) + "      all")
    for k in keys:
        print(f"{k:12} " + " ".join(f"{t[(k, s)]:>10}" for s in sts) + f" {sum(t[(k, s)] for s in sts):>8}")

print(f"variants: {len(rows)}; tasks: {len({r['task'] for r in rows})}")
table("provenance"); table("label"); table("scope")
print("\nh1 on SAFE verdicts:", dict(collections.Counter(r["h1"] for r in rows if r["verdict"] == "SAFE")))
print("\nverdicts:", dict(collections.Counter(r["verdict"] for r in rows)))
times = [r["cpu_s"] for r in rows if isinstance(r["cpu_s"], (int, float))]
q = statistics.quantiles(times, n=4)
print(f"cpu time (s): n={len(times)} median {statistics.median(times):.3f} IQR {q[0]:.3f}-{q[2]:.3f} max {max(times):.2f}")
print("\nnot correct:")
for r in rows:
    if r["status"] != "correct":
        print(f"  {r['record']:50} {r['provenance']:11} {r['label']:9} exp={r['expected']} got={r['verdict']} {r['error']}")
(res / "suite_summary.json").write_text(json.dumps(rows, indent=1) + "\n")

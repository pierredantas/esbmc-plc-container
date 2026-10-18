#!/usr/bin/env python3
"""Count the variables of each interface tier over the LD corpus (concern M28).

For every LD variant of the suite: read each declared variable's section and
address from the PLCopen XML (the textual dialect after the suite's converter),
and ask ESBMC which variables the scan loop reads freely (the assignments of
`nondet` at the top of `ld::scan_loop`, from --goto-functions-only). A variable
read freely is tier 1 when declared in `inputVars`, `inOutVars` or
`externalVars`, tier 2 when it has a `%I` or `%M` address, and tier 3
otherwise; a variable not read freely is program-owned (an output or internal
state). Usage: io_tiers.py --esbmc PATH [--suite DIR] [--out FILE] [--jobs N]
"""
import argparse
import collections
import concurrent.futures as cf
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

import xml.etree.ElementTree as ET

import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ESBMC-Benchmark-Suite" / "tools"))
from ld_text_to_xml import ParseError, translate  # noqa: E402

SUITE = HERE.parents[1] / "ESBMC-Benchmark-Suite"
SECTIONS = {"inputVars": "inputVars", "inOutVars": "inOutVars", "externalVars": "externalVars",
            "outputVars": "outputVars", "localVars": "localVars", "globalVars": "globalVars"}


def declared(xml_text):
    root = ET.fromstring(xml_text.encode("utf-8"))
    out = {}
    programs = [e for e in root.iter() if e.tag.split("}")[-1] == "pou" and e.get("pouType") == "program"]
    for pou in programs[:1]:
        for elem in pou.iter():
            tag = elem.tag.split("}")[-1]
            if tag in SECTIONS:
                for var in elem:
                    if var.tag.split("}")[-1] == "variable":
                        kind = next((c.tag.split("}")[-1] for t in var if t.tag.split("}")[-1] == "type" for c in t), "")
                        out[var.get("name")] = (tag, var.get("address", ""), kind)
    return out


def free_reads(esbmc, ld_path, props):
    env = {**os.environ, "LLVM_PROFILE_FILE": "/dev/null"}
    p = subprocess.run([esbmc, ld_path, "--ld-props", props, "--goto-functions-only"],
                       capture_output=True, text=True, env=env, timeout=120)
    out = p.stdout + p.stderr
    if "scan_loop" not in out:
        return None
    body = out.split("scan_loop (ld::scan_loop):", 1)[1]
    names = []
    for line in body.splitlines():
        m = re.match(r"\s+ASSIGN (\S+?)=NONDET", line)
        if m:
            names.append(m.group(1))
        elif re.match(r"\s+(ASSIGN|IF|GOTO|ASSERT|FUNCTION_CALL)", line) and "NONDET" not in line:
            if "IF !1 THEN" in line:
                continue
            break
    return set(names)


def one(job, esbmc):
    task_dir, variant = job
    text = (task_dir / variant).read_text(encoding="utf-8").lstrip("﻿")
    spec = yaml.safe_load((task_dir / "props.yaml").read_text())
    if not text.lstrip().startswith("<"):
        names = set()
        for prop in spec.get("properties", []):
            for key in ("expression", "trigger", "response"):
                names.update(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", str(prop.get(key, ""))))
            names.update(prop.get("variables", []))
        try:
            text = translate(pathlib.Path(variant).stem, text, sorted(names - {"true", "false"}))
        except ParseError:
            return f"{task_dir.name}/{variant}", None
    work = pathlib.Path(tempfile.mkdtemp(prefix="tiers."))
    (work / "p.ld").write_text(text, encoding="utf-8")
    decl = declared(text)
    first = next((n for n, (_s, _a, k) in decl.items() if k == "BOOL"), None)
    (work / "p.yaml").write_text(
        'format_version: "0.1"\nproperties:\n  - id: P0\n    kind: invariant\n'
        f'    expression: "{first} || !{first}"\n    justification: "placeholder"\n')
    try:
        free = free_reads(esbmc, str(work / "p.ld"), str(work / "p.yaml"))
    except subprocess.TimeoutExpired:
        free = None
    if free is None or first is None:
        return f"{task_dir.name}/{variant}", None
    tiers = collections.Counter()
    for name, (section, addr, _kind) in decl.items():
        key = f"ld::{name}"
        read_free = name in free or key in free
        if read_free and section in ("inputVars", "inOutVars", "externalVars"):
            tiers["tier 1, free: interface section"] += 1
        elif read_free and addr[:2].upper() in ("%I", "%M"):
            tiers["tier 2, free: address"] += 1
        elif read_free:
            tiers["tier 3, free: contact-only"] += 1
        elif section == "outputVars" or addr[:2].upper() == "%Q":
            tiers["owned: output"] += 1
        else:
            tiers["owned: internal state"] += 1
    return f"{task_dir.name}/{variant}", dict(tiers)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esbmc", required=True)
    ap.add_argument("--suite", type=pathlib.Path, default=SUITE)
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "io_tiers_results.json")
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()
    jobs = []
    for d in sorted((args.suite / "benchmarks").glob("*/*")):
        if not (d / "benchmark.yml").exists() or not (d / "props.yaml").exists():
            continue
        meta = yaml.safe_load((d / "benchmark.yml").read_text())
        if str(meta.get("language", "")).startswith("LD"):
            jobs += [(d, v["file"]) for v in meta.get("variants", []) if (d / v["file"]).exists()]
    with cf.ThreadPoolExecutor(args.jobs) as ex:
        results = list(ex.map(lambda j: one(j, args.esbmc), jobs))
    total = collections.Counter()
    by_language = {"checked": 0, "skipped": 0}
    for name, tiers in results:
        if tiers is None:
            by_language["skipped"] += 1
            continue
        by_language["checked"] += 1
        total.update(tiers)
    args.out.write_text(json.dumps({"variants": by_language, "variables": total, "per_variant": results}, indent=1))
    print(json.dumps(by_language))
    n = sum(total.values())
    for key, value in sorted(total.items()):
        print(f"  {key:36} {value:5}  ({100 * value / n:.1f}%)")
    print(f"  {'all declared variables':36} {n:5}")


if __name__ == "__main__":
    main()

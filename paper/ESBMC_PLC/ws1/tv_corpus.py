#!/usr/bin/env python3
"""Run --ld-tv-check on every LD task of the suite, graphical and textual.

A textual variant is first rendered to PLCopen XML by the suite's own converter
(tools/ld_text_to_xml.py); that XML is what both sides read, so the converter
itself is not validated. For each variant: build the MATIEC reference with tv_ref.py
(every non-input variable is state), run ESBMC's translation validation against
it, and record one verdict per task. Usage:
    tv_corpus.py --esbmc PATH [--suite DIR] [--out DIR] [--jobs N] [TASK ...]
Verdicts: equivalent (UNSAT), different (SAT), refused (ESBMC rejected the
program, so there is nothing to compare), error (anything else).
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import re
import shutil
import subprocess
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ESBMC-Benchmark-Suite" / "tools"))
from ld_text_to_xml import ParseError, translate  # noqa: E402
SUITE = HERE.parents[1] / "ESBMC-Benchmark-Suite"
MATIEC_LIB = pathlib.Path.home() / "plc-tools/matiec/lib/C"


def run(cmd, timeout):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return None, "timeout"


def property_variables(props):
    names = set()
    for prop in props.get("properties", []):
        for key in ("expression", "trigger", "response"):
            names.update(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", str(prop.get(key, ""))))
        names.update(prop.get("variables", []))
    return sorted(names - {"true", "false"})


def props_file(task_dir):
    """The task's property file: `properties_file` in benchmark.yml, else props.yaml.
    A syntax twin names its sibling's file, and requiring a props.yaml in its own
    folder dropped it from the corpus."""
    meta = yaml.safe_load((task_dir / "benchmark.yml").read_text())
    return (task_dir / meta.get("properties_file", "props.yaml")).resolve()


def ld_variants(task_dir):
    """The LD variants of a task: PLCopen XML as is, the suite's text DSL after its converter."""
    meta = yaml.safe_load((task_dir / "benchmark.yml").read_text())
    if not str(meta.get("language", "")).startswith("LD"):
        return []
    return [v["file"] for v in meta.get("variants", []) if (task_dir / v["file"]).exists()]


def variants(task_dir):
    meta = task_dir / "benchmark.yml"
    files = re.findall(r"^\s*-\s*file:\s*(\S+)", meta.read_text(), re.M) if meta.exists() else []
    return files or ["program.xml"]


def one(job, args):
    task_dir, variant = job
    name = task_dir.name if variant == "program.xml" else f"{task_dir.name}__{pathlib.Path(variant).stem}"
    work = args.out / name
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    shutil.copy(props_file(task_dir), work / "props.yaml")
    text = (task_dir / variant).read_text(encoding="utf-8").lstrip("\ufeff")
    if not text.lstrip().startswith("<"):
        try:
            text = translate(pathlib.Path(variant).stem, text,
                             property_variables(yaml.safe_load((work / "props.yaml").read_text())))
        except ParseError as exc:
            return name, "refused", f"suite converter: {exc}"[:160]
    (work / "program.xml").write_text(text, encoding="utf-8")
    (work / "program.ld").write_text(text, encoding="utf-8")
    # The front end runs first, so a program it refuses (an SFC body, say) counts
    # as refused here as in the suite, not as a reference that failed to build.
    _, out = run([str(args.esbmc), str(work / "program.ld"), "--goto-functions-only",
                  "--ld-sound-mode"], args.timeout)
    if re.search(r"^ERROR: (PARSING|CONVERSION) ERROR$", out or "", re.M):
        return name, "refused", re.search(r"^ERROR: (.*)$", out, re.M).group(1)[:160]
    rc, out = run([sys.executable, str(HERE / "tv_ref.py"), str(work / "program.xml"),
                   str(work / "ref"), "--state-all"] + (["--mutate"] if args.control else []), 300)
    if rc != 0:
        return name, "error", "reference build: " + out.strip().splitlines()[-1][:160] if out.strip() else "reference build"
    cdir = work / "ref" / "c"
    props = work / "props.yaml"
    first_bool = re.search(r'<variable name="(\w+)">\s*<type>\s*<BOOL', (work / "program.xml").read_text())
    if first_bool:
        # Translation validation compares scans, not properties, and a suite property can
        # use syntax the LD property parser does not read (`->`, kind termination); a
        # placeholder over a declared variable stands in for the file.
        props.write_text('format_version: "0.1"\nproperties:\n  - id: P0\n    kind: invariant\n'
                         f'    expression: "{first_bool.group(1)} || !{first_bool.group(1)}"\n'
                         '    justification: "Placeholder for translation validation."\n')
    cmd = [str(args.esbmc), str(work / "program.ld"), str(cdir / "ref.c"),
           "--ld-props", str(props), "--ld-tv-check", str(cdir / "correlation.txt"),
           "--secondary-entry-point", "--function", "ref_scan",
           "-I", str(MATIEC_LIB), "-I", str(cdir), "--ld-sound-mode",
           "--timeout", f"{args.timeout}s"]
    rc, out = run(cmd, args.timeout + 60)
    (work / "esbmc.log").write_text(out)
    kinds = [line.split()[0] for line in (cdir / "correlation.txt").read_text().splitlines()
             if line and not line.startswith("#")]
    ufbs = len(re.findall(r'pouType="functionBlock"', (work / "program.xml").read_text()))
    entries = f"in={kinds.count('in')} out={kinds.count('out')} state={kinds.count('state')}; user FBs={ufbs}"
    if "LD-TV-CHECK UNSAT" in out:
        return name, "blind" if args.control else "equivalent", entries
    if "LD-TV-CHECK SAT" in out:
        return name, "detected" if args.control else "different", entries
    m = re.search(r"^ERROR: (.*)$", out, re.M)
    if m and ("UnsupportedConstruct" in m.group(1) or "TypeCheck" in m.group(1)
              or "type" in m.group(1)):
        return name, "refused", m.group(1)[:160]
    return name, "error", (m.group(1) if m else out.strip().splitlines()[-1] if out.strip() else "no output")[:160]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esbmc", type=pathlib.Path, required=True)
    ap.add_argument("--suite", type=pathlib.Path, default=SUITE)
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "tv_corpus_out")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--control", action="store_true",
                    help="mutate each reference (flip one compared BOOL); every row must report SAT")
    ap.add_argument("tasks", nargs="*")
    args = ap.parse_args()
    dirs = sorted(d for d in (args.suite / "benchmarks").glob("*/*")
                  if (d / "benchmark.yml").exists() and props_file(d).exists())
    jobs = [(d, v) for d in dirs for v in ld_variants(d)]
    if args.tasks:
        jobs = [j for j in jobs if j[0].name in args.tasks]
    args.out.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(args.jobs) as ex:
        results = list(ex.map(lambda j: one(j, args), jobs))
    counts = {}
    for _n, v, _w in results:
        counts[v] = counts.get(v, 0) + 1
    lines = ["| task | verdict | detail |", "|---|---|---|"]
    lines += [f"| {n} | {v} | {w} |" for n, v, w in results]
    (args.out / "results.md").write_text("\n".join(lines) + "\n")
    (args.out / "results.json").write_text(json.dumps(
        {"counts": counts, "results": results}, indent=1))
    print(json.dumps(counts))
    for n, v, w in results:
        if v != "equivalent":
            print(f"  {v:10} {n}  {w}")
    if args.control:
        return 0 if set(counts) <= {"detected", "refused"} else 1
    return 0 if set(counts) <= {"equivalent", "refused"} else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Antecedent reachability for the suite's LD properties (concern M23).

A property can hold because what it protects against never happens: an
invariant `A -> B` is vacuous when A is unreachable, and `!(A && B)` when A or
B is. For each property of kind invariant, mutual_exclusion or response, this
derives the conditions that must be reachable for the property to say
anything, and asks ESBMC whether each one is. Usage:
    vacuity.py --esbmc PATH [--suite DIR] [--out DIR] [--jobs N] [TASK ...]
Structured Text variants (.st) are not on the LD route and are skipped. Verdict per condition: reached (BMC or k-induction finds a state), unreachable
(k-induction proves it), unknown, or refused (ESBMC rejects the program). A property with an unreachable condition is
vacuous; with an unknown one, possibly vacuous. A property from which no
condition can be derived (an expression of another shape) is not checked.
"""
import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

sys.path.insert(0, str(SUITE_TOOLS := pathlib.Path(__file__).resolve().parents[2] / "ESBMC-Benchmark-Suite" / "tools"))
from ld_text_to_xml import ParseError, translate  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SUITE = HERE.parents[1] / "ESBMC-Benchmark-Suite"
TOKEN = re.compile(r"\s*(->|&&|\|\||!|\(|\)|[A-Za-z_][A-Za-z_0-9]*)")


def tokens(text):
    pos, out = 0, []
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"cannot read {text[pos:]!r}")
        out.append(m.group(1))
        pos = m.end()
    return out


def parse(text):
    toks = tokens(text)
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def take():
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def implies():
        left = disj()
        if peek() == "->":
            take()
            return ("imp", left, implies())
        return left

    def disj():
        terms = [conj()]
        while peek() == "||":
            take()
            terms.append(conj())
        return terms[0] if len(terms) == 1 else ("or", terms)

    def conj():
        terms = [neg()]
        while peek() == "&&":
            take()
            terms.append(neg())
        return terms[0] if len(terms) == 1 else ("and", terms)

    def neg():
        if peek() == "!":
            take()
            return ("not", neg())
        if peek() == "(":
            take()
            node = implies()
            if take() != ")":
                raise ValueError("missing )")
            return node
        return ("var", take())

    node = implies()
    if pos != len(toks):
        raise ValueError("trailing tokens")
    return node


def render(node):
    kind = node[0]
    if kind == "var":
        return node[1]
    if kind == "not":
        return "!(" + render(node[1]) + ")"
    sep = {"and": " && ", "or": " || ", "imp": " -> "}[kind]
    parts = node[1] if kind in ("and", "or") else node[1:]
    return "(" + sep.join(render(p) for p in parts) + ")"


def conditions(prop):
    """The conditions that must be reachable for `prop` to constrain anything."""
    kind = prop.get("kind")
    if kind == "mutual_exclusion":
        return list(prop.get("variables", []))
    if kind == "response":
        return [prop["trigger"]] if prop.get("trigger") else []
    if kind != "invariant":
        return []
    node = parse(prop["expression"])
    if node[0] == "imp":
        return [render(node[1])]
    if node[0] == "or":
        negated = [t[1] for t in node[1] if t[0] == "not"]
        if len(negated) == len(node[1]):
            return [render(n) for n in negated]  # !A || !B, an exclusion
        return [" && ".join(render(n) for n in negated)] if negated else []
    if node[0] == "not" and node[1][0] == "and":
        return [render(t) for t in node[1][1]]
    return []


def variants(task_dir):
    meta = task_dir / "benchmark.yml"
    files = re.findall(r"^\s*-\s*file:\s*(\S+)", meta.read_text(), re.M) if meta.exists() else []
    return [f for f in (files or ["program.xml"]) if not f.endswith(".st")]


def property_variables(props):
    names = set()
    for prop in props.get("properties", []):
        for key in ("expression", "trigger", "response"):
            names.update(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", str(prop.get(key, ""))))
        names.update(prop.get("variables", []))
    return sorted(names - {"true", "false"})


def reach(esbmc, program, cond, timeout, pvars=()):
    work = pathlib.Path(tempfile.mkdtemp(prefix="vac."))
    try:
        ld = work / "p.ld"
        text = program.read_text(encoding="utf-8")
        if not text.lstrip().startswith("<"):
            try:
                text = translate(program.stem, text, pvars)
            except ParseError:
                return "refused"
        ld.write_text(text, encoding="utf-8")
        (work / "v.yaml").write_text(yaml.safe_dump({
            "format_version": "0.1",
            "properties": [{"id": "V", "kind": "reachability", "expression": cond,
                            "justification": "antecedent reachability"}]}))
        env = {**os.environ, "LLVM_PROFILE_FILE": "/dev/null"}
        try:
            p = subprocess.run([esbmc, str(ld), "--ld-props", str(work / "v.yaml"), "--k-induction",
                                "--timeout", f"{timeout}s"], capture_output=True, text=True,
                               timeout=timeout + 60, env=env)
            out = p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            return "unknown"
        if "VERIFICATION FAILED" in out:
            return "reached"
        if "VERIFICATION SUCCESSFUL" in out:
            return "unreachable"
        return "refused" if "\nERROR:" in out or out.startswith("ERROR:") else "unknown"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def one(job, args):
    task_dir, variant = job
    spec = yaml.safe_load((task_dir / "props.yaml").read_text())
    pvars = property_variables(spec)
    rows = []
    for prop in spec.get("properties", []):
        try:
            conds = conditions(prop)
        except (ValueError, KeyError) as exc:
            rows.append((prop.get("id"), "unparsed", str(exc)))
            continue
        if not conds:
            rows.append((prop.get("id"), "not checked", prop.get("kind")))
            continue
        verdicts = {c: reach(args.esbmc, task_dir / variant, c, args.timeout, pvars) for c in conds}
        if "refused" in verdicts.values():
            status = "refused"
        elif "unreachable" in verdicts.values():
            status = "vacuous"
        elif "unknown" in verdicts.values():
            status = "possibly vacuous"
        else:
            status = "non-vacuous"
        rows.append((prop.get("id"), status, "; ".join(f"{c}: {v}" for c, v in verdicts.items())))
    return f"{task_dir.name}/{variant}", rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esbmc", required=True)
    ap.add_argument("--suite", type=pathlib.Path, default=SUITE)
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "vacuity_out")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("tasks", nargs="*")
    args = ap.parse_args()
    dirs = sorted(d for d in (args.suite / "benchmarks").glob("*/*") if (d / "props.yaml").exists())
    jobs = [(d, v) for d in dirs for v in variants(d) if (d / v).exists()]
    if args.tasks:
        jobs = [j for j in jobs if j[0].name in args.tasks]
    args.out.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(args.jobs) as ex:
        results = list(ex.map(lambda j: one(j, args), jobs))
    counts = {}
    lines = ["| variant | property | status | conditions |", "|---|---|---|---|"]
    for name, rows in results:
        for pid, status, detail in rows:
            counts[status] = counts.get(status, 0) + 1
            lines.append(f"| {name} | {pid} | {status} | {detail} |")
    (args.out / "results.md").write_text("\n".join(lines) + "\n")
    (args.out / "results.json").write_text(json.dumps({"counts": counts, "results": results}, indent=1))
    print(json.dumps(counts))
    checked = sum(v for k, v in counts.items() if k in ("vacuous", "possibly vacuous", "non-vacuous"))
    flagged = counts.get("vacuous", 0) + counts.get("possibly vacuous", 0)
    if checked:
        print(f"vacuity rate: {flagged}/{checked} checked properties ({100 * flagged / checked:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

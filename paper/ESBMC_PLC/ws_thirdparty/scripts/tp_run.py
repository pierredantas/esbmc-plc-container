#!/usr/bin/env python3
"""Front-end acceptance and translation validation on the mined third-party LD programs.

Per distinct program (programs.json from dedup.py): run the front end alone; if it accepts,
build the MATIEC reference with ws1/tv_ref.py, run --ld-tv-check, and run it again against
a reference with one compared BOOL flipped (the control must report SAT). No property of
the program is needed: the query compares the two scans, and a tautology over a declared
BOOL stands in for the property file the option requires.
Usage: tp_run.py --esbmc PATH --programs programs.json --raw DIR --out DIR [--jobs N] [ID ...]
"""
import argparse, concurrent.futures as cf, json, pathlib, re, shutil, subprocess, sys, time

WS1 = pathlib.Path(__file__).resolve().parents[2] / "ws1"
MATIEC_LIB = pathlib.Path.home() / "plc-tools/matiec/lib/C"


def run(cmd, timeout):
    t0 = time.monotonic()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr, time.monotonic() - t0
    except subprocess.TimeoutExpired:
        return None, "timeout", time.monotonic() - t0


def first_error(out):
    m = re.search(r"^ERROR: (.*)$", out or "", re.M)
    return m.group(1)[:200] if m else (out.strip().splitlines()[-1][:200] if out and out.strip() else "no output")


def tv(esbmc, work, timeout, mutate):
    ref = work / ("ref_mut" if mutate else "ref")
    rc, out, _ = run([sys.executable, str(WS1 / "tv_ref.py"), str(work / "program.xml"), str(ref), "--state-all"]
                     + (["--mutate"] if mutate else []), 300)
    if rc != 0:
        return "ref_error", first_error(out), 0.0
    cdir = ref / "c"
    corr = cdir / "correlation.txt"
    dropped = []
    while True:
        rc, out, secs = run([str(esbmc), str(work / "program.ld"), str(cdir / "ref.c"),
                         "--ld-props", str(work / "props.yaml"), "--ld-tv-check", str(cdir / "correlation.txt"),
                         "--secondary-entry-point", "--function", "ref_scan",
                         "-I", str(MATIEC_LIB), "-I", str(cdir), "--ld-sound-mode", "--timeout", f"{timeout}s"],
                        timeout + 60)
        # A variable the LD side does not treat as free: one the body never mentions, or a
        # never-written one it keeps at its initial value (a preset, P4). The reference must
        # then not havoc it either, or the two sides start from different stores.
        m = re.search(r"no nondet-fed write to ld::(\w+) found on the LD side", out or "")
        if not m or len(dropped) > 50:
            break
        dropped.append(m.group(1))
        corr.write_text("".join(l for l in corr.read_text().splitlines(True)
                                if not re.match(rf"(in|state) ld::{m.group(1)} ", l)))
        ref_c = cdir / "ref.c"
        ref_c.write_text("".join(l for l in ref_c.read_text().splitlines(True)
                                 if not re.match(rf"\s*__SET_VAR\(d\., {m.group(1)}, ", l, re.I)))
    (work / ("dropped_mut.txt" if mutate else "dropped.txt")).write_text("\n".join(dropped))
    (work / ("tv_mut.log" if mutate else "tv.log")).write_text(out)
    if "LD-TV-CHECK UNSAT" in out:
        return "unsat", "", secs
    if "LD-TV-CHECK SAT" in out:
        return "sat", "", secs
    return ("timeout" if out == "timeout" else "tv_error"), first_error(out), secs


NS = "http://www.plcopen.org/xml/tc6_0201"


def normalize(text):
    """What both sides of the check read. I/O addresses bind a variable to the runtime's image
    and MATIEC turns them into pointers the reference harness cannot havoc; the namespace and
    comment fixes only make the file load in Beremiz. None changes what a scan computes."""
    applied = []
    t = re.sub(r'(<variable name="\w+")\s+address="[^"]*"', r"\1", text)
    if t != text:
        applied.append("address")
    t2 = re.sub(r"plcopen\.org/xml/tc6_0200", "plcopen.org/xml/tc6_0201", t)
    if not re.search(r'<project[^>]*\sxmlns="', t2):
        t2 = re.sub(r"<project\b", f'<project xmlns="{NS}"', t2, count=1)
    if t2 != t:
        applied.append("namespace")
    def clean(m):
        body = m.group(1)
        while "--" in body:
            body = body.replace("--", "- -")
        return "<!--" + body.rstrip("-") + "-->"
    t3 = re.sub(r"<!--(.*?)-->", clean, t2, flags=re.S)
    if "<fileHeader" not in t3:
        t3 = re.sub(r"(<project\b[^>]*>)", r'\1<fileHeader companyName="unknown" productName="unknown" '
                    r'productVersion="1" creationDateTime="2000-01-01T00:00:00"/>'
                    r'<contentHeader name="unknown"><coordinateInfo><fbd><scaling x="1" y="1"/></fbd>'
                    r'<ld><scaling x="1" y="1"/></ld><sfc><scaling x="1" y="1"/></sfc></coordinateInfo>'
                    r"</contentHeader>", t3, count=1)
        applied.append("header")
    if t3 != t2:
        applied.append("comment")
    # MATIEC refuses an instance or task named like a POU type ("PROGRAM Main WITH Main : Main").
    pous = set(re.findall(r'<pou name="(\w+)"', t3))
    t4 = re.sub(r'<pouInstance name="(\w+)"', lambda m: f'<pouInstance name="{m.group(1)}_inst"'
                if m.group(1) in pous else m.group(0), t3)
    t4 = re.sub(r'<task name="(\w+)"', lambda m: f'<task name="{m.group(1)}_task"'
                if m.group(1) in pous else m.group(0), t4)
    if t4 != t3:
        applied.append("instance_name")
    return t4, applied


def one(prog, args):
    work = args.out / prog["id"]
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    text = (args.raw / f"{prog['sha']}.xml").read_text(encoding="utf-8", errors="replace").lstrip("﻿")
    (work / "program.xml").write_text(text, encoding="utf-8")
    (work / "program.ld").write_text(text, encoding="utf-8")
    row = {"id": prog["id"], "repos": prog["repos"]}
    rc, out, secs = run([str(args.esbmc), str(work / "program.ld"), "--goto-functions-only", "--ld-sound-mode"],
                        args.timeout)
    (work / "frontend.log").write_text(out or "")
    row["frontend_s"] = round(secs, 2)
    if rc != 0:
        row["status"] = "refused" if re.search(r"^ERROR: (PARSING|CONVERSION) ERROR", out or "", re.M) or "ERROR" in (out or "") else "frontend_error"
        row["reason"] = first_error(out)
        if out == "timeout":
            row["status"] = "frontend_timeout"
        return row
    row["status"] = "accepted"
    text, row["normalized"] = normalize(text)
    (work / "program.xml").write_text(text, encoding="utf-8")
    (work / "program.ld").write_text(text, encoding="utf-8")
    if row["normalized"]:
        rc, out, _ = run([str(args.esbmc), str(work / "program.ld"), "--goto-functions-only", "--ld-sound-mode"],
                         args.timeout)
        if rc != 0:
            row["tv"], row["tv_detail"] = "normalized_refused", first_error(out)
            return row
    m = re.search(r'<variable name="(\w+)"[^>]*>\s*<type>\s*<BOOL', text)
    var = m.group(1) if m else None
    if not var:
        row["tv"] = "no_bool"
        return row
    (work / "props.yaml").write_text('format_version: "0.1"\nproperties:\n  - id: P0\n    kind: invariant\n'
                                     f'    expression: "{var} || !{var}"\n'
                                     '    justification: "Placeholder for translation validation."\n')
    row["tv"], row["tv_detail"], row["tv_s"] = tv(args.esbmc, work, args.timeout, False)
    if row["tv"] == "unsat":
        row["control"], _, _ = tv(args.esbmc, work, args.timeout, True)
    corr = work / "ref" / "c" / "correlation.txt"
    if corr.exists():
        kinds = [l.split()[0] for l in corr.read_text().splitlines() if l and not l.startswith("#")]
        row["compared"] = {k: kinds.count(k) for k in ("in", "out", "state")}
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esbmc", type=pathlib.Path, required=True)
    ap.add_argument("--programs", type=pathlib.Path, required=True)
    ap.add_argument("--raw", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("ids", nargs="*")
    args = ap.parse_args()
    args.out, args.raw, args.esbmc = args.out.resolve(), args.raw.resolve(), args.esbmc.resolve()
    progs = [p for p in json.loads(args.programs.read_text()) if p["bodies"].get("LD")]
    if args.ids:
        progs = [p for p in progs if p["id"] in args.ids]
    args.out.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(args.jobs) as ex:
        rows = list(ex.map(lambda p: one(p, args), progs))
    (args.out / "results.json").write_text(json.dumps(rows, indent=1))
    from collections import Counter
    print("status:", dict(Counter(r["status"] for r in rows)))
    print("tv:", dict(Counter(r.get("tv") for r in rows if r["status"] == "accepted")))
    print("control:", dict(Counter(r.get("control") for r in rows if r.get("tv") == "unsat")))


if __name__ == "__main__":
    main()

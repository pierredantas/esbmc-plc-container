#!/usr/bin/env python3
"""Generate the L1 timing cases: PLCopen LD program, ST twin, response properties, predicted verdicts.

Usage: gen_l1.py OUTDIR
Each case directory holds prog.ld (ESBMC dialect), prog.st (for MATIEC, OpenPLC, Beremiz), props_pass.yaml
(max_ms = worst case, expected SUCCESSFUL), props_fail.yaml (max_ms = worst case - 1, expected FAILED) and
case.json (parameters and predictions from model.py).
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import model

GRID = []
for kind in ("TON", "TOF", "TP"):
    for pt in (50, 100):
        for rng in ((10, 10), (10, 20), (10, 30), (20, 30)):
            GRID.append((kind, [(kind, pt)], rng))
for rng in ((10, 10), (10, 20)):
    GRID.append(("TON", [("TON", 30), ("TON", 40)], rng))

XML = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="SAFE-LD" productVersion="1.0" creationDateTime="2026-10-11"/>
  <contentHeader name="L1"/>
  <types/><instances/>
  <pous>
    <pou name="L1" pouType="program">
      <interface>
        <inputVars><variable name="IN1"><type><BOOL/></type></variable></inputVars>
        <outputVars>
{outs}
        </outputVars>
        <localVars>
{decls}
        </localVars>
      </interface>
      <body>
        <LD>
{rungs}
        </LD>
      </body>
    </pou>
  </pous>
</project>
"""


def var(name, typ, init=None):
    iv = f'<initialValue><simpleValue value="{init}"/></initialValue>' if init is not None else ""
    return f'          <variable name="{name}"><type><{typ}/></type>{iv}</variable>'


def program(kind, timers):
    decls, outs, rungs = [], [], []
    for i, (k, pt) in enumerate(timers, 1):
        outs.append(var(f"Q{i}", "BOOL"))
        decls += [var(f"ET{i}", "INT"), var(f"PT{i}", "INT", pt)]
        src = "IN1" if i == 1 else f"Q{i-1}"
        rungs.append(
            f'          <rung localId="{i}"><block typeName="{k}" instanceName="t{i}">'
            f'<variable formalParameter="IN">{src}</variable><variable formalParameter="PT">PT{i}</variable>'
            f'<variable formalParameter="Q">Q{i}</variable><variable formalParameter="ET">ET{i}</variable>'
            f'</block></rung>')
    n = len(timers)
    extra = []
    if kind == "TOF":
        outs.append(var("Idle", "BOOL"))
        extra.append(("IN1", "Idle"))
    if kind in ("TOF", "TP"):
        outs.append(var("QOff", "BOOL"))
        extra.append((f"Q{n}", "QOff"))
    for j, (src, dst) in enumerate(extra, n + 1):
        rungs.append(f'          <rung localId="{j}"><contact variable="{src}" negated="negated"/><coil variable="{dst}"/></rung>')
    trig, resp = {"TON": ("IN1", f"Q{n}"), "TOF": ("Idle", "QOff"), "TP": (f"Q{n}", "QOff")}[kind]
    return XML.format(outs="\n".join(outs), decls="\n".join(decls), rungs="\n".join(rungs)), trig, resp


def st_twin(timers, interval):
    lines = ["PROGRAM L1", "  VAR_INPUT IN1 : BOOL; END_VAR", "  VAR_OUTPUT"]
    for i, (k, pt) in enumerate(timers, 1):
        lines += [f"    Q{i} : BOOL;", f"    ET{i} : TIME;"]
    lines += ["  END_VAR", "  VAR"]
    for i, (k, pt) in enumerate(timers, 1):
        lines += [f"    t{i} : {k};"]
    lines += ["  END_VAR"]
    for i, (k, pt) in enumerate(timers, 1):
        src = "IN1" if i == 1 else f"Q{i-1}"
        lines += [f"  t{i}(IN := {src}, PT := T#{pt}ms);", f"  Q{i} := t{i}.Q;", f"  ET{i} := t{i}.ET;"]
    lines += ["END_PROGRAM", "", "CONFIGURATION Config0", "  RESOURCE Res0 ON PLC",
              f"    TASK Task0(INTERVAL := T#{interval}ms, PRIORITY := 0);",
              "    PROGRAM Inst0 WITH Task0 : L1;", "  END_RESOURCE", "END_CONFIGURATION", ""]
    return "\n".join(lines)


def props(trig, resp, limit, why):
    return (f"properties:\n  - id: P1\n    kind: response\n    trigger: {trig}\n    response: {resp}\n"
            f"    max_ms: {limit}\n    justification: \"{why}\"\n")


def main(out):
    out = pathlib.Path(out)
    for kind, timers, (tmin, tmax) in GRID:
        cid = "l1_{}_{}_{}_{}".format("_".join(f"{k.lower()}{pt}" for k, pt in timers), kind.lower() if len(timers) == 1 else "cascade", tmin, tmax)
        if len(timers) == 1:
            cid = f"l1_{kind.lower()}_pt{timers[0][1]}_{tmin}_{tmax}"
            assert model.worst_case(kind, timers, tmin, tmax)[0] == model.closed_form(timers[0][1], tmin, tmax)
        worst, scans = model.worst_case(kind, timers, tmin, tmax)
        d = out / cid
        d.mkdir(parents=True, exist_ok=True)
        xml, trig, resp = program(kind, timers)
        (d / "prog.ld").write_text(xml)
        (d / "prog.st").write_text(st_twin(timers, tmin))
        why = f"worst case from model.py: {worst} ms in {scans} scans"
        (d / "props_pass.yaml").write_text(props(trig, resp, worst, why))
        (d / "props_fail.yaml").write_text(props(trig, resp, worst - 1, why))
        (d / "case.json").write_text(json.dumps({
            "id": cid, "kind": kind, "timers": timers, "tmin": tmin, "tmax": tmax,
            "worst_ms": worst, "scans_to_worst": scans, "unwind": scans + 3,
            "expect": {"props_pass.yaml": "SUCCESSFUL", "props_fail.yaml": "FAILED"}}, indent=2) + "\n")
    print(f"{len(GRID)} cases in {out}")


if __name__ == "__main__":
    main(sys.argv[1])

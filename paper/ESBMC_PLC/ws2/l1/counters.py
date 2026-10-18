#!/usr/bin/env python3
"""Counter cases of the L1 family (ws2/l1_programs.md section 10).

Usage: counters.py WORKDIR ESBMC MATIEC_DIR
1. Tool against an independent model: for CTU and CTD the fewest scans that make Done true, found by search over the
   input sequences (model below); the tool must verify the invariant "not Done" one scan below and refute it at it.
2. R priority: the invariant "not (R and Q)" must hold (k-induction).
3. Oracle level A: MATIEC's compiled CTU and CTD against the model on random inputs, preset also random (dynamic PV).
"""
import itertools, json, pathlib, random, re, subprocess, sys, tempfile
from collections import deque

# ---- model: one scan of each counter (same rules as ld_converter::translate_counter and MATIEC's bodies) ----
def ctu(s, cu, r, pv):
    cv, prev = s
    if r:
        cv = 0
    elif cu and not prev and cv < pv:
        cv += 1
    return (cv, cu), cv >= pv

def ctd(s, cd, ld, pv):
    cv, prev = s
    if ld:
        cv = pv
    elif cd and not prev and cv > 0:
        cv -= 1
    return (cv, cd), cv <= 0

def fewest_scans(kind, pv):
    """Fewest scans after which Done holds; Done = Q for CTU, Q and Loaded (LD seen) for CTD."""
    init = ((0, False), False)
    seen, queue = {init}, deque([(init, 0)])
    while queue:
        (st, loaded), n = queue.popleft()
        for a, b in itertools.product((False, True), repeat=2):
            if kind == "CTU":
                st2, q = ctu(st, a, b, pv); l2 = False
            else:
                st2, q = ctd(st, a, b, pv); l2 = loaded or b
            if q and (kind == "CTU" or l2):
                return n + 1
            if (st2, l2) not in seen:
                seen.add((st2, l2)); queue.append(((st2, l2), n + 1))

# ---- generated programs ----
def var(name, typ, init=None):
    iv = f'<initialValue><simpleValue value="{init}"/></initialValue>' if init is not None else ""
    return f'<variable name="{name}"><type><{typ}/></type>{iv}</variable>'

def pou(kind, pv):
    a, b = ("Up", "Rst") if kind == "CTU" else ("Down", "Load")
    ins = var(a, "BOOL") + var(b, "BOOL")
    block = (f'<rung localId="1"><block typeName="{kind}" instanceName="c1"><variable formalParameter="{"CU" if kind == "CTU" else "CD"}">{a}</variable>'
             f'<variable formalParameter="{"R" if kind == "CTU" else "LD"}">{b}</variable><variable formalParameter="PV">P</variable>'
             f'<variable formalParameter="Q">Q</variable><variable formalParameter="CV">CV</variable></block></rung>')
    extra, loc = "", var("P", "INT", pv) + var("CV", "INT", 0) + var("Q", "BOOL") + var("Done", "BOOL")
    if kind == "CTD":
        loc += var("Loaded", "BOOL")
        extra = ('<rung localId="2"><contact variable="Load"/><coil kind="set" variable="Loaded"/></rung>'
                 '<rung localId="4"><contact variable="Q"/><contact variable="Loaded"/><coil variable="Done"/></rung>')
    else:
        extra = '<rung localId="2"><contact variable="Q"/><coil variable="Done"/></rung>'
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<project xmlns="http://www.plcopen.org/xml/tc6_0200">'
            f'<fileHeader companyName="SAFE-LD" productVersion="1.0" creationDateTime="2026-10-12"/><contentHeader name="C1"/><types/><instances/>'
            f'<pous><pou name="C1" pouType="program"><interface><inputVars>{ins}</inputVars><localVars>{loc}</localVars></interface>'
            f'<body><LD>{block}{extra}</LD></body></pou></pous></project>\n')

PROPS = {"not_done": 'properties:\n  - id: P1\n    kind: invariant\n    expression: "!Done"\n    description: "Done never holds"\n',
         "r_wins": 'properties:\n  - id: P1\n    kind: invariant\n    expression: "!Rst || !Q"\n    description: "R forces Q low"\n'}

def verdict(esbmc, d, *flags):
    p = subprocess.run([esbmc, "--ld-props", "props.yaml", *flags, "prog.ld"], cwd=d, capture_output=True, text=True)
    m = re.search(r"VERIFICATION (\w+)", p.stdout + p.stderr)
    return m.group(1) if m else "ERROR"

def tool_cases(work, esbmc):
    rows = []
    for kind, pvs in (("CTU", (1, 2, 3, 5, 10, 20)), ("CTD", (1, 2, 3, 5, 10, 20))):
        for pv in pvs:
            d = pathlib.Path(work) / f"{kind.lower()}_pv{pv}"
            d.mkdir(parents=True, exist_ok=True)
            (d / "prog.ld").write_text(pou(kind, pv)); (d / "props.yaml").write_text(PROPS["not_done"])
            n = fewest_scans(kind, pv)
            fl = lambda u: ["--unwind", str(u), "--no-unwinding-assertions"]
            rows.append({"kind": kind, "pv": pv, "fewest_scans": n, "below": verdict(esbmc, d, *fl(n - 1)) if n > 1 else "n/a", "at": verdict(esbmc, d, *fl(n))})
    d = pathlib.Path(work) / "ctu_rwins"
    d.mkdir(parents=True, exist_ok=True)
    (d / "prog.ld").write_text(pou("CTU", 3)); (d / "props.yaml").write_text(PROPS["r_wins"])
    rows.append({"kind": "CTU", "pv": 3, "r_wins_kinduction": verdict(esbmc, d, "--k-induction", "--max-k-step", "6"),
                 "r_wins_bmc20": verdict(esbmc, d, "--unwind", "20", "--no-unwinding-assertions")})
    return rows

# ---- oracle A ----
ST = """PROGRAM PC
  VAR_INPUT CU : BOOL; R : BOOL; CD : BOOL; LDI : BOOL; PV : INT; END_VAR
  VAR_OUTPUT Q1 : BOOL; CV1 : INT; Q2 : BOOL; CV2 : INT; END_VAR
  VAR k1 : CTU; k2 : CTD; END_VAR
  k1(CU := CU, R := R, PV := PV); Q1 := k1.Q; CV1 := k1.CV;
  k2(CD := CD, LD := LDI, PV := PV); Q2 := k2.Q; CV2 := k2.CV;
END_PROGRAM
CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK Task0(INTERVAL := T#10ms, PRIORITY := 0);
    PROGRAM Inst0 WITH Task0 : PC;
  END_RESOURCE
END_CONFIGURATION
"""
DRIVER = r'''
#include "iec_std_lib.h"
#include "POUS.h"
#include "POUS.c"
#include <stdio.h>
TIME __CURRENT_TIME;
int main(void) {
  PC d = {0}; PC_init__(&d, 0);
  int cu, r, cd, ld, pv;
  while (scanf("%d %d %d %d %d", &cu, &r, &cd, &ld, &pv) == 5) {
    __SET_VAR(d., CU, , cu); __SET_VAR(d., R, , r); __SET_VAR(d., CD, , cd); __SET_VAR(d., LDI, , ld); __SET_VAR(d., PV, , pv);
    PC_body__(&d);
    printf("%d %d %d %d\n", (int)__GET_VAR(d.Q1,), (int)__GET_VAR(d.CV1,), (int)__GET_VAR(d.Q2,), (int)__GET_VAR(d.CV2,));
  }
  return 0;
}
'''

def oracle(work, matiec, runs=2000, length=40):
    w = pathlib.Path(work) / "oracle"; w.mkdir(parents=True, exist_ok=True)
    (w / "prog.st").write_text(ST); (w / "drv.c").write_text(DRIVER)
    subprocess.run([str(matiec / "iec2c"), "-I", str(matiec / "lib"), "prog.st"], cwd=w, check=True, capture_output=True)
    subprocess.run(["cc", "-w", "-I", str(matiec / "lib" / "C"), "-I", ".", "drv.c", "-o", "drv"], cwd=w, check=True, capture_output=True)
    rng, tot = random.Random(2026), {"scans": 0, "q": 0, "cv": 0}
    for k in range(runs):
        pvmax = rng.choice((0, 1, 3, 5))
        seq = [(rng.random() < .5, rng.random() < (.1 if k % 2 else .4), rng.random() < .5, rng.random() < (.1 if k % 2 else .4),
                rng.randint(0, pvmax)) for _ in range(length)]
        out = subprocess.run([str(w / "drv")], input="".join(" ".join(str(int(x)) for x in s) + "\n" for s in seq), capture_output=True, text=True).stdout.split("\n")
        s1 = s2 = (0, False)
        for line, (cu, r, cd, ld, pv) in zip(out, seq):
            s1, q1 = ctu(s1, cu, r, pv); s2, q2 = ctd(s2, cd, ld, pv)
            got = list(map(int, line.split()))
            tot["scans"] += 1
            tot["q"] += (got[0], got[2]) != (int(q1), int(q2))
            tot["cv"] += (got[1], got[3]) != (s1[0], s2[0])
    return tot

def main(work, esbmc, matiec):
    rows = tool_cases(work, esbmc)
    for r in rows:
        print(json.dumps(r))
    orc = oracle(work, pathlib.Path(matiec))
    print(json.dumps({"oracle_a": orc}))
    (pathlib.Path(work) / "counters.json").write_text(json.dumps({"cases": rows, "oracle_a": orc}, indent=1) + "\n")

if __name__ == "__main__":
    main(*sys.argv[1:4])

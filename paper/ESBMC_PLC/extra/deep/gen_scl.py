#!/usr/bin/env python3
"""Write the SCL that PLCverif checks for the two RQ6 families: gen_scl.py BENCH_DIR OUT_DIR

Delay chain: each OTE rung of clean.ld/bomb.ld becomes an assignment in the same order, with the v_ prefix that
STEP 7 needs for names like A1. Dual counter: two CTU instances of iec_blocks.scl with the presets of the .ld file.
Every program asserts that the two outputs agree, as props.yaml states.
"""
import pathlib
import re
import sys

VAR = re.compile(r"\b([AB]\d+|In|Trig)\b")


def chain(ld, n):
    body = []
    for line in ld.read_text(encoding="utf-8").splitlines():
        m = re.match(r"OTE\((\w+)\) := (.*) ;", line)
        if m:
            expr = m.group(2).replace("XIC(", "(").replace("XIO(", "NOT (").replace("*", "AND")
            body.append(f"  v_{m.group(1)} := {VAR.sub(r'v_' + chr(92) + '1', expr)};")
    names = sorted({f"v_{x}" for x in re.findall(r"\b([AB]\d+)\b", ld.read_text(encoding="utf-8"))})
    ins = ["v_In"] + (["v_Trig"] if ld.stem == "bomb" else [])
    return ("FUNCTION_BLOCK DC\nVAR_INPUT\n" + "".join(f"  {v} : BOOL;\n" for v in ins) + "END_VAR\nVAR\n"
            + "".join(f"  {v} : BOOL;\n" for v in names) + "END_VAR\nBEGIN\n" + "\n".join(body)
            + f"\n  //#ASSERT (v_A{n} AND v_B{n}) OR (NOT v_A{n} AND NOT v_B{n}) : P1\nEND_FUNCTION_BLOCK\n")


def counter(ld):
    pa, pb = (int(x) for x in re.findall(r"CTU\(Q[AB], (\d+),", ld.read_text(encoding="utf-8")))
    return ("FUNCTION_BLOCK DCNT\nVAR_INPUT\n  Pulse : BOOL;\n  Reset : BOOL;\nEND_VAR\nVAR\n  CA : CTU;\n  CB : CTU;\n"
            "  QA : BOOL;\n  QB : BOOL;\nEND_VAR\nBEGIN\n"
            f"  CA(CU := Pulse, R := Reset, PV := {pa});\n  QA := CA.Q;\n"
            f"  CB(CU := Pulse, R := Reset, PV := {pb});\n  QB := CB.Q;\n"
            "  //#ASSERT (QA AND QB) OR (NOT QA AND NOT QB) : P1\nEND_FUNCTION_BLOCK\n")


def main():
    bench, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for ld in sorted(bench.glob("*/dual_*_n*/*.ld")):
        if "__uniform" in ld.name:
            continue
        family = ld.parent.name
        n = int(re.search(r"n(\d+)", family).group(1))
        scl = chain(ld, n) if family.startswith("dual_chain") else counter(ld)
        (out / f"{family}__{ld.stem}.scl").write_text(scl, encoding="utf-8")
        print(family, ld.stem, "DC" if family.startswith("dual_chain") else "DCNT")


if __name__ == "__main__":
    main()

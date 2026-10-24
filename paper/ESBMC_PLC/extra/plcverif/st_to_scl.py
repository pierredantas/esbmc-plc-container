#!/usr/bin/env python3
"""Turn a suite variant into SCL that PLCverif reads, with its state properties as assertions (PLCverif pilot).

    st_to_scl.py SUITE NAME OUT.scl HARNESS_C [--witness]

The Structured Text comes from the suite's own C route (Beremiz's generator), so PLCverif and MATIEC start from the
same text. PROGRAM becomes FUNCTION_BLOCK with a BEGIN before the body; the CONFIGURATION is dropped. Variables
that the C harness drives with nondet_* each scan become VAR_INPUT, matching the C route's scan model. Invariant,
absence, reachability, and mutual-exclusion properties become //#ASSERT lines at the end of the scan, encoded as the
C route encodes them; other kinds are not converted. Identifiers that STEP 7 reserves as absolute operands get a v_
prefix.
Exits 2 when the program or a property is outside what the pilot handles.
"""
import os
import pathlib
import re
import sys

import yaml


# STEP 7 reserves absolute operand names (timer T1, counter C3, memory word MW10, block DB2, ...) as keywords.
S7_OPERAND = re.compile(r"\b((?:T|C|Z|I|Q|E|A|M|L|DB|DI|FB|FC|SFB|SFC|UDT|OB|PIB|PIW|PID|PQB|PQW|PQD|IB|IW|ID|QB|QW|QD|"
                        r"EB|EW|ED|AB|AW|AD|MB|MW|MD|LB|LW|LD)\d+)\b", re.I)


def scl_expr(expr):
    e = expr.replace("&&", " AND ").replace("||", " OR ").replace("!=", "<>").replace("==", "=")
    e = re.sub(r"!\s*", "NOT ", e)
    return re.sub(r"\s+", " ", e).strip()


def main():
    suite, name, out, harness = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3]), sys.argv[4]
    witness = "--witness" in sys.argv[5:]
    os.environ.setdefault("PLC_TOOLS", str(pathlib.Path.home() / "plc-tools"))
    sys.path[:0] = [str(suite / "runner"), str(suite / "tools")]
    import record_via_c as rvc  # noqa: E402
    from record_all import variants  # noqa: E402
    from ld_text_to_xml import translate  # noqa: E402
    from record import property_variables  # noqa: E402

    task = next(t for t in variants("ld") if t["name"] == name)
    props = yaml.safe_load(task["props"].read_text(encoding="utf-8"))["properties"]
    program = task["program"]
    if task["text_ld"]:
        program = out.with_suffix(".xml")
        program.write_text(translate(task["program"].stem, task["program"].read_text(encoding="utf-8"),
                                     property_variables({"properties": props})), encoding="utf-8")
    st = rvc.to_st(program, out.parent)
    st = st.split("CONFIGURATION", 1)[0]
    if re.search(r"\b(FUNCTION_BLOCK|FUNCTION)\b", st) or len(re.findall(r"\bPROGRAM\b", st)) != 1:
        sys.exit(2)
    inputs = set(v.upper() for v in re.findall(r"__SET_VAR\(d\., (\w+), , nondet_\w+\(\)\)", pathlib.Path(harness).read_text(encoding="utf-8")))
    m = re.search(r"PROGRAM (\w+)\n(.*?)\n\n(.*)END_PROGRAM", st, re.S)
    if not m:
        sys.exit(2)
    pou, decls, body = m.groups()
    blocks = []
    for kind, block in re.findall(r"(VAR\w*)\n(.*?)END_VAR", decls, re.S):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        ins = [ln for ln in lines if ln.split(":")[0].strip().upper() in inputs]
        rest = [ln for ln in lines if ln not in ins]
        if ins:
            blocks.append(("VAR_INPUT", ins))
        if rest:
            blocks.append(("VAR" if kind == "VAR_INPUT" else kind, rest))
    asserts = []
    # Same encoding as the suite's C route (runner/record_via_c.py): the claim must hold at the end of every scan.
    for p in props:
        kind, expr = p["kind"], p.get("expression")
        expr = rvc.rewrite_implication(expr) if expr else expr
        if witness:
            # A required state: the claim fails exactly when the state is reached (runner/record_via_c.py witnesses).
            if kind == "reachable" and expr:
                asserts.append(f"  //#ASSERT {scl_expr(f'!({expr})')} : {p['id']}")
            continue
        if kind == "invariant" and expr:
            claim = expr
        elif kind in ("absence", "reachability") and expr:
            claim = f"!({expr})"
        elif kind == "mutual_exclusion" and p.get("variables"):
            claim = "!(" + " && ".join(p["variables"]) + ")"
        else:
            continue
        asserts.append(f"  //#ASSERT {scl_expr(claim)} : {p['id']}")
    if not asserts:
        sys.exit(2)
    decl_text = "".join(f"{k}\n" + "\n".join(ls) + "\nEND_VAR\n" for k, ls in blocks)
    text = f"{decl_text}BEGIN\n{body.rstrip()}\n" + "\n".join(asserts) + "\n"
    text = S7_OPERAND.sub(lambda m: "v_" + m.group(1), text)
    out.write_text(f"FUNCTION_BLOCK {pou.upper()}\n{text}END_FUNCTION_BLOCK\n", encoding="utf-8")
    print(pou.upper())


if __name__ == "__main__":
    main()

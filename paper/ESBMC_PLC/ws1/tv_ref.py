#!/usr/bin/env python3
"""Build the reference side of --ld-tv-check for one suite program.

Compiles program.xml to C with MATIEC (via the suite's record_via_c.py), then
writes ref.c, one scan of the program with a nondet value for every input and
for every --state variable, and correlation.txt for the matching ld-tv-check
run. Usage: tv_ref.py program.xml outdir [--state VAR ... | --state-all] [--mutate]
"""
import argparse
import pathlib
import re
import sys

SUITE = pathlib.Path(__file__).resolve().parents[2] / "ESBMC-Benchmark-Suite"
sys.path.insert(0, str(SUITE / "runner"))
import record_via_c as rvc  # noqa: E402

NONDET = rvc.NONDET


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("program", type=pathlib.Path)
    ap.add_argument("outdir", type=pathlib.Path)
    ap.add_argument("--state", nargs="*", default=[])
    ap.add_argument("--mutate", action="store_true",
                    help="flip the first compared BOOL variable after the scan, a control "
                         "that must make the check report SAT")
    ap.add_argument("--state-all", action="store_true",
                    help="treat every non-input program variable as state")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    props = args.program.with_name("props.yaml")
    _, cdir, _ = rvc.build(args.program, props, args.outdir, 1)

    header = (cdir / "POUS.h").read_text(encoding="utf-8")
    struct = rvc.entry_struct(args.program, header)
    prefix = struct[: -len("_data__")]
    end = re.search(r"\}\s*" + struct + ";", header).start()
    variables = rvc.declared_vars(header[header.rindex("typedef struct {", 0, end):end])
    ins = rvc.inputs_of(args.program)
    types = {name: iec for _k, iec, name in variables}
    upper = {n.upper(): n for _k, _t, n in variables}

    def resolve(name):
        return name.upper() if name.upper() in upper else name

    def havoc(name):
        target = resolve(name)
        return (f"  __SET_VAR(d., {target}, , "
                f"{NONDET.get(types.get(target, 'BOOL'), 'nondet_int()')});")

    in_names = {resolve(n) for n in ins}
    if args.state_all:
        body_c = (cdir / "POUS.c").read_text(encoding="utf-8")
        # A variable the program never assigns is written only by the environment,
        # which ESBMC models as a free read each scan: an input here.
        in_names |= {n for _k, _t, n in variables
                     if not n.startswith("_TMP_") and not re.search(r"__SET_VAR\(data__->,\s*" + n + r"\b", body_c)}
    state = [resolve(n) for n in args.state]
    if args.state_all:
        state += [n for _k, _t, n in variables
                  if n not in in_names and n not in state and not n.startswith("_TMP_")]
    body = ['#include "iec_std_lib.h"', '#include "POUS.h"', '#include "POUS.c"', "",
            "int ref_scan(void) {", f"  {struct} d = {{0}};", f"  {prefix}_init__(&d, 0);"]
    body += [havoc(n) for n in state]
    body += [havoc(n) for n in sorted(in_names)]
    body += [f"  {prefix}_body__(&d);"]
    if args.mutate:
        target = next((n for _k, t, n in variables
                       if t == "BOOL" and n not in in_names and not n.startswith("_TMP_")), None)
        if target is None:
            sys.exit("no compared BOOL variable to mutate")
        body += [f"  d.{target}.value = !d.{target}.value;"]
    body += ["  return 0;", "}"]
    (cdir / "ref.c").write_text("\n".join(body) + "\n", encoding="utf-8")

    in_up = in_names
    source_case = {n.upper(): n for n in re.findall(
        r'<variable name="(\w+)"', args.program.read_text(encoding="utf-8"))}
    lines = ["# ld-tv-check correlation: kind ld_var ref.field.path"]
    for _k, _t, name in variables:
        if name.startswith("_TMP_"):
            continue  # MATIEC's own temporaries; the LD side has no counterpart
        ld_name = source_case.get(name, name)
        path = f"d.{name}.value"
        if name in in_up:
            lines.append(f"in ld::{ld_name} {path}")
        elif name in state:
            lines.append(f"state ld::{ld_name} {path}")
        else:
            lines.append(f"out ld::{ld_name} {path}")
    (cdir / "correlation.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(cdir)


if __name__ == "__main__":
    main()

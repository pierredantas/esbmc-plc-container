#!/usr/bin/env python3
"""Generate the dual-channel delay chain family: gen_dual_chain.py OUT_DIR N [N ...]

Two redundant channels pass one input through N latch stages. The rungs run from the last stage to the first, so
each stage takes its predecessor's value from the previous scan and the input reaches stage N after N scans. The
outputs always agree, but a k-induction step that starts from an arbitrary state can plant a disagreement at stage 1
that surfaces only N scans later, so the proof needs k to grow with N. The bomb drops channel B at its middle stage
while Trig is set, which makes the outputs disagree.
"""
import pathlib
import sys

META = """format_version: "0.1"
id: dual_chain_n{n}
name: "dual-channel delay chain, depth {n} (deep-state family)"
domain: manufacturing
language: LD-textual
source:
  origin: authored
  reference: "deep-state family for the ESBMC-PLC paper"
  license: CC-BY-4.0
properties_file: props.yaml
validation_status: candidate
variants:
  - file: clean.ld
    expected_verdict: true
    ground_truth:
      method: construction
  - file: bomb.ld
    expected_verdict: false
    ground_truth:
      method: construction
features: [contacts, coils]
difficulty: parametric
tags: [deep-state, k-growth]
"""

PROPS = """format_version: "0.1"
properties:
  - id: P1
    kind: invariant
    expression: "(A{n} && B{n}) || (!A{n} && !B{n})"
    justification: "Both channels carry the same input through {n} stages, so their outputs agree."
"""


def program(n, bomb):
    mid = max(1, n // 2)
    rungs = [f"// dual_chain n={n}{' bomb' if bomb else ''}: rungs run from stage {n} down to stage 1"]
    for i in range(n, 1, -1):
        rungs.append(f"OTE(A{i}) := XIC(A{i - 1}) ;")
        guard = " * XIO(Trig)" if bomb and i == mid else ""
        rungs.append(f"OTE(B{i}) := XIC(B{i - 1}){guard} ;")
    rungs.append("OTE(A1) := XIC(In) ;")
    rungs.append("OTE(B1) := XIC(In)" + (" * XIO(Trig)" if bomb and mid == 1 else "") + " ;")
    return "\n".join(rungs) + "\n"


def main():
    out = pathlib.Path(sys.argv[1])
    for n in map(int, sys.argv[2:]):
        d = out / "manufacturing" / f"dual_chain_n{n}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "benchmark.yml").write_text(META.format(n=n), encoding="utf-8")
        (d / "props.yaml").write_text(PROPS.format(n=n), encoding="utf-8")
        (d / "clean.ld").write_text(program(n, False), encoding="utf-8")
        (d / "bomb.ld").write_text(program(n, True), encoding="utf-8")
        print(d)


if __name__ == "__main__":
    main()

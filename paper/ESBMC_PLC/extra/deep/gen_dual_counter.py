#!/usr/bin/env python3
"""Generate the dual-counter family: gen_dual_counter.py OUT_DIR N [N ...]

Two redundant up-counters count the same pulses to the same preset N, and their outputs always agree. Unlike the
delay chain, the property is not k-inductive for any k: a step that starts with unequal counts can wait with no
pulses for as long as it likes before one pulse exposes the difference, so a proof needs the relational invariant
CV_A = CV_B. The bomb gives channel B the preset N + 1; each count needs a rising edge, so the outputs first
disagree after about 2N scans.
"""
import pathlib
import sys

META = """format_version: "0.1"
id: dual_counter_n{n}
name: "dual redundant counters, preset {n} (deep-state family)"
domain: packaging
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
features: [ctu, contacts, coils]
difficulty: parametric
tags: [deep-state, relational]
"""

PROPS = """format_version: "0.1"
properties:
  - id: P1
    kind: invariant
    expression: "(QA && QB) || (!QA && !QB)"
    justification: "Both counters see the same pulses and resets with the same preset, so they finish together."
"""


def program(n, bomb):
    return (f"// dual_counter n={n}{' bomb' if bomb else ''}\n"
            f"CTU(QA, {n}, XIC(Pulse), XIC(Reset)) ;\n"
            f"CTU(QB, {n + 1 if bomb else n}, XIC(Pulse), XIC(Reset)) ;\n")


def main():
    out = pathlib.Path(sys.argv[1])
    for n in map(int, sys.argv[2:]):
        d = out / "packaging" / f"dual_counter_n{n}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "benchmark.yml").write_text(META.format(n=n), encoding="utf-8")
        (d / "props.yaml").write_text(PROPS, encoding="utf-8")
        (d / "clean.ld").write_text(program(n, False), encoding="utf-8")
        (d / "bomb.ld").write_text(program(n, True), encoding="utf-8")
        print(d)


if __name__ == "__main__":
    main()

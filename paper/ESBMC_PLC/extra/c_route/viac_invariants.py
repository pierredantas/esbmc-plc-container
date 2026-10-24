#!/usr/bin/env python3
"""Add loop-head invariants to an exported C-route harness (item 12):
viac_invariants.py HARNESS_DIR [--timers] [--counters]

Writes harness_inv.c, or harness_inv_timers.c / harness_inv_counters.c with the options. Each fact is assumed at
the top of the scan loop and asserted at its end, so every scan checks it and k-induction's step may use it; an
assertion at the top would face the step's arbitrary start state and never close:
  - no variable carries MATIEC's force flag, which nothing in the program sets (__SET_VAR skips a forced variable,
    accessor.h);
  - with --timers, each TON/TOF/TP is enabled, its STATE is 0, 1, or 2, and its START_TIME and the clock hold
    normalized timespecs with START_TIME not after the clock;
  - with --counters, each counter and edge block is enabled, and a CTU's CV is not negative.
"""
import os
import pathlib
import re
import sys

MATIEC_FB = pathlib.Path(os.environ.get("PLC_TOOLS", pathlib.Path.home() / "plc-tools")) / "matiec/lib/C/iec_std_FB.h"
DECL = re.compile(r"__DECLARE_VAR\(\s*\w+\s*,\s*(\w+)\s*\)")
INSTANCE = re.compile(r"^\s*(\w+)_data__\s+(\w+);", re.M)
TIMERS = {"TON", "TOF", "TP"}
COUNTERS = {"CTU", "CTD", "CTUD"}
EDGES = {"R_TRIG", "F_TRIG"}


def struct_body(text, name):
    m = re.search(r"typedef struct \{((?:(?!typedef struct).)*?)\}\s*" + re.escape(name) + r"\s*;", text, re.S)
    return m.group(1) if m else ""


def fields(prefix, body, fb_text):
    out = [f"{prefix}.{v}" for v in DECL.findall(body)]
    instances = []
    for fb, inst in INSTANCE.findall(body):
        instances.append((fb, f"{prefix}.{inst}"))
        sub, sub_inst = fields(f"{prefix}.{inst}", struct_body(fb_text, f"{fb}_data__"), fb_text)
        out += sub
        instances += sub_inst
    return out, instances


def normalized(t):
    return f"{t}.tv_nsec >= 0 && {t}.tv_nsec < 1000000000 && {t}.tv_sec >= 0"


def not_after(a, b):
    return f"({a}.tv_sec < {b}.tv_sec || ({a}.tv_sec == {b}.tv_sec && {a}.tv_nsec <= {b}.tv_nsec))"


def main():
    d = pathlib.Path(sys.argv[1])
    timers = "--timers" in sys.argv[2:]
    counters = "--counters" in sys.argv[2:]
    harness = (d / "harness.c").read_text(encoding="utf-8")
    data_type = re.search(r"\b(\w+_data__) d = \{0\};", harness).group(1)
    fb_text = MATIEC_FB.read_text(encoding="utf-8")
    variables, instances = fields("d", struct_body((d / "POUS.h").read_text(encoding="utf-8"), data_type), fb_text)
    facts = [f"!({v}.flags & __IEC_FORCE_FLAG)" for v in variables]
    if timers:
        facts.append(normalized("__CURRENT_TIME"))
        for fb, inst in instances:
            if fb in TIMERS:
                start = f"{inst}.START_TIME.value"
                facts += [f"{inst}.EN.value", f"{inst}.STATE.value >= 0 && {inst}.STATE.value <= 2",
                          normalized(start), not_after(start, "__CURRENT_TIME")]
    if counters:
        for fb, inst in instances:
            if fb in COUNTERS | EDGES:
                facts.append(f"{inst}.EN.value")
            if fb == "CTU":
                facts.append(f"{inst}.CV.value >= 0")
    assumes = "".join(f"    __ESBMC_assume({f});\n" for f in facts)
    asserts = "".join(f"    __ESBMC_assert({f}, \"inv\");\n" for f in facts)
    out = harness.replace("    advance_clock();\n", assumes + "    advance_clock();\n", 1)
    loop_end = out.rindex("  }\n  return 0;")
    out = out[:loop_end] + asserts + out[loop_end:]
    suffix = "".join(s for s, on in (("_timers", timers), ("_counters", counters)) if on)
    (d / f"harness_inv{suffix}.c").write_text(out, encoding="utf-8")
    print(f"{d.name}: {len(facts)} facts, {len(instances)} block instances {[fb for fb, _ in instances]}")


if __name__ == "__main__":
    main()

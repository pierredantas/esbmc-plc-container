#!/usr/bin/env python3
"""Negative controls for P1 and P2 of ws2/timer_theorem.md.

Usage: neg_controls.py WORKDIR ESBMC MATIEC_DIR
Each control proves with the tool a response bound under the model, then drives MATIEC's compiled timer code with a
clock that breaks one precondition and measures the real response time (sum of scan durations from the trigger scan
to the scan where the response holds, the monitor of timer_theorem.md section 4). A control "bites" when the real
time exceeds the bound the tool proved.
  P1: the clock is read at each timer call (per-call offsets) instead of once per scan.
  P2a: one scan lasts longer than Tmax.
  P2b: scan durations are not whole milliseconds (nanosecond clock), every scan inside [Tmin, Tmax].
Sanity: with the preconditions restored the same driver never exceeds the bound.
"""
import json, pathlib, random, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_l1, model

DRIVER = r'''
#define __CURRENT_TIME (*clk())
#include "iec_std_lib.h"
#include "POUS.h"
#include "POUS.c"
#include <stdio.h>
#undef __CURRENT_TIME
static long long now_ns, off_ns[4];
static int calln;
TIME *clk(void) {
  static TIME t;
  long long v = now_ns + off_ns[calln++];
  t.tv_sec = v / 1000000000LL; t.tv_nsec = v % 1000000000LL;
  return &t;
}
int main(void) {
  L1 d = {0}; L1_init__(&d, 0);
  long long dns, o[4]; int in, first = 1;
  while (scanf("%d %lld %lld %lld %lld", &in, &dns, &o[0], &o[1], &o[2]) == 5) {
    if (!first) now_ns += dns;
    first = 0; calln = 0;
    for (int j = 0; j < 3; j++) off_ns[j] = o[j];
    __SET_VAR(d., IN1, , in);
    L1_body__(&d);
    printf("%d\n", (int)__GET_VAR(d.Q%LAST%,));
  }
  return 0;
}
'''


def make_case(work, name, kind, timers, tmin, tmax):
    d = work / name
    d.mkdir(parents=True, exist_ok=True)
    worst, scans = model.worst_case(kind, timers, tmin, tmax)
    xml, trig, resp = gen_l1.program(kind, timers)
    (d / "prog.ld").write_text(xml)
    (d / "prog.st").write_text(gen_l1.st_twin(timers, tmin))
    (d / "props.yaml").write_text(gen_l1.props(trig, resp, worst, "negative control"))
    return d, worst, scans


def tool_verdict(esbmc, d, tmin, tmax, scans):
    cmd = [esbmc, "--ld-props", "props.yaml", "--ld-cycle-time", f"{tmin}:{tmax}", "--unwind", str(scans + 3),
           "--no-unwinding-assertions", "prog.ld"]
    p = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
    m = re.search(r"VERIFICATION (\w+)", p.stdout + p.stderr)
    return m.group(1) if m else "ERROR"


def build(d, matiec, ntimers):
    subprocess.run([str(matiec / "iec2c"), "-I", str(matiec / "lib"), "prog.st"], cwd=d, check=True, capture_output=True)
    (d / "drv.c").write_text(DRIVER.replace("%LAST%", str(ntimers)))
    subprocess.run(["cc", "-w", "-I", str(matiec / "lib" / "C"), "-I", ".", "drv.c", "-o", "drv"], cwd=d, check=True, capture_output=True)
    return d / "drv"


def real_response(exe, durations_ns, offsets_ns, scans=40):
    """Monitor value of a run with IN held from scan 0: the durations of the scans before the first scan with Q true.

    As in model.worst_case, scan 0 counts in full (durations_ns[0] is not used by the clock)."""
    lines = "".join(f"1 {durations_ns[i]} {offsets_ns[i][0]} {offsets_ns[i][1]} 0\n" for i in range(scans))
    out = subprocess.run([str(exe)], input=lines, capture_output=True, text=True).stdout.split()
    for i, q in enumerate(out):
        if q == "1":
            return sum(durations_ns[:i]) / 1e6
    return None


def p1(work, esbmc, matiec):
    timers, tmin, tmax = [("TON", 30), ("TON", 40)], 10, 10
    d, worst, scans = make_case(work, "p1", "TON", timers, tmin, tmax)
    exe = build(d, matiec, 2)
    ms = tmin * 1_000_000
    fixed = [ms] * 40
    zero = [(0, 0)] * 40
    base = real_response(exe, fixed, zero)
    # timer 1 starts late inside its scan and is then read early; the same for timer 2 when it starts
    offs = [(9_000_000 if i == 0 else 0, 9_000_000 if i == 4 else 0) for i in range(40)]
    bite = real_response(exe, fixed, offs)
    rng, best, best_offs = random.Random(1), 0.0, None
    for _ in range(3000):
        o = [(rng.randint(0, 9) * 1_000_000, rng.randint(0, 9) * 1_000_000) for _ in range(40)]
        r = real_response(exe, fixed, o)
        if r is not None and r > best:
            best, best_offs = r, o[:12]
    wide = model.worst_case("TON", timers, tmin, 2 * tmax)[0]
    return {"control": "P1", "program": "TON(30) -> TON(40), IN held", "range": f"{tmin}:{tmax}", "model_worst_ms": worst,
            "tool": tool_verdict(esbmc, d, tmin, tmax, scans), "real_one_clock_ms": base, "real_per_call_designed_ms": bite,
            "real_per_call_random_best_ms": best, "bound_if_range_widened_to_2x": wide}


def p2a(work, esbmc, matiec):
    tmin, tmax = 10, 10
    d, worst, scans = make_case(work, "p2a", "TON", [("TON", 50)], tmin, tmax)
    exe = build(d, matiec, 1)
    ms = 1_000_000
    base = [10 * ms] * 40
    over = [40 * ms] + [10 * ms] * 39
    z = [(0, 0)] * 40
    return {"control": "P2a", "program": "TON(50), IN held", "range": f"{tmin}:{tmax}", "model_worst_ms": worst,
            "tool": tool_verdict(esbmc, d, tmin, tmax, scans), "real_in_range_ms": real_response(exe, base, z),
            "real_with_40ms_first_scan_ms": real_response(exe, over, z),
            "model_bound_with_Tmax_40": model.worst_case("TON", [("TON", 50)], tmin, 40)[0]}


def p2b(work, esbmc, matiec):
    tmin, tmax = 10, 20
    d, worst, scans = make_case(work, "p2b", "TON", [("TON", 50)], tmin, tmax)
    exe = build(d, matiec, 1)
    z = [(0, 0)] * 40
    integer = [20_000_000] + [12_000_000] * 3 + [13_000_000] + [20_000_000] * 35  # partial sum 49 ms, then 20 ms
    finer = [20_000_000] + [12_475_000] * 4 + [20_000_000] * 35  # partial sum 49.9 ms, then 20 ms
    return {"control": "P2b", "program": "TON(50), IN held", "range": f"{tmin}:{tmax}", "model_worst_ms": worst,
            "tool": tool_verdict(esbmc, d, tmin, tmax, scans), "real_whole_ms_clock": real_response(exe, integer, z),
            "real_ns_clock": real_response(exe, finer, z)}


def main(work, esbmc, matiec):
    work, matiec = pathlib.Path(work), pathlib.Path(matiec)
    work.mkdir(parents=True, exist_ok=True)
    rows = [f(work, esbmc, matiec) for f in (p1, p2a, p2b)]
    for r in rows:
        print(json.dumps(r))
    (work / "negctl.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:4])

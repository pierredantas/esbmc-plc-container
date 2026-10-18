#!/usr/bin/env python3
"""Oracle level A: MATIEC's own timer code under a synthetic clock, against model.py.

Usage: oracle_a.py CASEDIR MATIEC_DIR [SEQUENCES_PER_CASE]
For every case it compiles prog.st with iec2c, drives the generated program with chosen input and clock sequences
(the clock is __CURRENT_TIME, advanced by d_i at scan i, as the runtimes of ws2/timer_theorem.md section 2a do),
and compares Q and ET after every scan with the model. No runtime is involved, so it tests Theorem 1 only.
"""
import json, pathlib, random, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import model

DRIVER = r'''
#include "iec_std_lib.h"
#include "POUS.h"
#include "POUS.c"
#include <stdio.h>
TIME __CURRENT_TIME;
int main(void) {
  L1 d = {0}; L1_init__(&d, 0);
  long long t = 0; int in, dms, first = 1;
  while (scanf("%d %d", &in, &dms) == 2) {
    if (!first) t += dms;
    first = 0;
    __CURRENT_TIME.tv_sec = t / 1000; __CURRENT_TIME.tv_nsec = (t % 1000) * 1000000;
    __SET_VAR(d., IN1, , in);
    L1_body__(&d);
    printf("%d", (int)NTIMERS_PLACEHOLDER);
%PRINTS%
    printf("\n");
  }
  return 0;
}
'''

def build(case, matiec, timers, work):
    work = pathlib.Path(work)
    subprocess.run([str(matiec / "iec2c"), "-I", str(matiec / "lib"), str(case / "prog.st")], cwd=work, check=True, capture_output=True)
    prints = "".join(
        f'    printf(" %d %lld", (int)__GET_VAR(d.Q{i},), (long long)__GET_VAR(d.ET{i},).tv_sec * 1000 + __GET_VAR(d.ET{i},).tv_nsec / 1000000);\n'
        for i in range(1, len(timers) + 1))
    src = DRIVER.replace("%PRINTS%", prints).replace('printf("%d", (int)NTIMERS_PLACEHOLDER);', f'printf("{len(timers)}");')
    (work / "drv.c").write_text(src)
    subprocess.run(["cc", "-w", "-I", str(matiec / "lib" / "C"), "-I", ".", "drv.c", "-o", "drv"], cwd=work, check=True, capture_output=True)
    return work / "drv"

def sequences(tmin, tmax, count, rng, length=60):
    pats = []
    for d in (tmin, tmax):
        pats.append(([1] * length, [d] * length))
        pats.append(([1] * (length // 2) + [0] * (length // 2), [d] * length))
    for _ in range(count):
        ins, cur = [], rng.random() < 0.5
        for _ in range(length):
            if rng.random() < 0.15:
                cur = not cur
            ins.append(int(cur))
        pats.append((ins, [rng.randint(tmin, tmax) for _ in range(length)]))
    return pats

def replay(timers, ins, ds):
    st = tuple(model.START for _ in timers)
    out = []
    for inp, d in zip(ins, ds):
        st = model.scan(timers, st, bool(inp), d)
        out.append([(int(s[1]), s[0]) for s in st])
    return out

def main(root, matiec, count=200):
    matiec, rng = pathlib.Path(matiec), random.Random(2026)
    total = {"scans": 0, "q": 0, "et": 0, "et_tp_expiry": 0}
    cache = {}
    for case in sorted(pathlib.Path(root).iterdir()):
        info = json.loads((case / "case.json").read_text())
        timers = [tuple(t) for t in info["timers"]]
        key = (case / "prog.st").read_text()
        if key not in cache:
            tmp = tempfile.mkdtemp(prefix="l1a_")
            cache[key] = build(case, matiec, timers, tmp)
        exe = cache[key]
        for ins, ds in sequences(info["tmin"], info["tmax"], count, rng):
            run = subprocess.run([str(exe)], input="".join(f"{i} {d}\n" for i, d in zip(ins, ds)), capture_output=True, text=True).stdout.split("\n")
            ref = replay(timers, ins, ds)
            for n, line in enumerate(run[:len(ins)]):
                f = list(map(int, line.split()))[1:]
                total["scans"] += 1
                for ti, (q, et) in enumerate(ref[n]):
                    mq, met = f[2 * ti], f[2 * ti + 1]
                    total["q"] += mq != q
                    if met != et:
                        tp_gap = info["kind"] == "TP" and ins[n] == 0 and mq == 0 and met == 0 and et == timers[ti][1]
                        total["et_tp_expiry" if tp_gap else "et"] += 1
    print(json.dumps(total))
    return total

if __name__ == "__main__":
    t = main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 200)
    sys.exit(1 if t["q"] or t["et"] else 0)

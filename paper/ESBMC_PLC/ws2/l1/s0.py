#!/usr/bin/env python3
"""Stairs-light case S0 (ws2/l1_programs.md section 7): the real CONTROLLINO light_control program in timing mode.

Usage: s0.py WORKDIR ESBMC
Adds two observer rungs (Unwanted = stairs_light and not PIR and not button state; Gone = not Unwanted) after the
original coils, scales the TOF preset, and compares the tool with model_s0 at the predicted worst case and one below.
"""
import json, pathlib, re, subprocess, sys, time
from collections import deque
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import model

ORIGINAL = pathlib.Path(__file__).resolve().parent / "s0" / "stairs_light_original.ld"


def program(pt_ms):
    s = ORIGINAL.read_text()
    assert s.count("T#20s") == 1
    s = s.replace("T#20s", f"T#{pt_ms}ms")
    s = s.replace("<localVars>\n            <variable name=\"TOF0\">",
                  '<localVars>\n            <variable name="Unwanted"><type><BOOL/></type></variable>\n'
                  '            <variable name="Gone"><type><BOOL/></type></variable>\n          </localVars>\n          <localVars>\n            <variable name="TOF0">')
    def contact(i, var, y, src, neg):
        return (f'            <contact localId="{i}" negated="{neg}" width="30" height="20">\n'
                f'              <position x="110" y="{y}"/>\n'
                f'              <connectionPointIn><relPosition x="0" y="10"/><connection refLocalId="{src}"/></connectionPointIn>\n'
                f'              <connectionPointOut><relPosition x="30" y="10"/></connectionPointOut>\n'
                f'              <variable>{var}</variable>\n            </contact>\n')
    def coil(i, var, y, src):
        return (f'            <coil localId="{i}" negated="false" width="30" height="20">\n'
                f'              <position x="610" y="{y}"/>\n'
                f'              <connectionPointIn><relPosition x="0" y="10"/><connection refLocalId="{src}"/></connectionPointIn>\n'
                f'              <connectionPointOut><relPosition x="30" y="10"/></connectionPointOut>\n'
                f'              <variable>{var}</variable>\n            </coil>\n')
    obs = (contact(20, "stairs_light", 530, 1, "false") + contact(21, "stairs_pir_sensor", 530, 20, "true")
           + contact(22, "lights_buttons_state", 530, 21, "true") + coil(23, "Unwanted", 530, 22)
           + contact(24, "Unwanted", 610, 1, "true") + coil(25, "Gone", 610, 24))
    assert s.count('<comment localId="15"') == 1
    s = s.replace('<comment localId="15"', obs + '            <comment localId="15"')
    s = s.replace('<connection refLocalId="11">\n                </connection>\n              </connectionPointIn>',
                  '<connection refLocalId="11">\n                </connection>\n              </connectionPointIn>\n'
                  '              <connectionPointIn><connection refLocalId="23"/></connectionPointIn>\n'
                  '              <connectionPointIn><connection refLocalId="25"/></connectionPointIn>', 1)
    return s


def worst_case(pt, tmin, tmax, bound=10**6):
    """Largest monitor value of Unwanted over all PIR and delta sequences; buttons never change the state (W11)."""
    start = (False, model.START)          # (previous PIR, TOF state)
    best, queue, top = {start: (0, 0)}, deque([start]), (0, 0)
    while queue:
        st = queue.popleft()
        c, n = best[st]
        prev_pir, tof = st
        for pir in (False, True):
            for d in range(tmin, tmax + 1):
                tof2 = model.tof(tof, pir and not prev_pir, d, pt)
                unwanted = tof2[1] and not pir
                c2 = c + d if unwanted else 0
                if c2 > bound:
                    return None, None
                nxt = (pir, tof2)
                old = best.get(nxt)
                if old is None or c2 > old[0] or (c2 == old[0] and n + 1 < old[1]):
                    best[nxt] = (c2, n + 1)
                    queue.append(nxt)
                    if c2 > top[0] or (c2 == top[0] and n + 1 < top[1]):
                        top = (c2, n + 1)
    return top


def run(esbmc, case, props, rng, unwind):
    t0 = time.perf_counter()
    try:
        p = subprocess.run([esbmc, "--ld-props", props, "--ld-cycle-time", rng, "--unwind", str(unwind), "--no-unwinding-assertions", "prog.ld"],
                           cwd=case, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 300
    m = re.search(r"VERIFICATION (\w+)", p.stdout + p.stderr)
    return (m.group(1) if m else "ERROR"), round(time.perf_counter() - t0, 1)


def main(work, esbmc):
    rows = []
    for pt, rng in ((200, (20, 20)), (500, (20, 20)), (1000, (20, 20)), (2000, (20, 20)), (100, (15, 25)), (150, (15, 25))):
        worst, scans = worst_case(pt, *rng)
        case = pathlib.Path(work) / f"s0_pt{pt}_{rng[0]}_{rng[1]}"
        case.mkdir(parents=True, exist_ok=True)
        (case / "prog.ld").write_text(program(pt))
        for side, lim in (("pass", worst), ("fail", worst - 1)):
            (case / f"{side}.yaml").write_text(
                "properties:\n  - id: P1\n    kind: response\n    trigger: Unwanted\n    response: Gone\n"
                f"    max_ms: {lim}\n    justification: \"S0 from model_s0: {worst} ms\"\n")
            v, sec = run(esbmc, case, f"{side}.yaml", f"{rng[0]}:{rng[1]}", scans + 3)
            rows.append({"pt": pt, "range": f"{rng[0]}:{rng[1]}", "worst": worst, "scans": scans, "side": side, "limit": lim, "verdict": v, "sec": sec})
            print(rows[-1], flush=True)
    pathlib.Path(work, "s0.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

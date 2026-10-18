#!/usr/bin/env python3
"""Scaling measurements for the timing mode (ws2/l1_programs.md section 7).

Usage: scale_l1.py WORKDIR ESBMC EXPERIMENT [TIMEOUT_S]    EXPERIMENT in s1, s2, s3
  s1  exact response bound by BMC: time and memory against PT / Tmin
  s2  k-induction on 'ET <= PT' with and without --ld-fb-invariants, against PT
  s3  history chain 'Q implies IN held m scans': the k that induction needs, against m = PT / Tmax + 1
  s3b the same properties by BMC (unwind m + 3): time and memory
  s4  the s1 cases by k-induction with --ld-fb-invariants --ld-monitor-invariants (experimental branch exp/ld-monitor-invariant)
Needs an ESBMC with --ld-cycle-time, --ld-fb-invariants and max_ms (branch scratch/ws2-all). macOS /usr/bin/time -l.
"""
import json, pathlib, re, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_l1, model

TIMEOUT = 600


def run(esbmc, case, args):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(["/usr/bin/time", "-l", esbmc] + args, cwd=case, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"verdict": "TIMEOUT", "k": None, "sec": TIMEOUT, "mb": None}
    out = p.stdout + p.stderr
    v = re.search(r"VERIFICATION (\w+)", out)
    k = re.search(r"inductive step \(k = (\d+)\)", out)
    rss = re.search(r"(\d+)\s+maximum resident set size", out)
    return {"verdict": v.group(1) if v else "ERROR", "k": int(k.group(1)) if k else None,
            "sec": round(time.perf_counter() - t0, 2), "mb": round(int(rss.group(1)) / 2**20) if rss else None}


def worst_and_scans(pt, tmin, tmax):
    """Closed form worst case and the fewest scans that reach it, by a DP over sums below PT."""
    best, count = {0: 0}, 0
    for s in range(1, pt):
        c = [best[s - d] + 1 for d in range(tmin, tmax + 1) if (s - d) in best]
        if c:
            best[s] = min(c)
    top = max(best)
    return tmax + top, best[top] + 2  # first scan, the deltas, and the scan that sets Q


def write_ton(case, pt, outs, rungs_extra="", decls_extra=""):
    case.mkdir(parents=True, exist_ok=True)


def s1(work, esbmc):
    rows = []
    for (tmin, tmax) in ((10, 10), (10, 30)):
        for pt in (50, 100, 200, 500, 1000, 2000, 5000):
            worst, scans = worst_and_scans(pt, tmin, tmax)
            case = pathlib.Path(work) / f"s1_pt{pt}_{tmin}_{tmax}"
            case.mkdir(parents=True, exist_ok=True)
            xml, trig, resp = gen_l1.program("TON", [("TON", pt)])
            (case / "prog.ld").write_text(xml)
            for side, lim in (("pass", worst), ("fail", worst - 1)):
                (case / f"{side}.yaml").write_text(gen_l1.props(trig, resp, lim, "scaling"))
                r = run(esbmc, case, ["--ld-props", f"{side}.yaml", "--ld-cycle-time", f"{tmin}:{tmax}", "--unwind", str(scans + 3),
                                       "--no-unwinding-assertions", "prog.ld"])
                rows.append({"exp": "s1", "pt": pt, "range": f"{tmin}:{tmax}", "scans": scans, "worst": worst, "side": side, **r})
                print(rows[-1], flush=True)
    return rows


def ton_et_program(pt):
    xml, _, _ = gen_l1.program("TON", [("TON", pt)])
    # derive Ok = (ET <= PT) with a SUB and a CTU used as a comparator
    xml = xml.replace('<outputVars>', '<outputVars>\n          <variable name="Ok"><type><BOOL/></type><initialValue><simpleValue value="TRUE"/></initialValue></variable>')
    xml = xml.replace('<localVars>', '<localVars>\n          <variable name="Never"><type><BOOL/></type></variable>\n'
                      '          <variable name="D"><type><INT/></type><initialValue><simpleValue value="-1"/></initialValue></variable>\n'
                      '          <variable name="CV2"><type><INT/></type></variable>')
    extra = ('          <rung localId="8"><block typeName="SUB" instanceName="s1"><variable formalParameter="IN1">ET1</variable><variable formalParameter="IN2">PT1</variable><variable formalParameter="OUT">D</variable></block></rung>\n'
             '          <rung localId="9"><block typeName="CTU" instanceName="cu2"><variable formalParameter="CU">Never</variable><variable formalParameter="R">Never</variable><variable formalParameter="PV">D</variable><variable formalParameter="Q">Ok</variable><variable formalParameter="CV">CV2</variable></block></rung>\n')
    return xml.replace("        </LD>", extra + "        </LD>")


def s2(work, esbmc):
    rows = []
    ok = 'properties:\n  - id: P1\n    kind: invariant\n    expression: "Ok"\n    description: "ET never exceeds PT"\n'
    for pt in (50, 100, 500, 1000, 5000, 20000):
        case = pathlib.Path(work) / f"s2_pt{pt}"
        case.mkdir(parents=True, exist_ok=True)
        (case / "prog.ld").write_text(ton_et_program(pt)); (case / "props.yaml").write_text(ok)
        for inv in (False, True):
            r = run(esbmc, case, ["--ld-props", "props.yaml", "--ld-cycle-time", "10:30", "--k-induction", "--max-k-step", "6"] + (["--ld-fb-invariants"] if inv else []) + ["prog.ld"])
            rows.append({"exp": "s2", "pt": pt, "invariants": inv, **r}); print(rows[-1], flush=True)
    return rows


def chain_program(pt, m):
    decls = "".join(f'          <variable name="H{i}"><type><BOOL/></type></variable>\n' for i in range(1, m + 1))
    xml, _, _ = gen_l1.program("TON", [("TON", pt)])
    xml = xml.replace('<localVars>\n', '<localVars>\n' + decls)
    chain = "".join(f'          <rung localId="{100 + m - i}"><contact variable="H{i-1}"/><coil variable="H{i}"/></rung>\n' for i in range(m, 1, -1))
    chain += '          <rung localId="99"><contact variable="IN1"/><coil variable="H1"/></rung>\n'
    return xml.replace("        </LD>", chain + "        </LD>")


def s3(work, esbmc, tmax=10):
    rows = []
    for pt in (20, 50, 100, 200, 300):
        m = pt // tmax + 1
        for label, mm in (("holds", m), ("fails", m + 1)):
            case = pathlib.Path(work) / f"s3_pt{pt}_{label}"
            case.mkdir(parents=True, exist_ok=True)
            (case / "prog.ld").write_text(chain_program(pt, mm))
            expr = "!Q1 || (" + " && ".join(f"H{i}" for i in range(1, m + 1 if label == 'holds' else m + 2)) + ")"
            (case / "props.yaml").write_text(f'properties:\n  - id: P1\n    kind: invariant\n    expression: "{expr}"\n    description: "Q needs IN held {mm} scans"\n')
            for inv in (False, True):
                r = run(esbmc, case, ["--ld-props", "props.yaml", "--ld-cycle-time", f"{tmax}:{tmax}", "--k-induction", "--max-k-step", str(mm + 8)] + (["--ld-fb-invariants"] if inv else []) + ["prog.ld"])
                rows.append({"exp": "s3", "pt": pt, "m": mm, "claim": label, "invariants": inv, **r}); print(rows[-1], flush=True)
    return rows


def s4(work, esbmc):
    rows = []
    for kind in ("TON", "TOF", "TP"):
        for (tmin, tmax) in ((10, 10), (10, 30)):
            for pt in (50, 200, 1000, 5000, 20000):
                worst, scans = worst_and_scans(pt, tmin, tmax)
                case = pathlib.Path(work) / f"s4_{kind.lower()}_pt{pt}_{tmin}_{tmax}"
                case.mkdir(parents=True, exist_ok=True)
                xml, trig, resp = gen_l1.program(kind, [(kind, pt)])
                (case / "prog.ld").write_text(xml)
                for side, lim in (("pass", worst), ("fail", worst - 1)):
                    (case / f"{side}.yaml").write_text(gen_l1.props(trig, resp, lim, "scaling"))
                    r = run(esbmc, case, ["--ld-props", f"{side}.yaml", "--ld-cycle-time", f"{tmin}:{tmax}", "--k-induction", "--max-k-step", "8",
                                           "--ld-fb-invariants", "--ld-monitor-invariants", "prog.ld"])
                    rows.append({"exp": "s4", "kind": kind, "pt": pt, "range": f"{tmin}:{tmax}", "worst": worst, "bound_by_invariant": tmax + pt - 1, "side": side, **r})
                    print(rows[-1], flush=True)
    return rows


def s3b(work, esbmc, tmax=10):
    rows = []
    for pt in (20, 50, 100, 200, 300, 500, 1000):
        m = pt // tmax + 1
        case = pathlib.Path(work) / f"s3b_pt{pt}"
        case.mkdir(parents=True, exist_ok=True)
        (case / "prog.ld").write_text(chain_program(pt, m))
        expr = "!Q1 || (" + " && ".join(f"H{i}" for i in range(1, m + 1)) + ")"
        (case / "props.yaml").write_text(f'properties:\n  - id: P1\n    kind: invariant\n    expression: "{expr}"\n    description: "Q needs IN held {m} scans"\n')
        r = run(esbmc, case, ["--ld-props", "props.yaml", "--ld-cycle-time", f"{tmax}:{tmax}", "--unwind", str(m + 3), "--no-unwinding-assertions", "prog.ld"])
        rows.append({"exp": "s3b", "pt": pt, "m": m, **r}); print(rows[-1], flush=True)
    return rows


if __name__ == "__main__":
    work, esbmc, exp = sys.argv[1], sys.argv[2], sys.argv[3]
    if len(sys.argv) > 4:
        TIMEOUT = int(sys.argv[4])
    rows = {"s1": s1, "s2": s2, "s3": s3, "s3b": s3b, "s4": s4}[exp](work, esbmc)
    pathlib.Path(work, f"{exp}.json").write_text(json.dumps(rows, indent=1))

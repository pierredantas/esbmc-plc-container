#!/usr/bin/env python3
"""Verify the suite's LD variants through MATIEC's C instead of the LD front end.

Answers the referee question "why not verify MATIEC's C directly?". For each variant the
suite's own C route builds the C (PLCopen XML -> Beremiz ST -> MATIEC C) and a harness; this
script then makes the harness match the LD route's scan model: an unbounded scan loop
instead of a fixed count, and a clock that advances 1 ms per scan (the LD default counts one
tick per scan), since MATIEC's timers read the global __CURRENT_TIME and nothing else
advances it. Every task gets the same engine as the uniform LD run: k-induction, one
timeout. Plain-text LD variants are converted to PLCopen XML first, as the LD route does. Writes one
JSON line per variant to OUT/<jsonl>.

    viac_uniform.py --esbmc PATH --suite DIR --names FILE --out DIR [--timeout 120] [--jobs 6]
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

CLOCK = """TIME __CURRENT_TIME = {0, 0};
static void advance_clock(void) {
  __CURRENT_TIME.tv_nsec += 1000000;
  if (__CURRENT_TIME.tv_nsec >= 1000000000) { __CURRENT_TIME.tv_nsec -= 1000000000; __CURRENT_TIME.tv_sec++; }
}
"""
LOOP = re.compile(r"  for \(int scan = 0; scan < \d+; scan\+\+\) \{\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esbmc", required=True)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--names", required=True, help="file with one variant name per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--jsonl", default="viac.jsonl")
    args = ap.parse_args()

    suite = pathlib.Path(args.suite).resolve()
    sys.path.insert(0, str(suite / "runner"))
    os.environ.setdefault("PLC_TOOLS", str(pathlib.Path.home() / "plc-tools"))
    sys.path.insert(0, str(suite / "tools"))
    import record_via_c as rvc  # noqa: E402
    from record_all import variants, is_termination  # noqa: E402
    from ld_text_to_xml import translate  # noqa: E402
    from record import property_variables  # noqa: E402
    import yaml  # noqa: E402

    wanted = set(pathlib.Path(args.names).read_text().split())
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    def one(task):
        row = {"name": task["name"], "expected": "SAFE" if task["expected"] else "VIOLATION"}
        if is_termination(task["props"]):
            row["verdict"] = "skipped: termination task"
            return row
        with tempfile.TemporaryDirectory() as tmp:
            program = task["program"]
            try:
                if task["text_ld"]:
                    # The LD route converts the plain-text DSL to PLCopen XML first; give the C route the same input.
                    pvars = property_variables(yaml.safe_load(task["props"].read_text(encoding="utf-8")))
                    program = pathlib.Path(tmp) / "converted.xml"
                    program.write_text(translate(task["program"].stem, task["program"].read_text(encoding="utf-8"), pvars),
                                       encoding="utf-8")
                harness, outdir, _ = rvc.build(program, task["props"], pathlib.Path(tmp), 8)
            except Exception as e:  # noqa: BLE001  the C route's own failure is a result
                row["verdict"] = "build-failed"
                row["reason"] = str(e).strip().splitlines()[-1][:160] if str(e).strip() else type(e).__name__
                return row
            text = harness.read_text(encoding="utf-8")
            if not LOOP.search(text):
                row["verdict"] = "harness-unrecognized"
                return row
            text = LOOP.sub("  while (1) {\n    advance_clock();\n", text, count=1)
            text = text.replace("int main(void) {", CLOCK + "int main(void) {", 1)
            harness.write_text(text, encoding="utf-8")
            cmd = [args.esbmc, str(harness), "-I", str(rvc.TOOLS / "matiec" / "lib" / "C"),
                   "-I", str(outdir), "--k-induction", "--timeout", f"{args.timeout}s"]
            t0 = time.time()
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            log = res.stdout + res.stderr
            row["cpu_s"] = round(time.time() - t0, 3)
        row["verdict"] = ("SAFE" if "VERIFICATION SUCCESSFUL" in log else
                          "VIOLATION" if "VERIFICATION FAILED" in log else
                          "timeout" if "Timed out" in log else
                          "error" if "ERROR" in log else "unknown")
        if row["verdict"] == "error":
            row["reason"] = next((l for l in log.splitlines() if "ERROR" in l), "")[:160]
        k = re.findall(r"(?:Bug found|Solution found by the forward condition|Solution found by the inductive step).*?\(k = (\d+)\)", log)
        row["k"] = int(k[-1]) if k else None
        return row

    tasks = [t for t in variants("ld") if t["name"] in wanted]
    with open(out / args.jsonl, "w") as fh, concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        for row in pool.map(one, tasks):
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(row["name"], row["verdict"], row.get("cpu_s", ""), flush=True)
    print(f"\n{len(tasks)} variant(s); missing from the C route: {sorted(wanted - {t['name'] for t in tasks})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

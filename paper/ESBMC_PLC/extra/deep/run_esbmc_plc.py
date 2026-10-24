#!/usr/bin/env python3
"""ESBMC-PLC k-induction on the deep-state families: run_esbmc_plc.py BENCH_DIR ESBMC OUT.jsonl [TIMEOUT_S] [FLAG ...]

Each text-LD variant goes through the suite's converter (tools/ld_text_to_xml.py) and then the uniform run's
command line, with --max-k-step 64 so that deep proofs are not cut off. ESBMC's --timeout is backed by a Python
limit 30 s later, since ESBMC does not always honour its own.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import yaml

SUITE = pathlib.Path(os.environ.get("SUITE", pathlib.Path.home() / "Claude/suite-v120-run"))
sys.path[:0] = [str(SUITE / "runner"), str(SUITE / "tools")]
from ld_text_to_xml import translate  # noqa: E402
from record import property_variables  # noqa: E402


def main():
    bench, esbmc, out = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    extra = sys.argv[5:]
    with open(out, "w", encoding="utf-8") as fh:
        for meta_path in sorted(bench.glob("*/*/benchmark.yml")):
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            props = meta_path.parent / meta["properties_file"]
            pvars = property_variables(yaml.safe_load(props.read_text(encoding="utf-8")))
            for var in meta["variants"]:
                src = meta_path.parent / var["file"]
                xml = src.with_name(src.stem + "__uniform_xml.ld")
                xml.write_text(translate(src.stem, src.read_text(encoding="utf-8"), pvars), encoding="utf-8")
                cmd = [esbmc, str(xml), "--ld-props", str(props), "--k-induction", "--max-k-step", "64",
                       "--ld-scan-watchdog", "--ld-scan-budget", "8", "--ld-sound-mode", "--timeout", f"{limit}s",
                       *extra]
                t0 = time.time()
                try:
                    p = subprocess.run(cmd, capture_output=True, text=True, timeout=limit + 30, check=False)
                    log = p.stdout + p.stderr
                except subprocess.TimeoutExpired:
                    log = "Timed out (external limit)"
                sec = round(time.time() - t0, 2)
                verdict = ("SAFE" if "VERIFICATION SUCCESSFUL" in log else "VIOLATION" if "VERIFICATION FAILED" in log
                           else "timeout" if "Timed out" in log else "UNKNOWN" if "VERIFICATION UNKNOWN" in log
                           else "error")
                k = re.findall(r"(?:inductive step|base case|forward condition)\D*k = (\d+)", log)
                row = {"name": f'{meta["id"]}__{src.stem}', "expected": "SAFE" if var["expected_verdict"] else "VIOLATION",
                       "verdict": verdict, "k": int(k[-1]) if k else None, "sec": sec, "command": " ".join(cmd)}
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(row["name"], verdict, "k =", row["k"], f"{sec} s", flush=True)


if __name__ == "__main__":
    main()

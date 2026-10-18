#!/usr/bin/env python3
"""Rerun the suite's LD route with one engine for every task.

The suite runner picks k-induction for a task expected SAFE and 20-scan BMC for one expected
to fail, so a wrong VIOLATION label is never challenged. This drives record.py with
--mode kinduction for every non-termination task, writes the records to OUT/records, and
leaves the suite's own results untouched.

    uniform_ld.py --esbmc PATH --suite DIR --out DIR [--timeout 120] [--jobs 6]
"""
import argparse
import concurrent.futures
import pathlib
import shutil
import subprocess
import sys

import yaml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esbmc", required=True)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()

    suite = pathlib.Path(args.suite).resolve()
    sys.path.insert(0, str(suite / "runner"))
    sys.path.insert(0, str(suite / "tools"))
    from record_all import variants, is_termination  # noqa: E402
    from ld_text_to_xml import ParseError, translate  # noqa: E402
    from record import property_variables  # noqa: E402

    records = pathlib.Path(args.out).resolve() / "records"
    records.mkdir(parents=True, exist_ok=True)

    def one(task):
        program, props = task["program"], task["props"]
        if task["text_ld"]:
            copy = program.with_name(program.stem + "__uniform_xml.ld")
            try:
                pvars = property_variables(yaml.safe_load(props.read_text(encoding="utf-8")))
                copy.write_text(translate(program.stem, program.read_text(encoding="utf-8"), pvars),
                                encoding="utf-8")
            except ParseError as e:
                return f'SKIP {task["name"]}: {e}'
        else:
            copy = program.with_name(program.stem + "__uniform.ld")
            shutil.copyfile(program, copy)
        cmd = [sys.executable, str(suite / "runner" / "record.py"), str(copy), str(props),
               "true" if task["expected"] else "false", "--timeout", str(args.timeout),
               "--source", str(program), "--tool", f"uniform={args.esbmc}",
               "-o", str(records / f'{task["name"]}.json')]
        if task["text_ld"]:
            cmd.append("--converted-from-text-ld")
        cmd += ["--watchdog-only"] if is_termination(props) else ["--mode", "kinduction"]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, check=False)
        finally:
            copy.unlink(missing_ok=True)
        return out.stdout.strip() or out.stderr.strip()[:160]

    tasks = list(variants("ld"))
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        for line in pool.map(one, tasks):
            print(line, flush=True)
    print(f"\n{len(tasks)} variant(s) recorded into {records}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

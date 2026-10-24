#!/usr/bin/env python3
"""Export the C route's harnesses so other verifiers and longer limits can run on them (item 12).

For each named variant, builds the harness exactly as run/viac_uniform.py does (unbounded scan loop, 1 ms
per scan) and writes OUT/<name>/harness.c, the form ESBMC reads, and OUT/<name>/harness.i, preprocessed in
SV-COMP style: nondet_* becomes __VERIFIER_nondet_*, and a failed __ESBMC_assert calls reach_error().

    viac_export.py --suite DIR --names FILE --out DIR [--jobs 1]
"""
import argparse
import concurrent.futures
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

# paper/ESBMC_PLC, which holds run/viac_uniform.py
ROOT = pathlib.Path(__file__).resolve().parents[2]
PRELUDE = """extern void abort(void);
extern void __assert_fail(const char *, const char *, unsigned int, const char *);
void reach_error() { __assert_fail("0", "harness.c", 0, "reach_error"); }
#define __ESBMC_assert(c, m) do { if (!(c)) { reach_error(); abort(); } } while (0)
"""
NONDET = re.compile(r"\bnondet_(\w+)\s*\(")
C_TYPES = {"bool": "_Bool", "char": "char", "uchar": "unsigned char", "short": "short",
           "ushort": "unsigned short", "int": "int", "uint": "unsigned int", "long": "long",
           "ulong": "unsigned long", "float": "float", "double": "double"}


def load_viac():
    spec = importlib.util.spec_from_file_location("viac_uniform", ROOT / "run" / "viac_uniform.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sv_prelude(text):
    lines = [PRELUDE]
    for t in sorted(set(NONDET.findall(text))):
        lines.append(f"extern {C_TYPES[t]} __VERIFIER_nondet_{t}(void);\n#define nondet_{t} __VERIFIER_nondet_{t}\n")
    return "".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--names", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=1)
    args = ap.parse_args()

    viac = load_viac()
    suite = pathlib.Path(args.suite).resolve()
    os.environ.setdefault("PLC_TOOLS", str(pathlib.Path.home() / "plc-tools"))
    sys.path[:0] = [str(suite / "runner"), str(suite / "tools")]
    import record_via_c as rvc  # noqa: E402
    from record_all import variants, is_termination  # noqa: E402
    from ld_text_to_xml import translate  # noqa: E402
    from record import property_variables  # noqa: E402
    import yaml  # noqa: E402

    wanted = set(pathlib.Path(args.names).read_text(encoding="utf-8").split())
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    matiec_lib = rvc.TOOLS / "matiec" / "lib" / "C"

    def one(task):
        row = {"name": task["name"]}
        if is_termination(task["props"]):
            return {**row, "status": "skipped: termination task"}
        dest = out / task["name"]
        with tempfile.TemporaryDirectory() as tmp:
            program = task["program"]
            try:
                if task["text_ld"]:
                    pvars = property_variables(yaml.safe_load(task["props"].read_text(encoding="utf-8")))
                    program = pathlib.Path(tmp) / "converted.xml"
                    program.write_text(translate(task["program"].stem, task["program"].read_text(encoding="utf-8"),
                                                 pvars), encoding="utf-8")
                harness, outdir, _ = rvc.build(program, task["props"], pathlib.Path(tmp), 8)
            except Exception as e:  # noqa: BLE001
                return {**row, "status": "build-failed", "reason": str(e).strip()[-160:]}
            text = harness.read_text(encoding="utf-8")
            if not viac.LOOP.search(text):
                return {**row, "status": "harness-unrecognized"}
            text = viac.LOOP.sub("  while (1) {\n    advance_clock();\n", text, count=1)
            text = text.replace("int main(void) {", viac.CLOCK + "int main(void) {", 1)
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(outdir, dest)
            (dest / "harness.c").write_text(text, encoding="utf-8")
            (dest / "prelude.h").write_text(sv_prelude(text), encoding="utf-8")
            pp = subprocess.run([os.environ.get("CC", "cc"), "-E", "-P", "-include", str(dest / "prelude.h"), "-I", str(matiec_lib),
                                 "-I", str(dest), str(dest / "harness.c"), "-o", str(dest / "harness.i")],
                                capture_output=True, text=True, check=False)
            shutil.copy(task["props"], dest / "props.yaml")
        return {**row, "status": "ok" if pp.returncode == 0 else "preprocess-failed",
                "expected": "SAFE" if task["expected"] else "VIOLATION"}

    tasks = [t for t in variants("ld") if t["name"] in wanted]
    with open(out / "export.jsonl", "w", encoding="utf-8") as fh, concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        for row in pool.map(one, tasks):
            fh.write(json.dumps(row) + "\n")
            print(row["name"], row["status"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

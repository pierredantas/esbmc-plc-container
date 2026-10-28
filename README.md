# ESBMC-PLC artifact

A pinned container for the ESBMC-PLC work: ESBMC with the Ladder Diagram front end, the IEC 61131-3 benchmark suite, the Beremiz/MATIEC toolchain behind the suite's second route, and the WS0 defect reproducers.

Every source is fixed in `Dockerfile`: the Ubuntu 24.04 base by digest, and ESBMC, the suite, Beremiz and MATIEC by commit. The `image` workflow builds it on an amd64 runner and runs `check.sh` inside it.

## For reviewers: build the image

Build the image from this archive's `Dockerfile` rather than pulling it:

```
docker build --platform linux/amd64 -t esbmc-plc .            # builds ESBMC, Beremiz and MATIEC from source
docker run --rm esbmc-plc check-image                         # LD unit tests, regression/ld, WS0 reproducers, both routes
docker run --rm -it esbmc-plc bash                            # esbmc, the suite, the tools
docker run --rm -v "$PWD/out:/out" esbmc-plc reproduce-paper     # the suite, translation validation, timers, both routes
docker run --rm -v "$PWD/out:/out" esbmc-plc reproduce-extra     # the C route at 900 s and with facts, deep states, RQ4 repeats
```

The image we built is not published; this is deliberate. The `Dockerfile` pins every source, the Ubuntu 24.04 base
by digest and ESBMC, the suite, Beremiz, and MATIEC by commit, so building it shows exactly what runs and nothing
else. Our CI built this `Dockerfile` on amd64 on October 24, 2026
(`sha256:d031b091b7f8db2d4d2149ba4d480aaf65913dc61e52b24482900e9e3ffce810`; `check-image` passed, 325 of 325 LD
tests and 12 of 12 WS0 reproducers). A local build need not match the digest byte for byte, but `check-image` and the
verdicts should.

`check-image` runs the LD unit tests, `regression/ld` and `ld-verify`, the twelve WS0 reproducers, and one benchmark program through both routes.

Inside the container: ESBMC in `/opt/esbmc` (built, with `esbmc` on `PATH`), the suite in `/opt/suite`, the tools in `/opt/plc-tools` (`$PLC_TOOLS`), and the reproducers in `/opt/ws0`.

## Reproducing the paper

The image pins the build behind *ESBMC-PLC: Verifying IEC 61131-3 Ladder Diagrams with a
Validated Translation to SMT-Based Model Checking*: ESBMC at fork commit `5efb80de72` (branch
`pin/paper-2026-10-jumps`), which carries the prototype `--ld-monitor-invariants` used in RQ4 and the parser refusals
that upstream ESBMC added later, and suite release v1.2.0. Every ESBMC number of the paper comes from this
one build. The run scripts are in `/opt/paper`.

`reproduce-paper` reruns the suite, translation validation, the timer experiments, and both routes (several hours on
8 cores). `reproduce-extra` then reruns the remaining ESBMC experiments: the C route at 900 s and with facts about
MATIEC's records (RQ3), the deep-state families (RQ6), and five repetitions of the RQ4 scaling runs; it takes about
10 hours. `paper/CLAIMS.md` maps each number in the paper to its archived record in `results-2026-10-24.tar.gz`,
archived next to this source, and to the step that regenerates it, and lists where an archived run differs from the
scripts. Run times depend on the machine; verdicts should not.

### Outside the image: PLCverif, NuSMV, 2LS

The comparison with PLCverif (RQ3, Table 8; RQ6, Table 9) and the 2LS attempt (Appendix E.8) need tools the image
does not carry; we ran them on macOS 26.7.1 (arm64). The scripts are in `paper/ESBMC_PLC/extra/` and take every
path from the environment.

| Tool | Version and source | Notes |
|---|---|---|
| Java | OpenJDK 25 or later (we used 27.0.1) | the PLCverif CLI requires Java 25 |
| PLCverif CLI | `https://plcverif-oss.web.cern.ch/releases/latest/cern.plcverif.cli/cern.plcverif.cli.cmdline.app.product-linux.gtk.x86_64.tar.gz`, SHA-256 `0e75f1982cf0ca0673d667db0c0dc177cbc4083af813198c380f06621815637d` (CLI 1.0.0.202607171441) | started as `java -jar plugins/org.eclipse.equinox.launcher_*.jar` from its folder; also runs on macOS |
| PLCverif block library | `builtin.scl` of `https://gitlab.com/plcverif-oss/plcverif-builtin-projects`, commit `c2734010b0ab112c2465126a7b60cc0410d97a88`, folder `.builtin_Siemens S7-300` | Eclipse Public License 2.0, so fetched, not copied here; supplies TON, TOF, TP |
| IEC blocks | `extra/plcverif/iec_blocks.scl` | our transcription of R_TRIG, F_TRIG, CTU, CTD; `run_blocktests.sh` checks them |
| NuSMV | 2.7.1 source, `https://nusmv.fbk.eu/distrib/2.7.1/NuSMV-2.7.1.tar.xz`, SHA-256 `f1e11931f71d98aa9b84181eed67db584d7111100c2e967c904a31c15f823f60` | `meson setup build --buildtype=release -Dbuild-doc=disabled -Dbuild-universal-binary=disabled`; needs GNU flex, pkg-config, GMP, libedit, and a `python` on `PATH` |
| 2LS | `https://github.com/diffblue/2ls`, commit `9a9ad377` (0.10.0) | built with `-Wno-error=#warnings` added to `src/config.inc` and the Glucose download of its CBMC; its verdicts were not used (Appendix E.8) |

```
export SUITE=<suite v1.2.0> PLC_TOOLS=<Beremiz and MATIEC> PLCVERIF=<CLI folder> NUSMV=<NuSMV binary> \
       JAVA=<java 25+> BUILTIN="<plcverif-builtin-projects>/.builtin_Siemens S7-300/builtin.scl" ESBMC=<esbmc>
extra/plcverif/run_blocktests.sh OUT/blocktests          # 8 of 8 OK
extra/plcverif/run_plcverif.sh OUT/routes OUT/plcverif    # Table 8; needs OUT/routes from reproduce-paper
extra/deep/run_deep.sh OUT/deep                           # Table 9, ESBMC-PLC and PLCverif parts
```

### Programs mined from GitHub (RQ2)

`paper/ESBMC_PLC/ws_thirdparty/` holds the GitHub search hits, a manifest with the repository, path, commit, blob, and
license of each of the 1,290 files, the 1,018 distinct programs after merging copies, and the per-program results.
Many of those repositories carry no license, so the files themselves are not included; `reproduce.sh` fetches them
through the GitHub API (it needs an authenticated `gh`) and reruns the check with the image's ESBMC. `REPORT.md`
records the corpus, the harness edits, and the results of an earlier build; the paper's numbers, with the image's
build, are in `single-build-2026-10-22/thirdparty/` of the results archive, which keeps only the logs and
`results.json`, not the programs.

## Updating a pin

Change the commit in `Dockerfile`, push, and record the new digest from the workflow summary. The `ws0/` folder is a copy of `ESBMC_PLC/ws0` (cases, reproducers, runner); refresh it when those change.

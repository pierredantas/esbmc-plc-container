# ESBMC-PLC artifact

A pinned container for the ESBMC-PLC work: ESBMC with the Ladder Diagram front end, the IEC 61131-3 benchmark suite, the Beremiz/MATIEC toolchain behind the suite's second route, and the WS0 defect reproducers.

Every source is fixed in `Dockerfile`: the Ubuntu 24.04 base by digest, and ESBMC, the suite, Beremiz and MATIEC by commit. The `image` workflow builds it on an amd64 runner, runs `check.sh` inside it, and publishes it to GHCR tagged with this repository's commit. Cite the image by the digest the workflow prints, not by tag.

## Use

```
docker run --rm ghcr.io/pierredantas/esbmc-plc-container@sha256:<digest>            # runs check-image
docker run --rm -it ghcr.io/pierredantas/esbmc-plc-container@sha256:<digest> bash   # esbmc, the suite, the tools
```

`check-image` runs the LD unit tests, `regression/ld` and `ld-verify`, the twelve WS0 reproducers, and one benchmark program through both routes.

Inside the container: ESBMC in `/opt/esbmc` (built, with `esbmc` on `PATH`), the suite in `/opt/suite`, the tools in `/opt/plc-tools` (`$PLC_TOOLS`), and the reproducers in `/opt/ws0`.

## Reproducing the TOSEM paper

The image pins the build behind *ESBMC-PLC: Verifying IEC 61131-3 Ladder Diagrams with a Validated Translation to
SMT-Based Model Checking*: ESBMC at fork commit `03ad8f91af` (tag `paper-pin-r3-2026-10-13`, which adds the prototype
`--ld-monitor-invariants` used in RQ4) and suite release v1.2.0. The run scripts are in `/opt/paper`.

```
docker run --rm -v "$PWD/out:/out" ghcr.io/pierredantas/esbmc-plc-container@sha256:<digest> reproduce-paper
```

`reproduce-paper` reruns every experiment (several hours on 8 cores). `paper/CLAIMS.md` maps each number in the paper
to its archived record in `results-2026-10-18.tar.gz`, attached to this repository's release, and to the step that
regenerates it. Run times depend on the machine; verdicts should not.

### Programs mined from GitHub (RQ2)

`paper/ESBMC_PLC/ws_thirdparty/` holds the GitHub search hits, a manifest with the repository, path, commit, blob, and
license of each of the 1,290 files, the 1,018 distinct programs after merging copies, and the per-program results.
Many of those repositories carry no license, so the files themselves are not included; `reproduce.sh` fetches them
through the GitHub API (it needs an authenticated `gh`) and reruns the check. This run used fork commit `1d7ad4332b`,
the image's commit plus four parser refusals; build it with `--build-arg ESBMC_COMMIT=1d7ad4332b60a32d69354af2abc1b4af50ee253e`.
`REPORT.md` records the corpus, the harness edits, and the results.

## Updating a pin

Change the commit in `Dockerfile`, push, and record the new digest from the workflow summary. The `ws0/` folder is a copy of `ESBMC_PLC/ws0` (cases, reproducers, runner); refresh it when those change.

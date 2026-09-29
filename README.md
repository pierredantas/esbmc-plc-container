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

## Updating a pin

Change the commit in `Dockerfile`, push, and record the new digest from the workflow summary. The `ws0/` folder is a copy of `ESBMC_PLC/ws0` (cases, reproducers, runner); refresh it when those change.

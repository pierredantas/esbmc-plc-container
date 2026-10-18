# Pinned build of ESBMC with the Ladder Diagram front end, the IEC 61131-3
# benchmark suite, and the Beremiz/MATIEC toolchain the suite's second route
# (PLCopen XML -> ST -> C -> ESBMC's C front end) runs on.
#
# Build from the repository root:
#   docker build --platform linux/amd64 -t esbmc-plc:paper .
#
# ESBMC is pinned at the fork commit behind the TOSEM paper (tag paper-pin-r3-2026-10-13), which
# carries the prototype --ld-monitor-invariants option; the suite at release v1.2.0.
#
# Every source is fixed by commit and the base image by digest. amd64 only:
# ESBMC's bundled 32-bit libc needs g++-multilib, which arm64 Ubuntu lacks.
FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3

ARG ESBMC_REPO=https://github.com/pierredantas/esbmc.git
ARG ESBMC_COMMIT=03ad8f91afe393b0cc58620c35fd3885c2ae3e25
ARG SUITE_REPO=https://github.com/pierredantas/esbmc-plc-benchmark-suite.git
ARG SUITE_COMMIT=6d1e3c3d3dde1188fa00a7397c36f1ecfaf8f843
ARG BEREMIZ_COMMIT=df4370ce2718e328297b31cf46e7fbca6210d55c
ARG MATIEC_COMMIT=7949c0bda1787de9c7cacaa4876ede49f85262dd

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential cmake ninja-build git wget curl ca-certificates \
      gcc-14 g++-14 g++-multilib libc6-dev-i386 \
      libboost-all-dev libgmp-dev libssl-dev bison flex \
      autoconf automake libtool \
      python3 python3-yaml python3-lxml \
    && rm -rf /var/lib/apt/lists/*

# fetch_commit DIR REPO COMMIT: a shallow fetch of exactly one commit.
RUN printf '#!/bin/sh\nset -e\nmkdir -p "$1" && cd "$1" && git init -q && git remote add origin "$2" && git fetch -q --depth 1 origin "$3" && git checkout -q FETCH_HEAD\n' \
      > /usr/local/bin/fetch_commit && chmod +x /usr/local/bin/fetch_commit

# ESBMC, configured as CI's "Run regression/ld and ld-verify" job.
RUN fetch_commit /opt/esbmc "$ESBMC_REPO" "$ESBMC_COMMIT" \
 && cmake -S /opt/esbmc -B /opt/esbmc/build -GNinja \
      -DCMAKE_BUILD_TYPE=RelWithDebInfo \
      -DCMAKE_C_COMPILER=gcc-14 -DCMAKE_CXX_COMPILER=g++-14 \
      -DDOWNLOAD_DEPENDENCIES=On \
      -DENABLE_BOOLECTOR=Off -DENABLE_YICES=Off -DENABLE_BITWUZLA=Off \
      -DENABLE_GOTO_CONTRACTOR=Off -DENABLE_SOLIDITY_FRONTEND=Off \
      -DENABLE_JIMPLE_FRONTEND=Off -DENABLE_PYTHON_FRONTEND=Off \
      -DENABLE_CSMITH=Off -DENABLE_LD_FRONTEND=On -DENABLE_Z3=On \
      -DBUILD_TESTING=On -DENABLE_REGRESSION=On \
 && cmake --build /opt/esbmc/build -j"$(nproc)" --target \
      esbmc ld-verify ld_parser_test ld_property_test ld_ir_gen_test

# MATIEC's iec2c and Beremiz's PLCopen-to-ST generator, where the suite's
# runner/record_via_c.py looks for them ($PLC_TOOLS).
RUN fetch_commit /opt/plc-tools/matiec https://github.com/beremiz/matiec.git "$MATIEC_COMMIT" \
 && cd /opt/plc-tools/matiec && autoreconf -i && ./configure && make -j"$(nproc)" \
 && fetch_commit /opt/plc-tools/beremiz https://github.com/beremiz/beremiz.git "$BEREMIZ_COMMIT"
COPY plc-tools/xml2st.py /opt/plc-tools/xml2st.py

RUN fetch_commit /opt/suite "$SUITE_REPO" "$SUITE_COMMIT"

# The WS0 reproducers (ESBMC_PLC/ws0) and the checks that validate the image.
COPY ws0/cases.tsv ws0/run_repro.sh /opt/ws0/
COPY ws0/repro /opt/ws0/repro
COPY check.sh /usr/local/bin/check-image

# The paper's run scripts expect the suite and MATIEC beside them, as in the authors' tree.
COPY paper /opt/paper
RUN ln -s /opt/suite /opt/paper/ESBMC-Benchmark-Suite \
 && ln -s /opt/plc-tools /root/plc-tools \
 && ln -s /opt/paper/reproduce.sh /usr/local/bin/reproduce-paper

ENV PATH=/opt/esbmc/build/src/esbmc:/opt/esbmc/build/tools/ld-verify:$PATH \
    PLC_TOOLS=/opt/plc-tools \
    SUITE=/opt/suite \
    ESBMC=/opt/esbmc/build/src/esbmc/esbmc
WORKDIR /opt/suite
CMD ["check-image"]

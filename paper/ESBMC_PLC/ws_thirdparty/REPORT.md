# Third-party LD programs mined from GitHub (October 19, 2026)

## Corpus

- GitHub code search for `leftPowerRail` in XML files, sliced by file size: 1,389 hits.
- Our own repositories excluded (pierredantas, esbmc, lucasccordeiro): 1,290 files from 173 repositories,
  all downloaded (`results/manifest.json`, with repository, path, blob sha, license, and head commit).
- Duplicates merged when `<types>` and `<instances>` agree after dropping timestamps and whitespace:
  1,059 distinct programs, 1,018 with an LD body (`results/programs.json`).
- Two groups, reported apart:
  - **projects**: 413 programs from 138 repositories. Mostly OpenPLC and Beremiz teaching, lab, and hobby
    projects; a few tool test files (Beremiz forks, MATIEC examples) and AI-related repositories.
  - **datasets**: 605 programs from three security and clone-detection datasets (PLC-Defuser 545,
    LLD_Security 59, a copy of PLC-LD, and one clone-detection set). PLC-Defuser variants are near copies
    of a few base programs.

## Tool and harness

- ESBMC fork commit `1d7ad4332b`: the paper pin `03ad8f91af` plus the four refusals of esbmc/esbmc#8858.
  Release build in `~/Claude/esbmc-tp/build`. Sanity check: `ws1/tv_corpus.py` on `g_ton_single`,
  `g_tof_hold`, `g_ctu_saturate`, `g_rtrig_edge` gives 4 equivalent and, with `--control`, 4 detected, as
  `CLAIMS.md` records for the pin.
- `scripts/tp_run.py`: front end alone; if it accepts, `ws1/tv_ref.py` builds the MATIEC reference and
  `--ld-tv-check` compares one scan; every UNSAT is rerun against a reference with one compared BOOL
  flipped (control). No property of the program is used.
- Harness adjustments, applied to a copy that both sides read (none changes what a scan computes):
  I/O addresses removed (MATIEC makes located variables pointers the harness cannot havoc); PLCopen
  namespace and missing file headers added; `--` inside XML comments split; an instance or task named
  like its POU type renamed (MATIEC refuses the clash). A variable the LD side does not treat as free is
  dropped from the comparison and from the reference's havocs. Audit of the 107 dropped variables:
  102 unused, 4 never written with an initial value (a preset kept constant, P4), 1 written, in a dataset
  program that is SAT anyway.

## Results

| | projects | datasets |
|---|---|---|
| Distinct LD programs | 413 (138 repos) | 605 (3 repos) |
| Accepted by the front end | 117 (28%, 48 repos) | 39 (6%) |
| Equivalent (UNSAT), control SAT | 104 | 2 |
| Different (SAT) | 0 | 37, all with user function blocks |
| Harness could not run | 13 | 0 |

- Every one of the 106 UNSAT queries was matched by a SAT control.
- The 37 differences are all in PLC-LD copies whose programs use user function blocks, the EN/ENO cause
  the paper already reports for the PLC-LD programs in the suite (Section 5.3, Table 5). Not narrowed
  per variable here.
- Equivalent project programs are small: median 6 contacts, coils, and blocks; largest 77; 27 use blocks
  (TON 22, TOF 8, CTU 2, TP 2). Query time median 1.3 s, max 16.9 s.
- Harness failures (13): MATIEC or Beremiz cannot load the file (7), the reference builder has no free
  value for TIME variables (4), one query timed out at 120 s, one correlation with nothing to compare.

## Why the front end refused 296 project programs

| Cause | Programs |
|---|---|
| Operator block (ADD, MOVE, GT, AND, ...) wired outside the subset | 58 |
| Integer type other than BOOL, INT, DINT (UINT, WORD, SINT, ...) | 35 |
| More than one task, program, or instance | 26 |
| Another language in the project (ST, SFC, FBD, IL body) | 25 |
| Timer or counter wiring outside the subset (pins, ENO, ET, CTUD) | 26 |
| Coil feeding further elements (series coil) | 20 |
| Negated or edge coil | 19 |
| Initial value or task interval the parser cannot read | 14 |
| Vendor or library block (MQTT, Modbus, ...) | 11 |
| SR or RS bistable | 11 |
| String, array, or struct type | 9 |
| Undeclared variable, empty program, non-constant preset | 19 |
| Other (connectors, user FB with LD body, cycles, ...) | 23 |

## What this says for the paper

- On 104 programs written by 48 unrelated authors, the translation agrees with MATIEC after one scan for
  every input and pre-state, and no project program shows a difference. That is RQ2 evidence on code
  nobody on the team wrote.
- The subset covers 28% of public project programs. The paper should say so. Five additions would
  cover most refusals: operator blocks on data wires, more integer types, series and negated coils,
  SR/RS, and multiple tasks.
- No properties were checked, so this adds nothing to RQ1 verdict counts.
- Licenses: many repositories have none. Measure on them, but ship the manifest and a fetch script, not
  the files.

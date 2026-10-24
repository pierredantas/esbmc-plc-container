# Second C verifier on MATIEC's C (item 12): attempts, 2026-10-23

Harnesses: the C route's harness.c, preprocessed in SV-COMP style (harness.i: __VERIFIER_nondet_*, reach_error()),
exported by viac_export.py; ESBMC finds the known violations in harness.i as in harness.c.

## 2LS 0.10.0 (commit 9a9ad377, built locally on macOS arm64; -Wno-error=#warnings added to src/config.inc)
- `2ls --k-induction`, 120 s watchdog, no facts. Results in ../twols-120-2026-10-23 and ../twols-soundness-2026-10-23.
- On the 125 LD-SAFE variants: 117 SUCCESSFUL, 8 crashes (all TON/TOF/TP programs: internal invariant
  `converted.has_value()` in SSA renaming).
- Soundness check on the 83 LD-VIOLATION variants: 70 FAILED, 11 SUCCESSFUL, 2 crashes (TP). In 10 of the 11
  SUCCESSFUL cases ESBMC finds the violation in the same harness.i (BMC, unwind 4). 2LS verdicts are unsound here
  and are not used.

## CPAchecker 4.2.2 (OpenJDK 21, Bash 5; bundled x86_64 Z3 replaced by the arm64 Z3 4.13.3 of the ESBMC toolchain)
- kInduction-kipdrdfInvariants with sv-comp-reachability.spc: UNKNOWN on every harness; the C frontend rejects
  __builtin_va_arg in MATIEC's variadic standard functions.
- After dropping functions main cannot reach (strip_unreachable.py; ESBMC still finds the violation in the stripped
  file): Boolean harnesses parse, but k-induction and plain bmc-incremental both hit the 120 s CPU limit in the first
  satisfiability check, including on a harness whose violation ESBMC finds in about 1 s. Timer harnesses still use
  the variadic ___LE_TIME and are rejected. The Z3 substitution is a possible cause; it was not resolved.
- Not used.

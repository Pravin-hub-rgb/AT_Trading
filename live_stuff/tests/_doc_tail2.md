---

## 11. Updated verdicts after independent verification

§7.1 stands, now confirmed by a second lane:

1. **ext_stop 1.5→2.5 on lb30-w0 is LEGIT** - independently verified +34.8R
   NET to the decimal. Lane-specific: OPT-cd10-w0 ADOPT (+291.4 vs +259.4);
   OPT-cd0 REJECT (+290.0 vs +322.5); A4 REJECT (+141.3 vs +203.3); w24 lanes
   keep ext1.5 (lb30-w24 peaks at 2.0 = +197.2, still below w0-ext2.5).
2. **Wage gate implementation is correct** on current code - 5/5 fine match
   (§10.2) + 4/4 coarse matrix (§4.2) + 4/4 user fine table (§4.3).
3. **w24 is NOT dead globally.** OPT-cd10 + w24 + ext1.5 = +337.7 / DD 19.2,
   zero losing WF segments - overall champion. But on lb30 it is NEGATIVE at
   ext1.5 (§10.3 correction): base-dependent, not universal.
4. **Anti-synergy holds**: w0 → wide ext; w24 → tight ext. Never mix.

---

## 12. Standing rules for any bot/lane running experiments in this repo

1. **Reference numbers:** only outputs of the current, gate-validated rebuild
   (`exp40c`/`exp41` + `build_module()` from `test_experiments_craze.py`) may
   be cited. The deleted-harness N5 rows are dead - never use them as expected
   values (§10.3).
2. **Gates before results:** identity gate + Phase A external matrix must pass
   AND be printed before reading any experiment output. Abort on mismatch.
3. **Label the scoring mode on every number:** coarse-gross or fine-NET.
   Never compare a coarse claimed value against a fine verified value (this
   produced the bogus "off by 1 trade" rows in the first §10.2 draft).
4. **Fine means 1m fills + fee + slip + funding** via
   `fine_ltf=_load_fine_1m(...)`. Never a bare-15m re-sim with costs bolted
   on. If 1m data is unavailable, report coarse only and say so.
5. **Base case or nothing:** experiments run on the identity-gated base (BP);
   new knobs go through the `build_module()` patch list with an asserted
   anchor string. No engine forks, no silent param edits.
6. **Delete nothing:** harnesses, verify scripts, output logs all stay on
   disk. A verification nobody can rerun is worth nothing (test_verify_wage.py
   was deleted after producing §10 - do not repeat that).
7. **Every number in a doc cites its source file** (script + output log).
8. **Docs are UTF-8 clean.** Double-encoded punctuation is a bug; write
   ASCII-safe if unsure of the toolchain.
9. **Verdicts are lane-specific.** "X works" without naming the base lane is
   not a verdict.
10. **Champion claims need walk-forward** (exp41-style segmented WF, fixed
    configs). Full-sample NET alone is not adoption-grade.

# RETIRED BOOKS

**Two retirement passes. Read this before restoring anything.**

---

## PASS 1 - 2026-10-08, measured on the chain as it stood then

The owner's rule, in his words:

> "any book jisme IS ya OOS negative hai usko hata"
> "OOS 50R se low hai to hata"

```
BAR 1   IS < 0  OR  OOS < 0      -> ERA_FITTED (28) + BOTH_NEGATIVE (1)
BAR 2   0 <= OOS < 50            -> LOW_OOS (52)
ALIAS   dangling alias           -> DANGLING_ALIAS (1)
``

---

## PASS 2 - 2026-10-14, re-applied to the CORRECTED chain

The engine moved after pass 1: B1 arming (`77711a6`), V13 (`88ecd00`),
the volatile-B1 colour rule and the same-bar duplicate-pivot fix
(`5d6cab2`, `d71304f`). Chain 2753 swings / 7505 marks -> **2840 / 7734**.
Every pin was re-measured (`dd02cf1`, 120 books, both eras).

**Pass 1's bar 1 was therefore re-applied to the new numbers rather than
trusted.** It had been decided on the old chain, and a book that was
positive then can be negative now.

The owner's rule, restated and closed for discussion:

> "any of on IS or OOS is negative retire that 's it.. no more discussion"
> "yup retire them remove them from results"

```
IS < 0  OR  OOS < 0  ->  RETIRE          ->  69 books
``

**All 69 were still ACTIVE in the registry** - pass 1 had not caught them
because they were positive on the old chain.

### Both eras negative (6) - failed outright

| book | IS n | IS net | OOS n | OOS net |
|---|---:|---:|---:|---:|
| `decayC_c` | 250 | **-40.97** | 156 | **-32.63** |
| `decayC_u` | 225 | **-34.11** | 134 | **-33.19** |
| `decayE_c` | 213 | **-1.48** | 118 | **-46.87** |
| `gap_campaign3` | 291 | **-40.62** | 172 | **-0.18** |
| `gap_entry_cap3` | 292 | **-45.48** | 172 | **-0.22** |
| `skipwinhalt_multi_sw10` | 289 | **-22.14** | 162 | **-10.60** |

### Era-fitted (63) - IS positive, OOS negative

This is the overfit shape: the book fits the era it was tuned on and
loses money on the one it was not. 63 of the 69 are this.

| book | IS n | IS net | OOS n | OOS net |
|---|---:|---:|---:|---:|
| `age50_utcsat_multi_sw10` | 376 | +95.68 | 221 | **-41.03** |
| `b2doji_utcsat_multi_sw10` | 354 | +110.72 | 197 | **-24.26** |
| `baseline_no_partial_sw10` | 420 | +123.59 | 264 | **-40.33** |
| `bm05_multi_sw10` | 391 | +142.04 | 238 | **-12.25** |
| `bm05_utcsat_multi_sw10` | 357 | +145.21 | 216 | **-37.39** |
| `cap12d` | 416 | +134.43 | 244 | **-21.65** |
| `cap16d` | 421 | +127.39 | 251 | **-31.05** |
| `cap20d` | 431 | +147.41 | 263 | **-47.63** |
| `cap32d` | 450 | +198.73 | 273 | **-30.28** |
| `cap48d` | 469 | +216.21 | 283 | **-50.10** |
| `causalsl_multi_sw10` | 417 | +115.40 | 250 | **-18.80** |
| `causalsl_utcsat_multi_sw10` | 379 | +131.30 | 224 | **-22.39** |
| `champion_multi_sw10` | 420 | +125.82 | 249 | **-45.20** |
| `champion_multi_sw10_entry1` | 420 | +130.54 | 249 | **-45.25** |
| `champion_multi_sw10_entry_both` | 416 | +124.46 | 247 | **-50.44** |
| `champion_multi_sw10_leg` | 421 | +127.39 | 251 | **-31.05** |
| `champion_multi_sw10_leg_no_entry` | 420 | +130.54 | 249 | **-45.25** |
| `chopband_multi_sw10` | 373 | +97.65 | 240 | **-29.13** |
| `combined_b2age_utcsat_multi_sw10` | 344 | +92.51 | 194 | **-24.63** |
| `curfew624_utcsat_multi_sw10` | 312 | +182.26 | 191 | **-28.71** |
| `decayA_c` | 421 | +127.39 | 251 | **-31.05** |
| `decayA_u` | 384 | +113.83 | 224 | **-42.77** |
| `decayB_c` | 278 | +92.38 | 132 | **-23.28** |
| `decayB_u` | 247 | +179.20 | 114 | **-4.14** |
| `decayE_u` | 189 | +52.18 | 101 | **-29.44** |
| `ext25_utcsat_multi_sw10` | 382 | +138.04 | 223 | **-37.46** |
| `ext2_utcsat_multi_sw10` | 356 | +147.07 | 213 | **-38.53** |
| `ext35_utcsat_multi_sw10` | 384 | +113.83 | 224 | **-42.77** |
| `ext4_utcsat_multi_sw10` | 384 | +113.83 | 224 | **-42.77** |
| `fsexit4_c` | 422 | +138.22 | 254 | **-17.78** |
| `fsexit6_c` | 434 | +170.04 | 270 | **-6.09** |
| `fsswing6_c` | 422 | +97.88 | 259 | **-14.71** |
| `gap_campaign4` | 328 | +39.00 | 193 | **-21.89** |
| `gap_cd15` | 410 | +117.24 | 242 | **-14.73** |
| `gap_cd5` | 427 | +149.89 | 256 | **-39.44** |
| `gap_cooldown4` | 427 | +151.81 | 256 | **-42.24** |
| `gap_curfew_a4_b8` | 405 | +71.25 | 244 | **-35.11** |
| `gap_mcl5` | 466 | +128.37 | 271 | **-3.03** |
| `gap_persist1` | 420 | +123.59 | 264 | **-40.33** |
| `gap_r_cap1` | 397 | +81.72 | 233 | **-59.35** |
| `gap_r_cap3` | 408 | +84.74 | 249 | **-31.60** |
| `gap_skip_decisive` | 421 | +127.39 | 188 | **-25.28** |
| `gap_slbuf010` | 422 | +159.98 | 250 | **-28.75** |
| `gap_trail_prevbar` | 426 | +152.28 | 235 | **-17.73** |
| `gap_wage24` | 308 | +149.33 | 191 | **-18.76** |
| `gap_wage28` | 294 | +141.72 | 185 | **-0.14** |
| `gap_window_r_cap2` | 397 | +81.72 | 243 | **-45.06** |
| `htfrr25_multi_sw10` | 378 | +75.64 | 210 | **-24.72** |
| `htfrr4_multi_sw10` | 330 | +100.91 | 191 | **-47.62** |
| `persist3_multi_sw10` | 425 | +137.59 | 267 | **-28.98** |
| `persist4_multi_sw10` | 421 | +125.98 | 262 | **-34.49** |
| `persist5_multi_sw10` | 421 | +127.39 | 262 | **-31.30** |
| `persist6_multi_sw10` | 421 | +127.39 | 256 | **-29.52** |
| `trail_delay1` | 426 | +152.28 | 235 | **-17.73** |
| `trail_half` | 411 | +152.66 | 239 | **-13.23** |
| `trail_half_delay1` | 411 | +159.99 | 232 | **-5.20** |
| `utcsat_cap16d` | 384 | +113.83 | 224 | **-42.77** |
| `utcsat_chopband_multi_sw10` | 335 | +85.20 | 213 | **-40.57** |
| `utcsat_entry_minus_1` | 380 | +100.97 | 223 | **-51.88** |
| `utcsat_multi_sw10` | 384 | +113.83 | 224 | **-42.77** |
| `wage12_utcsat_multi_sw10` | 329 | +159.08 | 202 | **-15.57** |
| `wage24_multi_sw10` | 308 | +149.33 | 191 | **-18.76** |
| `wage24_utcsat_multi_sw10` | 276 | +163.19 | 175 | **-24.49** |

---

## THREE BOOKS THAT LOSE BY LESS THAN 0.25R ARE STILL RETIRED

`gap_wage28` -0.14, `gap_campaign3` -0.18, `gap_entry_cap3` -0.22 on the
negative era. The rule was applied literally with no exception, because
an exception becomes a loop of "is this one an exception". Recorded here
so the decision is visible rather than looking like an oversight.

---

## SIX BOOKS ARE THE SAME STRATEGY UNDER SIX NAMES

| duplicate cluster | IS | OOS |
|---|---|---|
| `decayA_u`, `ext35_utcsat`, `ext4_utcsat`, `utcsat_cap16d`, `utcsat_multi_sw10`, +1 | 384 / +113.83 | 224 / -42.77 |
| `champion_multi_sw10_entry1`, `..._leg_no_entry` | 420 / +130.54 | 249 / -45.25 |
| `cap16d`, `champion_multi_sw10_leg`, `decayA_c` | 421 / +127.39 | 251 / -31.05 |
| `baseline_no_partial_sw10`, `gap_persist1` | 420 / +123.59 | 264 / -40.33 |
| `trail_delay1`, `gap_trail_prevbar` | 426 / +152.28 | 235 / -17.73 |
| `gap_wage24`, `wage24_multi_sw10` | 308 / +149.33 | 191 / -18.76 |

So the 69 keys are roughly a dozen distinct ideas with variant spellings.
All are retired together - leaving one spelling alive would put a
known-negative book back on the list.

---

## WHAT RETIREMENT DOES AND DOES NOT DO

**Definitions are untouched.** The configs stay in the six family
modules. `registry/retired.py` holds KEYS, and `registry/__init__.py`
subtracts them from the merged dict after the merge.

**Consequences worth stating:**

- A retired book is still fully runnable: `archived()` returns the full
  config and pins, read live from the family modules at call time, so the
  archive cannot drift from the definition.
- Restoring is one line - remove the key from `RETIRED`.
- `book()`, `shortlisted()`, `alias_of()` and every harness keep working;
  retired keys simply stop resolving, which is the same observable
  behaviour as deletion.

**One coupling had to be fixed.** `exp_tf_family.py` builds its identity
gate from `EXPERIMENTS[...]['pins']` at module scope, and
`champion_multi_sw10` and `utcsat_multi_sw10` are both in this pass. A
plain lookup raised `KeyError` at import and took down every harness that
imports that module. `_expected_pins` now falls back to `archived()`,
which is the same dict, so the gate still compares against real pins.

---

## STATE AFTER THIS PASS

```
registry          162 -> 93 active books
RETIRED           154 keys
pinverify         51 books checked, 0 mismatches
_results.json     25 books, none of them retired
BTC dropdown      1 retired book pulled - utcsat_entry_minus_1, OOS -51.88R
``

**The 51 survivors are every book positive in both eras.** That is the
complete list of what is still a candidate.

---

## HOW TO RESTORE ONE

```python
# backtest/tests/registry/retired.py
RE_RETIRED_ANY_ERA_NEGATIVE -= {'book_name'}
```

Then re-run `exp_pinverify.py`. The pins are unchanged - retirement does
not touch them - so restoring does not require a re-measurement.

# SL-Candle Reclaim Re-Entry — Descriptive Gate (2026-09-25)

**Idea (user):** After a losing trade, the 15m candle that hit the SL — re-enter SAME direction when price breaks that candle's high (long) / low (short). Stop-hunt reclaim confirmation: the dump that stopped us out gets reclaimed => enter again.

**Status: DEAD at Phase 1 (descriptive gate). Phase 2 (path-true) NOT run per pre-registration. No engine kwargs added. No production change.**

Harness `backtest/tests/exp_sl_reclaim_walk.py`; JSON `_sl_reclaim_walk_results.json`; identity gate IDENTICAL (`340t/+225.3R`).

## Pre-registered (frozen before run)

- **Eligibility:** every baseline loss (`r < 0`), both configs, IS + OOS.
- **Level:** exit 15m candle high (long) / low (short).
- **Trigger TOUCH:** first 1m bar strictly after the exit fill bar with `hi >= level` (long); fill = `max(level, open)` (gap-aware stop).
- **Trigger CLOSE:** first 15m close beyond level after the exit candle; fill = that close.
- **Wait:** `exit_ts + 240 min`, else timeout (miss). Conservative same-bar rule: touch-fill bar also touching the re-SL => SL first.
- **Re-SL:** exit-candle low/high ± 0.25·ATR15 (engine mirror); same engine risk guards.
- **Proxy exit:** 1m first-passage SL vs +1R/+2R/+3R (fixed targets, NO trail), 16-day horizon; binary = +1R touched before SL wins.
- **Cost proxy:** 0.125% notional in R (fee 0.055%×2 + slip 0.005%/0.010%; funding excluded).
- **Gate:** Phase 2 runs ONLY if binary net > 0 on BOTH eras in >=1 config × >=1 trigger; else DEAD here.

## Results

### champion_multi_sw10 (IS: 500 trades / 350 losses; OOS: 279 / 201)

| scope | mode | fill | timeout | r1win | sl1 | r2+ | r3 | gross* | net* | fillMed |
|---|---|---|---|---|---|---|---|---|---|---|
| IS | touch | 241 | 109 | 107 | 134 | 26 | 53 | −27.0 | **−91.7** | 23m |
| IS | close | 202 | 148 | 106 | 96 | 21 | 44 | +10.0 | **−35.9** | 45m |
| OOS | touch | 132 | 69 | 68 | 64 | 12 | 27 | +4.0 | **−15.4** | 30m |
| OOS | close | 121 | 80 | 58 | 62 | 6 | 28 | −4.0 | **−18.7** | 54m |

### age10_dirmatch_swingpause_single_sw10 (IS: 130 / 60 losses; OOS: 76 / 46)

| scope | mode | fill | timeout | r1win | sl1 | r2+ | r3 | gross* | net* | fillMed |
|---|---|---|---|---|---|---|---|---|---|---|
| IS | touch | 41 | 19 | 21 | 20 | 3 | 10 | +1.0 | **−8.2** | 21m |
| IS | close | 34 | 26 | 20 | 14 | 0 | 11 | +6.0 | **−0.9** | 45m |
| OOS | touch | 29 | 17 | 12 | 17 | 3 | 5 | −5.0 | **−9.2** | 35m |
| OOS | close | 26 | 20 | 10 | 16 | 4 | 3 | −6.0 | **−9.2** | 49m |

### Gate

| config | mode | net IS | net OOS | Phase 2 |
|---|---|---|---|---|
| champion multi | touch | −91.7 | −15.4 | no |
| champion multi | close | −35.9 | −18.7 | no |
| age10 single | touch | −8.2 | −9.2 | no |
| age10 single | close | −0.9 | −9.2 | no |

**8/8 cells negative. `phase2_warranted = False`.**

## Reading

1. **Binary proxy is a coin flip even gross.** Win rates: champion touch IS 44.4% (107/241), close IS 52.5%, OOS touch 51.5% (68/132); age10 46–59%. The reclaim of the SL candle does NOT imply the next leg goes in our direction — the same structure that stopped us out is being re-entered with a WIDER re-SL (full exit-candle range + 0.25 ATR below), so costs eat the marginal edge.
2. **Cost-in-R is the killer on wide stops.** Champion touch IS: gross −27 but net −91.7 (cost ≈ 65R over 241 fills) — re-SL spans the whole exit-candle range, risk/entry is large, but 0.125% still translates to meaningful R, and the binary 1R target barely covers it.
3. **Touch beats close on speed (23–35m vs 45–54m fill wait) but not on net.** No arm is positive anywhere; the pre-registered BOTH-eras rule fails on every cell.
4. **Coverage is decent** (49–69% of losses reclaim within 4h; 19–36% timeout) — the *mechanism exists* often, it just has no expectancy. This matches the family history: sweep-reclaim (DEAD 2026-09-18), retest-as-filter (24.26), dip→reclaim (24.31) — **reclaim/confirmation triggers on this engine have now failed 4/4 times.**

## Verdict

**DEAD at descriptive gate.** Pre-registered rule says a path-true run cannot recover −1 to −92R of negative binary expectancy through trail/coverage effects alone. Phase 2 skipped; no kwargs; no production change.

**Caveats:** proxy has no trail (fixed 1R target), funding excluded, eligibility = all losses incl. trail-exits; but gate requires BOTH eras positive in raw proxy — nothing came close.

## Untested families (backlog)

Position-sizing / add-on re-entries were the remaining untested class (see EXPERIMENT_SUMMARY.md §Untested Families): pyramid/scale-in Phase 1 run 2026-09-25 (24.43, thin/fragile) then Phase 2 run + CLOSED 2026-09-26 (24.87), same-window rewin tested+closed (24.61), revenge re-entry tested+dead (24.44).

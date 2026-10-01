# Winner Early-Path Autopsy — direct vs pullback-first (2026-09-25)

**Status:** descriptive study, no gates, no production change.  
**Question:** kya big winners seedha chalte hain (direct) ya pehle pullback dete hain?  
**Gap closed:** `LOSS_AUTOPSY.md` death-path taxonomy covered **losses only**; winner tPeak/retest/first-0.5R were computed inside `exp_deathpath_autopsy.py` but stripped by `pack()` — never reported.  
**Harness:** `backtest/tests/exp_winner_path_autopsy.py` · **JSON:** `_winner_path_autopsy_results.json` · identity gate IDENTICAL (340t/+225.3R) · run 64.8s  
**Configs:** champion_multi_sw10, age10_dirmatch_swingpause_single_sw10 · scopes IS (2023-26) + OOS (2021-22) · fine 1m walk from entry (signal-bar close) to exit.

## Metric definitions

| col | meaning |
|---|---|
| `direct%` | reached +0.5R with <0.10R adverse before it |
| `pbFirst%` | adverse ≥0.10R before first +0.5R (pullback-first) |
| `neverP%` | never reached +0.5R before exit |
| `f05med / f10med` | median 1m bars to first +0.5R / +1R |
| `maeB4med` | median worst adverse R before +0.5R |
| `tPk%` | median peak-bar as % of hold (late = runner) |
| `retest%` | after +0.5R, later came back to AT entry (full touch) |
| `dipB4%` | touched ≤entry before first +0.5R (or before death) |
| `deep<.5%` | adverse ≥0.5R before first +0.5R (deep dip first) |

## Results (all four lane×scope cells)

### champion_multi_sw10

| scope | cohort | n | NET | direct% | pbFirst% | neverP% | f05med | maeB4med | tPk% | retest% | deep<.5% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IS | loss | 350 | −321.8 | 14.6 | 38.6 | **46.9** | 64 | **0.78** | 23 | 53.1 | **59.7** |
| IS | win_0_4 | 98 | +130.3 | 23.5 | 76.5 | 0 | 102 | 0.26 | 66 | 43.9 | 24.5 |
| IS | win_4_10 | 35 | +215.6 | 14.3 | 85.7 | 0 | 73 | 0.21 | 70 | 45.7 | 28.6 |
| IS | **monster_10+** | 17 | **+421.1** | 35.3 | 64.7 | 0 | **7** | **0.14** | 75 | 58.8 | 29.4 |
| IS | winners_all | 150 | +767.0 | 22.7 | **77.3** | 0 | 79 | 0.25 | 69 | 46.0 | 26.0 |
| OOS | loss | 201 | −178.9 | 17.4 | 35.3 | 47.3 | 60 | 0.62 | 23 | 52.7 | 54.7 |
| OOS | win_0_4 | 58 | +87.0 | 20.7 | 79.3 | 0 | 208 | 0.31 | 67 | 53.4 | 31.0 |
| OOS | win_4_10 | 14 | +92.5 | 35.7 | 64.3 | 0 | 62 | 0.16 | 75 | 28.6 | 7.1 |
| OOS | **monster_10+** | 6 | **+105.1** | **0.0** | **100.0** | 0 | 270 | 0.67 | **83** | 66.7 | 66.7 |
| OOS | winners_all | 78 | +284.6 | 21.8 | **78.2** | 0 | 173 | 0.31 | 69 | 50.0 | 29.5 |

### age10_dirmatch_swingpause_single_sw10

| scope | cohort | n | NET | direct% | pbFirst% | neverP% | f05med | maeB4med | tPk% | retest% | deep<.5% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IS | loss | 60 | −51.0 | 18.3 | 61.7 | 20.0 | 81 | 0.43 | 36 | 80.0 | **41.7** |
| IS | winners_all | 70 | +527.5 | 22.9 | **77.1** | 0 | 65 | 0.27 | 74 | 58.6 | 31.4 |
| IS | monster_10+ | 14 | +382.1 | 28.6 | 71.4 | 0 | 15 | 0.30 | 75 | 57.1 | 35.7 |
| OOS | loss | 46 | −40.3 | 26.1 | 54.3 | 19.6 | 74 | 0.39 | 45 | 80.4 | 34.8 |
| OOS | winners_all | 30 | +95.1 | 16.7 | **83.3** | 0 | 92 | 0.32 | 69 | 53.3 | 30.0 |
| OOS | monster_10+ | 1 | +13.6 | 0.0 | 100.0 | 0 | 113 | 0.31 | 83 | 100.0 | 0.0 |

### Retest-entry capture rollup (Phase B miss proxy)

| lane×scope | winners touched ≤entry BEFORE +0.5R | monsters | missed win-R | winner wait median |
|---|---|---|---|---|
| champ IS | **150/150 (100%)** | 17/17 | +0.0 | **0** 1m-bars |
| champ OOS | **78/78 (100%)** | 6/6 | +0.0 | **0** 1m-bars |
| age10 IS | **70/70 (100%)** | 14/14 | +0.0 | **0** 1m-bars |
| age10 OOS | **30/30 (100%)** | 1/1 | +0.0 | **0** 1m-bars |

## Findings

1. **Winners are pullback-first, not direct (user's instinct correct).** 77–83% of winners show ≥0.10R adverse before +0.5R across all four cells. Only ~22% run straight. OOS monsters: **0/6 direct — 100% pullback-first** (n small). IS monsters are faster/firmer (f05med 7–15 bars, maeB4med 0.14–0.30R) — quick shallow dip then go.
2. **The winner/loss separator is depth + proof, not shape.** Losses: **47% never prove** (+0.5R never reached) and **55–60% dip ≥0.5R before dying**; winners dip shallow (deep<.5% = 26–31%, maeB4med 0.25–0.32R) then prove. Among *proved* trades the pullback-first share is similar (~72% losses vs ~77% winners) — "pulled back first" alone does not filter.
3. **Retest-at-entry has ZERO miss: 100% of winners AND monsters touch ≤entry before +0.5R, median wait 0 one-minute bars.** The touch-at-bar-0 is partly mechanical (entry = breakout-bar close; first 1m bar almost always trades back through the level). So a resting limit **at entry** is a near-certain fill — no monster missed — but fills ≈ same price → likely near-no-op.
4. **A deep zone is the wrong direction.** Median winner dips only 0.25–0.32R below entry before proving; median loss dips 0.62–0.78R. Requiring a deep pullback fill (≥0.5R) would catch **more losers than winners** (deep<.5%: losses 55–60% vs winners 26–31%).
5. **Winners peak late (tPk 69–75%) and 46–59% come all the way back to entry after proving** — trail/hold structure dominates payoff (consistent with Stage verdicts); this study adds early-path shape only.
6. **Entry-miss fear for an entry-level retest order is unfounded** in this dataset — capture 100%, wait median 0. The open question is purely *fill-price improvement* (limit slightly below entry), which is a path-true question, not a descriptive one.

## Phase B decision

- **Retest as FILTER (skip trades that don't dip):** no signal — dip is ~100% universal, filter has no selectivity.
- **Deep pullback zone entry:** autopsy direction is *against* (losses dip deeper).
- **Limit-fill-below-entry (entry improvement, SL unchanged):** the only surviving variant — fill better price on the shallow pre-proof dip that winners take. Median winner dip 0.25R supports a modest limit (e.g. 0.10–0.15R below entry). Miss risk ~0 at entry level; at 0.1R depth unknown → path-true test must report miss count. **Pre-registered arms:** baseline / limit@entry−0.10R / limit@entry−0.25R, wait-cancel 4h; champion + age10, IS + OOS; report n, miss, monsters captured/missed, net-R, equity. If no both-sides positive → DEAD (fill-improvement family), log and close.

## Phase B result (path-true, run 2026-09-25)

**Harness:** `exp_retest_fill.py` · **JSON:** `_retest_fill_results.json` · identity IDENTICAL (340t/+225.3R) · 111.8s.
Mechanics: kwarg `exp_retest_fill` (depth in R) + `exp_retest_wait=240` min; fine 1m walk; fill at `min(limit, open)` long / `max(limit, open)` short; **SL price unchanged**, risk/target recomputed at fill; no touch in 4h → cancel (counted `miss`); entry relocates to fill's 15m bar, trail events from there only.

### champion_multi_sw10

| scope | arm | n | fill | miss | gross | net | dNet/yr | WR% | mono | mCap | mMiss | dd_net |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IS | baseline | 500 | – | 0 | +445.2 | +325.8 | 0.0 | 30.0 | 17 | 17 | 0 | 27.7 |
| IS | limit_0.10R | 461 | 461 | 47 | +420.7 | +299.9 | −7.1 | 28.2 | 15 | 14 | 3 | 41.6 |
| IS | limit_0.25R | 399 | 399 | 125 | +322.9 | +194.8 | −35.7 | 22.8 | 14 | 11 | 6 | 44.8 |
| OOS | baseline | 279 | – | 0 | +105.7 | +70.2 | 0.0 | 28.0 | 6 | 6 | 0 | 53.2 |
| OOS | limit_0.10R | 259 | 259 | 32 | +101.6 | +63.5 | −3.3 | 25.9 | 7 | 6 | 0 | 57.5 |
| OOS | limit_0.25R | 235 | 235 | 79 | +92.2 | +47.3 | −11.4 | 21.7 | 7 | 5 | 1 | 53.4 |

**Verdict: BOTH HURT at both depths → DEAD for multi.** Timeout kills coverage (47/125 IS signals cancelled), cost-in-R rises as risk shrinks (fees/funding are % of notional), DD nearly doubles (27.7→41.6), monsters lost (17→14→11).

### age10_dirmatch_swingpause_single_sw10

| scope | arm | n | fill | miss | gross | net | dNet/yr | WR% | mono | mCap | mMiss | dd_net |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IS | baseline | 130 | – | 0 | +476.5 | +435.7 | 0.0 | 53.9 | 14 | 14 | 0 | 8.7 |
| IS | limit_0.10R | 118 | 118 | 15 | +472.3 | +431.4 | −1.2 | 53.4 | 13 | 12 | 2 | 10.3 |
| IS | **limit_0.25R** | 94 | 94 | 43 | **+527.9** | **+489.3** | **+14.6** | 53.2 | 13 | 11 | 3 | **8.4** |
| OOS | baseline | 76 | – | 0 | +54.9 | +43.2 | 0.0 | 39.5 | 1 | 1 | 0 | 8.6 |
| OOS | limit_0.10R | 66 | 66 | 14 | +69.2 | +57.6 | +7.2 | 42.4 | 1 | 1 | 0 | 8.6 |
| OOS | **limit_0.25R** | 50 | 50 | 31 | **+75.9** | **+65.8** | **+11.3** | 44.0 | 1 | 1 | 0 | **6.5** |

**Verdict: limit_0.25R POSITIVE BOTH (dIS/yr +14.6, dOOS/yr +11.3) → survives the pre-registered rule;** limit_0.10R IS −1.2 → dead. Survivor also improves equity: dd_net 8.7→8.4 (IS) and 8.6→6.5 (OOS), WR OOS 39.5→44.0, yearly gross up in **every** OOS year (2021 +20→+32, 2022 +34→+44) and 3/4 IS years (2025 is the one down year).

**Mechanism:** the 0.25R limit on the single lane filters out 43/137 IS + 31/107 OOS shallow-or-no-dip signals *and* fills the survivors ~0.25R better — gross IS +51.4R despite 36 fewer trades; cost drag (smaller risk → bigger fee-in-R) is outweighed. On multi the same mechanic loses: coverage holes + DD blowout dominate. Monster cost: age10 0.25R misses 3/14 IS baseline monsters (11 captured), 0/1 OOS — the tradeoff is real and reported. IS yearly: 2023 95.7→90.3, 2024 179.9→223.7, 2025 95.3→63.9 (the one down year), 2026 105.7→150.0.

**Status: OPEN CANDIDATE, default-off (`exp_retest_fill=0`), not adopted.** Per RESEARCH_POLICY: raw P&L + equity reported; no automatic ship. Combined with the open trail curve candidates (half+delay1, skip_decisive on multi) it stays in the registry as an unadopted experiment. Age10 lane caveat: n=94/50 is thin; OOS monster n=1.


## Caveats

- Descriptive only; no path cascade (halt/concurrency/streak) in this study — real retest fills would perturb subsequent trade order, which only Phase B can measure.
- Touch-at-bar-0 is partly mechanical (breakout close retest); depth metrics (maeB4, deep<.5) are the meaningful ones.
- OOS monster n = 6 / 1 — shapes only, not stable statistics.
- Full-history swing-chain prefix caveat (Stage 19) applies to all fine-path studies.

---

## Phase B2 — dip-then-reclaim confirmation entry (descriptive, 2026-09-25)

User idea: skip the direct entry; wait for price to go DEEP into the pullback, then enter ONLY when price re-breaches the entry level from the other side (dip -> reclaim -> enter). SL unchanged, entry price ~same as baseline (fill at the reclaim touch, gap-adjusted max(entry, open) long).

Pre-registered (frozen before run): depths 0.10R / 0.25R / 0.50R dip required before reclaim counts; wait 240 min from signal close then cancel; configs champion_multi_sw10 + age10_dirmatch_swingpause_single_sw10; IS + OOS. Conservative OHLC ordering: SL touched while waiting => setup killed permanently; reclaim counted only in a bar AFTER arming (no same-bar arm+reclaim); filled-trade r = ORIGINAL baseline r (proxy for selectivity only — path-true P&L would be Phase 2). Harness `exp_reclaim_walk.py`; JSON `_reclaim_walk_results.json`; identity gate IDENTICAL (340t/+225.3R).

Bucket definitions: **no_dip** = never reached depth (miss, direct/shallow); **killed** = SL level touched before any reclaim (miss, but these were baseline losses); **timeout** = armed but no re-breach within 4h (miss); **filled** = dip then reclaim (taken).

### champion_multi_sw10

| scope | depth | filled | fill% | fNet* | fWR% | noDip | ndNet | killed | kNet | t/o | toNet | mCap | mMiss | delta_proxy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IS | 0.10 | 387 | 77.4% | +375.1 | 30.2 | 47 | +100.7 | 37 | -37.0 | 29 | +6.4 | 13 | 4 | **-70.1** |
| IS | 0.25 | 238 | 47.6% | +330.8 | 28.2 | 129 | +192.2 | 75 | -75.0 | 58 | -2.7 | 12 | 5 | **-114.5** |
| IS | 0.50 | 97 | 19.4% | +186.5 | 28.9 | 240 | +386.4 | 103 | -103.0 | 60 | -24.7 | 7 | 10 | **-258.8** |
| OOS | 0.10 | 197 | 70.6% | +107.3 | 30.5 | 33 | +22.7 | 35 | -35.0 | 14 | +10.7 | 5 | 1 | +1.5 |
| OOS | 0.25 | 132 | 47.3% | +95.4 | 30.3 | 75 | +46.6 | 45 | -45.0 | 27 | +8.7 | 5 | 1 | -10.4 |
| OOS | 0.50 | 43 | 15.4% | +41.7 | 30.2 | 145 | +120.7 | 58 | -58.0 | 33 | +1.3 | 2 | 4 | -64.1 |

### age10_dirmatch_swingpause_single_sw10

| scope | depth | filled | fill% | fNet* | fWR% | noDip | ndNet | killed | kNet | t/o | toNet | mCap | mMiss | delta_proxy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IS | 0.10 | 110 | 84.6% | +413.9 | 53.6 | 16 | +64.6 | 1 | -1.0 | 3 | -1.0 | 12 | 2 | **-62.6** |
| IS | 0.25 | 79 | 60.8% | +376.7 | 53.2 | 42 | +106.0 | 1 | -1.0 | 8 | -5.3 | 11 | 3 | **-99.8** |
| IS | 0.50 | 37 | 28.5% | +207.6 | 59.5 | 80 | +276.4 | 1 | -1.0 | 12 | -6.5 | 6 | 8 | **-268.9** |
| OOS | 0.10 | 60 | 78.9% | +46.0 | 40.0 | 13 | +6.9 | 0 | +0.0 | 3 | +2.0 | 1 | 0 | -8.8 |
| OOS | 0.25 | 42 | 55.3% | +36.7 | 42.9 | 29 | +18.1 | 0 | +0.0 | 5 | -0.0 | 1 | 0 | -18.1 |
| OOS | 0.50 | 18 | 23.7% | +11.2 | 38.9 | 52 | +42.4 | 0 | +0.0 | 6 | +1.3 | 0 | 1 | -43.7 |

`delta_proxy` = -(no_dip_r + killed_r + timeout_r) = net R the predicate gives up versus baseline (negative = predicate hurts), measured on original-signal r.

### Reading

1. **No selectivity at any depth.** filled WR ~= baseline WR everywhere (multi 30.2 vs 30.0 IS; age10 53.6 vs 53.9 IS). The dip-then-reclaim predicate does not separate winners from losers — same conclusion as the retest-at-entry filter (24.26 finding 3) and the sweep-reclaim qualifier (DEAD 2026-09-18).
2. **Killed bucket is real but tiny on the single lane.** On multi, 37/35 IS/OOS signals at 0.10R died to SL before reclaim (avoids -37/-35 baseline R), but the no_dip + timeout bucket gives up more (+107 IS, +33 OOS). On age10 the single lane has almost NO killed trades (1/0) — its losses rarely tickle SL before the window, so the filter only loses.
3. **Deeper is strictly worse.** delta_proxy monotonically degrades with depth on all 4 cells (-70 -> -114 -> -259 IS multi). The autopsy warning was right: requiring a deep dip first skips the shallow-dipping winners (median winner dip 0.25-0.32R) while losses (median 0.62-0.78R) are exactly the ones that arm the predicate — then most reclaim anyway within 4h (median arm->fill wait only 15-119 1m-bars).
4. **Only positive cell: OOS multi 0.10R (+1.5R total, i.e. +0.8/yr) — noise-level, and its IS twin is -70.**

**Verdict: DEAD at the descriptive gate.** Pre-registration: Phase 1 decides whether Phase 2 (path-true engine run) is warranted. delta_proxy is negative on 11/12 cells and the one positive is +1.5R total; filled WR flat. A path-true run cannot recover -60 to -269R/3.7yr of skipped expectancy through fill-timing alone. **Phase 2 NOT run; no engine kwargs added; no production change.**

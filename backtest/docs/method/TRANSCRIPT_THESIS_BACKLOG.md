# Transcript Thesis Backlog — Bybit BTCUSDT Perp Only

> **READ FIRST: [`method/THE_CHAMPION_HANDOFF.md`](method/THE_CHAMPION_HANDOFF.md)** —
> the authoritative P55–P98 record. Any thesis below that overlaps
> existing research must be checked against its **PART 4 (closed, never
> rerun)** first — several theses in this backlog were re-derived and
> killed, and rerunning them wastes a cycle.

Dated: 2026-09-24. This file records the distinct theses extracted from the supplied trading-video transcripts and marks whether each overlaps existing v18 research.

## Queue order

| Priority | Thesis | Status | Decision |
|---|---|---|---|
| A | Causal 15m imbalance/FVG context: aligned/opposite, unfilled/partial/filled | **Tested/inactive** | Strict 3-candle BTC FVG gaps are too rare; Stage 14 closed as not interpretable. |
| B | Pre-impulse consolidation/supply-demand zone + retest | **Tested/descriptor** | Stage 15 completed; retest cohorts are not stable across eras. |
| C | Confirmation/fractal entry versus first risk entry | Partially covered | Existing B3/defer/swingpause work is not the same; run only if A/B justify it. |
| D | Minimum reward:risk based on next structural target | **Tested / underpowered** | Stage 16 completed. The nearest completed 15m structural endpoint is known for 99% of trades, but median room is only ~0.07–0.08R; `room_R >= 2.5` has 0 single, 3/1 champion, and 2/1 king trades in IS/OOS. Closed as non-informative; no path-true gate. |
| E | Moving-average trailing stop (20/50/100) | **Tested/closed** | Stage 18 completed on single king, champion multi, and UTC-Saturday multi for Bybit BTCUSDT perpetual. Completed-15m-close SMA20/50/100 exits layered over the existing structural stop/trail damaged both IS and reused OOS; no production change. |
| F | Higher-high/higher-low trend-only bias | Closed/core | 1h/15m direction and B2/FLIP routing already cover this family. |
| G | Range boundaries and key-level bounce | Closed/overlap | Range/compression/MR experiments are closed. |
| H | Narrow-range momentum breakout | Closed/overlap | Compression and breakout/range experiments already exist; no new standalone test unless a new causal definition appears. |
| I | VWOP/52-week-high/catalyst filters | Not applicable/unsupported | Bybit data has no validated VWOP/catalyst series; 52-week high overlaps boundary work. |
| J | Grid bot mechanics | Rejected for v18 | It is a different execution system and conflicts with the fixed-risk structural engine. |

## Video concepts already represented in v18 research

- Market structure and continuation are already the 1h HTF → 15m LTF architecture.
- B2/FLIP, higher-timeframe direction, and HTF windows are already tested extensively.
- Supply/demand-like retesting is represented by swing pivots, trail pivots, pullback gates, and boundary-state studies; Stage 15's dedicated causal pre-impulse zone autopsy is complete and descriptive-only.
- Risk/reward has fixed 1R/2R/3R/5R and structural-target tests; Stage 16's transcript-style target-derived minimum-RR test is complete and underpowered.
- A moving-average trend stop is now tested and closed for v18: Stage 18 SMA20/50/100 exits reduced or destroyed P&L across single and multi references. The existing structural ratchet remains superior.
- The videos' generic range/grid systems are not a direct v18 experiment.

## Current structural candidate after corrected Stage 28 and Stages 39–40

- Corrected stale-current-B1 thresholds `8?192` were swept path-true. The IS band did not reproduce in OOS; the family is closed as non-robust.
- Corrected `B1?B2 age-2 block` is the sole surviving narrow follow-up: reject B2 exactly two 15m bars after the nearest preceding B1. It is positive on literal-default v18 in all four style/period cells and champion multi in both periods, but negative in IS on low-filter pure v18, current fullstack single, and UTC-Saturday multi.
- Exact coverage: `286/286` IS and `135/135` OOS B2 signals matched exact current-bar B2 plus a unique nearest preceding B1. Age 0/1 had zero candidates, so ?immediate? means age 2 in this data.
- `only_delayed_3_8` failed and is closed.
- Stage 39 5m B1/B2/FLIP/FS morphology is descriptive post-entry conditioning. The no-event cohort is consistently bad, while post-entry structural activity is associated with better outcomes; this is not prospective entry information and does not support cutting trades.
- Stage 40 MB20/30/40 architecture changes are not universal. MB50 remains the stable architecture; isolated OOS gains do not reproduce on IS/current references.
- Prefix audit remains non-invariant for baseline and age-2 candidate because of the shared full-history swing-chain boundary caveat. Gate-level mark lookup is causal, but live replay equivalence still needs dedicated validation.
- B1?FLIP remains regime-dependent and should not be gated.
- Previous FS distance, relative-volume states, fresh-B1-only, and large-swing `4+ ATR` are not robust universal filters.
- Stages 44–46 found that green multi add-ons are consistently profitable in all six multi reference/era cells, but red add-ons are also positive with only 2–7 observations, so neither a red-add-on block nor a fixed cohort sequence cap is justified.
- Stage 45 found no universal completed-5m pre-entry scene: overlap/chop is profitable across references, and simple 5m opposition is often better than alignment. Stage 46 reconfirmed immediate/giveback loss structure but produced no entry-known loss scene.
- Stage 63 tested the loss-triggered HTF-window invalidation family (N2/3/4/5, window/global, soft/hard) across seven references. Zero arms were positive in both IS and OOS versus the no-halt control. OOS-only gains came from deleting later recovery/re-entry and runner trades; hard close changed little. Family closed; no production flag.
- Stage 64 tested completed-win-streak controls and then completed the direct shipped-default stacking matrix. Champion default + `global_soft_n3` improves IS `+325.8→+331.7R` and reused OOS `+70.2→+90.0R`, with better R/trade, PF, and drawdown while preserving the OOS 10R+ tail. King global N3 is only `+1.5/+0.6R`; conservative king `window_soft_n3` is `+3.2R` IS and neutral OOS with complete tail preservation. The rule is not universal: pure/literal/fullstack cells are mixed or negative. Keep champion-global and king-window as separate current-multi research candidates; reject a universal default; no production flag in the study. See `method/WIN_STREAK_STACKING_AUTOPSY.md` and `_thesis_win_streak_stack_results_{is,oos}.json`.

## Re-tested at P65 against the programme's own bar

The Stage 64 **win-streak** half above was re-tested at P65
(`method/WINSTREAK_M_P65.md`, `exp_winstreak_M.py`). Stage 64 had never met
M = 193.4R and had never received the P61 period partition — its hit bar was
a single-axis delta. It had the same profile that killed `cand_4h1h` (better
risk profile *and* better return), so it was worth putting through the
standard the programme adopted afterwards.

**Stage 64's numbers reproduce exactly** — champion IS +325.8→+331.7R,
OOS +70.2→+90.0R, better R/trade, PF and drawdown — **but the deltas are
+5.9R IS and +19.8R OOS on the champion lane, and +1.5R / +0.6R on utcsat.**
Best cell is **10.3% of the null**; on the second lane it is
indistinguishable from nothing.

**The period partition is the part worth keeping: 14 wins, 3 losses, 7 ties
across 24 half-year cells — the only candidate this round that is BOTH
period-stable AND positive in both eras in both lanes.**

Status: **NOT ADOPTED — real but small.** It fails on magnitude, not
direction. `cand_4h1h` failed the opposite way (a stable-looking aggregate
that became a 4-4 coin flip under partition). This one survives partition
and adds ~1.8% to a +325.8R book. Recorded for the pile and for a future
forward slice, which per P63 can rule but never confirm.
`window_soft_n3` is inert in OOS on both lanes (+0.0R), +3.2R in IS on both.





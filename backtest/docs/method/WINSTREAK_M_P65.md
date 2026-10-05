# P65: the Stage 64 win-streak block is period-stable and far too small

> Run 2026-09-29. Harness `exp_winstreak_M.py`. **Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **This is the first candidate this round to be stable AND positive in both
> eras. It still fails, on magnitude.**

## Why this was worth checking

`method/TRANSCRIPT_THESIS_BACKLOG.md` line 43 carried a live research candidate
that no one had ever put through the programme's own bar:

> *"Champion default + `global_soft_n3` improves IS +325.8→+331.7R and reused
> OOS +70.2→+90.0R, with better R/trade, PF, and drawdown while preserving
> the OOS 10R+ tail."*

Stage 64's hit bar was a single-axis delta. `method/WIN_STREAK_STACKING_AUTOPSY.md`
contains **no reference to the null at all**, and the candidate had never
received the P61 period partition. It was worth checking precisely because
it has the same profile that killed `cand_4h1h`: better risk profile *and*
better return.

## The rule, taken not re-derived

`exp_window_win_kill_n=3`, action `"soft"`, scope `"global"` — after three
completed global wins, block new entries in the current parent HTF window
while keeping open positions. Copied from `WIN3` in
`exp_thesis_win_streak_stack.py`.

## T1 — magnitude. Stage 64's numbers reproduce exactly, and they are small

| arm | lane / era | n | net | R/t | PF | DD | WR | dNet |
|---|---|---|---|---|---|---|---|---|
| shipped_default | champ IS | 500 | +325.8R | +0.652 | 2.38 | 17.8 | 30.0% | — |
| **global_soft_n3** | champ IS | **483** | **+331.7R** | **+0.687** | **2.46** | 17.8 | **30.6%** | **+5.9R** |
| shipped_default | champ OOS | 279 | +70.1R | +0.251 | 1.59 | 37.3 | 28.0% | — |
| **global_soft_n3** | champ OOS | **262** | **+90.0R** | **+0.343** | **1.74** | **35.1** | **29.0%** | **+19.8R** |
| global_soft_n3 | utcsat IS | 425 | +360.5R | +0.848 | 2.72 | 14.8 | 31.1% | **+1.5R** |
| global_soft_n3 | utcsat OOS | 245 | +60.8R | +0.248 | 1.59 | 21.5 | 29.4% | **+0.6R** |

`window_soft_n3` is inert in OOS on both lanes (+0.0R) and worth +3.2R in IS
on both — the same +3.2R on two different books is a coincidence worth
noting, not a finding.

**Every arm fails M = 193.4R, by an order of magnitude.** The best cell is
+19.8R, which is **10.3% of the null.** On the utcsat lane the effect is
+1.5R and +0.6R — indistinguishable from nothing.

**On the champion lane the rule removes 17 IS trades and 17 OOS trades for
+5.9R and +19.8R** — roughly +0.35R and +1.16R per trade removed.

## T2 — stability. This is where it is unlike everything else this round

Calendar half-years, mean R per trade, time-based, fixed before looking,
never by `r_multiple` / `outcome` / `pnl`:

| lane / era | wins | losses | ties |
|---|---|---|---|
| champion IS | 4 | 1 | 3 |
| champion OOS | 3 | 0 | 1 |
| utcsat IS | 4 | 1 | 3 |
| utcsat OOS | 3 | 1 | 0 |
| **total** | **14** | **3** | **7** |

**14 wins against 3 losses across 24 cells.** `cand_4h1h` was 4-4 in IS — a
coin flip. **This rule is directionally consistent**, and its losses are
small: champion IS loses only 2026H1 (+0.814 → +0.689) and utcsat OOS only
2022H2.

**So this is the first candidate this round that is BOTH period-stable AND
positive in both eras in both lanes.** That is a real and unusual property
here, and it should be recorded as such rather than buried under the
magnitude failure.

## Verdict: fails, but not the way the others failed

**Not adopted.** It clears neither half of the standard: it does not clear
M = 193.4R in any cell, and while it is period-stable, its stable direction
carries +5.9R on a +325.8R book — 1.8%.

**The distinction matters for what to do next.** `cand_4h1h` failed because
its advantage was an aggregate artefact that vanished under partition. This
one survives partition and fails on size. Those are different problems:
`cand_4h1h` was chasing noise, whereas this is a **real but small** effect
whose magnitude does not justify production complexity — a rule that blocks
entries after three wins, purely to add ~1.8% in the era it was fitted and
~28% in OOS on a book whose OOS R/trade is 0.251.

**A small stable effect is not a candidate, but it is a better thing to have
found than a large unstable one.** If the forward slice ever becomes usable
(P63: 40–70 trades can rule out but never confirm), this is a rule worth
listing among the things that pass a stability screen and await magnitude
they have not earned — not one to adopt now.

## A bug I found in my own harness, and why the first table was wrong

The first run of T2 reported **8 ties out of 8 in champion IS** with most
periods showing R/t of exactly −1.000, and three cells of "identical"
results. That was not a finding about the rule. The per-period dictionary
was keyed on the half-year and assigned into directly, so each period
collapsed to whichever trade happened to come **last** — and for a book
whose last trade in most half-years is a −1.0R stop, every period read
−1.000 for both arms.

Fixed to accumulate then average. **A table that reads all-ties and all
−1.000 is the reporting telling you it is broken** — the same lesson as
P64's silently empty book, and the reason both are written up rather than
quietly re-run.

## Stated limitations

- **Half-year buckets give 8 IS and 4 OOS cells.** The 14-3 count is
  meaningful but not a significance test.
- **Both lanes are the same data**; their agreement is not independent
  evidence.
- **Only `n=3` and the `global`/`window` scope pair were run.** `LEVELS`
  (2,3,4,5) and the `skip`/`hard` actions were not swept here, and
  sweeping them now would be a threshold search on a candidate that has
  already failed the magnitude bar on every cell measured.
- **The two lanes disagree on size** — +19.8R OOS on champion against
  +0.6R on utcsat — which is itself a reason for caution about the OOS
  figure specifically.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.

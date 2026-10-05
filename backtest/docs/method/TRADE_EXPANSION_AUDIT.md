# AUDIT of the practitioner research list + TRADE-COUNT EXPANSION (fails 4/4)

The user's own practitioner-research list was re-audited against what this
repo has actually measured, and then the one direction nothing had tested —
**adding trades** — was run end to end.

---

## Part 1 — Audit: what your research list already produced here

| Your item | Status in this repo | Evidence |
|---|---|---|
| Vol-targeting / inverse-vol sizing | **TRIED, FAILED** | `vol_target` 24.83 — curve_better FALSE ×3 (champ IS ulcer 14.62→29.82) despite net up 6/6 |
| Risk parity / equal risk contribution | n/a (single instrument) | — |
| Dynamic / fractional Kelly | **TRIED, PASSED, BEST RESULT** | `sMZX` 6/6: champion +346.5 IS / +130.4 OOS (book 325.8→672.3 IS, 70.2→200.5 OOS) |
| Multi-timeframe + multi-speed blending | **TRIED (4 windows)** | This study: 4h/1d/3d/1w, 7/27 pre-registered survivors |
| Regime filters / chop protection | **TRIED, family closed** | ER24 + ER50 rejected (`ANCHOR_BASIS_AUDIT` §3f); chop/ER/wick/swing-churn all bucketed, nothing gated |
| ADX > 25 | **DEAD** | `exp_oldengines_path` — fails both sides, kwargs reverted |
| Efficiency Ratio (Kaufman) | **REJECTED** | no bucket net-negative on either config; low-ER buckets hold +105R of real ≥2R winners |
| Donchian + position filter | not found as such | closest is the range-position study here |
| Diversification | **TRIED, era-flip** | rewin cohort: IS +282.0R avgR +3.52, OOS −12.9R — no filter survives both sides |
| Exit / trade-management tweaks | **TRIED, SHIPPED in the stack** | `trail_half=1` + `trail_delay_r=1.0` (24.20) — the stack's own edge |
| Break-even / time-stop / partial | **DEAD** | partial kills tail (MFE≥2R only 34.6% hit) |
| Pyramid / scale-in | **FAMILY CLOSED** | V4 −111.3/−87.3; no arm passes both gates |
| Revenge re-entry | **DEAD 8/8** | all cells negative net |
| 5m confirmation | reduces trades 502→351 | selective sub-strategy, not universal |
| Top-N removal robustness | **DONE, standing** | `TAIL_RISK_AUDIT`, `WIN_SPACING`, `STACK_SPACING` |

**The honest summary: this list has been worked through hard.** The only
lever that ever passed at scale is **sizing** (`sMZX`), and it already
increases R **without touching trade count** — which is exactly the
mechanism that works.

## Part 2 — The new direction: can we ADD trades?

Harness: `exp_trade_expansion.py`. The champion's two hard trade limiters are
ordinary engine kwargs, so this is path-true by construction — no injection,
no gray, no slot bookkeeping to get wrong (the bug class that faked +10.3R in
the previous study's streakOFF arm).

- `cooldown_bars = 8` — bars a loss blocks the next entry
- `max_consecutive_losses = 3` — the engine halts after N straight losses

**Controls: 4/4 reference ledgers exact; A0 reproduces byte-for-byte.**

| Arm | trades (is/champ) | Δnet IS champ | Δnet OOS champ | maxDD (is/champ) | verdict |
|---|---|---|---|---|---|
| A0 baseline | 500 | — | — | 27.7 | reference |
| A1 cd=4 | 503 (+3) | −0.6 | −2.2 | 26.7 | **no gain** |
| A2 cd=0 | 556 (+56) | **−120.6** | **−50.2** | **63.1** | destroys |
| A3 mcl=5 | 522 (+22) | −45.9 | −6.0 | 39.3 | mostly negative |
| A4 mcl=0 | 557 (+57) | −17.3 | −9.7 | 32.6 | mostly negative |
| A5 cd=0,mcl=0 | **659 (+159)** | **−136.4** | **−68.1** | **53.8** | destroys |

A5 is the extreme: **+32% trades, −136R IS, −68R OOS.** Per-trade falls
+0.652 → +0.287. WR 27.8% → 23.1%. PF 1.81 → 1.33. maxDD 27.7 → 53.8
(IS) and 53.2 → 84.4 (OOS).

### The added trades are net negative, and it gets worse the more you add

- A4 adds 57 IS trades and costs only −17.3R (≈ −0.30R per added trade) —
  the cheapest arm, and still negative.
- A5 adds 159 and costs −136.4R (≈ −0.86R per added trade) — nearly 3× worse.

**Both limiters are earning their keep.** The trades they block are losing
trades, and relaxing them imports progressively worse ones.

### Robustness gates break, they do not improve

ex-best5, the Rule 13 tail check, goes **negative**:
- is/champion A2: +113.5 → **+7.1**; A5: +113.5 → **−22.9**
- is/utcsat A2: +146.7 → **−19.8**

So the expanded books do not just earn less, they lose the property that
makes the original book survivable.

### The only positive cells do not replicate

A3 oos/utcsat **+4.7R** and A4 oos/utcsat **+8.4R** are positive, but both
come with a worse drawdown (39.8 and 34.2 vs 29.4) and neither replicates on
champion OOS (−6.0 and −9.7). A single lane × single era is not a result.

## Part 3 — Verdict

**0 of 4 relaxation arms pass. Trade-count expansion is closed.**

This is now the fourth independent way of asking "give us more trades" and
losing: pyramid (closed), revenge re-entry (8/8 dead), rewin (era-flip),
and now limiter relaxation (0/4). That convergence is itself the finding.

> The champion's low trade count is not a bug to be engineered away. Its
> selectivity is what makes the book work: the limiters remove trades that
> lose money on average, and the ones they let through carry a tail. Adding
> trades dilutes the per-trade edge faster than volume can replace it.

The way to "make it still better" is therefore **not more trades** — it is
better capture of the trades already taken, which is precisely what `sMZX`
sizing already does at +346.5 / +130.4 across 6/6 cells without touching a
single trade.

## Status

**NOT ADOPTED.** No production change; `cooldown_bars=8` and
`max_consecutive_losses=3` remain. Flags default-off.

## Files
- `backtest/tests/exp_trade_expansion.py` → `_trade_expansion.json`
- `backtest/docs/method/RANGE_PEAK_GRAY.md` — the mechanism this direction came from

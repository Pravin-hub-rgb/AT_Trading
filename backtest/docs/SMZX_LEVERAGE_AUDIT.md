# sMZX LEVERAGE AUDIT — real selection on the null test, BUT SEE THE RETRACTION

> **RETRACTED IN PART.** `SMZX_LOOKAHEAD_RETRACTION.md` withdraws the
> "SELECTION" interpretation below. The shuffle test here is the
> matched-count null this repo requires, and it does show the flags beat
> random size assignment — but it **cannot** separate skill from
> look-ahead, and the load-bearing flag **M2 is forward-looking** (it reads
> the swing segment's `end_px`, which does not exist at B2/flip entry time;
> `backend_check_wd_days.py:108` asserts `fs_at_idx >= seg.end_idx`). No
> send-time replacement exists — `CAPITAL_STAGE_PLAN.md` tested and recorded
> that before this run, and this run failed to read it. Read the retraction
> first; the numbers below are accurate but were over-interpreted.

The only lever in this repo that ever passed at scale deserved the same test
that killed `monster_sizing` M1. It now has one, and it passes.

## The question

`sMZX` applies `1.5^count` to trades flagged by **M2** (`cur_mag_atr >= 3.0`),
**ZC** (`vol7_prev7 <= 0.846`) and **X** (`parent risk_pct < 1.0`). It is the
repo's best result: PASS 6/6, champion +346.5 IS / +130.4 OOS.

But it works by *sizing up a subset with 1.5×*, and M1 was condemned in this
repo as a **"LEVERAGE TRAP - do not adopt"** for exactly that reason
(CHECKLIST 24.58). M1 and sMZX were never given the same test, so it was not
established that sMZX is different.

## The test

Harness `exp_smzx_leverage_audit.py`. Three arms on the same flat book:

- **A — flat leverage**: every trade × L, where L is sMZX's own average
  multiplier. This is the control that separates "beat the book" from "beat
  the book by more than the extra size explains."
- **B — sMZX real**: the published arm, unchanged.
- **C — sMZX shuffled**: the *identical multiplier values* randomly
  reassigned to other trades, 50 draws. Same size distribution, same total
  size budget, same magnitudes — but the flags no longer mean anything.

**C is the discriminator.** If C ≈ B, the arm is leverage. If B ≫ C, the
flags are selecting.

## Result — 4/4 SELECTION

| Cell | flat book | A flat leverage | **B sMZX real** | C shuffled (50) | shuffles beating B |
|---|---|---|---|---|---|
| is/champion | +325.8, DD 27.7, cal 3.20 | +495.3, DD 33.4, cal 4.05 | **+672.3, DD 33.1, cal 5.53** | +494.4 ±60.8 | **1/50** |
| is/utcsat | +358.9, DD 21.2, cal 4.62 | +542.7, DD 26.5, cal 5.57 | **+700.1, DD 27.2, cal 7.01** | +540.3 ±64.2 | **0/50** |
| oos/champion | +70.2, DD 53.2, cal 0.66 | +98.2, DD 63.1, cal 0.78 | **+200.5, DD 56.2, cal 1.78** | +94.2 ±23.8 | **0/50** |
| oos/utcsat | +60.2, DD 29.4, cal 1.03 | +86.8, DD 35.7, cal 1.21 | **+206.8, DD 29.1, cal 3.56** | +90.1 ±24.0 | **0/50** |

### Why this is not a leverage trap

1. **Control reproduces the published dNet exactly** — +346.5 / +341.2 /
   +130.4 / +146.6. Same arm, same numbers, so this really is an audit of the
   published result and not a re-tuned variant.
2. **B beats flat leverage (A) in all 4 cells** — by +177.0 / +157.4 /
   +102.3 / +120.0R. Flat leverage scales everything; it cannot be beaten on
   R by construction, so B winning this is the size-adjusted result.
3. **B beats 49-50 of 50 random size reassignments.** Random assignment
   lands at the *mean of flat leverage* (+494.4 vs A's +495.3 in is/champion
   — indistinguishable), which is exactly what theory predicts for a pure
   size effect. The real flags sit +177.8R above that. The selection is real.
4. **It wins on risk, not only on R.** oos/utcsat: DD **29.1 vs the flat
   book's 29.4** — the arm has *lower* drawdown than the book it came from,
   with net going +60.2 → +206.8. Calmar 1.03 → 3.56. M1's tell was that its
   gain was bought with concentration; sMZX's is not.

## The honest caveats

- **This is post-process sizing on a flat book.** It changes no trade
  selection. It is not a better strategy — it is the same strategy with a
  different risk budget, and the budget is demonstrably well spent.
- **Margin headroom is a real constraint.** 41–54% of trades get sized up and
  the maximum is `1.5³ = 3.375×`. On 3 concurrent positions the account can
  carry ~10× the base notional on a single idea. That has to be sized
  against real leverage limits, not assumed away.
- **The engine has no size state.** `AGENT_COORDINATION` records 0 hits for
  `equity` / `position_size` / `notional` / `qty` in `v18_streak_halt.py` —
  there is no channel for a size change to feed back into anything. Adoption
  is an executor/live-bridge task, not a research task.
- **The OOS slice is the one already inspected many times** in this repo.
  Independent `data/btc` replication is still owed before adoption.

## Status

**VERDICT: SELECTION, 4/4.** The repo's strongest lever survives the test
that killed `monster_sizing`, and survives it on the risk axis too. It is
still **NOT ADOPTED** — the blockers are the forward gate, the independent
replication, and the live size-state gap above, not the statistics.

## Files
- `backtest/tests/exp_smzx_leverage_audit.py` → `_smzx_leverage_audit.json`

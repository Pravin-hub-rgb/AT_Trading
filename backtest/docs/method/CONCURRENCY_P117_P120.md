# CONCURRENCY — P117 (grid), P119 (survivors), P120 (clock). One thread.

Branch: agents/champion-reality-audit · 2026-10-01 · backtesting only
Harnesses: `exp_p117_slot_grid.py`, `exp_p119_cap1_tail.py`, `exp_p120_cap_clock.py`
Book throughout: **`champion_multi_sw10_leg`** — 499t / +239.1R IS, 280t / +72.8R OOS

**Read this first.** Part of this thread was retracted. `method/LIVE_CONCURRENCY_P118.md`
holds that retraction; it is not summarised away here, because the retraction is
the most useful thing in it.

## What is settled

**The cap grid transfers to the leg book.** cap=5 is free: **dNet +1.1R IS /
+0.0R OOS**, reproducing `signal/ANCHOR_BASIS_AUDIT.md:344`. Both eras passed a
pin-from-run gate (IS 499/+239.1, OOS 280/+72.8) before anything was interpreted.

| cap | IS n | IS net | OOS n | OOS net |
|---|---|---|---|---|
| uncapped | 499 | +239.1R | 280 | +72.8R |
| 1 | 388 | +111.6R | 219 | −11.8R |
| 4 | 497 | +236.9R | 279 | +66.8R |
| 5 | 498 | +240.2R | 280 | +72.8R |
| 6 | 499 | +239.1R | 280 | +72.8R |

**The OOS arm of this grid is partly vacuous.** Max concurrency on the leg OOS
book is **5**, so cap=6 cannot bind there and cap=6's OOS row is identical to
uncapped by construction. `ANCHOR:344`'s "cap=5 free" is therefore an IS claim
with an OOS confirmation that cannot fail. Reporting +0.0R as OOS evidence would
be reading a tautology.

**The cap clock is correct — closed by evidence, not argument.** P120 replayed the
cap over the same candidate list under two clocks, `entry_ts` versus
`entry_ts + 900`, at every cap in both eras. **All 12 cells identical** in trade
count, dropped count and net. No trade exits inside the fifteen minutes after an
entry in a way that moves the open count, so the clock is irrelevant on this data.

That closes a question argued twice on false premises. An earlier rejection cited
"the independent audit agreed with every cap" — circular, because that audit reads
the same `exit_ts` / `entry_ts` the engine reads and both would be wrong together.
The `+900` claim it rejected was also wrong, for a different reason: `entry_ts` is
`int(candles_ltf[i]["ts"])` (`v19_champion.py:834`), the same bar-open clock the
whole injected walk uses, and `ts + 900` is the HTF-close alignment operation.

P120's replay is a **post-filter, not an inline replay**. Dropping a trade inside
the engine changes `last_loss_ts`, `cooldown_bars` and the window rules, so later
trades differ: P117 inline cap-1 OOS is 219 / −11.8R against 212 / −10.9R in the
replay. The A-vs-B verdict is unaffected — both clocks use the identical method —
but the absolute numbers are not P117's and are not offered as such.

## The one real finding, and it is not a deployment finding

**Capping to 1 slot deletes the good trades, not the spare ones.**

| | uncapped | cap-1 | change |
|---|---|---|---|
| IS R/trade | 0.479 | 0.288 | **−40%** |
| OOS R/trade | 0.260 | −0.054 | sign flip |
| IS trades lost | — | 111 | |
| OOS trades lost | — | 61 | |

The naive reading is that the champion's edge lives in the overlaps. P119 tested
that and it does not hold cleanly, so it is recorded as a **split**, not forced to
a verdict.

**H1 — ex-top-5%, both arms.** Strip the top 5% of trades by `r_multiple`:

| era | gap, full book | gap, ex-top-5% | reads |
|---|---|---|---|
| IS | +0.181 | **+0.216** | **persists** — not explained by tail |
| OOS | +0.312 | **+0.137** | **converges** — tail concentration |

**H2 — half-year partition, by entry timestamp:**

| era | uncapped H1 / H2 | cap-1 H1 / H2 | gap H1 / H2 | |
|---|---|---|---|---|
| IS | +0.492 / +0.933 | +0.436 / +0.627 | +0.056 / +0.306 | agree |
| OOS | **−0.092** / **+0.866** | −0.078 / +0.226 | −0.014 / +0.640 | **disagree** |

**The OOS half-split is the result.** Nearly all of the cap-1 damage is in one
half-period. H1 is roughly flat under both arms; H2 carries +0.866 → +0.226. So
−11.8R OOS is not "the cap is bad" — it is that **this book's OOS edge lives
entirely in the second half, and the cap removes trades from that half
specifically.**

**Verdict, as pre-registered:** one arm dead, one alive. IS survives ex-top-5%
and agrees across halves. OOS converges under ex-top-5% and disagrees across
halves. An n=1 positive that vanishes under one control is worth recording as
exactly that. Prior: `method/MASTER_CANDIDATES_V2.md` measured top-5% at 144.8% IS /
221.7% OOS.

## What was retracted, and why it matters more than the finding

The first version of this work reported **−11.8R OOS as "the config the live bot
can execute"**, and called multi-position a shipping blocker. Both were wrong.

The live engine runs **`v18_streak_halt.py`, a different book.**
`test_v18_causal_integrity.py:39` builds `kw` without `exp_mltf`, and
`v18_streak_halt.py` contains **no concurrency parameter at all** — v18 is serial
*natively*, and its 352 trades are already its cap-1 count. `COUNT_BAND=(348,358)`
and 388 is *inside* it, so the count gate does not fail. v18's own record is
+146.55R net / PF 1.947 / 5 of 5 tests pass.

So −11.8R belongs to a champion-at-cap-1 that nobody runs, and the headline was
backwards. `method/RISK_CONCURRENCY.md` had already said **"single = no-op"** — the file
was in the repo and was not used.

**What survives is a strategy statement, not a deployability one:** the champion
requires 5-deep concurrency to reach its own numbers, and v18 is a different book
with its own positive record. There are two books, not one book with a config
problem.

## A feature that no engine has

`exp_max_concurrent` has **zero occurrences under `backend/src`** — v18 and v19
both return 0. It exists only as a `test_experiments_craze.py` source patch
(:106 default, :760-763 enforcement). At the default of 0 the block is a silent
no-op, so experiments that did not set it ran uncapped and looked correct;
nothing could fail, so nothing was validated. Four documents described it as an
engine feature and the worst called it an "ALIVE deployment enabler". All
corrected. The cap *logic* is sound — P120 confirms it — but the knob is a
research instrument, not a feature.

## Still unmeasured

**Slot parity.** Swing parity between live and backtest is proven and unaffected
by any of this — entry logic is settled. Whether live and backtest agree on how
many positions are open simultaneously has never been tested. Do not read the
proven swing parity as general parity.

## Carried forward

**`P116` is blocked on this thread's own premise.** It measures blocked signals,
and the slot count that framed it was retracted with P118 and narrowed by P120.
It should re-derive its premise or die, not be revived on schedule.
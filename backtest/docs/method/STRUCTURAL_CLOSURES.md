# P2 is structurally void, and the forward slice is already spent

Checked both before running either, per the rule adopted after P3-D.

## P2 (risk-weighted concurrency) — VOID, premise false

**P2's thesis:** `exp_max_concurrent` caps how many positions are open,
treating a 3-ATR stop and a 1-ATR stop as identical risk, so cap the SUM
of open risk instead. Cost: ~30 lines. Confidence when proposed: medium,
"cheapest real edge candidate."

**The premise does not hold.** `v18_streak_halt.py` has no concurrency at
all:

- `:567` `busy_until = ""` — one in-flight trade, tracked by timestamp
- `:577` `if busy_until and bar_time <= busy_until: continue`
- `:743` `busy_until = candles_ltf[exit_idx]["date"]`

**The engine holds exactly one position at a time, by construction.** A new
signal during an open trade is skipped outright, not queued and not sized.
So there is never more than one open stop, never a sum of open risk to
cap, and never coincident risk — which is the entire mechanism P2 proposed
to fix. `max_concurrent` as a knob must be a post-process on the trade
list, not an engine gate.

**P2 is not "sweep it and see." It is answering a question about a
mechanism the book does not have.** Running it would produce a number
whose negative result is uninformative and whose positive result would be
an artefact of whatever re-sequencing the harness happened to do.

The underlying observation is not wrong — *if* positions overlapped, risk
weighting would beat position counting. It is just that this book never
overlaps, so the question is moot. **This belongs in the structural-excluded
list next to "position resize" (no size channel) and "risk cap" (no
concurrent positions).** Three variants of the same gap now: the engine
has no equity, no size, and no concurrency state.

## The forward slice — ALREADY READ, verdict already ruled NO VERDICT

`_forward_manifest.json`: 12.5 days, 2026-09-13 → 2026-09-25, 1203×15m /
301×1h / 18049×1m rows. `method/CHECKLIST.md:782` and `method/EXPERIMENT_LOG.md:407`
both record the evaluation as done on 2026-09-25.

- **R1 parity PASS** — pre-cutoff replay exact (champion 500t/+445.2R gross
  /+325.78R net, king 454t/+466.5R/+358.95R).
- **Forward: 5 trades**, gross −1.95R, net −3.83R, PF 0.22, WR 20%, all 5
  shorts into a rising market (77.0k → 83.9k), one −1.0R on a 1-bar SL.
- **All 4 pre-registered candidates produced the IDENTICAL 5 trades** —
  the N3 policies never fired in-window. So it tested the base
  architecture, not the variants.
- **R2 FAIL, R4 PASS, R5 = NO VERDICT.**

`method/FORWARD_TEST_PLAN.md:96-104` fixes the rule in advance: **below n=50,
report the ledger and say "no verdict yet."** At ~12 trades/month, n=50
needs ~4 more months and n=150 needs ~12.

**So the slice is not "now usable because M exists."** It was read before
M existed, and the contract it was read under says the only honest
conclusion at n=5 is no conclusion. M does not change the sample size.
Re-running it would produce the same 5 trades and the same R5 verdict, and
a second look at a pre-registered window is exactly the multiple-reads
error the contract exists to prevent.

`method/BASE_BOOK_NULL.md` and the queue row claiming the forward slice is "now
usable" are **wrong on this point** and need correcting. What M changes is
not that the forward slice may be read — it is that when n≥50 eventually
arrives, the pre-registered kill lines and the M bar are the two things the
read will be scored against, and both now exist.

## What is actually left

1. **Accumulate the window.** ~4 months to n=50. Nothing to do but wait;
   this is the only genuinely out-of-sample arbiter in the programme.
2. **Variance-reduced statistics.** The P5 finding says net-R-on-500-trades
   cannot resolve skill. Per-year, per-regime and ex-best-5 decompositions
   have far tighter nulls, and the repo already computes all three. The
   live question is **which decomposition of the champion clears its own
   reshuffle null** — that is the next runnable thing, and it is not on
   anyone's list yet.
3. **P1 (nested swing containment)** — still the only serious
   representation idea, still unrun, still the closest thing to the
   original "do something new on the 1h" request.

# P118 — RETRACTED IN SCOPE 2026-10-01. The live bot is out of scope.

**This investigation was a category error and its findings are withdrawn as
research.** Kept in the repo only so the mistake is not repeated.

## What it claimed

That `ANCHOR_BASIS_AUDIT.md:346-347` ("cap=5 is FREE, use for live risk") is a
capability mismatch, because `live_loop.py` is structurally single-position
(`_open_ltf_trade: dict | None` at :151, an unconditional `continue` at
:1781-1784, one symbol at `bybit_order.py:258`).

## Why it is withdrawn

**The programme is backtesting only. Reading `live_stuff/` was out of scope.**

Worse, the reasoning was wrong even as a live-engine argument. I measured
`champion_multi_sw10_leg` at `exp_max_concurrent=1` and reported −11.8R OOS as
"the config the bot can execute". But the live engine runs
**`v18_streak_halt.py`, which is a different book**:

- `test_v18_causal_integrity.py:39` builds `kw` without `exp_mltf`, and
  `v18_streak_halt.py` contains **no concurrency parameter at all**. v18 is
  serial *natively* — its 352 trades **are** its cap-1 count.
- `COUNT_BAND = (348, 358)`. My 388 is **inside** the band, so the gate does not
  fail. My "count gate is unreachable" conclusion was wrong.
- v18's own record is +146.55R net / PF 1.947 / 5 of 5 tests pass. The −11.8R
  belongs to a hypothetical champion-at-cap-1 that nobody runs.

**So the −11.8R is not a deployability finding. It is a finding about a book
that does not exist**, and I reported it as the headline.

## The three claims that were wrong

| claim | status |
|---|---|
| "COUNT_BAND will fail — 388 is outside" | **false.** 388 ∈ (348, 358) |
| "the live config gives −11.8R OOS" | **wrong object.** v18 ≠ champion |
| "multi-position is a SHIPPING BLOCKER" | **unsupported.** nothing measured a live bot |

## What survives

Only one thing, and it is a strategy statement, not a deployability one:

**The champion requires 5-deep concurrency to reach its own numbers, and v18 is a
different book that has its own positive record.** There are two books, not one
book with a config problem. Selecting between them is a strategy question.

`RISK_CONCURRENCY.md` had already said it: **"single = no-op"** — single-position is
v18's native state, not a modification of the champion. I had the file and did not
use it.

## The actual live finding is still tested

Not here, and not by re-running a backtest. Swing parity (entry logic) is proven.
**Slot parity has never been tested**, and this document does not establish it.
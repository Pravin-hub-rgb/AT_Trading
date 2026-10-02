# P118 (opened) — THE LIVE BOT IS STRUCTURALLY CAP-1. The shipping book is not executable.

Branch: agents/champion-reality-audit
Date: 2026-10-01. **Code read. No run.** Source: `ANCHOR_BASIS_AUDIT.md:343-347`.

## The claim under audit

> "cap=5 is FREE, use for live risk" — ANCHOR_BASIS_AUDIT.md:346-347, supported by
> the cap1..cap5 grid at :105-107.

## The finding

**The live bot cannot hold more than one position. This is structural, not
configurable.**

| site | evidence |
|---|---|
| `live_loop.py:151` | `self._open_ltf_trade: dict \| None = None` — a scalar, not a list |
| `live_loop.py:1781` | `in_trade = self._open_ltf_trade is not None` |
| `live_loop.py:1783` | `if in_trade:` → journal `stale_skip`, `continue` — trade is **not executed** |
| `bybit_order.py:258` | `get_positions(category="linear", symbol=self.symbol)` — one symbol |
| `bybit_order.py:279` | `get_position()` → `dict \| None` |

There is no position collection anywhere in `live_loop.py` or `bybit_order.py`. The
single-position guard at :1781-1784 is an unconditional `continue`: a second
concurrent signal is journaled as skipped and discarded.

## Why this is not a stale number

The P117 grid answers "does the cap grid transfer from origin to leg". It cannot
answer this. **Re-running a backtest against a bot that structurally cannot
execute the configuration reproduces the exact trap P115 fell into — a plausible
number surviving while its premise is false.** The premise here is that a live
bot holds 4–5 positions. It holds one.

So `ANCHOR_BASIS_AUDIT.md:343-347` is not "out of date". Its conclusion was never
about the grid; it was the grid **plus an unstated assumption about the live
architecture**, and that assumption is false against the code.

## Consequence for the shipping book

The backtest book at cap=6 has 280 OOS trades across several simultaneously open
positions. At cap=1 the same signals serialise, and the realised book is not a
subset — it is a different book, because entries that would have overlapped now
compete for the single slot.

**This puts `COUNT_BAND=(348, 358)` in question.** That band was measured at the
cap=6 basis. It is a live gate and it is currently anchored to a concurrency level
the bot cannot reach. It is **not yet known** to be wrong — that requires the
cap-1 measurement, which is P117's remaining half.

Note what was and was not verified here. **Swing parity between live and backtest
is proven and unaffected** — this finding is about slot occupancy, not entry
logic. What was never tested is slot parity.

## Open, deliberately undecided

Do not scope the cap-1 measurement until P117 reports the leg-era grid. Deciding
now, on origin-era numbers, is the same premature-commitment error as P95's
COUNT_BAND.

**Status: opened, not resolved. Blocks any "ship it" claim.**
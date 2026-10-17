# LIVE CONFIGURATION — what runs, and the two switches

**Written 2026-10-16.** Companion to `FORWARD_TESTING_CONTRACT.md`.

## The state of `live_stuff` right now: it cannot run

```
live_loop.py line 41:  from engine.v18_params import V18, V18_ENGINE, SWING, ...
ModuleNotFoundError: No module named 'engine'
```

This is **deliberate, not breakage.** Commit `2ada7a6` (2026-10-01) moved
`v18_params.py` to `backtest/engine/` with this in the message:

> *"v18_params.py went with the backtests. It is the v18 engine's parameter
> set, and v18 is a backtest engine here. **The live bot gets a fresh module
> when an engine is actually chosen for it.**"*

So the live engine is a blank waiting for the strategy decision. **Choosing the
book is the thing that unblocks it** — not the other way round.

## What the live bot already does correctly

**The architecture is better than it looks, and the owner's instinct was right
that backtest-to-live is "mostly plumbing".** `live_loop.py` does not
reimplement the strategy. It calls the **same engine the backtest calls**:

```python
result = simulate_htf_ltf_streak_halt(
    c1h, sw1h, c15, sw15, fine_ltf=[],
    sl_buf_atr=..., ext_stop_r=..., mode=...,
    chop_thresh=..., cooldown_bars=..., max_consecutive_losses=...)
ltf_trades = result["ltf_trades"]
```

then places orders on Bybit against the trades that engine returned. **Signal
generation is not a re-implementation risk at all — it is literally the same
code, fed live candles.** Only execution is live.

The following are built, working, and were written against that engine:

| stage | how | where |
|---|---|---|
| entry | fires on a **confirmed** 15m break — B2 or FLIP — never mid-candle | engine output |
| regime | 1h chop decides B2 vs FLIP, same as backtest | `live_loop.py:319` |
| swing chain | `PersistentSwingEngine` on 15m and 1h, survived restarts | `live_loop.py:94` |
| order entry | `place_market_order_retry` with the stop attached | `_execute_entry()` |
| stop placement | the pivot, pushed to Bybit as a conditional order | `_trail_sl()` |
| trailing | MB50 pivots, forward-walked, timestamp-keyed so window trims can't break it | `_trail_sl()` |
| server-side SL | synced to the exchange on every trail move, with retries | `_trail_sl()` |
| position sizing | from `risk_inr.txt`, leverage hard-capped at 3 | `config.py` |
| daily loss limit | 5R per UTC day, auto-halts | `config.py` |
| reconciliation | local position vs exchange on startup | Phase 15 |

## The ONE gap: how a stop actually fills

This is the whole distance between a backtest R and a live R.

```
BACKTEST   if lo <= sl_cur:  fill = min(sl_cur, bar_open)
           fills AT the stop price, or at the open if the bar gapped through

LIVE       Bybit creates a Market order by default (tpslMode=Full)
           fills at whatever the market does on the wick
```

On a clean bar they are identical. On a wick through the stop, **live is worse
and the backtest does not know it.**

**This is measurable and it has never been measured:** count how often the 15m
bar's low goes past the stop price. That count is the live slippage exposure.
It should be known before the forward window closes, not discovered by
trading it.

## The book switch — one file, and 7 more arguments

The live bot already reads its knobs out of one dict and already calls the real
engine, so the switch is **wiring, not a rewrite**. The work is exactly two
things:

**1. The fresh params module.** The one `2ada7a6` deliberately removed. It
carries the chosen book's `params` block and nothing else.

**2. Pass the remaining arguments.** The live call currently forwards **seven**
knobs. Every registered book needs more:

| knob | passed today | needed for 107 | needed for 110 |
|---|---|---|---|
| `sl_buf_atr`, `ext_stop_r`, `mode`, `chop_thresh`, `cooldown_bars`, `max_consecutive_losses` | yes | — | — |
| `pivot_rule` | **no** | `"leg"` | `"leg"` |
| `exp_persist` | **no** | `7` | `7` |
| `exp_fs_entry_side` | **no** | `"long"` | `"long"` |
| `max_positions` | **no** | `0` | `0` |
| **`exp_trail_skip_n`** | **no** | — | **`6`** |
| `exp_partial_r` | **no** | `0.0` | `0.0` |

**So 107 is a params module plus six arguments. 110 needs one more piece of real
work: `exp_trail_skip_n` does not exist in the live trail** — `live_loop.py` has
zero references to it, and `_trail_sl()` walks every trailing event from the
entry. It has to skip the first six. That is a contained change to one function,
but it must be built and parity-tested before 110 can run.

**That is the entire practical difference between the two candidates for live
work.** Everything else is shared.

## A third piece, found while checking the above

Both books are `swing: htf15`. The live bot hardcodes its swing length from
`SWING`, which is `min_bars_1h = 20`:

```python
self.swing_1h = PersistentSwingEngine("1h", db, {"minBars": SWING["min_bars_1h"]})
```

while the backtest builds htf15 at `min_bars=15`. **So the live bot currently
builds a 20-bar swing series and both candidate books need a 15-bar one.** That
is a third change, and it is shared by 107 and 110 — neither candidate avoids it.

This is also a trap worth naming: the swing length is the single most
load-bearing structural constant in the family (`min_bars_15m` was measured at 35
versus 50 and moved +58R to +238R), and the live bot reads it from a different
place than the backtest does. A book switch that changed only the params dict
would silently run the wrong swing chain.

## So the live work, complete, in three parts

1. **The params module** — the one `2ada7a6` deliberately removed.
2. **Six (107) or seven (110) extra arguments** to the engine call.
3. **Swing length from the book's `swing` key**, not from `SWING` — plus
   `exp_trail_skip_n` in `_trail_sl()` for 110 only.

Nothing else. Order management, reconciliation, sizing, daily loss limit,
persistence and restart recovery are already built.

## THE TWO SWITCHES

These are **owner decisions, not defaults to be picked for you.** Both are fixed
now, while nothing depends on them, rather than later while a result is
pointing at them.

### Switch 1 — the loss cap (`max_consecutive_losses`)

The reasoning is about money, and it is worth writing down because it is a
choice about capital rather than about the strategy:

| setting | what it does | who should use it |
|---|---|---|
| **3** (default, as registered) | halts entries for 3 bars after 3 consecutive losses | **normal operation.** Costs 4–5 trades per 100, halves the worst 50-trade window from −20R to −5.85R |
| **0** (off) | nothing | **only if the capital is deep enough to sit through the drawdown without acting on it.** Deeper drawdown, longer losing streaks |

**The trap:** turning it off is easy and it feels like freeing money. It actually
converts a risk control into a larger position by another name, and the person
who switches it off is the one who will be watching at 3am.

Measured cost of turning it on, versus off, on the same books: about 4–5% of
trades removed and the R those trades would have made is given up. That is the
whole trade.

### Switch 2 — the opposite-direction lock (`exp_no_opposite`)

Refuses a new trade if a trade in the **opposite direction** is already open.
Same-direction stacking is still allowed.

```
affects 1.3–1.5% of trades (8 of 528 in sample, 4 of 311 out of sample)
BASE   IS   +533.4 → +534.3   (better by 0.9R)
       OOS  +239.6 → +240.6   (better by 1.0R)
```

Those figures are from 2026-10-08 and **predate the causal-stop fix**, so they
need re-measuring before they are trusted. The shape — rare, near-neutral on net
— is what matters and it is not in doubt.

**The reason to want it anyway is not the R.** On one symbol, a long and a short
held together net to roughly zero exposure while paying fees twice and
occupying margin twice. On a multi book holding up to eight positions, that is
not a rounding error, it is a position-sizing bug you have not had yet.

**Recommended ON**, on the strength of the exposure argument rather than the
1.5% net difference.
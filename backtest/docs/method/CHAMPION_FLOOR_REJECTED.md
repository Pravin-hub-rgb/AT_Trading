# P4 — the live_R floor on the REAL champion: REJECTED, 0/7

`exp_champion_true.py`. This is the run that should have been run first.

## The pin reproduced exactly

| | got | want | |
|---|---|---|---|
| IS | **500 trades, +325.8R NET** (+445.2 gross) | 500 / +325.8 | **PIN OK** |
| OOS | **279 trades, +70.1R NET** (+105.7 gross) | 279 / +70.2 | **PIN OK** |

Identity gate green (340t/+225.3R), and the floored patch identity-gated
against the champion config at `floor=None` (500 vs 500, 279 vs 279) before
any arm was run.

## The result — every single arm is negative in BOTH eras

| floor | IS | | OOS | | both? |
|---|---|---|---|---|---|
| | n | netNET / PF / DD | n | netNET / PF / DD | |
| **None (champion)** | **500** | **+325.8 / 2.38 / 17.8** | **279** | **+70.1 / 1.59 / 37.3** | — |
| −0.25 | 370 | +228.2 / 2.35 / 22.2 | 227 | +31.7 / 1.41 / 40.5 | no |
| −0.10 | 331 | +230.4 / 2.50 / 26.5 | 196 | +39.7 / 1.50 / 46.6 | no |
| +0.00 | 300 | +220.6 / 2.59 / 19.4 | 177 | +53.4 / 1.64 / 44.2 | no |
| +0.10 | 271 | +211.7 / 2.64 / 20.0 | 159 | +11.0 / 1.29 / 41.3 | no |
| +0.25 | 236 | +110.4 / 2.14 / 12.7 | 137 | +18.4 / 1.38 / 38.4 | no |
| +0.50 | 192 | +175.4 / 2.97 / 12.8 | 101 | **−17.3 / 0.93** | no |

**0 of 7. Not one arm beats the champion in either era. The best OOS arm
(`+0.00`, +53.4R) is still −17R against a +70.1R champion.**

## Why P3-C and P3-D said the opposite

Both earlier runs were measured against a book that is not the champion, in
two independent ways:

1. **Wrong engine.** Champion is `engine: "patched"` with `exp_mltf=True,
   exp_persist=7`. Those kwargs do not exist on the shipped engine, so I
   was running a 356-trade book while the champion is a 500-trade book.
2. **Wrong metric.** The published pins are **NET** — gross minus fees minus
   funding (`run_experiment.py:121-124`). I was printing gross. The
   +277.1R I reported was not a 277.1R book; it was a gross figure on the
   wrong book, and it was never comparable to a net pin.
3. **Wrong config.** `mode=b2_vs_flip_chop / chop=61.8 / sl_buf=0.25 /
   ext=1.5 / mcl=5` versus the champion's `mode=atr_high / chop=58.0 /
   sl_buf=0.01 / ext=3.0 / mcl=3 / cooldown=8`.

The P3-C "confirmation" — a local maximum at exactly zero, reproduced from
two code paths — was a real feature **of a different book**. Two
independent measurements of the same wrong book agreed with each other, and
I read that agreement as confirmation. It was never evidence about the
champion. **This is the third time today that agreement between two runs
was mistaken for correctness, and the most expensive one.**

## What survives, and it is only this

The **inversion** is real and now measured on the champion: `+0.50` gives
the best IS PF in the entire grid (2.97) and turns OOS **negative
(−17.3R, PF 0.93)**. That is the same shape P3-C saw, so the ceiling/floor
conflict is a genuine property of the idea, not of the mis-specified book.

The champion already runs `ext_stop_r=3.0`, which is a live-R **ceiling**.
Adding a floor on top of it only removes trades, and on this book the
removed trades are net-positive: the champion's edge includes 15m entries
taken while the 1h leg is underwater.

**That is the finding. "Don't trade while the HTF leg is losing" is wrong
for this book, and it is wrong for a specific reason: `exp_mltf` and
`exp_persist` already build the book out of repeated entries within a
window, so an underwater 1h leg is frequently a *continuation* state, not
a warning.**

## Corrections owed to the docs

`method/LIVE_GATE_CONFIRMED.md` and `method/CHAMPION_GATE_IMPACT.md` describe a
**non-existent** champion. Both should be read as measurements of a
356-trade `b2_vs_flip_chop` book with a gross metric. Their central claims
("drawdown halves in both eras", "reshape rather than lift", "the strongest
candidate produced today") are **not supported on the champion** and the
second document's title is actively misleading. Flagged for correction in
`method/OPEN_RESEARCH_QUEUE.md`.

## Process lesson — the one that matters

`build_module()` and the pin both existed in the repo the whole time, in
`experiment_registry.py` and `run_experiment.py`. I had the correct
harness available from the first message and did not use it; I built a new
one from guessed parameters and then spent three experiments defending the
result. **The identity gate I did run proved the patch was faithful — and
never checked that the *book* was the champion.** A patch can be perfectly
faithful to the wrong thing.

Next time, the first command is to look up the config and the metric, not
to import a default.

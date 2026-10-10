# I was wrong about the window lookahead — the owner caught it, and the owner was right

Date: 2026-10-10. `exp_decision_instant.py`.

**This document withdraws a bug report I filed earlier today. There is no lookahead
in the window gate. The gate's 2700 is correct arithmetic and my "fix" would have
removed real trades.**

---

# 1. What I claimed

I reported that `fsent_champ_long` contained **6 lookahead trades**, each entering
exactly 900 seconds before the HTF window candle closed, and that the gate had a
900-second hole. I wrote a fix, re-pinned all 28 books, and produced two documents
and a registry entry built on the finding.

**All of that was wrong.**

---

# 2. What the owner said

> *"yeh rare overlap hai — flip is on 15min tf at 19:15 and yeh pata humko 19:30
> mai chalega, because 19:15 ki candle 19:30 mai close hogi. Toh yeh trade hum le
> sakte hain — window + trade taken on the same candle."*

Read plainly: the 15m entry candle opens 19:15 and **closes 19:30**. The 1h window
candle is 18:30 → **19:30**. **Both close at the same instant.** Deciding at 19:30
using two candles that both closed at 19:30 uses nothing from the future.

**That is correct, and it is the ordinary case of deciding on a closed bar.**

---

# 3. Why I got it wrong

`entry_ts` is `candles_ltf[i]["ts"]` — the **OPEN** of the 15m entry bar. It is a
**label**, not the decision time. The engine decides when that bar **closes**.

| | |
|---|---|
| my (wrong) test | `window_start + 3600 > entry_ts` — compared against the **label** |
| the real test | `window_start + 3600 > entry_ts + 900` — compared against the **decision** |

I measured the window's knowable instant against a bar's opening timestamp and
called the gap a lookahead. **The gap I kept reporting is exactly the 900 seconds
of the bar itself** — the bar's own settle time, which is not a leak, it is what
makes the bar knowable.

And the gate's 2700 is precisely the arithmetic of that: a floor of `s + 2700`
compared against `entry_ts + 900` **is** `s + 3600 <= entry_ts + 900`, which is
exactly "the 1h candle closes before the 15m bar closes". **The gate was right all
along.**

---

# 4. The measurement

| book | trades | flagged by my test | **real violations** |
|---|---:|---:|---:|
| `champ_long` | 839 | 6 | **0** |
| `champ_short` | 844 | 6 | **0** |
| `mcloff` | 912 | 7 | **0** |
| `mcloff_htf15` | 859 | 7 | **0** |
| `htf15` | 800 | 6 | **0** |
| `htfesmcl4` | 1230 | 4 | **0** |
| `sig_multi` | 520 | 5 | **0** |
| `sig_full` | 520 | 5 | **0** |
| | | **46** | **0** |

The six I named, measured both ways:

| era | # | bar OPENS (IST) | **decision (bar close)** | my flag | slack | verdict |
|---|---|---|---|---:|---:|---|
| IS | 46 | 2023-05-13 10:15 | **10:30** | YES | **0** | boundary — legal |
| IS | 316 | 2025-03-10 19:15 | **19:30** | YES | **0** | boundary — legal |
| IS | 522 | 2026-08-28 08:15 | **08:30** | YES | **0** | boundary — legal |
| OOS | 199 | 2022-03-19 09:15 | **09:30** | YES | **0** | boundary — legal |
| OOS | 258 | 2022-08-25 03:15 | **03:30** | YES | **0** | boundary — legal |
| OOS | 264 | 2022-09-10 19:15 | **19:30** | YES | **0** | boundary — legal |

**Every single one has slack exactly 0.** The 15m bar closes at the same instant
the 1h window candle closes. That is the tightest legal position, not an illegal
one — and a reviewer reading the chart would see the window line an hour earlier
and reasonably suspect a leak.

---

# 5. What was reverted

- the engine gate — back to `_floor < bar_ts + 900`, unchanged from shipped
- the harness anchors — back to their original forms
- all 28 re-pinned books — back to their original pins
- `fsent_champ_long_causalfloor` — the registry entry that existed only to work
  around the phantom bug is **gone**

**The chart, the pins and the engine are back to their pre-erroneous-report state.**

---

# 6. What the owner found that was real

The error was mine, but the investigation it produced was not wasted. One finding
survives, and it is a genuine defect — in the **display**, not the engine.

> *"UI mai vertical line ko ek candle se shift karo — waha se hi window khulegi.
> Abhi 18:30 mai hai par yeh pata 19:30 mai chalega."*

**The chart was drawing the window boundary at the wrong instant.**

`htf_windows` was built with `startTime = int(iv[0])` — the 1h candle's **open**.
The window is not knowable until that candle **closes**, 3600 seconds later. So a
window whose first knowable moment is 19:30 was being drawn at 18:30, asserting on
the chart that the window existed an hour before anyone could have known it.

That is exactly why this was believable as a bug, and it is a real problem: **the
chart was making an honest engine look dishonest.**

**The end side was already correct** — C17's `_wend_settle` stores the end
knowable (`exit_ts + 60` with 1m data). Only the start was drawing the raw open.

Fixed: `startTime = int(iv[0]) + 3600`, with the reasoning in the source at the
point of change. No pin moves — this is a chart rendering change only.

---

# 7. The lesson

**I compared a label against a decision time and called the difference a leak.**

The number I reported — "exactly 900 seconds early, every time" — should have been
the first clue that I was measuring the bar's own settle time and calling it a
defect. A leak of exactly one bar, identically, in every book, is arithmetic. I
preferred a clean story to a careful check.

The owner opened the chart, looked at the candles, and asked the one question I
should have asked myself first: **"when does this actually become known to a live
trader?"** The chart made the answer obvious in about a minute.

That is the third time this cycle a harness produced a confident wrong answer.
Two of them were caught by a structural argument — two books cannot have equal
pins, a tightening cannot add trades. **This one was caught by a person reading a
chart**, which is the strongest argument of the three and the reason the chart
exists.

---

*Engine, harness and all 28 pins reverted to their pre-report state. Shipping book
526 → restored to 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS.*
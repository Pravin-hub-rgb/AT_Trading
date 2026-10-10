# Window slack audit — is any pinned number contaminated by a lookahead?

**Run 2026-10-10. `exp_window_slack_audit.py` → `_window_slack_audit.json`.**

**Answer: no. Nothing in the family decided before its 1h window candle closed.**
One book has a reporting defect, and it is not the shipping book.

---

## Why this ran at all

Two claims sat in the record and they contradicted each other.

**Claim 1** — the original `fsent_champ_long_causalfloor` description, since withdrawn:

> "the shipped gate admits an LTF entry anywhere in (s + 2700, s + 3600] — a
> 900-second band in which the entry is knowable but the HTF window candle has
> NOT yet closed… the gate should have been s + 3600… MEASURED:
> `fsent_champ_long` has 6 such trades, every one exactly 900 seconds early."

That is a claim about the **gate**.

**Claim 2** — `exp_decision_instant.py`, which retracted claim 1:

> "the gate's 2700 is correct arithmetic, the six trades are legal."

That is a claim about the **trades**.

Both were about the same six trades and reached opposite conclusions, so at least
one was incomplete. The retraction was right that the trades are legal. It then
overreached: it generalised from "no sampled trade walked into the permissive
band" to "the arithmetic is correct". A gate that *admits* a lookahead is
permissive whether or not this dataset happens to use it.

---

## The gate, as written

`unified.py:1026` and `:1034`

```python
_floor = s + exp_window_floor_s          # default 2_700
...
if not (_floor < bar_ts+900 < e): continue
```

Define **slack** = seconds by which the decision instant runs past the close of
the governing 1h candle:

```
slack = (bar_ts + 900) - (s + 3600)
```

The gate admits `bar_ts + 900 > s + 2700`, i.e.

```
slack > -900
```

**So the gate is permissive by 899 seconds.** A trade landing anywhere in
`(-899, 0)` of slack would decide before its window candle closed. That is what
claim 1 said, and it is true of the gate. Whether any trade does it is a separate
question, and it is the one that decides whether a pinned number is contaminated.

---

## Measured, 29 books, both eras, 22,154 trades

| slack | trades | reading |
|---|---:|---|
| **< 0** — decides before window close | **0** | would be real lookahead |
| = 0 — simultaneous | 147 | legal, the boundary case |
| 0 < slack < 900 — inside the window candle | 0 | legal, tight |
| ≥ 900 — after the candle closed | 21,992 | comfortable |

**Zero trades anywhere in the family landed in the permissive band.** Not one.

`fsent_champ_long` itself: minimum slack **0**, and all 311 OOS trades satisfy
the gate as written.

---

## The 15 apparent violations — a reporting defect, not lookahead

The first run of this audit reported **15 trades with slack < 0**, every one of
them in `fsent_champ_long_mode_union`, with slack exactly −900 / −1800 / −2700.

That is arithmetically impossible. The gate admits `slack > -900`, so no trade
can pass it at −1800. Either the report and the gate disagree, or those trades
came through another door.

`exp_union_gate_truth.py` patches the engine so every filtered signal carries the
`bar_ts` its gate actually evaluated, and every booked trade records it:

| | |
|---|---|
| `gate_bar_ts != booked entry_ts` | **0 trades, both books** |
| `fsent_champ_long` — recorded window satisfies the gate | **311 of 311** |
| `fsent_champ_long_mode_union` — recorded window satisfies the gate | **311 of 442** |

The filtering loop and the booking loop read the same bar. But in union mode the
**reported** `window_start`/`window_end` is not the window that gated 131 of the
442 trades — for those, the reported window had already closed before the entry,
or closes after it.

`mode_union` matches against both interval sets (`intervals_b2`, then
`intervals_flip`) and breaks on the first hit; the window it reports and the
window it gated on come apart in the process.

**Why this is not lookahead:** the gate formula is checked *before* a trade is
accepted, and it cannot accept a trade whose window candle has not closed. The
131 trades were each gated by a window that was open at decision time.
`exp_union_window_label.py` reconstructs both interval sets from the engine's own
output and confirms a causal gate window exists for every flagged trade, closing
hours before the decision (trade #38: gate window closed 2021-03-04 23:30, decision
2021-03-05 05:45 — 6h15m of clearance, reported as −45 minutes).

**So: the pins stand. The label does not.**

---

## What this changes

1. **`fsent_champ_long_causalfloor`'s description was rewritten.** It asserted the
   retracted claim as fact and linked to two documents deleted in the retraction.
   It now says what the parameter actually does — a longer wait — and states the
   retraction up front instead of burying it.

2. **`mode_union`'s `window_start` should not be trusted** for lead-time or
   causality questions. It is reporting-only by the engine's own comment
   (`win_start=s  # report-only`), and in union mode it is wrong. Any chart that
   draws the window rectangle from it will draw the wrong rectangle for
   `fsent_champ_long_mode_union` — which is precisely what makes the book look
   like it trades on an unclosed candle.

3. **Every causality claim in the fsent family is now bounded by measurement**
   rather than by an argument about arithmetic. That bound is: the gate permits a
   900-second lookahead, and across 22,154 trades nothing used it.

## Reproduce

```
python backtest/tests/exp_window_slack_audit.py     # the distribution above
python backtest/tests/exp_union_gate_truth.py       # gate vs report, instrumented
python backtest/tests/exp_union_window_label.py     # reconstruction, both sets
```
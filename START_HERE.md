# START HERE

Everything below is written for whoever picks this up in three months with no
memory of it. If you only read one file in this repository, read this one, then
`backtest/docs/learn/02_verdict/PBO_DSR_GATE.md`.

---

## The answer, in four lines

1. A strategy family has a positive measured expectancy on real Bybit data,
   with costs verified against live demo fills and stop fills confirmed clean.
2. Thirteen book variants were explored. The best-looking was carried forward.
3. **The multiple-testing correction was never run — so it has been run. PBO
   0.57 to 1.00 against a 0.15 bar, and Deflated Sharpe fails for all thirteen
   books in both eras.**
4. Therefore: **no book is cleared for deployment.** Not "107 is bad" — the
   history simply does not identify which variant to pick. The next step is
   forward evidence on a frozen candidate, scored once.

Full reasoning and numbers: `backtest/docs/learn/02_verdict/PBO_DSR_GATE.md`

---

## Do not re-derive these. They are settled.

**The data is real.** A previous claim that the 1-minute candles were synthetic
was wrong and has been retracted. The files are byte-identical to a fresh Bybit
download. See `backtest/docs/learn/03_methodology_corrections/RETRACTION_SYNTHETIC_CLAIM.md`

**The cost model is sound.** Bybit taker is 5.5 bps per side. Orderbook spread
measured live at 0.012 bps. Stops fill essentially clean — measured, not assumed.
An apparent 11 bps "slippage" reading was the taker fee being double-counted in
the analysis, not market impact. See `03_methodology_corrections/SLIPPAGE_REPORT.md`

**The pipeline is deterministic.** 338 metrics across 13 books and 2 eras,
re-run from scratch: zero differences. If you re-run a harness and get different
numbers, something changed — that is the property worth preserving.

---

## The one decision that is actually open

Which of the thirteen books, if any, to trade. Everything else is done.

`107` and `108` are the two that come closest — each fails exactly one gate
criterion out of eighteen, both in survivability. `106` and `109` are 85-93%
overlapping duplicates of the same family, so choosing between the four is
closer to picking three than four.

The pre-declared gate sequence in `01_rules/SELECTION_RULES.md` produced **no
survivor out of thirteen**. PBO and DSR then established statistically what the
gate sequence had already concluded.

Note that `107` fails on "observed IS drawdown sat at the 99.85th percentile of
2000 shuffled orderings" — its historical ordering produced a near-worst-case
drawdown. That is a real risk signal, not noise.

---

## Where things live

```
backtest/docs/learn/
  README.md                     index, read this second
  00_reference/                 the source material the method came from
  01_rules/                     decided BEFORE the results they govern
  02_verdict/                   the answer
  03_methodology_corrections/   what went wrong, and what fixed it
  04_experiments/               raw evidence, superseded, kept for record

backtest/experiments/            the harness
  exp_verified_suite.py         metric suite, cross-checked with pandas
  exp_four_techniques.py        T1 sensitivity / T2 walk-forward / T3 stress / T4 MC
  exp_merge_rest.py             joins the 5-book and 8-book halves, refuses a bad merge
  exp_gate_eval.py              applies SELECTION_RULES.md
  exp_gate_counts.py            which criterion is doing the rejecting
  exp_extract_trades.py         caches per-trade R for all 13 books
  exp_pbo_dsr.py                CSCV and Deflated Sharpe
  exp_slippage_probe.py         measures real slippage against Bybit demo orders
  exp_real_slippage.py          slippage from candle data, and why it cannot be

live_stuff/                     the trading bot
  live_loop.py                  2149 LOC — NEEDS MODULARISING, see below
```

---

## Commands

Regenerate the results artifact the UI reads:

```
backend\venv\Scripts\python.exe backtest\tests\exp_results_export.py
backend\venv\Scripts\python.exe backtest\experiments\exp_enrich_results.py
```

Re-run a gate or a statistical test (each takes minutes; they re-run the engine):

```
backend\venv\Scripts\python.exe backtest\experiments\exp_gate_eval.py
backend\venv\Scripts\python.exe backtest\experiments\exp_pbo_dsr.py
```

The UI serves `/results` from `backtest/tests/_results.json`.

---

## Known problems, in priority order

1. **`live_loop.py` is 2149 lines in one file.** It works and it is stable, and
   that is exactly why it is dangerous to refactor casually. It wants splitting
   into signal handling, position lifecycle, risk, and reporting.

2. **The forward window is thin** — roughly one month, a handful of trades per
   book. The standard operational gate is 20-50 round trips or one quarter. It
   has not been reached, and that is precisely why the backtest is the only
   evidence available, and the backtest does not separate these books.

3. **The forward candle file is stale** — it ran to 2026-10-09 and has since
   been extended to 2026-10-19.

4. **`_results.json` was a snapshot from 2026-10-16** with no book codes, no gate
   verdicts and no PBO/DSR. `exp_enrich_results.py` was written to fix that and
   to be re-run whenever the underlying analysis changes.

5. **Four bugs were found in this codebase in a single session** — a
   profit-factor cross-check that could not fail, a drawdown percentage
   understated 17x, an ulcer index overstated 286x, and one piece of my own
   reasoning that got retracted. Assume more. Verify anything surprising.

---

## The one rule that matters most

**Do not tune against the forward window.** It is the only uncontaminated
evidence left, and it is small enough that a few glances will consume it. The
contract in `01_rules/FORWARD_TESTING_CONTRACT.md` was written before any of
this work and should not be edited to fit an outcome — amend it and date the
amendment instead.
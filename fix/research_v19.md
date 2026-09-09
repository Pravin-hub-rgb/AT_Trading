# AT_Trading BTC Strategy Research: v19 — HTF Window Definition Experiments

**Date:** 2026-09-08
**Author:** Pravin + AI Assistant
**Status:** Both variants REJECTED/NOT ADOPTED — v18 (window = HTF trade exit) confirmed as peak

---

## Table of Contents

1. [Context](#context)
2. [The Question](#the-question)
3. [v19a: 1.5R Window (r_touch) — REJECTED](#v19a-15r-window-r_touch--rejected)
4. [v19b: bias_flip Window — NOT ADOPTED](#v19b-bias_flip-window--not-adopted)
5. [Metric Philosophy: "Less trades = better?"](#metric-philosophy)
6. [Final Verdict](#final-verdict)
7. [Files](#files)

---

## Context

While validating v18 (see `backtest_checklist_v18.md`), Test A1 (HTF Window Check) exposed that
the HTF window definition had never been explicitly tested. The engine used:

```
window = [HTF trade entry_ts, HTF trade exit_ts]   (exit = SL / 3R target / 16-day cap)
```

Two alternative window definitions were proposed and tested:

- **r_touch ("1.5R fixed"):** window ends at the first touch of 1.5R from HTF entry.
  Rationale: "we reach 1.5R — we are done, look for new bias."
- **bias_flip:** window ends at the next OPPOSITE-direction HTF entry.
  Rationale: the HTF bias may outlive the individual HTF trade (e.g. bias alive after SL hit).

Config common to all runs: v18 engine, `mode=b2_vs_flip_chop`, `cooldown_bars=20`,
`max_consecutive_losses=5`, `sl_buf_atr=0.25`, `ext_stop_r=1.5`, 1m fills, fees 0.05%+2pt,
FULL 2023-2026.

---

## The Question

> "For the 1.5R cut we were trading less days, for until-exit more trades.
> I thought less trades = more better — but you were looking for average R being highest, right?"

**Answer: neither trade count nor average R was the decision metric.** The hierarchy used:

1. **Total net R** (what actually compounds — the book grows by total R, not avg R)
2. **Risk-adjusted:** net R / max drawdown
3. **Per-year consistency** (all 4 years positive; no single-regime dependence)
4. **Statistical significance of the delta** (t-stat of the added/removed cohort)
5. *Diagnostics (not targets):* avg R/trade, win rate, PF

It happens that v18 (until-exit) also has the highest avg R/trade (1.00 vs 0.83 vs 0.76),
so both lenses agree here — but that is a coincidence, not the criterion. "Less trades" is
not a virtue: it is only good when the removed trades are losers (see v18's streak halt,
which skipped 24 trades that were ALL losers → +66R). Cutting net-positive trades always
loses R (v16: −35R, v17: −13R, v19a: −130R).


## v19a: 1.5R Window (r_touch) — REJECTED

**Engine:** `v18_streak_halt.py` with `window_end="r_touch"` — window = HTF entry → first 1m bar
where price touches `entry ± 1.5 × |entry−sl|`; falls back to trade exit if SL/cap hits first.

### Results (4-year)

| Metric | v18 (exit) | v19a (r_touch) | Delta |
|---|---|---|---|
| Trades | 330 | 242 | −88 |
| **Total net R** | **+331.1** | **+200.6** | **−130.4** |
| Avg R/trade | 1.00 | 0.83 | −0.17 |
| Win% | 36.4% | 37.2% | — |
| PF | — | 2.51 | — |
| Max DD | 9.7R | 8.5R | −1.2R |

### Per Year

| Year | v18 | v19a |
|---|---|---|
| 2023 | +52.8 (74t) | +41.1 (50t) |
| 2024 | +86.3 (100t) | +84.3 (74t) |
| 2025 | +123.0 (91t) | +62.8 (73t) |
| 2026 | +69.0 (65t) | +12.4 (45t) |

### Why it failed

The 88 removed trades averaged **+1.48R each** — the BEST cohort in the book. Mechanism:
price pokes 1.5R intrabar → pulls back → LTF signal fires with close back inside 1.5R
(the ext-stop check already enforced this) → pullback continuation entry → wins.
A 1.5R poke does NOT mean the HTF bias is exhausted. Window length: avg 65.0h (exit) → 40.9h (r_touch).

**REJECTED.** Kept as `window_end="r_touch"` in the engine + wired as `htf_ltf_ver=v19` for comparison.

---

## v19b: bias_flip Window — NOT ADOPTED

**Engine:** `v18_streak_halt.py` with `window_end="bias_flip"` — window = HTF entry → entry_ts of
the next OPPOSITE-direction HTF trade (minus 1s), or data end. Bias-based, not trade-based.

### Results (4-year)

| Metric | v18 (exit) | v19b (bias_flip) | Delta |
|---|---|---|---|
| Trades | 330 | 485 | +155 |
| **Total net R** | +331.1 | **+368.6** | +37.5 |
| Avg R/trade | 1.00 | 0.76 | −0.24 |
| Win% | 36.4% | 34.8% | — |
| PF | — | 2.35 | — |
| Max DD | 9.7R | 9.6R | ~same |
| Net/DD | 34.0 | 38.6 | better |

### Per Year

| Year | v18 | v19b |
|---|---|---|
| 2023 | +52.8 (74t) | +52.0 (137t) — same R, 85% more churn |
| 2024 | +86.3 (100t) | +102.1 (129t) |
| 2025 | +123.0 (91t) | +159.4 (137t) |
| 2026 | +69.0 (65t) | **+55.1 (82t)** — worse, and DD 7.3 vs 5.0 |

### Why it was not adopted

1. **The +37.5R is noise.** Added cohort: 234 trades, avg +0.27R, **t = 1.21** (need ~2.0).
   Sequencing churn both ways: 79 baseline trades displaced (−26.0R) while 234 new ones added (+63.5R).
2. **2026 (regime closest to live) degrades:** less R AND deeper DD (+55.1/DD 7.3 vs +69.0/DD 5.0).
3. **2023 stress-chop year:** zero R gain for 85% more trades.

IS/OOS both improved nominally (IS +139→+154, OOS +192→+214) and net/DD is better —
so it is not a disaster, but it does not clear the evidence bar of this project
(v17 was rejected over a +13R exclusion; this delta is not even significant).

**NOT ADOPTED.** Kept as `window_end="bias_flip"` in the engine (not wired to routes).

---

## Metric Philosophy

The complete trade-count curve across all tested configs (4-year net R):

| Config | Trades | Net R | R/trade | What was cut/added |
|---|---|---|---|---|
| v5 (flip window) | 442 | +168.1 | 0.38 | — |
| v12+cd20 | 414 | +265.3 | 0.64 | 28 weak trades |
| v17 (ATR filter) ❌ | 389 | +261.9 | 0.67 | excluded were +13R |
| v16 (entry distance) ❌ | 347 | +230.5 | 0.66 | excluded were +35R |
| **v18 (exit window) ✅** | **330** | **+331.1** | **1.00** | skipped were all losers |
| v19a (r_touch) ❌ | 242 | +200.6 | 0.83 | excluded were +130R |
| v19b (bias_flip) ❌ | 485 | +368.6 | 0.76 | added cohort = noise (t=1.21) |

**Laws this table proves (3rd time each):**

1. **Trade count is not a lever.** Both directions from v18's 330 lose on real metrics.
2. **Cutting losers → R up** (cooldown, streak halt). **Cutting net-positive trades → R down** (v16, v17, v19a).
3. **Edge IS runners.** Win rate ~36%, avg win 4.29R, best +29.3R. Any indiscriminate filter
   risks deleting the rare runner that pays for everything. A filter must prove it cuts losers only.
4. **Unsignificant delta = no delta.** +37.5R on t=1.21 is not adoption material.

---

## Final Verdict

**v18 with `window_end="exit"` (HTF entry → trade exit, 16-day cap) is the confirmed peak.**
330 trades, +331.1R, maxDD 9.7R, positive all 4 years. No further window-definition work is warranted;
both alternatives are implemented in the engine behind `window_end=` and preserved for the record.

---

## Files

| File | Purpose |
|---|---|
| `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` | Engine with `window_end="exit\|r_touch\|bias_flip"` |
| `backend/src/btc/btc_routes.py` | `htf_ltf_ver=v19` → r_touch variant |
| `frontend/src/app/btc/page.tsx` | v19 dropdown option + lab table rows |
| `backend/debug/test_a1_v2.py` | A1 window validation (independent rebuild) |
| `backend/debug/test_v19_bias_flip.py` | r_touch vs bias_flip A/B stats |
| `backend/debug/test_v19_bias_flip_risk.py` | DD / IS-OOS / t-stat analysis |
| `fix/backtest_checklist_v18.md` | Validation checklist + changelog |

---

## Changelog

- 2026-09-08: v19a (r_touch) tested → REJECTED (−130.4R). v19b (bias_flip) tested → NOT ADOPTED (+37.5R, t=1.21, 2026 worse). v18 exit-window confirmed as peak. v19 wired to routes/frontend for comparison.

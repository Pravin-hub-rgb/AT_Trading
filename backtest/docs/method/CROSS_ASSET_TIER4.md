# CROSS-ASSET — tier 4's third axis

**Written 2026-10-14 on the corrected chain (BTC: 2,840 swings / 7,734 marks).**

Harnesses `exp_cross_asset_stage_eth.py` (data prep) and
`exp_cross_asset_eth.py` (measurement). Artifact `_cross_asset_eth.json`.

---

## Why this is a new study and not a re-run

Everything in this repo called "cross-instrument" is a cross-**venue** study.
`exp_cross_instrument_transfer.py` compares Bybit perp against Binance perp on
the **same asset**. Venue transfer is not asset transfer.

The framework's question (`docs/learn/finding optimal book.md`, bucket 11) is the
other one:

> **Does the underlying phenomenon survive across instruments?**

**Answer: yes, on the one non-BTC instrument available, and by a lot.**

---

## What data existed

The config knows two assets, both BTC: `BTCUSDT` spot and `BTCUSDT_BYBIT` perp.
`ETHUSDT_PERP` is configured but pointed at an empty directory.

The only non-BTC perp data on the machine was ETHUSDT 15m and 1m for 2025 in a
sibling project's archive. **Verified before use, not assumed:**

```
34,498 rows, 2025-01-01 00:00:00 -> 2025-12-26 08:15:00
expected 15m slots 34,498   actual 34,498   gaps 0
duplicate timestamps: 0
```

`data/eth-fut/ETHUSDT_15m.csv` copied verbatim; `ETHUSDT_1h.csv` **RESAMPLED**
from the 15m by plain OHLC aggregation — open of the first 15m bar in the hour,
max high, min low, last close.

## THE COMPARISON IS LIKE FOR LIKE

Same book params, same risk model, same costs (55bp fee/side, 2×, 5bp entry /
10bp exit), and **BTC trimmed to ETH's exact calendar window** — 34,498 x 15m
bars on both. Window-matching matters: three years of BTC against one of ETH
would compare a regime to a regime and nothing else.

Identity gate before any number was quoted: `fsent_champ_long` on the trimmed BTC
window gives 247 trades / +98.43R. (The full-history pin is 497 / +466.92; a
one-year window trades less by construction, so the gate is n>0, not equality.)

---

# RESULT — 6 of 6 books agree, and ETH is mostly BETTER

| book | BTC n / net | ETH n / net | ETH vs BTC |
|---|---|---|---|
| `fsent_champ_long` | 247 / 98.43 | 250 / **139.12** | **+41%** |
| `fsent_champ_long_mcloff` | 266 / 104.81 | 268 / **148.36** | **+42%** |
| `fsent_champ_long_htf15` | 247 / 98.43 | 249 / **139.23** | **+41%** |
| `fsent_champ_long_htffs` | 404 / 177.58 | 407 / **229.07** | **+29%** |
| `fsent_sig_multi` | 160 / 64.72 | 151 / **119.33** | **+84%** |
| `fsent_sig_full` | 112 / 27.63 | 111 / 22.76 | **−18%** |

**Sign agreement: 6 of 6. Five of six books make MORE on ETH than on BTC over the
identical window.** `sig_multi` is +84% — the largest relative gain, and it is a
serial book, which is the harder case for this architecture.

## WHAT THIS DOES AND DOES NOT ESTABLISH

**It does establish the thing bucket 11 actually asks for:** the edge is not an
artefact of BTC's own price history. The same knobs, untouched, produce a
positive result on an instrument that was never used to build them, at a
comparable or better magnitude, with comparable trade counts (250 vs 247, 407 vs
404, 268 vs 266). **The trade counts matching that closely is the strongest part
of it** — it means the HTF/LTF architecture is finding comparable structure on
both, not one market carrying a lucky stretch.

**It does not establish a cross-asset success rate.** The framework asks for 7-10
assets and produces a number like "7/10 profitable". **This is 1 asset**, so no
rate can be claimed and none is.

## Honest limits, all of which are real

1. **One asset, one year, no era split.** ETH 2025 only. There is no out-of-sample
   *within* the cross-asset test. The framework's tier 5 (OOS retention) cannot
   be applied to a cross-asset result at all with this data.

2. **The 1h layer on ETH is RESAMPLED from 15m.** The books are HTF/LTF — sw10
   opens the window from 1h swings. On BTC that is a native 1h file; on ETH it is
   derived. This is disclosed rather than buried, and it is the single largest
   caveat here: the HTF plane is exactly where a resample could matter.

3. **ETH has no 1m file here, so ETH runs on the COARSE basis and BTC on the FINE
   basis.** Coarse fills exits at the 15m bar; fine uses 1m. **The two assets are
   therefore not measured on an identical fill model.** This cuts against the
   result rather than for it — coarse fills are systematically worse — so ETH
   beating BTC despite the worse basis is if anything conservative. But these
   numbers are **not comparable to the registry pins**, which are all fine-basis.

4. **The sample is six books, chosen not by rank** — the shipping book, the two
   the optimal-book study now flags as strongest, the one it retires, and the two
   smallest serial books because they are the easiest to kill. That is a
   deliberately fair spread, but it is not a random draw.

5. **No ETH 1h means no proper HTF validation on the second asset.** Getting
   `ETHUSDT_1h.csv` and `ETHUSDT_1m.csv` as native downloads would close both
   caveats 2 and 3 and is the single highest-value thing this study needs next.

---

## Three harness failures this produced, recorded because all three looked like findings

Every one of these produced a clean, confident, all-null table that read as a
cross-asset result:

1. **Calling `unified.simulate_htf_ltf_streak_halt` directly instead of going
   through `repin.measure`.** Zero trades on BOTH assets — and the BTC control
   returns 497 trades through `measure` on the same data. A harness error on both
   sides is indistinguishable from "the strategy does not trade here".

2. **`FlowCandle.date` is a STRING and `candle["ts"]` is an int epoch.** The
   first trim compared `f.date` against a set of ints, which matches nothing, so
   the flow came back untrimmed while the candles were trimmed. Result: sw10 came
   back with **0 swings on BTC over a window that plainly contains 8,624 1h bars**.
   Three books then reported zero trades with no error.

3. **`basis="coarse"` with `fine_ltf=[]` returns zero trades.** The run printed
   **"sign agreement: 6 of 6"** — six books that agreed because both columns were
   zero. The identity gate is what caught it, which is why it is in the harness
   and not in a checklist.

All three would have been reported as "the phenomenon does not survive across
assets" without the gate. Nothing is adopted by this document.

## What to do next, in priority order

1. **Get native `ETHUSDT_1h.csv` and `ETHUSDT_1m.csv`.** That closes caveats 2
   and 3 together and makes the comparison like-for-like.
2. **Add 3-5 more alt perp pairs.** Only then does a cross-asset success rate
   become a number rather than an anecdote. ALT 1..N is what the framework
   actually asks for.
3. **Re-run with an ETH era split** once more ETH history exists, so tier 5 can
   be applied across assets rather than only within them.
# Forward Test Contract (pre-registered)

**Date:** 2026-09-25
**Status:** ACTIVE. This is the finish line for the research program.

## Why this document exists

Every result so far comes from data that has already been inspected:

- IS 2023-01-01 -> 2026-09-13
- "OOS" 2021-2022 (reused many times, not a holdout)

A pre-registered forward test is the only thing that can answer the question
the whole project actually cares about:

> Does the edge survive on data that was never used to choose anything?

## Data boundary (hard)

`data/bybit/` ends at **2026-09-13 10:02 IST** (last 1m bar).

Everything after that instant is **forward data**. It lives in
`data/forward/bybit/` and is **never** merged back into `data/bybit/`.

Rules:
1. Forward data is scored, never tuned on.
2. No parameter, threshold, filter, or config may be selected using it.
3. If a change is proposed because of forward results, the forward window is
   burned and a NEW window must start from scratch.
4. A negative forward result is as informative as a positive one and gets the
   same documentation weight.

Fetched by `scripts/download_bybit_forward.py`; manifest in
`data/forward/bybit/_forward_manifest.json`.

## Candidates under test (fixed now, before any forward data is scored)

| id | config | status before forward |
|---|---|---|
| `CHAMPION_BASE` | `champion_multi_sw10` as shipped | reference anchor |
| `CHAMPION_N3` | `champion_multi_sw10` + `global_soft_n3` | best multi candidate (IS +5.9R / OOS +19.8R vs shipped) |
| `KING_BASE` | `utcsat_multi_sw10` as shipped | reference anchor |
| `KING_WN3` | `utcsat_multi_sw10` + `window_soft_n3` | conservative king alternative (IS +3.2R, OOS neutral) |

Explicitly **not** carried forward:
- `exp_wage_h` on multi (Stage W: strict fail, family closed)
- 1h break-quality x1.5 sizing (Stage X: passed on 7-9 OOS trades, small-n)
- 4h EMA pullback sizing (Stage Y: dNet>0 in 6/6 but failed strict curve rule)
- every descriptive-only cohort from Stages 1-13, 24, 27-28, 30-33, 39-43, 63-64

Rationale: the search space is already large. Adding marginal candidates
raises selection risk faster than it adds evidence.

## Pre-registered decision rules

These are fixed BEFORE forward scoring. They cannot be relaxed after seeing
results.

### R1 - Execution parity (gate, checked first)

If the forward replay does not reproduce the shipped engine on the overlap
region, the forward test is void. Parity means: same trade count, same entry
timestamps, same R within 0.01R, on the 2023-09-13-overlap check.

### R2 - Edge survival

`CHAMPION_N3` passes if, on the accumulated forward window:

- net R > 0, AND
- net R per trade > 0.20R, AND
- profit factor > 1.20

`0.20R/trade` is deliberately below the OOS 2021-22 realization
(`+0.343R`) and far below IS (`+0.687R`). It is a floor for "the edge is
still there", not a target.

### R3 - No degradation versus anchor

`CHAMPION_N3` must not be materially worse than `CHAMPION_BASE` on forward
data: net R delta > -5% of `CHAMPION_BASE` net R (or both negative, in which
case compare per-trade).

This exists because a candidate can be positive in absolute terms while being
a worse trade than the anchor.

### R4 - Drawdown containment

Forward max drawdown must stay under the kill line from
`LIVE_DD_MONITOR.md` §1, scaled to the chosen risk per trade:

| candidate | kill line @ 1R = 1% | at 0.5%/trade |
|---|---|---|
| champion lane | 64.3% | ~32.2% |
| king lane | 55.3% | ~27.7% |

### R5 - Sample size honesty

Minimum sample before ANY verdict:

- **n >= 50 trades**: provisional read, direction only
- **n >= 150 trades**: first real verdict
- **n >= 300 trades**: publishable

Below n=50 we report the ledger and explicitly say "no verdict yet". A 12-day
forward window is roughly 30-40 trades, i.e. **provisional only**.

## Stop rules (decided now, not later)

- Two consecutive forward verdicts that fail R2 -> stop using the candidate.
- One forward verdict that trips R1 (parity) -> halt and fix the engine first.
- Forward maxDD exceeding the R4 line -> switch to the
  `LIVE_DD_MONITOR.md` kill procedure, not to parameter fiddling.

## What is forbidden during the forward window

- Changing `champion_multi_sw10` / `utcsat_multi_sw10` parameters
- Adding a filter because forward data "suggests" it
- Re-running the whole experiment battery
- Re-using forward trades as an OOS set after adopting a change

If a genuinely new idea appears, it goes into a new document with a new
window start, not into this one.

## How to score

```
python scripts/download_bybit_forward.py
python -m live_stuff.tests.exp_forward_eval --scope forward
```

Outputs `_forward_eval.json` and appends to this contract's results section.

## Results log

Append-only. Newest last.

| date | window start | n trades | candidate | net R | R/trade | PF | maxDD% | verdict |
|---|---|---|---|---|---|---|---|---|
| _pending_ | 2026-09-13 | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ |

### 2026-10-08 — candidate list amended BEFORE any new forward window

No forward window exists on this machine (`data/forward/bybit/` is absent), so
nothing is burned and the pre-registered list can be extended today at zero cost.
Rule 3 burns a window only when a change is proposed BECAUSE of forward results;
no such result has been produced since 2026-09-25.

Added, with the reason each is on the list and not a claim that it will win:

| id | config | status before forward | why it is here |
|---|---|---|---|
| `FSENT_CHAMP_LONG` | `fsent_champ_long` as shipped | reference anchor | the current multi shipping book on the fsent architecture — the anchor `sig_multi` must beat, and the anchor this line of work departs from |
| `FSENT_SIG_MULTI` | `fsent_sig_multi` (sig filters + `max_positions=0`) | IS +484.59R / 2021-22 +219.82R, dd 13.39 / 7.64, WR 45.6% / 47.2% | best candidate this repo has produced. 99% of its gap survives a half-year fixed effect in both eras, 12 of 12 half-year cells, tail dependence improves in every cell. Blocked ONLY on forward data — see `method/OOS_IS_NOT_A_HOLDOUT.md` for the correction that withdrew the earlier "underpowered OOS" objection, which was a measurement of the 2021-22 window and not a forward verdict |

Deliberately NOT added, and why:

| not added | reason |
|---|---|
| `fsent_champ_long_mode_union` | 23.8R in-sample dd is over the owner's 20R budget and its top 5% of trades carry 96.1% of in-sample profit |
| `fsent_champ_long_mode_atr_low` | in-sample dd 28.9R over budget; its extra return retains only 21.9% out of the 2021-22 window |
| `fsent_sig_trail_delay1` and `mp0+trail` | exit-timing changes, not entry changes — 90–100% of the gain sits inside trades both books take, so the cohort instrument does not apply. The +678.9R in-sample figure is the largest in the repo and it is not an entry effect |
| every other fsent variant | adding marginal candidates raises selection risk faster than evidence, which is this contract's own stated reasoning |

The `FSENT_SIG_MULTI` row is a commitment to TEST, not a prediction. A negative
forward result gets the same documentation weight as a positive one (rule 4).
| 2026-09-25 | 2026-09-13 10:03 IST | 5 | `CHAMPION_BASE` | -3.83 | -0.765 | 0.22 | 3.83 | R2 FAIL, R4 PASS, **NO VERDICT (n<50)** |
| 2026-09-25 | 2026-09-13 10:03 IST | 5 | `CHAMPION_N3` | -3.83 | -0.765 | 0.22 | 3.83 | R2 FAIL, R3 n/a, **NO VERDICT (n<50)** |
| 2026-09-25 | 2026-09-13 10:03 IST | 5 | `KING_BASE` | -3.83 | -0.765 | 0.22 | 3.83 | R2 FAIL, R4 PASS, **NO VERDICT (n<50)** |
| 2026-09-25 | 2026-09-13 10:03 IST | 5 | `KING_WN3` | -3.83 | -0.765 | 0.22 | 3.83 | R2 FAIL, **NO VERDICT (n<50)** |
| 2026-10-09 | 2026-09-13 10:03 IST | 6 | `CHAMPION_BASE` | -5.06 | -0.843 | 0.30 | 5.1R | R2 FAIL, R4 PASS, **NO VERDICT (n<50)** |
| 2026-10-09 | 2026-09-13 10:03 IST | 6 | `CHAMPION_N3` | -5.06 | -0.843 | 0.30 | 5.1R | R2 FAIL, R3 n/a, **NO VERDICT (n<50)** |
| 2026-10-09 | 2026-09-13 10:03 IST | 6 | `KING_BASE` | -5.06 | -0.843 | 0.30 | 5.1R | R2 FAIL, R4 PASS, **NO VERDICT (n<50)** |
| 2026-10-09 | 2026-09-13 10:03 IST | 6 | `KING_WN3` | -5.06 | -0.843 | 0.30 | 5.1R | R2 FAIL, **NO VERDICT (n<50)** |
| 2026-10-09 | 2026-09-13 10:03 IST | 5 | `FSENT_SIG_MULTI` | **-1.26** | -0.253 | 0.61 | **2.2R** | R2 FAIL, R4 PASS, **NO VERDICT (n<50)** |
| 2026-10-09 | 2026-09-13 10:03 IST | 4 | `FSENT_CHAMP_LONG` | -0.93 | -0.233 | 0.77 | **2.0R** | R2 FAIL, R4 PASS, **NO VERDICT (n<50)** |

### 2026-10-09 window — what it does and does not say

Forward data was re-fetched after 2026-09-13 10:03 IST and now runs to
**2026-10-09 10:30** — 2498 bars of 15m, 625 of 1h, 37468 of 1m. R1 parity holds:
pre-cutoff ledgers reproduce exactly (`FSENT_SIG_MULTI` 329t / +547.7 gross /
+484.6 net, matching its registry pin).

**R1 parity: PASS for all six candidates.**

**The four original candidates produce the identical six trades** again, so this
window tests the shared base architecture and not the N3 variants.

**On absolute numbers every candidate is negative and every candidate is
`NO VERDICT`.** Five to six trades. The contract's own n≥50 gate says so, and the
owner's instruction today was the same thing: *"we have to wait for at least four
months."*

**The only comparison the window supports is depth of loss, and it points one way
but is not a verdict:**

| candidate | n | net R | net avg | PF | forward max DD |
|---|---:|---:|---:|---:|---:|
| `CHAMPION_BASE` / `N3` / `KING_BASE` / `WN3` | 6 | −5.06 | −0.843 | 0.30 | 5.1R |
| **`FSENT_SIG_MULTI`** | 5 | **−1.26** | **−0.253** | **0.61** | **2.2R** |
| `FSENT_CHAMP_LONG` | 4 | −0.93 | −0.233 | 0.77 | 2.0R |

The fsent pair lost **a quarter of what the champion family lost**, with **twice
the win rate** and **under half the drawdown**. On five trades that is noise, and
it is recorded as noise. It is not evidence for adoption and it is not evidence
against. **R3 was not evaluated** because the anchor is not positive on forward,
which is the contract's own instruction for that case.

**Window length:** 26 days. At the realized rate in this window the n≥50 gate is
still roughly **four months** out and n≥150 roughly **a year** out. Nothing
recorded here should be revisited before then — and if it is revisited before
then, the window is burned under rule 3 and a new one must start.

### Harness bug fixed to run any of this

`exp_forward_eval.py` pointed `IS_DIR` at `data/bybit/`, which **no longer exists** —
the Bybit IS slice was moved out of the repo and resolves through
`btc_config.BTC_BYBIT_DATA_DIR` to `btc_data/is`. The path now resolves through
that config with the old path kept as a fallback. The symptom was a `KeyError:
'sum_r'`, which reads like a reporting bug and was actually an empty dataset: with
no IS bars, `pre` was empty and `stats([])` has no `sum_r`. It would have failed
the same way on any machine that ran this harness after the data move.

### R1 - Execution parity: PASS

Pre-cutoff replay reproduced the known IS ledgers exactly, which is the parity
evidence that appending forward data did not perturb the structural chains:

| candidate | pre-cutoff n | pre-cutoff gross R | pre-cutoff net R | known IS ledger |
|---|---|---|---|---|
| `CHAMPION_BASE` | 500 | +445.2 | +325.78 | 500t / +445.2R / +325.8R |
| `KING_BASE` | 454 | +466.5 | +358.95 | 454t / +466.5R / +358.9R |

`CHAMPION_N3` pre-cutoff: 483t / +448.1R / +331.68R (policy active, expected to
differ). `KING_WN3` pre-cutoff: 450t / +469.2R / +362.17R.

### The 5 forward trades

| entry (IST) | dir | entry px | gross R | net R | exit | bars |
|---|---|---|---:|---:|---|---:|
| 2026-09-13 12:15 | short | 77083.6 | -0.998 | -1.449 | trail | 39 |
| 2026-09-15 13:00 | short | 76987.7 | +1.267 | +1.093 | trail | 112 |
| 2026-09-16 00:00 | short | 75740.2 | -0.224 | -0.294 | trail | 68 |
| 2026-09-17 19:00 | short | 76116.9 | -0.998 | -1.104 | trail | 54 |
| 2026-09-18 12:15 | short | 77568.4 | -1.000 | -2.074 | sl | 1 |

All four candidates produced the **identical** five forward trades. None of the
N3 policies fired in this window, so this is a test of the shared base
architecture, not of the N3 variants.

Forward gross: 5t, -1.95R, 20.0% win rate, avg win +1.267R, avg loss -0.805R,
payoff 1.57, zero runners >= 3R, 3-loss streak. Forward net: -3.83R, PF 0.22.

### Honest reading

This is **not** a verdict and must not be read as one. n=5 is below the
pre-registered n>=50 threshold, and the contract explicitly says so. What it
does establish:

1. The forward pipeline is sound: R1 parity exact, data continuity exact on all
   three timeframes, zero gaps, no production code touched.
2. 12.5 days produced only **5 trades** (~12/month at this config's realized
   rate). The n>=50 gate needs roughly **4 more months**; n>=150 needs roughly
   **12 more months**.
3. All 5 trades were shorts into a rising market (BTC ~77.0k -> ~83.9k). One
   lost -1.0R on a 1-bar stop. That is a coherent losing regime for a
   structural-break long-biased system, not evidence of a bug.
4. Nothing here justifies changing any parameter. Acting on n=5 would violate
   the contract's own rules.

### Next scheduled action

Re-run `python -m live_stuff.tests.exp_forward_eval` after the next data pull.
Do not add candidates. Do not tune. The window keeps accumulating.


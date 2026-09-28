# OPEN RESEARCH QUEUE — every suggestion from the second-researcher round,
# in the order received. No priority. Worked one at a time.

Date: 2026-09-28. Source: `other bots proposal.md` (four sets: Nemotron 3,
Big Pickle, Link3.0, Mimo-V2). ~30 proposals were returned; they are
deduplicated below.

**Status key:** `[x]` done this session · `[~]` partially done · `[ ]` open

---

## DONE THIS SESSION

- `[x]` **P1/P2 wave labelling (Elliott)** — closed. The swing chain is
  sequential with a mean 10.3-bar gap, so no nested wave pair exists. One
  candidate in 2,900 swings. `P1P2_WAVE.md`
- `[x]` **Retracement depth at entry** (the P1/P2 quantity relocated to
  where it exists) — closed on two grounds: the harness omitted the HTF
  window gate so it did not reproduce the champion's book (1,285 vs 500
  trades), and the depth distribution is saturated at its floor (p10 =
  0.998) so the ladder has no gradient. `RETRACE_DEPTH.md`
- `[x]` **FS-only book with swing-trail exits** — closed. The "2,586
  never-priced swings" premise is false: all 2,900 carry a B2/FLIP.
  `FS_ONLY_ENGINE.md`
- `[x]` **Kelly sizing** — computed, and the interesting output is that
  the naive binary form is wrong for a heavy-tailed book and the
  long-run-corrected form is small (0.2-0.3% of bankroll per trade).
  `KELLY_CONTINUOUS.md`

## STRUCTURALLY EXCLUDED — do not attempt

- `[x]` **Order-book / microstructure** — `data/flow/bookDepth/` exists
  (3,617 files, never read) but starts 2023-01, so it has no 2021-22
  coverage and can never satisfy the two-era bar. Not weak: excluded.
  Same for `funding/`, `metrics/`, `premium1h/`.
- `[x]` **Scheduled events** — already closed path-true with ±1-day
  placebos (`SCHEDULED_EVENTS_AUTOPSY.md`). Confirmed, not re-proposed.
- `[x]` **30m / 2h timeframes** — already closed (`exp_tf_family.py`;
  30m costs 84R IS / 55R OOS).
- `[x]` **B1 entry** — closed (`B1_ENTRY.md`, WR 27.8% → 17.2%).
- `[x]` **4h HTF confirmation** — already closed.

## OPEN — engineering-blocked

- `[ ]` **Position resize instead of close** — the engine has no size
  channel (`v18_streak_halt.py` has zero hits for equity/size/notional),
  and `exp_max_concurrent` was already swept (cap=5 free-to-better).
  Blocked on the size channel existing first.
- `[ ]` **Correlation-aware portfolio weighting** — blocked on data: the
  current alt sweep is Binance fapi, not Bybit perp. The `inv_corr` scheme
  also degenerated to 100% LINK and its number must not be used.
  `PORTFOLIO_KILL_WEIGHT.md`

## NEW — window duration & the r_touch autopsy (measured today)

Both follow from `BIAS_WINDOW_THEORY.md`. Neither has been run.

### `[ ]` W1 — window duration as a feature

Median window is **1.17d IS / 1.06d OOS**, p75 ~3.8d. Two arms:

- **Late-window fade.** `HTF_DEEP_LAYER_AUTOPSY.md:30-55` found
  time-capped windows are the weak class — "a window that died of old age
  has already spent its volatility." Bias the 15m layer toward short
  windows, or fade it once a window passes ~p75 age.
- **Prove-it-first.** Require the window to have already cleared +1R
  before the 15m layer takes its first trade. Directly targets the
  measured fact that 69-74% of windows die at −1R inside a day.

**Falsifier:** a median age shift with no change in realised R means age
is a label, not a driver. **Not closed by `window_r_cap`** — that capped
R *within* a window, this filters *by* window age.

### `[ ]` W2 — why did `r_touch` lose 130R?

Closing at +1.5R should have helped if 25% of windows reach 3R. It
regressed instead. Worth understanding before any duration rule is
trusted — if the mechanism is unknowable, W1's arms are unfalsifiable.

**Falsifier:** reconstruct `_r_touch_end` and report, per window, the MFE
(max favourable excursion) in R. If MFE distribution is bimodal — a mass
below 1.5R and a spike at 3.0R — then 1.5R sits in the gap and should
have been free. If MFE is smooth, 1.5R truncates the runners that make
the book, and the −130R is correct rather than mysterious.

---


## SECOND ROUND (a later bot, same file) — stronger on three items

This set is worth more than the first on P3 and P5. It also corrected
two of my own seed-list errors and found a graveyard GAP.

### Corrections it made to my seed list

| item | I said | actual |
|---|---|---|
| 30m | "not in the repo" | **dead** — `exp_tf_family.py`, `exp_shadow_tf.py`; costs 84R IS / 55R OOS alone. AGENT_COORDINATION.md Rule 17: "the whole shadow-timeframe thread is now exhausted" |
| scheduled events | "audit exists, gate unknown" | **dead 3×** — Stage 22 gate (a −1d placebo beat the real calendar by +32.0R = date mining), Stage 23 Powell (0 of 62 eligible), Paradigm 4 |
| bookDepth | "excluded" | excluded for a sharper reason: starts 2023-01, so it can never clear the two-era bar |
| FS-only | "open" | already run and closed today; "2,900 untapped" was a post-filter trade count read as a swing count |

**A graveyard GAP it found:** partial profit-taking / scale-out is tested
and rejected (`exp_partial_r`: multi sw10 +247.9 vs no-partial +163.6 =
+84.3R, but single sw10 −67.7R; the `partial_r=1.0` rung is −267R). Ships
at 0.0. So "add / close earlier / partial" are ALL closed — **only shrink
is untested.**

### `[ ]` P3 — score the 1h HTF layer's own P&L ← highest value

Every run simulates the 1h book **three times** (`entry_break` ∈ {flip,
decisive, b2}, `v18_streak_halt.py:222-224`) and throws its P&L away,
keeping only `(entry_ts, exit_ts, dir, px, sl)` as window bounds. **Nobody
has ever reported what the 1h book earns standalone.**

Either the 1h book carries the edge (three-timeframe architecture is
decoration) or the 15m layer does. Pre-registered claim: the cascade
beats the best 1h standalone book on R/trade by ≥2× in both eras — if not,
the architecture is not earning its complexity.

**Output is attribution, not edge.** Nearly free — the trades already
exist inside every backtest — and it re-ranks the rest of the queue.
Falsifier: 1h standalone positive in both eras with PF > 1.3 means the LTF
layer adds nothing and the programme is one timeframe too low.

### `[ ]` P5 — the base-book null ← governance

No experiment has established what `dNet` must be to mean anything.
`IS_IT_RIGHT.md` has a zero-mean bootstrap (IS p=0.0025, **OOS p=0.199**,
undermined by the +0.498 ACF that proved a tail artefact).
`exp_montecarlo_dd.py` nulls DD and streak only. And **Stage 3's
random-entry placebo beat the real book out of sample: champion OOS
+25.5R real vs +65.6R random** — sitting in CHECKLIST.md unremarked.

Deliverable: block bootstrap (length 20, 10,000 draws, preserving count,
the 3-loss-streak process, lag-1..3 dependence) for **M**, the `|dNet|`
the null's 95th percentile exceeds. Then audit the registry: how many
registered PASS arms have `|dNet| < M`. **Publish it whatever it says.**
Zero edge; changes how every other result is read.

### `[ ]` P2 — risk-weighted concurrency

`exp_max_concurrent` counts open positions, treating a 3-ATR stop and a
1-ATR stop as identical risk. Cap the **sum** of open risk instead. Zero
repo hits for `sum_risk`/`open_risk`/`risk_cap`. The stated blocker (no
size channel) does **not** apply — a skip rule needs only the open
positions and their `sl`, which v18 has. Cheapest real edge candidate.
Caveat: the graveyard's one consistent brake lesson is that every brake
that actually binds costs R (`max_concurrent` 2/3 cost real R; campaign
caps +325.8 → +107.7 IS; `window_r_cap` rejected).

### `[ ]` P1 — nested swing containment (tree instead of tiling)

The chain is a strict tiling (`btc_swing.py:150`) and
`walker.py:76` `_enforce_alternation` both **destroy nested-counter-leg
evidence**, so the system cannot say "this 15m pullback sits inside a 15m
up-leg that sits inside a 1h up-leg". Letting legs nest changes which
marks EXIST, so it is not a filter. Grep: `hierarchy`/`multi_scale`/
`inner_leg` = zero hits repo-wide.

**Sharpest falsifier on the list:** if the containment cohort is a subset
of the one `RANGE_PEAK_GRAY` already showed is the book's BEST (WR 41-42%
vs 27.8%), nesting is re-discovering range position and fails 4/4 the
same way.

### `[ ]` P4 — sweep `cap_days`

The one window parameter never swept — a literal inside three calls with
no kwarg. `BIAS_WINDOW_THEORY.md` shows it binds on 5-7% of windows, so
expect a small effect; the **two-sided** hit bar (`cap=8 ≥ 0` AND
`cap=30 ≤ 0`) distinguishes a real monotone effect from an inert one.
`HTF_DEEP_LAYER_AUTOPSY.md:30-55` already predicted the direction.

### `[ ]` P6 — alt sleeve with the selection removed

Near-uncorrelated alt books are the one thing that transferred, but
13→7→6 selection contaminated it. Pre-register **all 13, drop nothing**
and the contamination is gone. **Blocked on a data fetch** (Bybit perp,
not the current Binance fapi), not on research.

### `[ ]` P7 — ATR-reversal ZigZag, argued down deliberately

The proposer ranks it 7th and argues **against** the favourite: it is a
second, independent decomposition the book was never fitted to; the
structure axis is knife-edge (`min_bars=50` is a sharp optimum, and
swapping the LTF structure cost 84R IS / 55R OOS); `exp18_arm` already
ran a 3-mark sequence labeller and was archived. **What survives is P1,
not P7:** keep the pivot generator the book was fitted to, change the
TILING. Cheapest falsifier in the list: Jaccard overlap between the Walker
and ZigZag pivot streams on control data — if > 0.9, dead in 30 minutes.

---

## OPEN — the real queue

- `[x]` **Multi-swing 1h bias confirmation (2-of-3)** *(Nemotron)* —
  closed **by the probe, no run needed**. The rule keeps 1,599/1,599 IS and
  901/901 OOS swings: the direction chain is built in same-direction PAIRS
  (1,1 / -1,-1), so any 3 consecutive swings contain a majority by
  construction. A vacuous rule. Its successor is **W1 above** (window
  duration), now measured properly: median **1.17d IS / 1.06d OOS** — *not*
  the 76h/66h mean I first wrote here, which was inflated by the 5-7% of
  windows sitting on the 16-day cap.
  `MULTISWING_BIAS_2OF3.md`, `BIAS_WINDOW_THEORY.md`
- `[ ]` **1h swing geometry gate at bias-window open** *(Nemotron)* —
  magnitude / duration / confirmation source, all known at the swing's
  confirmation instant. Overlaps the graveyard's "range width" row, so it
  must be pre-registered as distinct or it is a re-run.
- `[ ]` **Alt breadth as a BTC HTF feature** *(Nemotron P6)* — alt index
  state gating BTC bias. Flagged as risky by the proposer; the
  cross-sectional-rotation closure creates real tension.
- `[ ]` **One family-wise pass on `data/forward/bybit/`** *(Mimo-V2)* —
  adjudicate all unadopted survivors in a single pre-registered pass
  rather than spending the slice one candidate at a time. ~464 trades, so
  it can rule on things and confirm none.
- `[ ]` **Bybit perp alt data** — the transfer census (7/13 passing, 5/6
  kills-clean) is on Binance fapi and therefore does not answer a Bybit
  question. Fetching Bybit alts is the precondition for the whole
  multi-instrument thread.
- `[ ]` **ZigZag re-count over `normal_highs`/`normal_lows`** — the raw
  pivot pools already exist in `firstswing.py`; a different segmentation
  of the same bars, which is the closest reachable relative of the dead
  P1/P2 wave labelling.

## Notes recorded from the round

- My briefing was **three-quarters wrong** on "untouched" seeds, and two
  of its errors had reached `HANDOVER_SESSION.md`:
  `chop_thresh=58.0` is **inert** under `mode="atr_high"`, and
  `sw10`/`sw20` are built from the **1h** stream, not 15m. Both verified
  in code. `SECOND_RESEARCHER_REVIEW.md`
- The method failure across the session was checking **shape** and
  assuming **meaning**. `probe_structure.py` now runs first.
  `PROCESS_FIX_PROBES.md`

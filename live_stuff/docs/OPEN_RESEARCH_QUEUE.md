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

### `[x]` P2 — risk-weighted concurrency — **RUN 2026-09-29, no adoption. `RISK_CONCURRENCY.md`**

Premise **validated** (my "strictly serial" assumption was wrong in the
item's favour): **max concurrent open positions = 6 / 5 / 6 / 3.** The
`busy_until` guard compares a *date* against a *datetime* as strings, so it
does not block same-day re-entry — an engine inconsistency, **recorded, not
fixed** (the book is profitable with it and the control is pinned).

The gradient is real and 4/4 consistent — tight-stop trades run PF 1.7–3.4
against 1.4–1.7 for wide-stop. **But no brake extracts it**: the wide trades
are worse *and still profitable*, so every binding threshold spends more than
it earns. Best arm is `skip widest 10%` at **4/4 positive but +13.3R max**,
which is **1/15 of M = 193.4R** — an order of magnitude inside the null.

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

## `[x]` P3 — score the 1h HTF layer's own P&L — DONE, and it INVERTED

Run as `probe_htf_attribution.py`. Full write-up: **`HTF_ATTRIBUTION.md`**.

The user challenged the "15m finds its own edge in a dead window" reading:
*if 70% of windows are dead and we still make +325R, either the window
contributes none of it or we're missing something.* **Second horn, and it
is the bigger result.**

**Q1 — 1h standalone is worthless as a book.** flip +50.6R IS but
**−6.0R OOS** (PF 0.96); decisive +28.1 / −19.6; b2 +4.0 / −7.0.

**Q3 — but the window is a hugely binding gate.** Same 15m engine, same
swings, same exits, window removed:

| | 1h-gated | ungated | gate worth |
|---|---|---|---|
| IS | 396t **+227.5R** PF 1.87 | 843t **+17.0R** PF 1.04 | **+210.5R** |
| OOS | 242t **+22.7R** PF 1.14 | 530t **−24.7R** PF 0.91 | **+47.4R** |

In OOS the window is the difference between positive and negative.

**Q2 — the mechanism.** Cascade R by parent window's exit: **+3R windows →
55.7% WR, +231.4R. −1R windows → 8.6% WR, −133.6R** on 47% of all IS
trades. The window is a **quality oracle**, not a permission slice — and
its verdict only lands at the exit, a median 1.1 days later.

**Caveat recorded up front:** Q2 is partly circular (a +3R window and a
−1R window are different price paths). Q3 is not — it is a live gate.

**Consequence for the queue:** the pre-registered direction on P4 is now
**suspect**. The time-capped windows are the IS book's **+131.2R** bucket
(2nd largest), so cutting `cap_days` to 8 would likely destroy R rather
than add it. P4 must be re-registered before it runs.

## `[x]` P3-B — READ THE ORACLE EARLY — **RUN 2026-09-29, ANSWERED, nothing adopted. `HTF_ORACLE_P3B.md`**

**The read works and is causal, but carries no exploitable information.**

- **`DEAD` is structurally impossible — 0 trades in all four cells.** A 15m
  entry can only fire while the parent leg is still above −1R, so the LTF
  layer *already is* that filter. Half the oracle was never new information.
- Of the two reachable states, **`NEUTRAL` has a better PF than `PROVED` in
  all four cells** (2.56/2.20/2.69/2.12 vs 2.10/1.07/2.48/1.17). Once the
  parent is already +1.5R, the LTF trade is late.
- **Both selection arms are 4/4 negative.** This closed **W1's
  "prove-it-first" arm** (`only PROVED`: −232.2 / −76.5 / −234.9 / −61.3).
- The pre-registered falsifier could not be run as written: `skip DEAD`
  keeps 500/500 trades, so there is no coverage to match a window-open-only
  arm against.

**Scope note — this answers the *early read*, not the *gate*.** The harder
claim below, that the 1h layer is a hindsight label, is **untested and still
open**. Run 1 of the harness was void (baseline used `risk` where
`parent_entry` belonged); the built-in causality probe caught it and is
retained.

<details><summary>original brief, retained</summary>

The user asked what the 1h layer should do differently, since B1/B2/FLIP
obviously do not work there. **Answer: the 1h layer's job is not to be a
book, it is to be an oracle — and the oracle is currently read only in
hindsight, a median 1.1 days late.**

`HTF_ATTRIBUTION.md` shows the 1h leg has no standalone edge (best mode
+50.6R IS, **−6.0R OOS**) yet gates the 15m book worth +210.5R IS /
+47.4R OOS, and splits it into a 55.7%-WR cohort (+231R) and an 8.6%-WR
cohort (−134R). **That verdict is knowable in hindsight but partially
LIVE** — the 1h leg passes through +1.5R and −1R while the window is still
open. Use that state inside the open window.

**This is NOT the dead `r_touch`.** `r_touch` closed the *window* at
+1.5R and lost 130R. This leaves the window open and changes what the 15m
layer may do inside it. Opposite action, different mechanism.

**Falsifier (pre-registered before any run):** the live-oracle arm must
beat the same arm using only information available at window open, on
**both** eras. If it does not, the oracle is genuinely unknowable in real
time and Q2's entire advantage is hindsight — in which case the honest
conclusion is that the 1h layer is a good *hindsight* label and a useless
*live* gate, and the whole programme should stop pretending otherwise.

**Note this is also the only item that can resolve W2.** If the oracle is
readable early, then closing a window at +1.5R losing 130R becomes
intelligible: `r_touch` threw away the *timing* that made the early
verdict useful. Run P3-B before W2 and W1 — it is the same measurement
seen from the live side.

## `[x]` P3/P4 — the live_R floor: REJECTED on the real champion, 0/7

**Superseded. Read `CHAMPION_FLOOR_REJECTED.md` first.**

`P3-C` and `P3-D` reported this as "the strongest candidate produced today"
with drawdown halving in both eras. **That was measured on a book that is
not the champion**, in three ways at once: the shipped engine instead of
`engine:"patched"` (so `exp_mltf`/`exp_persist` were missing and the book
had 356 trades, not 500), a guessed config (`b2_vs_flip_chop/chop=61.8/
sl_buf=0.25/ext=1.5/mcl=5` instead of `atr_high/chop=58.0/sl_buf=0.01/
ext=3.0/mcl=3/cooldown=8`), and **gross** instead of NET.

Re-run properly (`exp_champion_true.py`) with the pin reproduced first
(IS 500t/+325.8R NET, OOS 279t/+70.1R NET — both exact):

| floor | IS net | OOS net | both? |
|---|---|---|---|
| **None (champion)** | **+325.8R** | **+70.1R** | — |
| −0.25 | +228.2R | +31.7R | no |
| −0.10 | +230.4R | +39.7R | no |
| +0.00 | +220.6R | +53.4R | no |
| +0.10 | +211.7R | +11.0R | no |
| +0.25 | +110.4R | +18.4R | no |
| +0.50 | +175.4R | **−17.3R** | no |

**0 of 7. Not one arm beats the champion in either era.**

**What survives:** the inversion is real on the champion too — `+0.50` has
the best IS PF in the grid (2.97) and turns OOS negative (PF 0.93). The
ceiling/floor conflict is a property of the idea, not of the mis-specified
book.

**Why it fails here:** the champion runs `ext_stop_r=3.0` (a live-R
ceiling) and builds the book from `exp_mltf` + `exp_persist` — repeated
entries inside a window. **An underwater 1h leg is often a continuation
state on this book, not a warning.**

## `[x]` P5 — the base-book null: **M = 479.9R IS / 193.4R OOS**

Full write-up: **`BASE_BOOK_NULL.md`**. Move-block bootstrap, block=20,
10,000 draws, pins reproduced first (IS 500t/+325.8R, OOS 279t/+70.1R).

| | observed | null mean | **M (p95 of a reshuffle)** | percentile | p |
|---|---|---|---|---|---|
| IS | +325.8R | +316.5R | **479.9R** | 45.7th | **0.914** |
| OOS | +70.1R | +69.2R | **193.4R** | 47.9th | **0.958** |

**The champion's own net sits at the 46th/48th percentile of a reshuffle
of itself. It is not distinguishable from reordering its own trades.**

### The bar every dNet must now clear

- **IS: |dNet| > 479.9R**
- **OOS: |dNet| > 193.4R**

**Immediate audit of headline results against it:**
- `exp_trail_half=1` (IS +103.8R, OOS +40.3R dNet) — **inside the null
  in both eras.** Its famous OOS maxDD −42% is not backed by a net move
  that clears M.
- `partial_r` (+84.3R) — inside the null.
- The `live_R` floor — rejected for real reasons, and would have been
  inside M regardless.

This does not make those results wrong; it means the repo has been scoring
arms against a number whose significance was never established.

### What this changes

1. **The forward slice is now usable.** `data/forward/bybit/` was blocked
   because nothing meant anything without a null. M exists. With
   M = 193.4R, a 60-70 trade slice **can rule things out and confirm
   nothing** — which is exactly what the queue already suspected. One
   family-wise pre-registered pass is now the right next move.
2. **Single net-R deltas stop being evidence.** Required instead: a
   forward pass, or a variance-reduced statistic (per-year, per-regime,
   ex-best-5), which the repo already computes.
3. **Not a reason to stop.** It is a reason to stop trusting one number.

**Caveat carried:** block length 20 was pre-registered to match
`exp_montecarlo_dd.py`, not tuned. Shorter block → wider null; much
longer → destroys the serial structure the method exists to preserve.
A block-length sensitivity sweep is the obvious next check.

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

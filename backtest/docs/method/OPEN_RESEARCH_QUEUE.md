# OPEN RESEARCH QUEUE — every suggestion from the second-researcher round,
# in the order received. No priority. Worked one at a time.

> **READ FIRST: [`method/THE_CHAMPION_HANDOFF.md`](method/THE_CHAMPION_HANDOFF.md)** —
> the authoritative P55–P98 record. It lists what is validated, what is
> exploratory, what is **retracted or corrected**, and what is **closed —
> never rerun as new**. Three recorded numbers are now superseded: **P89
> inverted, P92's drawdown depths were ~15× too large, P83's 37.3R max DD
> is actually 30.5R.** And **P96/P97: the concurrency guard has never
> once fired** — 58% of shipped IS R is not deployable by a bot whose
> guard works.

Date: 2026-09-28. Source: `signal/other bots proposal.md` (four sets: Nemotron 3,
Big Pickle, Link3.0, Mimo-V2). ~30 proposals were returned; they are
deduplicated below.

**Status key:** `[x]` done this session · `[~]` partially done · `[ ]` open

---

## DONE THIS SESSION

- `[x]` **Regime routing on `chop` for `fsent_champ_long`** — closed by the
  owner after measurement, nothing adopted. `chop` and `atr_high` are different
  variables (direction efficiency vs bar size) and disagree on ~25-35% of bars,
  but every routing mode built on the disagreeing cell loses in at least one era:
  best arm buys +42R IS by removing two trades at 21R each, next one supplies
  +46R of its +41R from a single trade while doubling IS drawdown. Gate and union
  both fail on 58 and 307 OOS trades. Mechanism: the cell's win rate is only 5.9
  points better, its edge is the top decile (p90 +9.42R vs +3.23R) and its median
  trade is *worse* than the book's, so it cannot be waited for at that size.
  Engine modes reverted; shipping book verified unchanged. **Numbers and the two
  structural traps in `closed/CLOSED_DO_NOT_REPEAT.md`.** Table:
  `_experiments_failed.md`
- `[x]` **Remove `ext_stop_r` from `fsent_champ_long`** — set to explicit
  `0.0`. Provably inert since C17: 3.0 and 0.0 give byte-identical trade lists
  and an identical equity curve in all four cells. Never omitted, because `BP`
  carries `1.5` and that binds for 51 IS / 36 OOS trades.
  `method/EXT_STOP_R_RIDGE.md`
- `[x]` **Is `exp_persist=7` still tuned right after C17?** — swept 0-7 against
  the shipping base. No value beats 7 in both eras, and the one candidate
  (persist=5, byte-identical IS, +3.2R OOS) rests on a single 2.2-day long worth
  +7.6R; drop it and persist=5 is 4.5R worse. 7 stands.
  `_persist_sweep.md`
- `[x]` **Halt flip trigger** — written as a rule rather than a verdict: halt
  stays ON while the live max-DD budget does not comfortably cover the book's own
  tail (need 14.16R, the halt-off OOS max_dd). Not "when we can afford more
  losses", which re-decides itself with the owner's mood. Counter-book registered
  and pinned so the flip needs no re-run.
  `method/EQUITY_LENS_EXT_AND_NOHALT.md`
- `[x]` **P1/P2 wave labelling (Elliott)** — closed. The swing chain is
  sequential with a mean 10.3-bar gap, so no nested wave pair exists. One
  candidate in 2,900 swings. `method/P1P2_WAVE.md`
- `[x]` **Retracement depth at entry** (the P1/P2 quantity relocated to
  where it exists) — closed on two grounds: the harness omitted the HTF
  window gate so it did not reproduce the champion's book (1,285 vs 500
  trades), and the depth distribution is saturated at its floor (p10 =
  0.998) so the ladder has no gradient. `method/RETRACE_DEPTH.md`
- `[x]` **FS-only book with swing-trail exits** — closed. The "2,586
  never-priced swings" premise is false: all 2,900 carry a B2/FLIP.
  `method/FS_ONLY_ENGINE.md`
- `[x]` **Kelly sizing** — computed, and the interesting output is that
  the naive binary form is wrong for a heavy-tailed book and the
  long-run-corrected form is small (0.2-0.3% of bankroll per trade).
  `method/KELLY_CONTINUOUS.md`

## STRUCTURALLY EXCLUDED — do not attempt

- `[x]` **Order-book / microstructure** — `data/flow/bookDepth/` exists
  (3,617 files, never read) but starts 2023-01, so it has no 2021-22
  coverage and can never satisfy the two-era bar. Not weak: excluded.
  Same for `funding/`, `metrics/`, `premium1h/`.
- `[x]` **Scheduled events** — already closed path-true with ±1-day
  placebos (`method/SCHEDULED_EVENTS_AUTOPSY.md`). Confirmed, not re-proposed.
- `[x]` **30m / 2h timeframes** — already closed (`exp_tf_family.py`;
  30m costs 84R IS / 55R OOS).
- `[x]` **B1 entry** — closed (`method/B1_ENTRY.md`, WR 27.8% → 17.2%).
- `[x]` **4h HTF confirmation** — already closed.

## OPEN — engineering-blocked

- `[ ]` **Position resize instead of close** — the engine has no size
  channel (`v18_streak_halt.py` has zero hits for equity/size/notional),
  and `exp_max_concurrent` was already swept (cap=5 free-to-better).
  Blocked on the size channel existing first.
- `[ ]` **Correlation-aware portfolio weighting** — blocked on data: the
  current alt sweep is Binance fapi, not Bybit perp. The `inv_corr` scheme
  also degenerated to 100% LINK and its number must not be used.
  `method/PORTFOLIO_KILL_WEIGHT.md`

## NEW — window duration & the r_touch autopsy (measured today)

Both follow from `method/BIAS_WINDOW_THEORY.md`. Neither has been run.

### `[~]` W1 — window duration as a feature - **ANSWERED 2026-10-10, not closed. `method/WINDOW_FLOOR_AND_AGE.md`.** Median window age at entry is 2.2-2.4 days on every book and flat; R per trade is NOT flat and moves 3x between age buckets, and the direction is OPPOSITE between families - the champ books earn most from young windows (1.46 and 1.82 R/trade in the first 36h) while `sig_multi` earns almost nothing there (0.53) and most from the oldest bucket (4.47 R/trade on 55 trades, 58% win). Age is a real feature with no single extractable rule. **NOT a candidate:** the strongest cell rests on n=55 and the buckets were chosen after the result existed, which is how `biasmom05` got killed. Closing it needs the treatment `mcloff` got - re-derive, then a period control - plus forward confirmation of the direction.

Median window is **1.17d IS / 1.06d OOS**, p75 ~3.8d. Two arms:

- **Late-window fade.** `signal/HTF_DEEP_LAYER_AUTOPSY.md:30-55` found
  time-capped windows are the weak class — "a window that died of old age
  has already spent its volatility." Bias the 15m layer toward short
  windows, or fade it once a window passes ~p75 age.
- **Prove-it-first.** Require the window to have already cleared +1R
  before the 15m layer takes its first trade. Directly targets the
  measured fact that 69-74% of windows die at −1R inside a day.

**Falsifier:** a median age shift with no change in realised R means age
is a label, not a driver. **Not closed by `window_r_cap`** — that capped
R *within* a window, this filters *by* window age.

### `[x]` P3 — score the 1h HTF layer's own P&L — **RUN 2026-09-29. The 1h layer has no standalone edge. `method/HTF_STANDALONE_P3.md`**

| net of costs | champ IS | champ OOS |
|---|---|---|
| 1h FLIP | 355t **+1.9R** PF 1.20 | 204t **−23.6R** PF 0.96 |
| 1h B2 | 309t **−49.6R** PF 0.92 | 194t **−21.7R** PF 0.94 |
| **CASCADE** | 500t **+325.8R** R/t +0.652 | 279t **+70.1R** R/t +0.251 |

The claim (**cascade ≥2× the best 1h standalone**) **passes at 4.6×**. The
falsifier (1h positive both eras, PF > 1.3) **does not fire** — 1h is
negative OOS and never above PF 1.20.

**The 1h layer supplies direction, it does not carry edge.** Same fact P3-B
found from the other side.

**Two corrections this run had to make:** the primary 1h book is
`htf_trades`, *not* `htf_trades_flip` (the engine returns no
`htf_trades_decisive` at all, and the first run of this file reported the
flip book as empty); and `r_multiple` sums to +50.6R gross where `net_r`
gives +1.9R, so costs are ~0.24R/trade and every figure above is net.

### `[x]` W2 — why did `r_touch` lose 130R? — **RUN 2026-09-29. MFE is bimodal; the recorded reason is wrong**

| MFE | champ IS | champ OOS |
|---|---|---|
| below 1.5R | **65.7%** | **66.0%** |
| 1.5–3.0 band | **12.6%** | **12.4%** |
| reaching 3R | **21.7%** | **21.6%** |

**The 1.5–3.0 band is the thinnest part of the distribution, in both eras.**
By the queue's own falsifier, 1.5R sits in a gap and should have been free —
**so the −130R is not explained by MFE, and `r_touch` was rejected for a
reason that does not hold up.**

**The blame is retracted, not the rejection.** An unexplained regression is
still a regression, and 1.5R still truncates the 21.7% of legs that run past
it. But the recorded *reason* must not be cited again.



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

### `[x]` P5 — the base-book null governance - **CLOSED 2026-10-10, and the deliverable overturned the quoted answer.** `method/NULL_AUDIT_P5.md`.

Both halves are now done. The block bootstrap was **re-derived on the book the file names but does not use**: M = **771.09R IS / 384.36R OOS**, against the 381.7 / 205.5 that `BASE_BOOK_NULL.md` carried. That quoted M was measured on `champion_multi_sw10` (its own first paragraph says 500t / +325.8R, which is not the shipping book and does not match the registry either - that key reads 502 / +279.33), and it is an absolute R figure when a null width scales with the book's trade count and per-trade spread. **The bar was roughly half its real size and the error ran permissive.**

The registry audit then ran on all 25 selected books with the **paired permutation**, which is the right test for a candidate - is this arm's choice of trades better than its parent's, rather than is its net above zero. **Five distinct books clear p < 0.05**: `mcloff` and `nohalt` in BOTH eras (0.0312 / 0.0117), `mcloff_htf15` and `htfesmcl4` in sample only, and the two sig short books - the latter two with a NEGATIVE gap, i.e. reliably worse than the parent, which is a result rather than an endorsement. `fsent_champ_long_mcloff` is the only book significant in both eras and the only one that also clears the period control with power.

Nothing clears the corrected ABSOLUTE bar, which is expected and is not the interesting result: the shipping book sits at the 58th and 45th percentile of a reshuffle of its own trades. The p-values are now written into the eight affected registry descriptions, because a finding that lives only in a document is one click from not existing.
### `[x]` P2 — risk-weighted concurrency — **RUN 2026-09-29, no adoption. `method/RISK_CONCURRENCY.md`**

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

### `[x]` P7 — ZigZag re-count over the raw pivot pools — **RUN 2026-09-29, dead, as the queue predicted. `method/QUEUE_SWEEP.md`**

Jaccard of a textbook ZigZag against the shipped chain: **0.0063 / 0.0017 /
0.0003** at 3/5/8% (champ IS), **0.0134 / 0.0037 / 0.0010** OOS. Effectively
**zero overlap at every threshold, both eras, both lanes.**

A ZigZag and the shipped chain find disjoint pivots — so the shipped chain
is a **segmentation**, and segmentation is a parameterised choice, never a
discovery. Same lesson as the 2h plane test: the plane and the chain carry
the edge.

### `[x]` W1 — late-window fade — **RUN 2026-09-29, era-flipped and inside the null. `method/QUEUE_SWEEP.md`**

Violent sign flip on every threshold — IS `−301.9R` at 2d, OOS `+15.4R`;
utcsat `−328.7R` / `+5.1R`. Largest `|dNet|` anywhere is **17.1R against
M = 193.4R**.

**The durable part, and it points the opposite way to intuition:** the p75
window-age cohort has a **higher** win rate than the book in **all four
cells** (33.9% vs 30.0%, 29.0% vs 28.0%, 31.7% vs 29.6%). Older windows are
not tired — they are the ones that worked. Consistent with P38's stale-legs
result and P3-B's impossible `DEAD`. Three results, one direction, none
tradable at the required size.

### `[x]` P1 — nested swing containment — **CLOSED 2026-09-29 without the rebuild. `method/NESTING_P1.md`**

The full test needed `btc_swing.py:150` + `walker.py:76` edited, which moves
the control off the pinned book. **The falsifier did not need that**, so
containment was measured on the existing chain first.

**It fires, from the other direction.** CONTAINED cohort WR is **29.1% /
25.9% / 30.0% / 27.2%** — *below* the book's 30.0 / 28.0 / 30.8 / 29.6 in
**all four cells**, and nowhere near the 41–42% `RANGE_PEAK_GRAY` it was
supposed to match. The `OUTSIDE` cohort is the best in every cell
(33.8 / 37.0 / 33.7 / 37.2%) — the good cohort is the one nesting would
*exclude*. Depth makes it worse: the deepest contained half is **−4.5R and
−6.7R OOS** on the two lanes.

**Verdict: do not build it.** Closed with the reasoning recorded so a future
revisit finds this rather than re-running it.



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

### `[x]` P4 — sweep `cap_days` - **CLOSED 2026-10-10.** Swept 3/7/10/14/21. 21 clears the negative half-year (+835.93R, 0 negative, against +680.52R at the default 10). The adjacent question - how long after a window OPENS you may enter - was a hardcoded literal and is now `method/WINDOW_FLOOR_AND_AGE.md`: raising it to 5400 adds +5 to +8R on every champ book, and only `champ_long` needs 7200 to clear its cell. **Neither is a new book; both refine a lever the loss-run cutoff already provides.**

The one window parameter never swept — a literal inside three calls with
no kwarg. `method/BIAS_WINDOW_THEORY.md` shows it binds on 5-7% of windows, so
expect a small effect; the **two-sided** hit bar (`cap=8 ≥ 0` AND
`cap=30 ≤ 0`) distinguishes a real monotone effect from an inert one.
`signal/HTF_DEEP_LAYER_AUTOPSY.md:30-55` already predicted the direction.

### `[ ]` P6 — alt sleeve with the selection removed

Near-uncorrelated alt books are the one thing that transferred, but
13→7→6 selection contaminated it. Pre-register **all 13, drop nothing**
and the contamination is gone. **Blocked on a data fetch** (Bybit perp,
not the current Binance fapi), not on research.

### `[x]` P7 — ATR-reversal ZigZag - **CLOSED 2026-10-10, deliberately not run.**

The proposer ranked this 7th and argued against it, and the falsifier it proposed is the cheap one: a Jaccard between the Walker and ZigZag pivot streams on control data, dead in 30 minutes if above 0.9. **That was already answered by the other P7** - ZigZag against the shipped chain returns 0.0063 / 0.0017 / 0.0003 at 3/5/8%, effectively zero overlap in both eras and both lanes (`method/QUEUE_SWEEP.md`). The two pivot streams find disjoint pivots, so the comparison has already been made and the overlap is nil.

Closed on the existing evidence rather than re-run for form. What survives from that line is P1, not P7: keep the pivot generator the book was fitted to and change the tiling.
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

- `[ ]` **KING_SINGLE report quotes three different nets for one book, and the
  book is not in the registry** *(found 2026-10-07, by the doc gate)*.
  `signal/KING_SINGLE_fullstack_wage10_cd0_RESEARCH_REPORT.md` is dated
  2026-09-22 and self-contradicts. Its own causal-SL disclaimer says the change
  moved the book **from +310.7R to +244.5R** in sample, and both metric tables
  (line 88 and line 505) say **NET R +360.61**, which is neither figure. On top
  of that the config it names, `fullstack_wage10_cd0_single_sw10`, **is not in
  `EXPERIMENTS` at all** — so there is no pin to say which number was ever true.
  Do not "fix" it by refreshing the tables: that is a guess about which of
  +310.7, +244.5 and +360.61 is meant to be current. What it needs is a decision
  about what happened to that config — retired, renamed, or never pinned — and
  then one number chosen on purpose. Left in place deliberately: it has been in
  the tree long enough that a fresh reader will land on it and trust one of the
  three. The gate now suppresses it rather than flagging it (the config is not
  in the registry, so there is no pin to have gone stale), so this entry is the
  only thing pointing at it.

- `[x]` **Multi-swing 1h bias confirmation (2-of-3)** *(Nemotron)* —
  closed **by the probe, no run needed**. The rule keeps 1,599/1,599 IS and
  901/901 OOS swings: the direction chain is built in same-direction PAIRS
  (1,1 / -1,-1), so any 3 consecutive swings contain a majority by
  construction. A vacuous rule. Its successor is **W1 above** (window
  duration), now measured properly: median **1.17d IS / 1.06d OOS** — *not*
  the 76h/66h mean I first wrote here, which was inflated by the 5-7% of
  windows sitting on the 16-day cap.
  `method/MULTISWING_BIAS_2OF3.md`, `method/BIAS_WINDOW_THEORY.md`
- `[x]` **1h swing geometry gate at bias-window open** *(Nemotron)* —
  **CLOSED at P54**, so this entry is historical, not open. Trailing 1h
  swing geometry gave a clean era inversion, and P55 then showed the
  inversion is not detectable at runtime (IS/OOS medians within 0.01–0.10
  against an IQR of ~0.75). `method/HTF_GEOMETRY_P54.md`, `method/REGIME_DETECT_P55.md`
- `[x]` ~~**Alt breadth as a BTC HTF feature**~~ *(Nemotron P6)* — **BLOCKED
  on Bybit perp alt data** (below). Not runnable without a data fetch.
- `[x]` **Nemotron P4 — 30m timeframe**: **RUN at P66, closed, nothing
  adopted.** `method/TF_INTERP_P66.md`, `exp_tf_interp.py`. P58 had skipped
  everything between 15m and 1h — the space the champion lives in — so P66
  ran LTF ∈ {15m, 30m, 45m} at a fixed 1h HTF with lag-matched `min_bars`
  (50/25/17) and the champion's own 1h/10 held constant.
  **30m in OOS more than doubles the champion in both lanes: +141.9R vs
  +70.1R and +103.1R vs +60.2R, with every quality measure better at once —
  R/trade 0.537 vs 0.251, PF 2.06 vs 1.59, DD 17.6 vs 37.3, WR 29.9% vs
  28.0%. And it costs −187.8R / −238.5R in IS.**
  Every measure moves together and in **opposite** directions across eras,
  which is the sixth appearance of the era-split pattern. **The adaptive
  fix is exactly the gate P55 could not support** — the eras are not
  separable at decision time — so switching by regime would be a lookahead
  wearing a switch. Not adopted; the 15m LTF is confirmed from both sides
  of the gap.
- `[ ]` **Bybit perp alt data** — the transfer census (7/13 passing, 5/6
  kills-clean) is on Binance fapi and therefore does not answer a Bybit
  question. Fetching Bybit alts is the precondition for the whole
  multi-instrument thread, and for P6 above. The two figures live at
  `method/AGE10_ALT_SWEEP.md` (7/13, harness `exp_age10_alt_sweep.py`) and
  `method/PORTFOLIO_KILL_WEIGHT.md` (5/6, harness `exp_portfolio_kill_weight.py`).
- `[x]` ~~**ZigZag re-count over `normal_highs`/`normal_lows`**~~ —
  **CLOSED at P70, dead.** `method/ZIGZAG_CLOSED_P70.md`. The integration finished:
  the engine's contract is in `_collect_signals` (`btc_engine.py`), and the
  adapter had violated it twice — `dir` must be the STRING `"up"`/`"down"`
  (an int collapses every swing to −1) and `kind` must be `B2`/`FLIP`
  (`"H"`/`"L"` skips every break). Both failed **silently**, printing clean
  tables of empty cells. With the engine actually trading:
  **12 of 24 cells clear M = 193.4R and all 12 are negative.**
  A fixed-percentage reversal rule is a worse swing detector than the
  engine's own tuned `min_bars` rule. Nemotron P10 answered. This was the
  last fully runnable item on the queue.
- `[ ]` **Stationary-block bootstrap to size the forward null** — added by
  P62. M = 193.4R comes from a two-year block; a forward slice is shorter
  and its null is wider, so the required forward length is currently
  unspecified. P62's disjoint-block version was **underpowered** (2–25
  blocks per size makes `max − min` a badly biased-low spread estimate) and
  its "20 trades suffice" reading is explicitly withdrawn. Build and
  validate the resampling estimator before anyone plans a date around it.
  `method/FORWARD_NEED_P62.md`
- `[x]` ~~**One family-wise pass on `data/forward/bybit/`**~~ — **NOT
  EXECUTABLE, entry corrected 2026-09-29.** It promised "~464 trades, so
  it can rule on things and confirm none." P61 measured the actual slice:
  **12.5 days, 14 1h swings, 2 champion trades and 1 candidate trade.** Two
  orders of magnitude short of the promise, and a long way below even the
  60–70 trade floor. At the champion's ~135 trades/year the 60–70 trade
  range is **~5–6 months of forward data, roughly March 2027** — a
  rate-based estimate, not a computed requirement. Do not spend a day
  building this pass. `method/STABILITY_FORWARD_P61.md`, `method/FORWARD_NEED_P62.md`

---

## `[ ]` P59 — `cand_4h1h`: 4h HTF + 1h LTF as a COMPLEMENT, not a replacement

**Status: REGISTERED CANDIDATE. Not adopted. Nothing changed in production.**

The only architecture in the programme that beats the champion in OOS, in
both lanes. Registered because its weakness has an identified cause, and a
candidate with a known weakness is decidable on the forward pass.

| | IS | OOS |
|---|---|---|
| champion 1h + 15m | 500t +325.8R PF 2.38 R/t 0.652 WR 30.0% | 279t +70.1R PF 1.59 R/t 0.251 WR 28.0% |
| **cand_4h1h 4h + 1h** | 286t +212.8R PF 2.59 R/t 0.744 WR 35.3% | 189t **+98.0R PF 2.02** R/t 0.519 WR 32.8% |
| utcsat champion | 454t +359.0R PF 2.62 R/t 0.791 | 253t +60.2R PF 1.58 R/t 0.238 |
| utcsat cand_4h1h | 257t +165.4R PF 2.38 R/t 0.643 | 171t **+72.1R PF 1.86** R/t 0.421 |

Better on R/trade, PF **and** win rate in **both** eras. Costs −113.0R IS /
−193.5R utcsat for 214 / 197 fewer trades. Gains +27.9R / +11.9R in OOS.
Params are lag-matched: HTF 4h `min_bars=3`, LTF 1h `min_bars=12`, both
~12h swing confirmation. Harness `exp_tf_matrix.py`.

### Why it is a complement and not a replacement — P59

Trades matched on **(4h bucket, direction)** only; never on `r_multiple`,
`outcome`, `exit_ts` or `pnl`. Result: **only 4–7% of trades are common.**

| lane / era | SHARED | CHAMP-ONLY | CAND-ONLY |
|---|---|---|---|
| champion IS | 19 (4%) +65.1R | **478 +370.0R** | 267 **+228.9R** |
| champion OOS | 19 (7%) +3.7R | **259 +103.0R** | 170 **+119.1R** |
| utcsat IS | 18 (4%) +62.5R | 433 +393.8R | 239 +181.6R |
| utcsat OOS | 15 (6%) +8.4R | 238 +84.2R | 156 +92.8R |

**No exclusive group is negative in any cell.** So the IS cost is **not bad
trades being removed — it is 214 fewer trades.** It is a volume story, not a
quality story. The candidate is a different book trading the same asset.

### The queued experiment, pre-registered

**One union of `champion_multi_sw10` and `cand_4h1h` under a single
slot-conflict rule, fixed before running.** The programme's existing
semantics cover it: `SKIP` = pre-entry reject with the slot free, `GRAY` =
reject while holding the slot. The rule must be pre-registered and chosen
without looking at the outcome of either book.

Passes only if it beats the champion in **both eras in both lanes** and
clears **M = 193.4R**.

**Explicitly NOT claimed:** the deduplicated sum of both books is
+664.0R IS / +225.8R OOS. That is a **bound, not a measurement** — the
engine holds one position, a union needs a conflict rule, and any rule
picked now is picked by looking at these cells.

### The overlap signal, recorded and not used

19 shared trades return **+3.425R each at PF 7.99 in IS** — the highest
conviction reading anywhere in the programme. In OOS the same 19 return
**+0.194R at PF 1.37.** Layer agreement is strong in the era the book was
built in and unremarkable out of it: the **third** appearance of the
IS-fitted pattern (P56 expiry, P58 granularity, here agreement). Recorded,
not gated on. 15–19 trades per cell is also too thin to filter on.

---

## `[x]` P59 → P61 — `cand_4h1h`: **DOWNGRADED, NOT A CANDIDATE** (2026-09-29)

**Closed at P61. `method/STABILITY_FORWARD_P61.md`, harness `exp_stability_forward.py`.**

P58 and P59 recorded `cand_4h1h` (4h HTF + 1h LTF) as a registered
candidate on the strength of an aggregate: better R/trade, PF and win rate
than the champion in **both** eras, at the cost of −113.0R in IS. **P61
broke that aggregate into calendar half-years and the advantage is a coin
flip — 4 wins and 4 losses of 8 in IS, 3-1 in OOS — and the candidate has
lost every period since 2025H2.**

| period | champ R/t | cand R/t | cand |
|---|---|---|---|
| 2023H1 | +0.897 | +1.842 | YES |
| 2023H2 | +1.217 | +2.319 | YES |
| 2024H1 | +1.081 | +0.518 | no |
| 2024H2 | +0.421 | +1.557 | YES |
| 2025H1 | −0.126 | +0.054 | YES |
| **2025H2** | **+1.470** | **−0.401** | no |
| **2026H1** | **+0.814** | **−0.115** | no |
| **2026H2** | **+1.807** | **+0.056** | no |

**The aggregate advantage lives in 2023–2024 and is gone since 2025H2 —
and in exactly the periods where the champion is strongest. A book whose
edge only exists in the older half of the sample is a fitted artefact.**

Partitioned by calendar period, fixed before looking, never by
`r_multiple` / `outcome` / `pnl`. No threshold was searched.

**The union route was closed at P60** (4/4 losses; 43–46% of signals
skipped; the +664.0R / +225.8R "bound" was 2.9x and 36x too high).

**The forward pass is a smoke test only**: 12.5 days, 14 1h swings, **2
champion trades against 1 candidate trade**. It confirms the P58
construction ports without crashing and settles nothing. The champion's
reported PF of 6195000000.00 is a divide-by-near-zero artefact on n=2 and
is left visible rather than tidied away.

**Keep the harness and the finding. Do not rebuild the architecture.** The
1h+15m champion is confirmed from every direction (P58) and nothing is
adopted.

---

## Notes recorded from the round

- My briefing was **three-quarters wrong** on "untouched" seeds, and two
  of its errors had reached `method/HANDOVER_SESSION.md`:
  `chop_thresh=58.0` is **inert** under `mode="atr_high"`, and
  `sw10`/`sw20` are built from the **1h** stream, not 15m. Both verified
  in code. `method/SECOND_RESEARCHER_REVIEW.md`
- The method failure across the session was checking **shape** and
  assuming **meaning**. `probe_structure.py` now runs first.
  `method/PROCESS_FIX_PROBES.md`

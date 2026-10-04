# CLOSED — do not repeat these

One page. Every direction that has been tested and lost, with the number that
killed it. Before starting any new experiment, check this list.

**Status: nothing in this file is adopted. Nothing here is a suggestion.**
These are closed. If one is proposed again, cite the row rather than re-running.

## The two lines that are worth keeping (and are NOT experiments)

1. **Low win rate + tail concentration is a FEATURE, not a bug.** Markets
   trend ~20-30% of the time; a trend system takes many small losses and few
   large wins. Proof, not theory: tightening the SL drops WR 27.8% → 18.8%
   and inflates maxDD 27.7 → 115.0. The wide stop **is** the mechanism that
   lets a 25%-hit-rate book survive. See `SL_TIGHTEN.md`.
2. **The common traps list was right every time.** It predicted every failure
   in this file: exiting early to raise WR, tighter stops, stacking complex
   filters, adding filters for their own sake.

Nothing further to experiment on here. These two are constraints, not
hypotheses.

## Closed — entry / signal side

| direction | result | doc |
|---|---|---|
| Range position × width gate (4h/1d/3d/1w, 27 pre-registered tests, 7 survived) | GATE FAILS 4/4. The gated cohort is the book's **best** cohort: WR 41-42% vs book 27.8-29.1%, carrying +107R/+127R in IS. Deleting it destroys R. | `RANGE_PEAK_GRAY.md` |
| Mid-range avoidance | falsified — middle buckets were profitable OOS | `RANGE_POS_WIDTH.md` |
| ADX > 25 | DEAD, both eras | repo, `exp_oldengines_path` |
| Kaufman Efficiency Ratio (ER24/ER50) | REJECTED — no bucket net-negative; low-ER holds +105R of real winners | repo, `ANCHOR_BASIS_AUDIT` §3f |
| Regime/chop/wick/swing-churn filters | all bucketed, none gates | repo, `REGIME_STRUCTURE_AUTOPSY` |
| **`exp_mltf_green_r` — R-threshold on the 1m add-on (k=0.25/0.5/1.0/1.5)** | **FAILS 16/16, monotone in k.** IS −17.7→−117.3 (champion), −19.9→−121.0 (utcsat); OOS −36.4→−76.6, −37.5→−68.2. OOS goes outright negative at k≥0.5; ex-best-5 negative in 14/16. Removing non-green add-ons makes the book WORSE — under `exp_mltf` they were holding concurrency slots and suppressing worse replacements (the 3-5× cascade). **Do not retune k.** | `MLTF_GREEN_R.md` |
| **1m scalping book** (separate 1m engine inside the 1h window, fixed 1:2, all mark kinds incl. B1; 24 cells) | **FAILS 0/24.** IS trimmed mean negative in **24/24** cells; WR ~35%, **PF 0.98–1.06**, avg ≈ −0.06R/trade. 1m swing breaks carry no standalone edge. Do not retune `target_r`/`max_hold_min` — per-trade expectancy is already zero. **One live lead: 1m B1 is OOS-positive on trimmed mean (mb10 +0.039 / +864.4R, mb20 +0.037 / +706.6R) where 15m B1 failed 4/4** — era-flipped, not adoptable, but the one 1m idea with a reason to exist. | `SCALP_1M_BOOK.md` |
| **1m trigger book, scored NET R** (the above, re-scored with costs) | **THE KILLER: 0.79R cost per round trip.** 20,185 trades = **−16,220R net** on −361R gross. A 1:2 wager needs ~0.8R of edge just to break even; this book's gross edge is **−0.018R**. **This is why the whole 1m trigger family is dead — not a tuning failure, an arithmetic one.** | `SCALP_1M_BOOK.md` |
| **`exp_retest_fill=0.25` on age10, replicated on data/btc** | **FAILS TO REPLICATE.** Bybit said +14.6/+11.3 R/yr in both eras; on the independent file it era-flipped: **btc_is −6.47/yr, btc_oos +13.31/yr.** A candidate that only reproduces on the data that found it is not a candidate. Closed. | `_retest_replicate.json` |
| **1m path context at the 15m entry** (feature gate, zero extra trades) | **DEAD after correction, 0/10 same sign.** The first run was invalid (grayed 658/660 — a units bug of mine: 15m distance ÷ 1m ATR). Corrected to scale-matched features (median 8.7 → 0.485/0.688), it still loses everywhere. Best arm `ext_hi_4` = **−27.6R IS / −9.7R OOS** — the strongest 1m result of the session, and still negative. | `ONE_MIN_PATH_CONTEXT.md` |
| **1m in ANY role — the whole timeframe** | Tested as **trigger** (0/196 cells), **book** (0/24), **fill** (replication fail), **add-on gate** (16/16 fail), and **feature** (0/10). **Closed as a source of edge.** Its cost structure (0.7-0.8R per round trip) exceeds anything it can produce, and the 15m book's edge is a property of 15m swing *structure* that finer data does not add to. **1m is finer, not more informative.** | the rows above |

## Closed — sizing / capital

| direction | result | doc |
|---|---|---|
| Vol-targeting (inverse-vol) | FAILED — net up 6/6 but curve worse ×3 (ulcer 14.62→29.82) | repo, 24.80/24.83 |
| sMZX sizing (M2/ZC/X, 1.5^count) | **RETRACTED — look-ahead.** M2 reads `seg.end_px`, which does not exist at B2/flip entry. The "4/4 selection" was a look-ahead detector, not skill. | `SMZX_LOOKAHEAD_RETRACTION.md` |
| M2-free ZC×X | the only live-computable residue, but 3/4 (fails is/champion) — not pursued | `SMZX_LOOKAHEAD_RETRACTION.md` |
| Add 0.5 at FS | +R, but `add_any` beat `add_M2` 4/4 and `add_BAD` was also +R → **drift, not selection**. Drawdown rises 1.3-1.7×. | `FS_ADD_VS_BASE.md` |
| Cross-venue (Binance perp) | 2/4 — fails the pre-registered bar | `SMZX_BINANCE_REPLICATION.md` |

## Closed — exit / stop

| direction | result | doc |
|---|---|---|
| Exit at FS when the swing looks bad | DEAD 4/4. Every subset's remaining R is positive; exiting always gives up money (+3.6R best case). | `FS_TIME_DECISION.md` |
| Tighter SL (0.5-2.0 × ATR toward entry) | CATASTROPHIC 4/4. WR −9pts, DD 2-4×. Non-monotonic wobble is noise. | `SL_TIGHTEN.md` |
| Wider SL buffer (0.10 / 0.25) | worse 3/4; calmar 3.20→2.90→2.51 | `SL_VARIANTS.md` |
| Causal SL | era-flipped: IS −77.8/−63.2, OOS +9.9/+12.6 | `SL_VARIANTS.md` |
| Pivot trail | catastrophic; oos/champion +70.2 → **−2.5R**, PF 1.34→0.99 | `SL_VARIANTS.md` |
| Half-swing stop | degenerate — for a small swing the midpoint sits inside the noise, hit 84-93% of the time | `FS_ENTRY_RISK_CONTROL.md` |

The stop has now been attacked from **both** directions (tighter and wider)
and every variant loses. `sl_buf_atr=0.01` + swing-pivot stands.

## Closed — more trades

| direction | result | doc |
|---|---|---|
| Relax `cooldown_bars` / `max_consecutive_losses` | 0/4. A5 adds 159 trades (+32%) for −136R IS / −68R OOS; ex-best5 goes **negative** in 3 cells. Both limiters earn their keep. | `TRADE_EXPANSION_AUDIT.md` |
| Pyramid / scale-in | FAMILY CLOSED — V4 −111.3/−87.3, no arm passed both gates | repo, `PYRAMID_PHASE2_DESIGN.md` |
| Revenge re-entry | DEAD 8/8, all cells negative | repo, 24.44 |
| Same-window re-entry (rewin) | era-flipped; no filter survives both sides | repo, 24.61 |
| 5m confirmation | cuts trades 502→351, era-dependent | repo, 24.39 |

## Two traps that produce spectacular fake numbers

Both hit in this work; both are easy to repeat.

1. **Degenerate risk denominator.** A stop that sits near the fill makes R
   explode (avg +19.4R, net +9700R was a real output of a real harness before
   it was caught). Any stop closer than ~0.25 × ATR is inside the noise.
2. **Comparing across buckets without holding the risk denominator constant.**
   This made "big swings are worst" look like a finding when it was partly
   measuring stop distance. The confounded claim had to be retracted.
   `FS_ENTRY_RISK_CONTROL.md`.

Rule: when comparing things of different scale, the denominator must be
constant, or report a size-neutral measure (e.g. % move) alongside R.

## Still open (not closed)

- **B1 entry.** ~~No kwarg fires the entry on B1.~~ **CLOSED at P71,
  on evidence.** `B1_ENTRY_P71.md`, `exp_b1_entry.py`. Adding B1 to the
  decisive tradeable set loses **36–164R in all four cells** and makes the
  book *smaller* (500 → 466 IS). Adding it to the flip set changes the book
  by **exactly +0.0R in all four cells**. The reason is structural and is
  the useful part: `_collect_signals` is FCFS — first tradeable mark wins,
  then the swing closes — and a B1 mark always fires *earlier* than its own
  swing's B2/FLIP, so it can only ever displace them, never join them. B1
  marks are not scarce either: per chain, OOS runs **B1 = 2537, B2 = 1990,
  FLIP = 1985**, so B1 is the *most common* mark and is excluded correctly.
  **This retires the standing "only ~1/3 of swings get priced, that's
  headroom" temptation — the unpriced swings are supersessions of marks on
  swings that were priced, not unused capacity.** Caveat recorded in the doc:
  the per-chain, per-kind attribution is not measured, so why the flip arm
  is inert is inferred rather than shown.
  blocking filter on the B2 trigger, not a different trigger. Needs a
  signal-selection patch plus a full path-true run. Honestly **unknown**;
  every B1 number produced so far has been an artefact.
- **True FS-only engine.** ~~2900/1634 confirmed swings exist; only the
  314/179 that produced a B2/flip entry have been priced.~~ **RUN at P73,
  AUDITED at P74.** `FS_ONLY_AUDIT_P74.md`, `FS_ONLY_P73.md`,
  `exp_fs_only.py`.
  **Two separate findings, and P73 conflated them.**
  **(a) PURE FS-only was already answered** in `FS_ONLY_ENGINE.md`
  (2026-09-28): **263t +31.7R IS, 108t +1.3R OOS** — *smaller*, not bigger,
  because every one of the 2900 swings carries a B2/FLIP mark, so the
  "unpriced" population is unpriced *trades*, not unpriced *swings*.
  **(b) P73 ran a HYBRID**: routing the `decisive` entry path alone from
  break-entry to FS-first-seal, with `flip` and `b2` untouched, gave 646t
  +405.2R IS / 364t +233.6R OOS — 3 of 4 cells positive, more trades AND
  better PF AND better DD in both champion-lane cells.
  **P73 was wrong to call (b) FS-only, wrong to present it as novel, and
  wrong to present "+146 trades for +79.4R" without a trade-level
  decomposition — that reading assumes additions which were never shown to
  be additions. Registration WITHDRAWN.** Outstanding before it can be
  believed: rename as hybrid, decompose survivors vs newcomers, run the P61
  period partition, reconcile with (a), and check the `FS_ENTRY.md`
  warning that FS-time buckets invert 4/4 when made legal.
- **Live size state.** `v18_streak_halt.py` has zero hits for
  equity/size/notional/qty. Any sizing change has no execution channel.

## The one caveat that applies to all of the above

The champion's IS/OOS slices are the most-inspected data in this repo. An
arm can pass everything above and still fail on a genuinely untouched
dataset. Several candidates in this file were killed *only* by OOS or
cross-venue, after looking excellent in IS.

## The open-position gate (prevpos) — measured, never fired, code removed

**Idea:** when entering, look at trades already running. If they are in profit,
take the entry; if not, skip it or flag it. No open trades means take it
normally. Both variants tested on the champion multi book, IS and OOS.

| arm | IS n / net R | OOS n / net R | blocked IS / OOS |
|---|---|---|---|
| control | 499 / +239.12 | 280 / +72.79 | - / - |
| grey, all / any | 499 / +239.12 | 280 / +72.79 | 0 / 0 |
| skip, all / any | 499 / +239.12 | 280 / +72.79 | 0 / 0 |
| skip, all, +0.5R | 388 / +111.65 | 219 / -11.76 | 134 / 83 |

**Stronger null than "no effect."** The gate evaluated 119 entries in sample and
68 out of sample - entries where a position genuinely was already running - and
blocked **none**. In all 187 cases the open position was above its own entry.
**When this engine adds to a position it only ever adds to a winner, so there is
no "added to a loser" event for the gate to catch.**

Forcing it with a +0.5R threshold does gate, and costs 111R in sample and turns
+72.79R out of sample into -11.76R. The trades it removed were carrying more
than the threshold.

**Do not retry on this book.** Third gate conditioned on "the last thing lost
money" with nothing to attach to, after the cohort knob (needs two overlapping
positions, cannot fire here) and chop_thresh (not read at all under
mode=atr_high). Results in `_prevpos_results.json`; commit 77a4dc2 removed the
knob and the harness patch entirely.

---

# CLOSED 2026-10-04 — `dirmatch` / `age` PREDICTS THE SWING DIRECTION. Dead.

The owner found it by asking the right question: *"but how is that a look-ahead?"*
The answer turned out to be one line of code and a date.

## What the filter actually does

`exp_require_dir_match` is an entry filter. It decides whether to take an LTF
signal by asking which 15m swing contains the entry bar, and reading that
swing's direction:

```python
for _gs in swings_ltf:
    _gsi = _gs["seg"]["start_idx"]
    if 0 <= _gsi <= i:            # swing started at or before the entry bar
        _gen_dir = _gs["dir"]     # <-- the swing's FINAL direction
if exp_require_dir_match and _gen_dir != direction:
    continue                      # no match, no trade
```

A swing that has STARTED is not a swing yet. Its direction is final only when
it confirms, at `confirmed_at_idx`. So the filter reads a label that becomes
correct **after** the entry bar it is being used to judge.

## The evidence, with dates

`exp_dir_causal_evidence.py` on `dirmatch_multi_sw10`, in sample:

| | |
|---|---|
| trades examined | 389 |
| picks whose swing **confirms after entry** | **331 (85.1%)** |
| dir label **differs** from the entry-bar truth | **176 (45.2%)** |
| lookahead gap | p05 **+1h**, p50 **+8h**, p95 **+12h** |

Twelve worst, largest confirmation delay. "pin" is the label the filter read,
"known" is what a live process could have computed from candles up to entry:

```
entry             side   swing started     swing confirmed     gap h    pin  known
2025-03-13 03:30  short  2025-03-13 03:15  2025-03-13 19:00   15.5     -1      1  <-- MOVED
2025-12-17 19:45  long   2025-12-17 19:30  2025-12-18 10:45   15.0      1     -1  <-- MOVED
2023-12-28 01:45  short  2023-12-28 01:00  2023-12-28 16:30   14.8     -1      1  <-- MOVED
2024-12-16 16:00  long   2024-12-16 13:00  2024-12-17 06:30   14.5      1     -1  <-- MOVED
2024-03-18 07:00  short  2024-03-18 05:45  2024-03-18 21:00   14.0     -1      1  <-- MOVED
2025-02-06 15:00  short  2025-02-06 12:00  2025-02-07 04:30   13.5     -1      1  <-- MOVED
```

The 2025-03-13 row in full: the 15m swing began 03:15, the book entered short
at 03:30, and the swing did not resolve until 19:00. The filter used **down**.
At 03:30 the knowable answer was **up**. It applied a label from 15.5 hours in
the future to a decision made at 03:30.

## Why that makes it an oracle, not a filter

| swing resolves | trade outcome |
|---|---|
| **with** the signal | trade wins |
| **against** the signal | trade loses |

"Is this swing going my way?" and "is this trade going to win?" are the same
question. The filter was reading the answer. That is why it produced the two
findings that made it look real and are quoted all over the older docs:

- **125/125 "opposed" swings at 0% win rate** - every loser removed
- **WR 51.7%**, the highest in the repo at the time
  (`ANCHOR_BASIS_AUDIT.md:804`, `151t / +455.5R / DD 6.0 / WR 51.7%`)

A filter cannot reach 0% by finding skill. It reaches 0% by looking.

## Path-true, `exp_dir_causal=1`

The guard adds one line: skip any swing not yet confirmed by the entry bar.
Every number below is the engine, both eras, current code.

| book | pinned (lookahead) | **path-true** | WR |
|---|---|---|---|
| `dirmatch_multi_sw10` | IS 389 / **+444.21R** | IS 257 / **+70.79R** | 24.9% |
| `dirmatch_single_sw10` | IS 392 / +442.72 | IS 260 / **+75.66R** | 25.4% |
| `age10_dirmatch_multi_sw10` | IS 150 / **+417.68R** | **0 trades** | — |
| `age25_dirmatch_multi_sw10` | IS 249 / +357.01 | IS **9t / −4.66R** | 11.1% |
| `age25_multi_sw10` | IS 249 / +319.22 | IS 31t / **+5.90R** | 29.0% |
| `dirmatch_swingpause_single` | IS 362 / +273.84 | IS 254 / **+77.14R** | 24.8% |
| `age10_dirmatch_swingpause_single` | IS 149 / **+414.08R** | **0 trades** | — |

**The 51.7% win rate becomes 24.9%.** Two books stop trading entirely.

### Why `age10` and `age25` go to zero

`exp_max_swing_age` requires the swing to be at most 10 bars old at entry,
while `exp_dir_causal` requires it to be already confirmed. A 15m swing needs
`min_bars=50` to form. **A swing cannot be both confirmed and ten bars old.**
The two conditions are mutually unsatisfiable, so the intersection is empty.
That is not a tuning accident - it is the mechanism showing itself.

## Also caught: two directional-FS books built on this base

`fsent_dirmatch_long` / `fsent_dirmatch_short` (commit 539935c) inherited the
contaminated base. They were pinned and `exp_fastcheck.py` called them OK -
the checker verifies that the engine reproduces the pin, and it did. It cannot
verify that the engine is causal.

| book | pinned | **path-true** |
|---|---|---|
| `fsent_dirmatch_long` | IS 426 / +477.38R / DD 11.15 | IS 426 / **+322.67R** / DD 15.41 |
| `fsent_dirmatch_short` | IS 417 / **+658.65R** / DD 11.60 | IS 402 / **+368.54R** / DD 19.29 |

**The directional FS effect survives path-true in both eras** (+184.44 and
+185.13 OOS), so the FS signal is real and those books can be rebuilt on a clean
base. For now they are reference, alongside the seven that are simply the
artifact.

## The lesson that matters more than the family

**A pin is not a proof of correctness.** Every number here was re-derived from
the engine and every check passed. The engine itself was reading the future.

`exp_fastcheck.py` and `exp_pinverify.py` answer "does the engine produce this
number?". They cannot answer "is this number allowed to exist?". Only an
explicit causal guard - like `exp_dir_causal` - answers the second question,
and it has to be applied by whoever writes the filter, not by whoever verifies
the pin.

## The family is dead too, not just the lookahead version

The evidence above proves the leak. It does not answer the next question: does
direction-matching survive when it is only allowed to read labels that exist at
the entry bar? Measured, both eras, on a CLEAN base (`exp_dir_causal_rebuild.py`):

| arm | IS n / net / WR | OOS n / net / WR |
|---|---|---|
| champion leg (control) | 499 / **+239.1R** / 27.5% | 280 / **+72.8R** / 27.1% |
| **+ causal dirmatch** | 257 / **+70.8R** / 24.9% | 158 / **+62.8R** / 27.8% |

**-168R in sample, -10R out of sample.** The causal version is not a weaker
version of the artifact, it is a *harmful* filter: it drops 242 trades and
loses money doing it.

And the base turns out to have been carrying nothing. `dirmatch_multi_sw10`
path-true measures 257t / +70.8R - **bit-for-bit identical** to champion plus
the causal filter, and adding `exp_require_dir_match=1` on top of it changes
the result by **+0.0R**. So `fsent_dirmatch_long` / `fsent_dirmatch_short` were
never "dirmatch based"; they were champion + FS + dirmatch, and their numbers
(+322.67R / +368.54R) are exactly champion + FS + causal dirmatch.

**Which is worse than champion + FS alone:**

| arm | IS | OOS |
|---|---|---|
| **champion + FS long** | 525 / **+528.9R** / **39.6%** | 310 / **+243.9R** |
| champion + FS long + causal dirmatch | 426 / +322.7R / 38.3% | 254 / +184.4R |
| **champion + FS short** | 531 / **+571.4R** / 36.5% | 309 / **+239.3R** |
| champion + FS short + causal dirmatch | 402 / +368.5R / 36.1% | 228 / +185.1R |

**There is nothing to rebuild.** The clean replacements already exist as
`fsent_champ_long` / `fsent_champ_short`, at +528.9R and +571.4R in sample.

### What replaced the 51.7% win rate, honestly

| | WR | status |
|---|---|---|
| `age10_dirmatch_multi` (old champion claim) | 51.7% | **lookahead** - it read the answer |
| champion leg | 27.5% | real |
| **`fsent_champ_long`** | **39.6%** | **real and causal** |

A 39.6% win rate that a live process can actually reproduce is worth more than
a 51.7% that it cannot. The higher number was the artifact.

## Also closed: `union_multi` / `dualunion_multi` read `end_px` — the M2 field

Second family found by auditing which knob reads which swing field, rather than
by guessing. `exp_min_swing_ratio`:

```python
_sw  = swings_ltf[int(sig["swing_no"])]
_spx = _sw["seg"]["start_px"]
_epx = _sw["seg"]["end_px"]          # the swing's FINAL structural extreme
if abs(_epx - _spx) / atr < exp_min_swing_ratio:
    continue                          # swing too small -> skip the trade
```

`end_px` is the extreme bar. It is settled at `confirmed_at_idx`, not at the
entry bar, so "is this swing big enough?" is a question about a bar that had not
printed yet. Measured:

| book | trades | swing already settled at the entry bar |
|---|---|---|
| `union_multi` | 137 | **0 / 137 = 0.0%** |
| `dualunion_multi` | 90 | **0 / 90 = 0.0%** |

**Not one trade out of 227 had a settled swing.** This is the same field M2
reads, and `FS_TIME_GEOMETRY.md` already closed it: *"M2's information is
entirely retrospective."* A different knob, the same leak.

Both books are `status: "reference"`. `exp_union_dual_only` (1 book) lives in
the same code block and is closed with them.

## The audit tool that does not work — do not trust it

`exp_prefix_audit.py` corrupts the tail of the sample and checks whether the
trades before the cut move. Good idea, and it **does not work**:

```
dirmatch_multi_sw10    changed=0 of 31  -> clean   <-- KNOWN LOOKAHEAD
champion_multi_sw10_leg changed=0 of 39 -> clean
fsent_champ_long       changed=0 of 38  -> clean
fsent_champ_short      changed=0 of 36  -> clean
trail_half_skipn6_dr3  changed=0 of 30  -> clean
fsent_sig_sw10_short   changed=0 of 30  -> clean
```

**It cleared `dirmatch_multi_sw10`, which is proven contaminated.** A tool that
misses a bug you already know about has proved nothing by passing. Its power is
limited to long-range leaks: it only inspects trades within ~2 days of a
corruption point, because that is as far as a look-ahead can reach. A median
8-hour leak mostly lands the other side of that window by chance.

Four versions were built before this was understood - truncation, wider bands,
corruption, then multiple cuts. All four called `dirmatch` clean. **Do not use
it as a gate.** What works is the direct instrument: for each knob, find which
swing field it reads, then measure whether that field was settled at the
decision bar. That is what found `union_multi`.

## SWING-SIZE EXIT AT FS — the owner's proposal. This one works.

`exp_fs_small_swing`, default 0 = off. Enter at B2/flip exactly as the book
does. When the swing that opened the trade CONFIRMS, measure that swing's own
leg, `abs(seg.end_px - seg.start_px)` over ATR(20), and exit if it is under the
threshold. `exp_fs_gray` additionally holds the slot after such an exit.

**Why this quantity is legal here and was not legal before.** It is the same
field `union_multi` was closed on and the same field M2 reads. The difference is
*when*. `end_px` and `start_px` are both settled at or before `confirmed_at_idx`,
and the FS bar has already closed when the rule reads them. At the FS bar this
is a settled fact about the past. At the entry bar - which is where
`exp_min_swing_ratio` and M2 read it - it is a fact about a bar that had not
printed yet. **Same number, legal and illegal depending on when you look at
it.**

Measured, both eras, engine:

| base book | arm | IS n / net / dd_net | OOS n / net / oos_dd_net |
|---|---|---|---|
| champion_multi_sw10_leg | control | 499 / +239.1 / 46.85 | 280 / +72.8 / 50.55 |
| | **<= 6 ATR** | 502 / **+283.1** / **43.39** | 282 / **+94.2** / **44.17** |
| champion_single_sw10 | control | 503 / +170.9 / 50.5 | 295 / +78.6 / 38.1 |
| | **<= 6 ATR** | 508 / **+201.9** / **47.0** | 299 / **+94.4** / **35.5** |
| champion_single_sw20 | control | 496 / +196.3 / 58.2 | 269 / **+6.7** / 48.5 |
| | **<= 6 ATR** | 498 / **+199.4** / 55.6 | 274 / **+27.0** / **41.7** |
| fsent_champ_long | control | 525 / **+528.9** / 14.2 | 310 / +243.9 / 11.9 |
| | <= 6 ATR | 544 / +463.9 / 14.3 | 319 / +262.4 / 17.2 |

**Every arm from 3 to 6 ATR beats its control on BOTH eras** - 16 of 16 cells
across the three books that take it, and the effect is monotonic in the
threshold. The sw20 single is the clearest: out of sample it goes from **+6.7R
at a 48.5 drawdown to +27.0R at 41.7**.

It fails on `fsent_champ_long`, which is coherent rather than surprising: in a
directional-FS book the trade opens *at* the FS print, so by the time that swing
confirms, the trade it opened is already over. The rule has nothing left to act
on.

### The gray half is a no-op, and the reason is worth recording

`exp_fs_gray` arms `busy_until` on such an exit so no replacement trade can
enter - aimed at the crossover that made `exp_fs_move_to_be` lose 64R (518 trades
instead of 499). It changed **nothing**, byte-for-byte, on every book tested,
serial ones included. The reason is that `busy_until` is already set to the
exit bar, so arming it to the exit bar is a no-op by construction. A gray that
means anything has to hold the slot *past* the exit, and this one does not. Left
in the engine as a default-off knob with an honest description rather than
quietly removed.

## The swingpause scare, and why the rest of the knob queue is clean

`exp_swingpause` was briefly graveyarded on the strength of a generic
measurement, and that was wrong. Recorded because the next person will hit the
same tool.

The measurement asks "is the swing that owns this trade settled at the entry
bar?" and reported 451 of 451 unconfirmed on `swingpause_single_sw10`. But
`exp_swingpause` never reads that swing:

```python
if exp_swingpause > 0 and last_loss_ts > 0:
    _si = bisect_right(confs_ts, candle_ts[i]) - 1
    if _si < 0 or pivs_ts[_si] <= last_loss_ts:
        continue
```

`confs_ts` is the list of swings **confirmed** at or before bar `i`. Swings that
confirm later sort after `i` and cannot move the index, so the answer at bar `i`
is fixed by what existed at bar `i`. Checked directly - full chain against a
chain rebuilt from candles up to `i`, 45 sampled bars, **0 differences.**

It is a cooldown that waits for fresh structure after a loss, and it is causal.
The 31 books were unmarked and are candidates again.

**The distinction that matters is entirely in the selector:**

| selector | picks a swing that | settled at entry? |
|---|---|---|
| `start_idx <= i` | **started** before entry - `exp_require_dir_match`, `exp_max_swing_age`, `exp_max_running_mag` | **no** |
| `confirmed_at <= i` | **confirmed** before entry - `exp_swingpause`, `exp_causal_sl` | yes |

Same "find a swing and read a field" shape. One implemented correctly, one not.

### The rest of the queue, read line by line

| knob | books | reads | verdict |
|---|---|---|---|
| `b3_k` | 5 | bars `i+1 .. i+k` | **causal** - deferred fill, see below |
| `exp_entry_swing_age_max` | 3 | `seg.start_idx` | **causal** - a swing's start does not move |
| `exp_pivot_trail` | 1 | `seg.end_px` | **causal** - read after the extreme, see below |
| `exp_causal_sl` | 4 | `confirmed_at_idx`, `seg.end_idx` | **causal** - explicit `<= i` gate |

`b3_k` looks forward at bars `i+1 .. i+k`, which is the only suspicious thing
about it, and then **re-prices the entry at the bar it lands on**:
`i = _jj; bar_time = candles_ltf[i]["date"]; entry = float(candles_ltf[i]["close"])`.
That is a deferred fill - wait up to k bars for a better price, then enter at
that bar's own close. A live process can do exactly this: the decision uses data
up to `_jj` and the fill happens at `_jj`.

`exp_pivot_trail` reads `end_px`, the same field `union_multi` was closed on,
and it is still fine because of *when*. The trail event arms at the first bar
`_j` **after** the extreme bar `_ei` at which price exceeds `_ep`. By bar `_j`
the extreme has already printed. `end_px` is knowable from the moment its own
bar closes, which is before the swing confirms. Reading it *after* the extreme
has settled is fine; reading it *at* the entry bar, as `exp_min_swing_ratio`
does, is not.

Third and final instance of the same lesson in this repo: **the number is never
the problem. The moment you read it is.**

## Do not retry

Direction-matching by final swing label, in any form, on any timeframe. If a
feature needs to know which way a swing resolves before it resolves, it is
reading the outcome. The causal version of the same idea - wait for the
confirmation and enter then - is what `exp_fs_entry_side` does, and it holds up:
it changes **when the trade opens** instead of judging a trade that is already
open.

All nine books are `status: "reference"`, and `shortlisted()` now returns False
for any reference book regardless of size, so a large contaminated number can
never re-enter the candidate list on size alone.

The user's proposal, taken seriously and measured four separate ways. The
premise is sound - enter where the book already enters (B2/flip), leave when the
swing that opened the trade CONFIRMS, and the FS print is legal to read because
it has already happened. **The premise was never the problem. Every way of
acting on it lost money.**

Entry is B2/flip throughout. This is NOT the closed FS-ENTRY experiment, which
removed the B2/flip entry and waited for FS instead (`FS_ENTRY.md`). Different
book, different denominator. The two must never be quoted as one result.

## What was measured, all on the champion multi book, all on the engine

| # | idea | IS net | OOS net | vs control |
|---|---|---|---|---|
| — | **control (shipped)** | **+239.12R** (499t) | **+72.79R** (280t) | — |
| 1 | exit on **every** FS | +133.26R | +57.90R | worse, worse |
| 2 | exit if FS lands within 2–6h | +245.52 … +303.36R | +75.37 … +80.30R | better, better |
| 3 | exit if **room < threshold** (room = FS close vs entry, in R) | +103.57 … +241.60R | +47.40 … +69.22R | worse, worse |
| 4 | **move SL to breakeven** at FS | +174.58R (518t) | +44.67R (301t) | −64.54R, −28.12R |
| 5 | **4h swing direction** as a filter on 1h entries | +124.29R (277t) | +14.95R (150t) | −114.83R, −57.84R |
| 6 | **`window_end="fs"`** — HTF bias window closes at the FS | **−36.12R** (79t) | **−22.94R** (39t) | −275R, −95.7R |

Idea 2 is the one exception and it is already shipped as `fsexit4_c` /
`fsexit6_c`. It closes a trade when the swing confirms FAST — a narrow window,
never an unconditional exit.

## Idea 6 in one line: the bias must OUTLIVE the swing that created it

`window_end="fs"` is the user's own framing — HTF hands the LTF a bias window,
LTF trades normally inside it, and the window ends at the FS. It killed 84% of
the trades (499 → 79) and went negative in both eras. The bias window closing
on confirmation is the single worst FS arm tested. A confirmed swing does not
mean the bias is spent; that is where the book makes its money.

## Idea 3 and 4: the information is retrospective, exactly like M2

`FS_TIME_GEOMETRY.md` already closed the same trap with swing magnitude. Room
and magnitude are the same kind of quantity: **descriptive of a move that has
already finished.** The census that motivated idea 3 was real — room > +2R
earned +2.21R/trade in IS and +1.76R in OOS — but that correlation is measured
against the FINAL result, after the trade closed. It does not predict anything
at the FS bar. Same failure, second instance.

## THE PROCESS ERROR, WHICH IS THE PART WORTH REMEMBERING

Idea 4 was first measured as a post-hoc overlay that re-scored trades rather
than re-running the engine. It reported **IS +349.90R, OOS +125.93R, DD 46.9 →
27.7** — a huge apparent win, quoted as a result. Promoted to the engine and
measured properly it is **IS +174.58R, OOS +44.67R, and 518 trades instead of
499.**

The overlay never changed the trade set, so it never saw the second-order cost:
closing a loser early frees the slot, `cooldown_bars=8` and
`max_consecutive_losses=3` then admit NEW trades, and those trades displace
winners. **A post-hoc re-score cannot see a change in what gets traded.** Every
overlay number in the FS series is suspect for the same reason; the numbers in
the table above are all engine runs.

> **An overlay is not a result. If a rule changes which trades exist, it has to be
> run in the engine. Re-scoring closed trades only measures the old book.**

## Do not retry

FS as an EXIT trigger is closed on this book: time-gated exit apart, the room
rule, the breakeven rule, the higher-timeframe direction filter and the
FS-closed bias window have all failed in both eras. The failure is structural,
not a tuning problem — the swing's own geometry is settled by the time it is
read, so there is nothing left to differentiate.

`exit_fs_max_gap_h` stays in the engine because arm 2 clears control in both
eras and is pinned. `exp_fs_move_to_be` and `window_end="fs"` have both been
REMOVED from `unified.py` — neither is reachable, and neither is a knob anyone
should re-add on the strength of this section alone. Run the engine first.

Harnesses kept for the record: `exp_fs_census.py` (the direction/room census),
`exp_fs_room_exit.py` (idea 3), `exp_fs_untested.py` (ideas 4/5/6),
`exp_fs_be_books.py` (idea 4 across books). Results in `_fs_*_results.json`.

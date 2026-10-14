# CLOSED — do not repeat these


<!-- C17-NOTICE -->
> **C17 NOTICE (2026-10-07).** The figures in this document were measured before
> the C17 gate fix, which removed a lookahead from the HTF window gate and
> invalidated 214 of 215 registry pins. They are kept as the dated record they
> were, and they are **not** what the engine produces today - do not quote them
> as current. Current numbers: `python exp_pinverify.py` (re-derives every pin),
> `docs/method/C17_WINDOW_END_CAUSALITY.md` (what changed and why),
> `docs/multi/MULTI_RANKINGS.md` and `docs/signal/SIGNAL_RANKINGS.md`
> (regenerated from a post-C17 measurement).
------------------------------------------------------------------------------

One page. Every direction that has been tested and lost, with the number that
killed it. Before starting any new experiment, check this list.

**Status: nothing in this file is adopted. Nothing here is a suggestion.**
These are closed. If one is proposed again, cite the row rather than re-running.

## The two lines that are worth keeping (and are NOT experiments)

1. **Low win rate + tail concentration is a FEATURE, not a bug.** Markets
   trend ~20-30% of the time; a trend system takes many small losses and few
   large wins. Proof, not theory: tightening the SL drops WR 27.8% → 18.8%
   and inflates maxDD 27.7 → 115.0. The wide stop **is** the mechanism that
   lets a 25%-hit-rate book survive. See `method/SL_TIGHTEN.md`.
2. **The common traps list was right every time.** It predicted every failure
   in this file: exiting early to raise WR, tighter stops, stacking complex
   filters, adding filters for their own sake.

Nothing further to experiment on here. These two are constraints, not
hypotheses.

## Closed — entry / signal side

| direction | result | doc |
|---|---|---|
| Range position × width gate (4h/1d/3d/1w, 27 pre-registered tests, 7 survived) | GATE FAILS 4/4. The gated cohort is the book's **best** cohort: WR 41-42% vs book 27.8-29.1%, carrying +107R/+127R in IS. Deleting it destroys R. | `method/RANGE_PEAK_GRAY.md` |
| Mid-range avoidance | falsified — middle buckets were profitable OOS | `method/RANGE_POS_WIDTH.md` |
| ADX > 25 | DEAD, both eras | repo, `exp_oldengines_path` |
| Kaufman Efficiency Ratio (ER24/ER50) | REJECTED — no bucket net-negative; low-ER holds +105R of real winners | repo, `ANCHOR_BASIS_AUDIT` §3f |
| Regime/chop/wick/swing-churn filters | all bucketed, none gates | repo, `REGIME_STRUCTURE_AUTOPSY` |
| **`exp_mltf_green_r` — R-threshold on the 1m add-on (k=0.25/0.5/1.0/1.5)** | **FAILS 16/16, monotone in k.** IS −17.7→−117.3 (champion), −19.9→−121.0 (utcsat); OOS −36.4→−76.6, −37.5→−68.2. OOS goes outright negative at k≥0.5; ex-best-5 negative in 14/16. Removing non-green add-ons makes the book WORSE — under `exp_mltf` they were holding concurrency slots and suppressing worse replacements (the 3-5× cascade). **Do not retune k.** | `method/MLTF_GREEN_R.md` |
| **1m scalping book** (separate 1m engine inside the 1h window, fixed 1:2, all mark kinds incl. B1; 24 cells) | **FAILS 0/24.** IS trimmed mean negative in **24/24** cells; WR ~35%, **PF 0.98–1.06**, avg ≈ −0.06R/trade. 1m swing breaks carry no standalone edge. Do not retune `target_r`/`max_hold_min` — per-trade expectancy is already zero. **One live lead: 1m B1 is OOS-positive on trimmed mean (mb10 +0.039 / +864.4R, mb20 +0.037 / +706.6R) where 15m B1 failed 4/4** — era-flipped, not adoptable, but the one 1m idea with a reason to exist. | `method/SCALP_1M_BOOK.md` |
| **1m trigger book, scored NET R** (the above, re-scored with costs) | **THE KILLER: 0.79R cost per round trip.** 20,185 trades = **−16,220R net** on −361R gross. A 1:2 wager needs ~0.8R of edge just to break even; this book's gross edge is **−0.018R**. **This is why the whole 1m trigger family is dead — not a tuning failure, an arithmetic one.** | `method/SCALP_1M_BOOK.md` |
| **`exp_retest_fill=0.25` on age10, replicated on data/btc** | **FAILS TO REPLICATE.** Bybit said +14.6/+11.3 R/yr in both eras; on the independent file it era-flipped: **btc_is −6.47/yr, btc_oos +13.31/yr.** A candidate that only reproduces on the data that found it is not a candidate. Closed. | `_retest_replicate.json` |
| **1m path context at the 15m entry** (feature gate, zero extra trades) | **DEAD after correction, 0/10 same sign.** The first run was invalid (grayed 658/660 — a units bug of mine: 15m distance ÷ 1m ATR). Corrected to scale-matched features (median 8.7 → 0.485/0.688), it still loses everywhere. Best arm `ext_hi_4` = **−27.6R IS / −9.7R OOS** — the strongest 1m result of the session, and still negative. | `method/ONE_MIN_PATH_CONTEXT.md` |
| **1m in ANY role — the whole timeframe** | Tested as **trigger** (0/196 cells), **book** (0/24), **fill** (replication fail), **add-on gate** (16/16 fail), and **feature** (0/10). **Closed as a source of edge.** Its cost structure (0.7-0.8R per round trip) exceeds anything it can produce, and the 15m book's edge is a property of 15m swing *structure* that finer data does not add to. **1m is finer, not more informative.** | the rows above |

## Closed — sizing / capital

| direction | result | doc |
|---|---|---|
| Vol-targeting (inverse-vol) | FAILED — net up 6/6 but curve worse ×3 (ulcer 14.62→29.82) | repo, 24.80/24.83 |
| sMZX sizing (M2/ZC/X, 1.5^count) | **RETRACTED — look-ahead.** M2 reads `seg.end_px`, which does not exist at B2/flip entry. The "4/4 selection" was a look-ahead detector, not skill. | `method/SMZX_LOOKAHEAD_RETRACTION.md` |
| M2-free ZC×X | the only live-computable residue, but 3/4 (fails is/champion) — not pursued | `method/SMZX_LOOKAHEAD_RETRACTION.md` |
| Add 0.5 at FS | +R, but `add_any` beat `add_M2` 4/4 and `add_BAD` was also +R → **drift, not selection**. Drawdown rises 1.3-1.7×. | `method/FS_ADD_VS_BASE.md` |
| Cross-venue (Binance perp) | 2/4 — fails the pre-registered bar | `method/SMZX_BINANCE_REPLICATION.md` |

## Closed — exit / stop

| direction | result | doc |
|---|---|---|
| Exit at FS when the swing looks bad | DEAD 4/4. Every subset's remaining R is positive; exiting always gives up money (+3.6R best case). | `method/FS_TIME_DECISION.md` |
| Tighter SL (0.5-2.0 × ATR toward entry) | CATASTROPHIC 4/4. WR −9pts, DD 2-4×. Non-monotonic wobble is noise. | `method/SL_TIGHTEN.md` |
| Wider SL buffer (0.10 / 0.25) | worse 3/4; calmar 3.20→2.90→2.51 | `method/SL_VARIANTS.md` |
| Causal SL | era-flipped: IS −77.8/−63.2, OOS +9.9/+12.6 | `method/SL_VARIANTS.md` |
| Pivot trail | catastrophic; oos/champion +70.2 → **−2.5R**, PF 1.34→0.99 | `method/SL_VARIANTS.md` |
| Half-swing stop | degenerate — for a small swing the midpoint sits inside the noise, hit 84-93% of the time | `method/FS_ENTRY_RISK_CONTROL.md` |

The stop has now been attacked from **both** directions (tighter and wider)
and every variant loses. `sl_buf_atr=0.01` + swing-pivot stands.

## Closed — more trades

| direction | result | doc |
|---|---|---|
| Relax `cooldown_bars` / `max_consecutive_losses` | 0/4. A5 adds 159 trades (+32%) for −136R IS / −68R OOS; ex-best5 goes **negative** in 3 cells. Both limiters earn their keep. | `method/TRADE_EXPANSION_AUDIT.md` |
| Pyramid / scale-in | FAMILY CLOSED — V4 −111.3/−87.3, no arm passed both gates | repo, `signal/PYRAMID_PHASE2_DESIGN.md` |
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
   `method/FS_ENTRY_RISK_CONTROL.md`.

Rule: when comparing things of different scale, the denominator must be
constant, or report a size-neutral measure (e.g. % move) alongside R.

## Still open (not closed)

- **B1 entry.** ~~No kwarg fires the entry on B1.~~ **CLOSED at P71,
  on evidence.** `method/B1_ENTRY_P71.md`, `exp_b1_entry.py`. Adding B1 to the
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
  AUDITED at P74.** `method/FS_ONLY_AUDIT_P74.md`, `method/FS_ONLY_P73.md`,
  `exp_fs_only.py`.
  **Two separate findings, and P73 conflated them.**
  **(a) PURE FS-only was already answered** in `method/FS_ONLY_ENGINE.md`
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
  period partition, reconcile with (a), and check the `method/FS_ENTRY.md`
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
  (`signal/ANCHOR_BASIS_AUDIT.md:804`, `151t / +455.5R / DD 6.0 / WR 51.7%`)

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
reads, and `method/FS_TIME_GEOMETRY.md` already closed it: *"M2's information is
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
removed the B2/flip entry and waited for FS instead (`method/FS_ENTRY.md`). Different
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

`method/FS_TIME_GEOMETRY.md` already closed the same trap with swing magnitude. Room
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

## REGIME ROUTING ON CHOP — closed 2026-10-07, nothing adopted

The owner asked whether `chop_thresh` could be used on `fsent_champ_long`, since
the knob is reported INERT there. It is not inert because it does nothing in
general — the book runs `mode="atr_high"` and never reads it. Answered: **no
routing on chop beats the shipping router, and the owner closed it.**

`fsent_champ_long` as shipped: IS 528 / +533.37 / dd 13.42, OOS 311 / +239.59 /
dd 11.88. **That book is unchanged. The three `mode` branches added to test this
have been reverted out of `unified.py`.**

**Why it looked worth trying.** Two indicators, genuinely different variables:
`chop_thresh` is the CHOP index on 1h (direction efficiency — high means
one-directional travel), `atr_high_thresh` is ATR% of price on 15m (bar size,
direction-blind). They disagree on 24.6% of IS bars and 35.5% of OOS bars, and
in opposite directions on exactly the bars that matter. The joint cell where chop
reads HIGH and atr_pct reads LOW is the book's best region in **both** eras: mean
R +1.76 IS / +2.61 OOS against +1.01 / +0.77 for the whole book, at max DD 7.6R
/ 4.7R against 13.4R / 11.9R, longest losing run 6 / 5 against 11 / 15. It
survives the outlier bar — +83.4R in both eras with its single largest trade
removed, +41.3 / +45.6 with its top three.

**What failed, with the mechanism:**

| attempt | result | why |
|---|---|---|
| `decisive_vs_flip_chop` ch=30,40 | IS +124R, OOS **−49R** | era split, the seventh appearance |
| `decisive_vs_flip_chop` ch=50 | +41R IS / +18.6R OOS | one added trade supplies +46.24R; without it **−2.4R**. IS drawdown 13.4R → **28.2R** |
| `decisive_vs_flip_chop` ch=55 | +42R IS, **2 trades removed** | 21R per trade. A threshold excluding two known trades is a fit to them |
| `chop_or_atr_low` | IS +112R, OOS **−56.7R** | era split |
| gate: take only the cell | IS 144 trades +116R, OOS 58 trades +37.6R | win rate collapses to **20.7%** OOS against the book's 37.0%. 58 trades cannot wait for a tail |
| union: book + cell | OOS net +239.6 → **+217.3R** | the added trades are **−19.0R** OOS |

**The mechanism, which is the part worth keeping.** The cell's win rate is only
5.9 points better than the book's (42.9% vs 37.0%). That cannot produce +1.84R
of mean. It comes from the right tail — the cell's 90th-percentile trade is
**+9.42R** against the book's +3.23R, and 9 of its 42 OOS trades clear +3R against
the book's 33 of 311 — while the cell's **median** trade is *worse* than the
book's (−0.262 vs −0.224). It does not win more often; it wins bigger, rarely.
A book cannot wait for that on 42 trades, and halving those trades still leaves
full-size losses behind. Its monthly R is +0.65 to +0.69 correlated with the
whole book, so sizing it as a sleeve buys no diversification either.

**Two structural facts found on the way, both reusable:**

1. **A "union" written as `if not (A or B): continue` is not a union.** `continue`
   drops the signal, so it removes every trade the ordinary router would have
   taken — it measured **−392R IS / −194R OOS**. A union has to fall through to
   the router (`use="flip"` in the else), not skip past it. This is the same shape
   of mistake as the `prevpos` gate above, and it is worth checking every gate for.
2. **`exp_persist` is structurally inert on any gate-shaped `mode`.** A gate
   `continue`s before `use` is assigned, so the v19 hysteresis state
   (`_rg_s`/`_rg_c`) never advances and every persist value 0–7 returns
   byte-identical results. Sweeping it on a gate is not a question the engine can
   answer.

**Do not re-add these `mode` branches.** `chop_hi_atr_lo`,
`chop_hi_atr_lo_gate` and `atr_high_or_chop_hi_atr_lo` were added, measured and
then reverted. If someone wants the cell again, the missing piece is not a
threshold — `chop_thresh` is flat from 58 to 70 and cliffs at 30 — it is a
condition on the **trade** that picks the tail directly, rather than a regime
condition on the bar before it that picks the tail as a side effect.

Harnesses deleted per the owner's instruction rather than kept per the policy
above. The numbers are all here, and the shipping book was verified unchanged
after the revert (`exp_fastcheck.py fsent_champ_long` PASS on both eras).

---

## FS-BREAK CONFIRMATION ENTRY — closed 2026-10-14, nothing adopted

The owner's idea, verbatim: *"when for FS, when the high of or long, when the high
of FS will break, then we will enter. For short, when FS low will be broken, then
we'll enter."*

This is NOT a re-run of FS entry. `method/FS_ENTRY.md` already measured entering
AT the FS print (36% of the book gone, M2 inverts 4/4) and
`method/DIRECTIONAL_FS_P80.md` closed the directional FS trigger at P82 on a
permutation test. This asks a different question, on top of the print: take the
FS trade only once the FS candle's **own extreme** breaks — a continuation
filter on the FS arm, aimed at the 36% `FS_ENTRY.md` left open.

**Result: it loses, 7 of 8 book x era cells negative on net R.**

| book | era | base (FS print) | +8 bars | +4 bars | +16 bars |
|---|---|---|---|---|---|
| `fsent_champ_long` | IS | 497 / **+561.36R** | 402 / +458.00R | 374 / +379.99R | 431 / +521.70R |
| | OOS | 281 / **+251.07R** | 224 / +214.65R | 217 / +206.72R | 249 / +241.33R |
| `fsent_champ_short` | IS | 466 / **+667.52R** | 398 / +601.06R | 362 / +618.91R | 416 / +631.07R |
| | OOS | 298 / **+231.12R** | 238 / +233.27R | 209 / +218.64R | 256 / +225.01R |
| `fsent_champ_long_htffs` | IS | 753 / **+906.62R** | 627 / +753.96R | 590 / +681.56R | 676 / +865.48R |
| | OOS | 389 / **+366.43R** | 339 / +344.58R | 315 / +330.18R | 365 / **+374.50R** |
| `fsent_champ_long_mcloff` | IS | 533 / **+605.33R** | 440 / +496.55R | 407 / +416.38R | 467 / +556.91R |
| | OOS | 300 / **+251.66R** | 236 / +214.86R | 228 / +208.78R | 262 / **+255.85R** |

The single positive OOS cell at the 8-bar arm is `fsent_champ_short` at **+2.15R**
on a 60-trade reduction. That is noise and is not treated as a win.

**The mechanism is M2 again, and it is the third sighting.** Waiting makes the
trade smaller and not better. Every arm throws away 13-17% of the entries and the
survivors are strictly worse in R, because by the time the FS candle's extreme
has broken, the move that made the FS worth taking is largely behind us. This is
the same reason `method/FS_ENTRY.md` found M2 inverts when it becomes legal: the
information that made the swing interesting is consumed before the entry.

**What the arm does improve, which is the only reason it is worth writing down.**
Quality rises while size falls — it is a selection effect, not an edge:

| cell | PF base -> 16 bars | WR | maxDD |
|---|---|---|---|
| `fsent_champ_long` IS | 3.84 -> **4.16** | 43.3% -> 44.3% | 19.57 -> **12.80** |
| `fsent_champ_short` IS | 4.46 -> **4.83** | 40.1% -> 41.3% | 8.65 -> 9.07 |
| `fsent_champ_long_htffs` OOS | 3.40 -> **3.59** | 39.6% -> 40.0% | 10.59 -> 11.84 |
| `fsent_champ_long_mcloff` OOS | 3.11 -> **3.68** | 42.0% -> 44.7% | 8.30 -> **7.21** |

So the break condition is a decent *filter* and a bad *entry*. If this is picked up
again, the promising form is not "enter later" but either a per-trade risk change
on the trades it would have dropped, or using the level as a trail trigger on the
FS entry rather than as an entry delay. Both are different mechanisms and neither
is measured.

**Causality is clean and that is not why it failed.** The knob reads
`candles_ltf[fs_at_idx].high/low` and `candles_ltf[j]` for `j > fs_at_idx`. The FS
candle has closed (`fs_at_idx >= seg.end_idx`) and the entering bar `j` is the bar
the break happens on, so nothing settles later than the decision bar. No swing
field is read except this swing's own `fs_at_idx`. Contrast `exp_require_dir_match`
and `exp_max_swing_age`, which read the swing's FINAL direction and settle
mid-swing — this does not, and it is not in their family.

**Identity gate passed on landing**: `exp_fastcheck.py fsent_sig_full` ->
`shipped 325t/+114.6R vs patched-off 325t/+114.6R -> IDENTICAL`. The default is
off and byte-identical, so no shipping book moved.

`exp_fs_break_confirm=1.0` and `exp_fs_confirm_bars` stay in `unified.py`,
default-off, because the harness is kept per policy above and a knob the harness
needs is not dead code. Harness kept:
`backtest/experiments/fs_break_confirm/exp_fs_break_confirm.py`, results beside
it in `fs_break_confirm_results.json`.

### The owner's colour condition, which is the version actually asked for

`exp_fs_break_confirm=1.0` above delays **every** FS entry. The owner's own
framing was narrower and is worth recording separately, because it is the
sharper hypothesis and because it produced a near-identical result for a reason
worth knowing:

> "we enter on fs if long and fs is green we enter directly if short fs is red we
> enter directly but if long and fs is red on the break of red high we enter and
> vice versa"

i.e. delay only when the FS candle's COLOUR opposes the trade. Implemented as
`exp_fs_break_confirm=2.0`.

**It loses, and the reason it loses is that the condition almost never fires the
"enter directly" branch.** On `fsent_champ_long` IS, base is 497 trades, the
colour-conditioned arm is 405, and the unconditional arm is 402 — **only 3 trades
differ**. About 97% of FS entries already carry an opposing colour, because an FS
candle breaks the swing's *opposing* pivot and is therefore usually red on an up
swing and green on a down swing. The colour gate is nearly a no-op, so this is
the same experiment wearing a condition.

| book | era | base | colour-opposed (8b) | delta |
|---|---|---|---|---|
| `fsent_champ_long` | IS | 497 / +561.36R | 405 / +456.01R | -92 / **-105.35R** |
| | OOS | 281 / +251.07R | 233 / +229.83R | -48 / **-21.24R** |
| `fsent_champ_short` | IS | 466 / +667.52R | 399 / +598.77R | -67 / **-68.75R** |
| | OOS | 298 / +231.12R | 240 / +242.15R | -58 / **+11.03R** |
| `fsent_champ_long_htf15` | IS | 500 / +600.12R | 415 / +474.21R | -85 / **-125.91R** |
| | OOS | 281 / +291.43R | 238 / +280.52R | -43 / **-10.91R** |
| `fsent_champ_long_htffs` | IS | 753 / +906.62R | 631 / +756.33R | -122 / **-150.29R** |
| | OOS | 389 / +366.43R | 334 / +342.30R | -55 / **-24.13R** |
| `fsent_champ_long_mcloff` | IS | 533 / +605.33R | 445 / +496.44R | -88 / **-108.89R** |
| | OOS | 300 / +251.66R | 246 / +231.78R | -54 / **-19.88R** |

**IS is negative in 5 of 5 books at every confirmation window.** Summed over all
five books:

| window | IS | OOS | total |
|---|---|---|---|
| 4 bars | **-857.35R** | -125.50R | **-982.85R** |
| 8 bars | **-559.19R** | -65.13R | **-624.32R** |
| 16 bars | **-202.99R** | +18.88R | **-184.11R** |

**The 16-bar window is the only arm that looks alive, and it should not be taken
at face value.** At 16 bars OOS is positive on 3 of 5 books — `htf15` +10.65R,
`mcloff` +11.09R, `htffs` +8.60R, with PF up and maxDD down on every one of
them. But the same arm is negative in IS on all five books (-34R to -49R each).

**OOS-positive / IS-negative is an era split**, and that is the signature that
closed regime routing on chop above ("era split, the seventh appearance"). A
filter that suits one period and harms the other is not a filter that works; it
is a filter that fits. The proper test is the paired bootstrap over the trade
differences that P80 named and never ran, and that test is still outstanding
here too.

**Same mechanism as the unconditional arm and as FS_ENTRY.md's M2 inversion**:
by the time the FS candle's extreme breaks, the move that made the FS worth
taking is behind you. Confirmation is worth having; paying for it with the entry
is not.

**Not closed as a lead, only as an entry rule.** Quality improves in BOTH eras at
16 bars - pf 3.29->3.77 and maxDD 9.85->6.21 on `fsent_champ_long` OOS, pf
3.11->3.78 and maxDD 8.30->7.21 on `mcloff` OOS, with WR up in every cell. So the
FS-extreme level is a real discriminator of trade quality. The forms still worth
trying are a **trail trigger on the FS entry** rather than an entry delay, and a
**per-trade risk change** on the trades it would have dropped. Neither is the
same mechanism as this one and neither is measured.

Identity gate re-run after `2.0` landed: `exp_fastcheck.py fsent_champ_long` ->
IS 497/+466.92, OOS 281/+215.32, every pinned field reproduced, default still
byte-identical.

### The trail-trigger form, and a correction to what the section above claims

The two leads this file left open after the entry-delay arms were (a) a trail
trigger on the FS entry and (b) a per-trade risk change on the trades it would
have dropped. **(a) is now measured — and it closes the premise, not just the arm.**

`exp_fs_trail_trigger`: the entry stays on the FS print, nothing is dropped, and
once the FS candle's own extreme breaks the stop ratchets — `1.0` to breakeven,
`2.0` to the FS candle's opposite extreme. Entry price, risk, `sl0` and the 3R
target are all fixed at entry and never recomputed; only the live stop moves,
only tighter, only to a level on the losing side of the current bar. Causal: the
ratchet is applied inside the bar loops at bars at or after the trigger bar, so
nothing settles later than the bar it is used on.

**It loses, and much harder than the entry delay did.** IS, per book:

| book | base | breakeven 8b | FS extreme 8b | delta (FS extreme) |
|---|---|---|---|---|
| `fsent_champ_long` | 497 / +561.36R | 525 / +284.96R | 520 / +302.08R | **-259.28R** |
| `fsent_champ_short` | 466 / +667.52R | 505 / +602.58R | 503 / +608.09R | **-59.43R** |
| `fsent_champ_long_htf15` | 500 / +600.12R | 521 / +312.78R | 517 / +338.25R | **-261.87R** |
| `fsent_champ_long_htffs` | 753 / +906.62R | 818 / +606.52R | 821 / +694.07R | **-212.55R** |
| `fsent_champ_long_mcloff` | 533 / +605.33R | 599 / +340.70R | 590 / +367.47R | **-237.86R** |

Negative on 5 of 5 books in IS and on every arm in every era. OOS is better than
IS but still negative on 4 of 5 books. Win rate collapses from ~43% to 21-30%
while trade count RISES — the stop scratches the tail that was paying.

**WHY, and this corrects the claim made above.** This section said the FS-extreme
level is "a real discriminator of trade quality". It is not. The level breaks on
the MAJORITY of FS swings:

| cap | swings whose FS extreme breaks |
|---|---|
| 8 bars | **1856 of 2840 — 65.4%** |
| 16 bars | 2135 of 2840 — 75.2% |
| 32 bars | 2346 of 2840 — 82.6% |

A level that fires two times in three cannot discriminate good trades from bad
ones. What looked like a quality gain in the entry-delay arms was largely the
**arithmetic of removing trades** — dropping 13-17% mechanically raises profit
factor and lowers maxDD whether or not the survivors are better. That reading was
wrong and this test is what falsified it.

So both costs are now explained by one fact, and they are opposite errors on the
same signal:
- **delay the entry** — you give up the move that made the FS worth taking
- **ratchet the stop** — you scratch the tail, and it fires on 65-83% so it
  scratches most of the book

**Do not read the PF/maxDD improvement in the arms above as evidence of edge.**
Read it as selection.

(b), the per-trade risk change on the trades it would have dropped, remains
unmeasured and is now the weaker of the two leads — the underlying claim that
those trades are identifiable is what this section got wrong.

Identity gate: `exp_fastcheck.py fsent_champ_long` -> shipped 325t/+114.6R vs
patched-off 325t/+114.6R IDENTICAL; IS 497/+466.92, OOS 281/+215.32, every pinned
field reproduced. Harness:
`backtest/experiments/fs_break_confirm/exp_fs_trail_trigger.py`.

### FS COVERAGE: the open question in FS_ENTRY.md is CLOSED - the answer is zero

`method/FS_ENTRY.md` left one thing open: *"2900 swings exist in IS and 1634 in
OOS, all with an FS - so a true FS-only engine could in principle take swings that
never produced a B2/flip entry, which would be a much larger book. That is not
simulated here."*

`method/FS_ONLY_ENGINE.md` answered it on 2026-09-28: zero such swings. Re-measured
on the **corrected chain** (the volatile-B1 fix of 2026-10-13), both eras:

| era | swings with an FS | ...that also carry a B2/FLIP mark | FS-only, no break mark |
|---|---|---|---|
| IS | 2840 | **2840** | **0** |
| OOS | 1571 | **1571** | **0** |

**Every confirmed swing already has a break mark. The coverage gain is exactly
zero.** An FS-only book cannot be larger than the break-entry book, because there
is no swing the break book misses and FS would reach. The hope stated in
FS_ENTRY.md is dead and stays dead — the answer did not change with the chain.

### The trade-level decomposition P74 asked for, and never got

P74: *"the missing measurement is a trade-level decomposition - how many of the
champion's 500 survive into the FS arm, how many FS-arm trades are new, and the
net R of survivors vs newcomers. Without it, +146 trades for +79.4R is not a
claim, it is an arithmetic coincidence."*

Routed **both** sides to FS (`exp_fs_entry_side="both"` + `exp_htf_fs_entry="all"`),
so the label "FS-only" is earned rather than borrowed. Identity key is
`(entry_ts, dir, swing_no)` — the same key the repo already dedups marks on.

**`fsent_champ_long`, IS:** base 497 / +561.36R -> FS 803 / +753.18R (+306, +191.82R)

| group | n | net | avgR |
|---|---|---|---|
| survivors, same trade in both | **150** | +258.51R | +1.723 |
| newcomers, FS arm only | 653 | +494.67R | **+0.758** |
| base trades the FS arm dropped | 347 | +302.84R | **+0.873** |

**`fsent_champ_long`, OOS:** base 281 / +251.07R -> FS 446 / +181.95R (+165, **-69.12R**)

| group | n | net | avgR |
|---|---|---|---|
| survivors | 86 | +58.63R | +0.682 |
| newcomers | 360 | +123.32R | **+0.343** |
| dropped from base | 195 | +192.44R | **+0.987** |

`fsent_champ_short` behaves identically — OOS newcomers +0.424R against dropped
survivors +0.932R, net **-49.17R**. (Both books collapse to the same FS-both
configuration, so that row is the same book measured twice; the directional
distinction is gone by construction there.)

**Two findings, and the first is the important one.**

1. **Only ~30% of the base book survives routing** — 150 of 497 in IS, 86 of 281 in
   OOS. The two books are not variants of each other; they are mostly
   *different trades*. So any "+N trades for +R" reading that treats the FS arm
   as an addition is wrong by construction, which is exactly P74's objection.

2. **The newcomers are individually worse than the survivors they replace, in
   both eras.** IS +0.758R against +0.873R dropped. OOS +0.343R against +0.987R
   dropped. If the newcomers were pure additions they would be remarkable; they
   are a swap of better trades for worse ones, and the OOS swap is bad enough to
   turn +251.07R into +181.95R.

**And it is an era split on top of that**: +191.82R in IS against -69.12R in OOS.
The same signature that closed regime routing on chop, and the one P80 named when
it asked for a paired bootstrap that was never run.

**So P73's "+146 trades for +79.4R" is confirmed to be an arithmetic
coincidence.** Not because the numbers were wrong — they reproduce — but because
the newcomers are worth less than what they displace, in both eras, and the one
era where the headline is positive is the in-sample one.

**Nothing adopted.** No shipping book moved. Identity gate held throughout.

Harness: `backtest/experiments/fs_break_confirm/exp_fs_coverage_decomp.py`,
results beside it. This closes the FS-entry family: the trigger was measured
(FS_ENTRY.md), the directional form was closed by permutation (P80/P82), the
entry-delay forms are above, the stop-trigger form is above, and the coverage
argument for a bigger FS-only book is now zero rather than unmeasured.

---

## "EXTREME PIVOT" IS NOT A TYPE OF PIVOT — the rule is stated, and it gets misread

Not an experiment. A **terminology** closure, written 2026-10-13 because it cost a
live session.

**What happened.** The owner asked whether a specific bar should have produced a B2.
A chart example was built on the running low at `2024-05-10 18:15` (62900.0), and
the answer given was "the gap rule blocked that mark". The owner's response:

> *"Does 18:15 candle's low, was there a pivot? What are you talking about? ... There
> is no marks there."*

There was no white pivot at 18:15. It was only the lowest price touched since the
leg began. Under the actual rule it was a legitimate candidate target — and under
the owner's reading of it, it was never a target at all and nothing was blocked.
**The example was meaningless, and it was presented as a finding.**

**The cause.** The owner's own ruling is quoted in `firstswing.py` and in
`SWING_THEORY_B1_B2_FLIP.md` §6.1 using the phrase **"extreme pivot"**:

> *"if they break an extreme pivot for B2 there is a one candle gap."*

Read literally that is a type of pivot — which is the opposite of the ruling. The
same document's §3 says the opposite thing correctly (*"the running extreme, not a
sealed pivot"*), but the two statements sat ~100 lines apart with nothing tying
them together. B2/FLIP use the extreme; FS uses a sealed pivot. Nothing said so
anywhere near the gap-rule discussion.

**The ruling, re-affirmed by the owner the same day, 2026-10-13:**

> *"It should be for B2 flip, it is extreme pivots."*

**What changed.** The theory doc now opens with a two-anchor block stating the
difference before any section; every occurrence of "extreme pivot" carries a
translation beneath it while the owner's quotes stay verbatim; the gap rule is
stated once, applied to the running extreme; `fix/V2_BOT_PROMPT.md` §6.2 points
at the canonical block as the single source of truth.

**The transferable rule, for whoever reads this next:**

> Any question about a B2 or FLIP must say which anchor it means. If a mark is
> being discussed without naming the running extreme or the white pivot, the
> discussion is not yet answerable.

`exp_theory_wording_gate.py` now fails if the two-anchor block is removed from the
theory doc, or if "extreme pivot" reappears anywhere outside the owner's own
quotes. Docs and comments only — no behaviour change, and the chain fingerprint
was verified identical afterwards.

---

## SWING SHAPE AS A FEATURE - the whole shape space, tested. Nothing adopted.

The chain has a rigid shape that NO book has ever used: `B1 -> B2/FLIP strict
alternation -> FS`, and FS is the LAST event in 2840/2840 IS swings and 1571/1571
OOS (proved by exp_fs_terminal_gate.py, 0 violations on 15m mb50 and 1h mb10/mb15
both eras, ~8600 swings). So the entire swing history is in the past at the entry
bar, and shape is fully observable before every trade is taken. 14 distinct
sequences on 15m; terminal B2 1667 / FLIP 1173; 0-6 alternations.

Every one of the five books enters on FS with identical logic regardless of shape.
`exp_shape_quality.py` asks whether that is leaving anything on the table.

    terminal    long   short   htf15   htffs        (mean R, IS)
    B2        +0.854  +1.108  +0.848  +1.051
    FLIP      +1.560  +1.905  +1.756  +1.451

On IS, FLIP-terminal trades beat B2-terminal trades in all four books. 95% block
bootstrap on the difference: 3 of 4 "not separable", htf15 "SIGNIFICANT" at
[-1.762, -0.074] - a CI that touches zero.

Then OOS:

              IS diff    OOS diff
    long       -0.7069     +0.1866   <- FLIP better   ->  B2 better
    short      -0.7970     +0.3209   <- FLIP better   ->  B2 better
    htf15      -0.9087     -0.0728   <- FLIP better   ->  FLIP better
    htffs      -0.4002     +0.1455   <- FLIP better   ->  B2 better

SIGN FLIP ON THREE OF FOUR BOOKS, and 7 of 8 bootstrap CIs across both eras say
"not separable". Terminal kind does not carry a stable edge. Alternation depth is
dominated by sample size at the deep end (depth 3+ is n=3-20 and goes negative in
both eras for htffs). Nothing adopted.

THE LESSON, WHICH IS THE REASON THIS IS HERE

The shape space is rich, fully observable at entry, and completely unused - and
it carries no edge. The most attractive property an idea can have is that it is
EASY to measure. This one was measurably worthless. Do not reopen it without a
mechanism that predicts WHY depth or terminal kind would matter; "it is available
so it must be useful" is the reasoning that produced seven era splits already.

## VOLATILE CANDLES AS A FEATURE - strong on IS, inverted on OOS. Nothing adopted.

Volatile candles are where the youngest logic in the engine sits and where none of
it has been tested as a population: the close-colour rule (5d6cab2, 2026-10-13),
and firstswing.py:528-534 where a volatile candle sustaining an already-flipped
leg produces NO MARK AT ALL ("we cannot mark it anything here ... so we have to
wait", owner 2023-06-10 22:30). 197 volatile B1s and 51 direction flips were
recorded when the colour rule landed. That category did not exist before the fix.

`exp_volatile_b1.py` detects volatility the way the engine does - a candle whose
high exceeds the running high AND whose low breaches the running low, both against
prior candles in the same leg - and splits swings into clean / volatile-early
(before the first FLIP) / volatile-late.

volatile-early, mean R against the same book's clean swings:

    book      IS clean -> vol-early    OOS clean -> vol-early
    long       1.083  ->  1.528  +41%   0.915  ->  0.244  -73%
    short      1.257  ->  4.346 +246%   0.875  -> -0.126
    htf15      1.184  ->  1.613  +36%   1.070  ->  0.271  -75%
    htffs      1.116  ->  1.842  +65%   1.022  ->  0.095  -91%

IS: volatile-early is 40% to 246% BETTER in all four books. OOS: WORSE in all
four, and negative on short. Four books agreeing on IS is not evidence here -
four books reading the SAME signal agreeing on IS is what an era effect looks
like. This is the seventh appearance of this shape.

Note also that short's volatile-early carries mean +4.35R and PF 10.77 on n=28.
Means on tiny groups are exactly the fat-tail artefact documented in the C1
section, so treat the IS magnitude as untrustworthy even before the era flip.

Nothing adopted. The harness stays - the next person will want to know a
population this clean was tested and found empty.

## SUPPRESSION ACCOUNTING - 12,981 breaks still unexplained

The invariant harness counts 20,460 ARMED breaks that never became an emitted
mark, against 7,734 that did. 73% of everything the engine detects is discarded.
A whole sweep has been run without anyone asking where it goes.

Attributable today:

    gap rule (b2_gap_bars, isolated by chain toggle)      811
    dir_confirmed (measured by exp_dir_confirmed_b2_path) 6,668
    RESIDUAL - not attributed                            12,981

The residual is 63.4% of armed suppressions and 1.68x the emitted mark count. The
4,102 not-armed drops are a SEPARATE bucket (firstswing.py:428, source comment
records 96% of them broke a pivot sealed on an earlier bar) and are not part of
the 20,460; conflating them would make the residual look smaller than it is.

Two more paths are inventoried but unmeasured, both of which are SILENT - they
produce no row in the swing record at all:

    firstswing.py:528-534  volatile candle sustains an already-flipped leg -> NO MARK
    firstswing.py:535      _b2_done_in_dir -> one B2 per direction per swing

Closing the residual needs counters inside the walk, not a read of the finished
chain. NOT DONE - it needs engine instrumentation and is a separate, riskier
change.

Side finding from the toggle: `b2_gap_bars` removes 599 B2 marks AND 73 FLIP
marks. A knob named for B2 also suppresses FLIP. Not a defect found, just not
something the name would tell you.
# PROMPT FOR A SECOND RESEARCHER

Copy everything below this line into a fresh agent with file access to
this repo. It is written to be self-contained: you should not need to ask
me anything, and you should not re-run anything reported here as if it
were new.

---

## YOUR TASK

Propose **genuinely new research directions** for this trading system.
Not variations on what has been tried. Not re-runs. If a direction is
already in the graveyard list below, it is closed — do not propose it,
and do not propose "a better version of it".

Deliverable: **6 to 10 distinct research proposals**, each with
- a one-line thesis in plain language
- the mechanism (why would this work when the closed list did not?)
- exactly what data it needs and whether that data exists here
- what result would falsify it
- a pre-registered hit bar, written BEFORE any run

You are not writing code yet. You are proposing. Rank them by how much you
believe them after reading the graveyard.

## READ THESE FIRST (in this order)

| file | why |
|---|---|
| `backtest/docs/closed/CLOSED_DO_NOT_REPEAT.md` | **the graveyard. 31 closed directions.** Start here or you will waste our time |
| `backtest/docs/method/HANDOVER_SESSION.md` | the full state of play, including the 1m thread |
| `backtest/docs/method/ENTRY_TIME_AUTOPSY.md` | why per-trade filters are exhausted |
| `backtest/docs/method/RETROSPECTIVE_AND_FORWARD.md` | the methodology trap and the forward data |

## THE SYSTEM

Single instrument: **BTCUSDT, Bybit linear perpetual.** Roughly 3.7 years
of IS (2023-01 → 2026-09) and 2.0 years of OOS (2021-01 → 2022-12).

The architecture is a three-timeframe cascade:

- **1h (HTF)** opens a *bias window* — a swing leg with a direction and a
  time range. "Bias is long from here until here."
- **15m (LTF)** opens the *trade* — a B2 or FLIP break mark fires, and if it
  lands inside an open 1h window, in the same direction, a trade opens.
- **1m** supplies the *exit fills* — the trail and stop are walked on 1m
  bars so exit prices are precise.

The shipped book is flat-sized. There is no sizing logic and no live size
channel (`v18_streak_halt.py` has zero hits for equity/size/notional).

**The base books you must measure against:**

| lane | IS | OOS |
|---|---|---|
| `champion_multi_sw10` | 500t, **+325.8R net**, WR 27.8%, PF 1.81, maxDD 27.7 | 279t, **+70.2R net**, WR 27.2% |
| `utcsat_multi_sw10` | 454t, **+358.9R net**, WR 29.1%, PF 2.01 | 253t, **+60.2R net** |

Key params: `cooldown_bars=8`, `max_consecutive_losses=3`, `ext_stop_r=3.0`,
`sl_buf_atr=0.01`, `mode="atr_high"`, `chop_thresh=58.0`, `exp_mltf=True`,
`exp_persist=7`.

**The character of the book, which constrains everything:** ~28% win rate,
and the net is carried by a handful of very large winners. IS has 17 trades
≥ +10R. **Low WR plus tail concentration is a feature of trend systems, not
a defect** — tightening the stop drops WR to 18.8% and quadruples drawdown.

## WHAT IS ALREADY CLOSED (the graveyard — read the doc, this is the short list)

**Entry/signal side:** range-position × width gating, mid-range avoidance,
ADX, Kaufman efficiency ratio, regime/chop/wick/swing-churn filters, B1
entry, all of the 1m layer (as trigger, as a separate book, as a fill, as
an add-on gate, and as an entry-time feature).

**Sizing:** vol-targeting, the sMZX family (retracted — it was
forward-looking), add-at-FS, cross-venue.

**Stop/exit:** tighter SL, wider SL, causal SL, pivot trail, half-swing stop,
exit-at-FS, "exit when the swing looks bad". **The stop has been attacked
from both directions and every variant loses.** `sl_buf_atr=0.01` with a
swing-pivot stop stands.

**More trades:** relaxing cooldown or loss limits, pyramid/scale-in,
revenge re-entry, same-window re-entry.

**Other:** 4h HTF confirmation, 1h-momentum gate, window-age gates,
campaign policies, cross-sectional alt rotation, flow/positioning data,
scheduled-event filters.

## FINDINGS FROM TODAY THAT SHOULD NARROW YOUR SEARCH

1. **The 1m timeframe is closed as a source of edge.** Not a tuning
   failure — arithmetic. A 1m book pays ~0.79R of cost per round trip;
   a 1:2 wager needs ~0.8R of edge just to break even, and the 1m book's
   gross edge was −0.018R. Twenty thousand trades came to −16,220R net.

2. **Per-trade entry features are exhausted.** Nine candidate features were
   scored for whether they separate the top decile of trades from the bottom
   decile at the entry instant. The only one that separated was
   `swing_no`, and it turned out to be calendar time
   (corr with calendar index = +1.000 exactly, in both eras). Everything
   else sat at AUC ≈ 0.5. **This is why the graveyard is so long: the
   buckets that "looked different" in earlier experiments were measuring
   calendar and regime, not a trade-level property.**

3. **`max_consecutive_losses=3` is a real optimum, not an inherited
   constant.** Swept for the first time: IS peaks sharply at 3 (k=2 is
   −77.7R, k=6 is −103.7R). The reason it works is measured directly —
   skipping after 3 losses is worth +17.3R against not doing it. It is
   *not* because loss streaks are exploitable: the win/loss sequence is
   close to independent in both eras.

4. **The book's win/loss sequence is near-independent.** Do not propose
   anything premised on predicting the next trade's direction from the
   previous trade's outcome. That avenue is measured and closed.

5. **A R-sequence autocorrelation of +0.498 in OOS turned out to be a tail
   artefact** — big winners sitting next to each other, not directional
   clustering. If you find a serial-correlation effect, check it against
   the rank-transformed series before believing it.

6. **The one thing that transferred:** the same frozen lane works on 7 of
   13 alt-coins with both eras positive, and those books are near-
   uncorrelated (mean pairwise monthly-R +0.072 IS, −0.053 OOS), so six of
   them together draw down 1.25–1.79× a single book rather than 6×.

## WHAT HAS NOT BEEN TOUCHED (seed list — verify, do not trust)

Check these yourself; some may be more covered than they look.

- **Label/notation redesign.** The system uses B1/B2/FLIP/FS marks. Nobody
  has examined whether a *different labelling* of the same price structure
  — say P1/P2 wave labelling, or a ZigZag + Elliott hybrid — produces a
  different and better-conditioned trigger set than the current four marks.
  This is a change to what the system SEES, not a filter on trades it
  already rejects. **This is my strongest suggestion; treat it as a
  starting point to argue with, not an assignment.**
- **`data/scheduled_events/`** — official Fed speech and US event archives,
  2021-2026, sitting on disk. An audit exists; I do not know whether a
  pre-registered event gate was ever run path-true, or only audited.
- **30m and 5h timeframes.** 4h data exists and 4h confirmation was tested
  and closed. 5m exists and 5m confirmation was tested and closed. 30m I
  do not see anywhere in the repo. Note the barrier: 30m would need
  building from 15m or refetching, and any new timeframe inherits the
  bar-counted-parameter problem (a 30m bar is not half a 15m bar to a
  parameter counted in bars).
- **Order-book / microstructure.** The repo is OHLCV only. If you want
  something genuinely outside the current information set, say so
  explicitly and name what would have to be fetched.
- **Position lifecycle as resize rather than close.** The cohort lifecycle
  policies (close older positions on a newer stop, on an opposite swing,
  freeze entries after an opposite swing) were tested at fixed thresholds.
  Nobody has asked whether the right response to a multi-position book is
  to *resize* rather than close. Note this needs a size channel, which the
  engine does not have.

## HARD RULES (violating these wastes everyone's time)

1. **No forward-looking data.** Any feature must be computable at the
   decision instant. A feature that reads a future price is dead on
   arrival — that mistake already shipped a false "4/4 pass" once (the sM2
   case, retracted in `method/SMZX_LOOKAHEAD_RETRACTION.md`).
2. **No retrospective selection.** If you screen 13 things and report the
   winner, that number is worth nothing — the screen was fitted to the data
   that reported it. `data/forward/bybit/` holds a slice from 2026-09-13
   that has never been used to choose anything; it is small (~60-70 trades)
   so it can KILL a candidate but not confirm one.
3. **Judge on the trimmed mean, not average R.** These books are
   tail-concentrated; a 0.5R target and a 4R target have wildly different
   average-R profiles for the same underlying edge.
4. **Report ex-best-3 and ex-best-5** on anything tail-dependent.
5. **Same sign in both eras or it is closed.** Seven candidates died on
   era-flip alone in one session.
6. **Controls first.** Assert the reference ledgers (500/+325.8, 454/+358.9,
   279/+70.2, 253/+60.2) before any arm is scored, or the run aborts.
7. **Never edit `backend/src/btc/btc_engine.py`.** Rebuild it in memory and
   install into `sys.modules` — see `exp_b1_entry.py` for the pattern.

## USEFUL FILES

- data: `data/bybit/` (15m/1h/1m/4h/5m), `data/btc/`, `data/btc-fut/`,
  `data/scan-fut/` (16 alts), `data/flow/`, `data/scheduled_events/`,
  `data/forward/bybit/` (untouched)
- engine: `backend/src/btc/engines/htf_ltf/v18_streak_halt.py`
- swings: `backend/src/btc/btc_swing.py`, `backend/src/firstswing.py`,
  `backend/src/walker.py`
- harnesses to copy: `exp_b1_entry.py` (in-memory engine patch),
  `exp_5m_confirm.py` (data loading), `exp_cluster_autopsy.py` (clean stats)
- registry: `backtest/tests/experiment_registry.py` (`BP`, `EXPERIMENTS`)

## ANSWER FORMAT

For each proposal:

```
P<n>. <name>
THESIS:        one sentence, plain language
MECHANISM:     why this should work where the closed list did not
NEW DATA:      what it needs, and whether it exists on disk
FALSIFIER:     the result that would kill it
HIT BAR:       pre-registered, written before any run
MY CONFIDENCE: high / medium / low, and why
```

Then: **which one would you run first, and what would you need from me.**

---

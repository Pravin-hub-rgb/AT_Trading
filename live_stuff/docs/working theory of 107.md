# Working Theory of 107 (plain-language)

This is a simple, non-technical walkthrough of how the live engine actually works,
how it relates to the old backtest machinery, every knob that matters, and how to
prove that live and backtest agree.

---

## 1. Big picture: two timeframes, one decision

The engine looks at **two charts at once**:

| Chart | We keep | Why |
|---|---|---|
| **1h** ("HTF", higher timeframe) | Last 20 days of candles | Decides: is this trade ON or OFF? |
| **15m** ("LTF", lower timeframe) | Last 30 days of candles | Decides: exactly when do I click "buy"? |

**Not one single price.** We do not watch a price line and buy when it crosses
something. We draw swing highs and swing lows on both charts, and a trade
"happens" only when a very specific pattern of breaks lines up:

1. On the **1h chart**, a "window" opens: a recent swing high is broken while a
   recent swing low still holds (or vice versa). This is the **bias** — the
   longer-timeframe clue that this move is worth following. It has a SL (the
   swing low it must protect) and a 3R target.
2. On the **15m chart**, a "ladder" builds: swing highs and swing lows chain into
   a staircase pattern (down, down, down… then a break **up**).
3. One more reading decides **which** 1h window actually gates the bar: the
   book's regime router. Book 107 (`mode="atr_high"`) reads the 15m **ATR%
   (ATR(14)/close × 100)** — above 0.65 the **DECISIVE** window family gates;
   below it the **FLIP** family does (exact chains in §2/§3).
4. When both align — the 1h window is open in the right direction, the regime
   router allows it, and the 15m trigger fires (longs: FS; shorts: the first
   B2 mark — see "Entry triggers" in §3) — **that bar close is the entry**.
   Stop goes at the leg extreme (the pivot the leg defends, `pivot_rule="leg"`)
   plus a tiny 0.01-ATR buffer.

This "1h sets the door open, 15m walks through it" idea is the whole strategy.
Everything else is safety rules around it.

---

## 2. What already happened vs what will happen — the rolling window

We do **not** recompute history every tick. We keep a **rolling window** of
finished candles and run the strategy engine against that window. Every time a
new candle closes:

1. The candle is appended to the correct window (`window_15m` or `window_1h`).
2. Old candles past the window limit are dropped (30 days for 15m, 20 days for
   1h).
3. A **chain of swing points** is maintained. This is the key trick: even though
   the window is short, the swing *chain itself* is long — it remembers where
   every past swing high/low sits, so an old price level can still be broken by
   tomorrow's candle. It just gets trimmed from the far end (never mid-chain).
4. The whole book-107 engine is re-run over the (window + swing chain). This
   means the **same code that produced the backtest numbers also produces the
   live signals** — there is no separate "live logic". It just runs on a rolling
   slice instead of a full backtest slice.

**Bottom line: not one guess per something. It is a per-bar, stateful simulation
that rolls forward.** Every time a 15m candle (or 1h candle) closes, the engine
redisplays the exact same "what if I had this data in the backtest" picture, and
the signals it produces are the signals the backtest would have taken.

At any moment, the active 1h window is described by:
- status: **OPEN** or **CLOSED**
- direction: **long or short** — window families exist on both sides, and
  book 107 trades both (long via FS, short via the first B2 mark)
- entry price, stop price (−1R), 1.5R level, 3R level
- current unrealized R (that price moved how many R already?)

Book 107's regime is **not** driven by chop. The engine's regime chain
(`unified.py:1183`) reads how wild the 15m chart currently is — **ATR(14) of
the 15m candles as a percent of price** (ATR% = ATR/close × 100). The mode is
`atr_high`:

- **ATR% above 0.65 → the "decisive" family** gates this bar.
- **ATR% below 0.65 → the "flip" family** gates this bar.

The engine computes **all three window families every bar** (decisive, flip,
and a third "b2" family that belongs to *other* books' rules — 107 never
trades behind it) and the router picks the gating family **per bar close**, so
the same instant a regime flips, the gate switches to the new family. The live
status/tracker mirrors this same rule (`state._compute_regime`), so what you
see printed (REGIME=... → DECISIVE/FLIP) is the family the engine would gate
with at that bar.

---

## 3. The rules — the exact gate every signal passes

Every 15m signal has to pass **all** of these to become a live order:

1. **HTF window exists.** A 1h swing-break must already be open in the same
   direction (long only for book 107). No window = no trade.
2. **Regime matches.** The signal must come from the window family the regime
   router selects **for that bar** (ATR% > 0.65 → "decisive" family; otherwise
   "flip"). Every trade carries the regime family it was gated with
   (`htf_regime` stamp), and windows/signals from the other families are
   diagnostics only. Note: "b2" windows seen in tables belong to other books'
   rules; book 107's families are decisive/flip.
3. **3R extension not done.** The 1h window must not have already traveled its
   3R target (`ext_stop_r=3.0`, `htf_rr=3.0`). If the move is already past 3R,
   we do not chase it.
4. **Cooldown.** After any trade closes, the book accepts no new signal for
   **8 × 15m bars** (2 hours). Both completed trades and gray shadow legs count.
5. **Streak halt off.** Book 107 sets `max_consecutive_losses=0`, meaning we
   do **not** halt after N losses. But the loss count is still tracked, because
   the **daily loss limit** uses the same counter.
6. **Age.** A signal cannot fire if the 15m candle that produced it is more
   than 2 bars old (30 min). This is the anti-repaint rule — we only take signals
   that are fresh enough that a live order would have been placed on them in a
   real-time backtest too.
7. **Window cap 16 days.** The 1h window dies after 16 days even if it never
   closed on its own.
8. **Cap on concurrency.** Book allows up to 10 open legs (`max_positions=0`
   means "no hard cap from the strategy itself"; the live executor allows
   `LIVE_MAX_LEGS=10`).
9. **Wait for the previous swing's FS.** A signal may not be taken until the
   swing BEFORE the one it belongs to has printed its FS. This is the engine's
   `filter_pre_fs` gate and it is the last rule, not the first: it decides
   *when* a mark may be used, not *which* marks count. See the subsection
   below — it is the rule with the most history and the least documentation.

### The wait-for-FS rule (added 2026-10-22)

**The rule.** No entry may be taken before the **previous** swing has printed
its FS. The swing you are trading on is still forming — its own extreme is not
final until its FS prints, and that print is *after* the entry bar — so the
only swing whose declaration you can know at entry time is the previous one.
Waiting for it is the most the rule can ask for without asking for the future.

**What it does NOT touch.** Entering at a swing's **own** FS print is a
different thing and is unchanged: the swing is declaring itself at that
instant, so it is declared by construction. What the rule covers is the
**fall-through side** — the side that enters on a mark (B2 / FLIP / DECISIVE)
instead of at the print. That is the side that was broken.

**Where it lives.** In the engine, in `_collect_signals` (`btc_engine.py`), in
the `fs_` branch's fall-through sub-loop. It is not a book parameter and not a
live-loop rule: it is engine-level, so every book that uses that path obeys
it, and the vendored copy that `live_stuff` runs is byte-identical to the
research one. The HTF leg cannot reach it — the HTF side is only ever handed
`"fs_both"`, which has no fall-through.

**Why it was added.** The fall-through sub-loop was re-implemented on
2026-10-04 (`539935c`, "DIRECTIONAL FS ENTRY") with no pre-FS check and an
early return past the normal loop's C13a filter. From that date, every
fall-through entry was taken on an **undeclared** swing — the exact thing the
normal path had forbidden since 2026-09-11. For book 107 that was 51
in-sample and 48 out-of-sample entries.

**What it cost.** The pre-FS entries were worth **+36.56R in sample** and
**+50.19R out of sample** as a group. Removing them shifted the chain, and
the trades that replaced them were worth only ~+7.8R / ~+4.5R. Book 107 goes
from 525t / +538.40R to **520t / +508.37R** in sample and from 295t / +272.92R
to **290t / +220.71R** out of sample — **-30.03R in sample and -52.21R out of
sample**. The out-of-sample cost is roughly twice the in-sample cost on most
books in the family. That is the honest price of the rule, and it is not a
rounding error.

**How it is checked.** Not by reading the code. `exp_gate_sweep.py` re-derives
every /results book on both eras with the gate on and off, and asserts for
every trade that the entry is not before the previous swing's confirmation.
On the gated engine the fall-through count is **0**.

### Entry triggers (quick note — where each side fires)

- **Long** = the **FS print** of a declared up-swing: the 15m candle that
  closes with the declaration (chop-target or sustain confirm, leg ≥50 bars).
  An open (undeclared) up-swing cannot FS yet — nothing fires.
- **Short** = the **first B2 mark** of the forming down leg (`B1 → B2`):
  fires that candle's close, before the leg declares. But only once the
  **previous** swing has declared — the wait-for-FS rule above. The live
  engine call appends the open leg's marks to the signal list every 15m close
  ("L5"), so the B2 candle is the entry candle. When the leg later declares,
  its declared break list carries the same mark — the dedupe key
  `(entry_ts, dir)` skips it, no double entry.
- **FLIP** (leg's origin broken against it) is also a tradeable mark in the
  mark's OWN direction (a flip-up on a down leg = a long signal), but
  **FCFS**: the *first* tradeable mark of a leg owns that leg's single
  entry — if B2 fired first, later marks of the same leg stay diagnostic.
  A flip re-arms a fresh leg, so the counters reset.
- B1 never trades (structure only). `stale` guard (>2 bars old at journal
  time) is the recovery safety net, not the normal path.

---

## 4. Order types, sizing and gray legs

### Sizing (the actual money maths)

Everything starts from a single number: **all-in risk per trade in INR**.
Stored in `risk_inr.txt` (default **₹250**), editable **without restart**.

```
risk_usdt = risk_inr / usdt_inr_rate
1R_price  = | entry_price − stop_price |        (price-level distance)
quantity  = risk_usdt / 1R_price                (in BTC)
```

Quantity is then floored to the exchange step `0.001 BTC` and capped by
leverage (3x, isolated margin), balance safety (95% of available) and the
aggregate notional cap (₹ --- example: `$6,500` at 3x). The printed stop is
Bybit's `triggerPrice`; a panic SL (5% away) is attached as a safety net only
during orphan/force-close situations.

### Gray legs — the interesting part

The exchange will not accept less than `0.001 BTC`. When the formula above
lands on a quantity below that, **you cannot place a real order**. What you
*do* with that signal decides whether your live book still behaves like the
backtest:

- **Old behaviour (boring, simple):** the signal is simply skipped. Trade lost
  to precision. This is what every naive implementation does.
- **Book-107 live behaviour:** the signal is kept as a **gray leg**. It:
  - has no real order, so no fees, no margin, no liquidation risk
  - **still occupies one leg slot** in `LIVE_MAX_LEGS`, because the strategy
    must behave as if it were open;
  - **still counts toward the 8-bar cooldown** and the loss-streak — a gray
    loss bumps the counter the same way a real loss does;
  - runs its own simulated SL (`entry − 1R`) and trail exit, entirely in the DB;
  - is **excluded** from exchange reconciliation, funding, fees, and the
    **daily loss limit** (setting `GRAY_MIN_QTY_ENABLED=false` restores the
    old skip behaviour).

Why bother? Because if a region produces 1-market-reject and 1-gray-loss within
a window, the *strategy* still experiences "2 moves happened here"; the real
wallet just does not feel the gray part. Backtests already priced this in via
`exp_sl_gray_tail.py` (the wide-stop tail scenario), so keeping them as shadows
matches the backtest book exactly.

---

## 5. Knobs that actually change behaviour

| Knob | Where | Default | Effect |
|---|---|---|---|
| `risk_inr.txt` | file, hot-reloaded | 250 | 1R per trade, in ₹ |
| `LIVE_MAX_LEGS` | env | 10 | Max concurrent open legs (real + gray) |
| `MAX_AGGREGATE_NOTIONAL` | env | 6,500 (USDT) | Total open notional cap; 0 disables |
| `GRAY_MIN_QTY_ENABLED` | env | true | Keep min-qty rejects as shadow legs |
| `MAX_LEVERAGE` | config.py | 3 | Hard cap on implied leverage |
| `BALANCE_SAFETY_MARGIN` | config.py | 0.95 | Max fraction of available balance used |
| `MARGIN_MODE` | config.py | isolated | Each trade risks only its own margin |
| `DAILY_LOSS_MULTIPLIER` | config.py | 5 | ₹ loss stops the bot for the day at 5 × `risk_inr` |
| `TAKER_FEE_PCT` | config.py | 0.055% | Used in live R maths |
| `ENTRY_SLIP_PCT` / `EXIT_SLIP_PCT` | config.py | 0.005% / 0.010% | Conservative slippage estimates |
| `WINDOW_DAYS_15M` / `WINDOW_DAYS_1H` | config.py | 30 / 20 | Rolling window lengths |
| `CAP_DAYS` | config.py | 16 | Max life of a 1h bias window |
| `book.py` params | book.py | pinned | The 15 hardened engine values — do not touch |

The one thing you **should** change in production is `risk_inr.txt`.
The things you **should not** change are `book.py` values — they are the pinned
backtest signature. All the capital-policy knobs (`LIVE_MAX_LEGS`,
`MAX_AGGREGATE_NOTIONAL`, `MARGIN_MODE`, `DAILY_LOSS_MULTIPLIER`) are **live
executor choices**, not strategy choices; changing them will not shift the
signal pattern, only the money on the exchange.

---

## 6. Does live reproduce the backtest numbers exactly?

**Short answer: signature yes, rupees roughly, tick-for-tick no.**

There are two separate ideas to keep apart:

### A. The trade list ("did we take the same 525 trades?")

This is where the engine is designed to be **exact**. Because the live code
runs the **same vendored `simulate_htf_ltf_streak_halt` function** that was
used to produce the pinned backtest numbers, on the same rolling candle
window and swing-chain logic, it reproduces the same trade list whenever the
data is the same. The two tests that already prove this:

- **Pin parity, with 1m data:** 525 trades / +538.40R / DD 28.38R — the
  research-side reference run.
- **Live-basis parity, no 1m data:** 526 trades / +537.13R / DD 29.65R. The
  `+1 trade / −1.27R` delta is the accepted cost of running on 15m+1h only
  (the research-side `exp_sl_gray_tail` test showed the wide-stop tail of
  min-qty trades skews without the 1m tick overlay).

So: **live == backtest trade-for-trade, to within the accepted 1-trade delta.**

### B. The money ("do we make the same +₹?")

This is **not** exact and is **meant** not to be. Three extra layers live only
in the executor and cannot exist in a backtest:

1. **Real fees and funding.** Taker fee 0.055%/side, funding every 8h. The
   backtest prices only the signal R, not the exchange bill. This is why the
   grey shadowlegs are excluded from the daily-loss limit — the wallet feels
   them in R but not in fees.
2. **Real slippage.** No exchange fills at the exact candle close of the
   signal bar. The 0.005%/0.010% config values are conservative stand-ins;
   real fills land somewhere around them, and the per-trade delta is
   recorded in the DB.
3. **Real coin size.** The floor-to-0.001 step and the ₹ sizing mean the
   ratio of real to gray legs depends on the current INR rate, which the
   backtest does not model at all — it assumes all signals are tradeable.

So the correct sentence is: **live trades the same list of signals as the
backtest; the ₹ P&L on the statement is the backtest R-series multiplied by
the per-trade risk, minus fees, slippage and funding.** This is what the
per-trade DB record (`slippage`, `fees`, `funding`) is there to reconcile.

---

## 7. How to test correctness (cheap → full in order)

### 1. Engine parity (already done, run from repo root, needs research data)

```bash
# Re-run the pinned numbers from the vendored engine, no edits needed.
# See live_stuff/_vendored/MANIFEST.md for the exact parity command.
```

Expected: 525 trades / +538.40R / DD 28.38R (with 1m).
Expected live basis: 526 trades / +537.13R / DD 29.65R (no 1m).

### 2. Local unit tests (already done, run from `live_stuff/`)

```bash
python testing/test_per_leg_execution.py   # old min-qty path still skipped when GRAY_MIN_QTY_ENABLED=false
python testing/test_reconcile_legs.py      # one-leg-only close, exit remainder
python testing/test_trail_isolation.py     # each leg trails on its own DB trail
python testing/test_multi_position.py      # 10 legs + aggregate notional + trigger SL
python testing/test_gray_legs.py           # gray entry, gray SL, cooldown/streak, toggle off
python testing/test_live_gray.py           # journaling, leg cap, restart restore, engine-close recovery
```

All green. The last two are the new book-107 integration tests.

### 3. Paper-money demo orders (already done, runs against a real exchange demo account)

```bash
python testing/test_real_execution_demo.py   # 1 leg, real order, SL, close
python testing/test_real_multi_leg.py        # 3 legs, one triggered SL, reconcile that leg, exit rest, flat
```

These are the ones that produce actual Bybit demo account fills. They are the
final check that ordering, sizing, SL attachment and reconciliation all behave
on the exchange, not just in memory. They ran green on 2026-10-21.

### 4. Swing-start timestamp sync verification (done, 2026-10-25)

**The procedure:** Look up a recent swing's starting timestamp from the backtest
chart (one for 15m, one for 1h). These are the first B1/B2/FLIP break timestamps
within each swing — e.g. `2026-09-26 10:00:00` (15m) and `2026-09-26 16:30:00` (1h).
The live engine backfills the full CSV from `BTC_BYBIT_DATA_DIR` up to that point,
then recomputes the swing chain with identical `compute_btc_swings` + `minBars`
(50 for 15m, 15 for 1h). The marks from that handoff point forward are then compared
against the backtest chain.

**Result (30-day window):** 2924 swings on 15m and 1441 on 1h — every swing start
(time, px, kind, direction) and every confirmed_at timestamp matches exactly between
live engine and backtest. No mismatches.

**Key point:** You cannot cold-start mid-chain. The swing engine is path-dependent —
seeding from an arbitrary Oct 24/Oct 23 timestamp produces different marks than
the backtest because the swing state from Jan 2023→that point is missing. The fix
is to backfill the **full CSV** (not a partial window), so the entire swing chain
is identical. See `backend/src/live/main.py` — `min_bars` must match backtest (50/15),
not 2.

### 5. Full restart during an open position (done, 2026-10-21)

The kill/restart test was run twice against a real Bybit demo account, with the
process hard-killed (no cleanup, exactly like a crash) after opening a real
leg, and a fresh real `LiveLoop` booted on the same DB:

- **Leg alive at boot:** the leg is fully restored from `backbencher.db`
  (qty, entry order id, SL order id intact), `_boot_sync_sl` re-checks the SL
  against the exchange (amended it to the DB value), and a clean
  `_execute_exit("cap")` closes it. Account flat at the end.
- **SL fires while the process is dead:** the SL is tightened just below the
  market before the kill, so it triggers *during* the downtime. On restart,
  boot `_reconcile_bybit_position` sees the SL executions ("SL already fired @
  82732.80 - closing DB"), closes the DB leg, and re-arms the 8-bar cooldown
  and loss streak from the recovered loss.

The one real-executor item still open is a **partial fill across restart**
(partial fill itself is handled in-memory on entry; the restart path for a
half-filled leg is not demo-tested).

---

## 8. Startup, timestamps and robustness

What happens when you turn the engine on at an arbitrary moment, not right at a
candle boundary?

**The engine is robust to that.** Here's the chain:

1. **You give (optional) seed timestamps** — the 15m and 1h start. Run:
   `python main.py "2026-09-01 00:00" "2026-09-01 00:00"`
   Both are IST, **and the timestamps mark the *first candle you want to have
   already happened*, not a hard "start here" wall.** A seed timestamp means
   "grab candles from this point onward, back-fill from the exchange, then start
   the loop from the next candle close".
2. **If the loop starts mid-candle** (say 14:32, a 15m close at 14:30 just
   passed), it waits for the **next** boundary close before generating signals.
   It does not fire on a half-formed bar. A timeout safety net exists so that a
   stalled websocket cannot hang the whole engine; an internal
   `_fire_boundary_simulation` path can push the loop forward with the last
   close if the boundary candle never arrives.
3. **The rolling window makes the start point irrelevant for correctness.** Once
   both windows are full (30 days of 15m and 20 days of 1h) the strategy sees
   the same picture no matter when you started, because the swing chain — not
   the window start — is what carries position-sensitive state. Seeding matters
   only to make sure the **swing chain has enough history** to already know
   where its levels are; without a seed the engine waits until the window is
   full on its own before it starts.
4. **The 8-bar cooldown and loss-streak counter are in the DB**, so they
   survive a restart. If a restart happens during a cooldown, the cooldown
   continues for the remaining bars only; it does not reset to 8.
5. **Boot sequence on every start.** Restore HTF windows from DB → restore any
   open legs from DB → re-attach SLs on the exchange → reconcile against Bybit
   (find the SL that already fired but we weren't looking) → reset daily loss
   counter if it's a new day → start the candle loop. Any gap during downtime
   is closed by replaying candles from the DB/seed through the engine.

**One caveat worth knowing:** the crash-recovery path only rebuilds the swing
chain from the last completed swing, not the full rolling window. If the
process was down more than a few bars, give it explicit seed timestamps on
restart (`python main.py "<15m seed>" "<1h seed>"`) to rebuild the full chain.
This is in `README.md` line ~109 as a known operational caveat.

---

## 9. One-paragraph summary

Book 107 says "buy the 15m continuation that the 1h window already opened the
door for", every 15 minutes, with an 8-bar memory, a 16-day window cap, and a
3R target. The live engine runs the same code the backtest ran, on a rolling
window, so the trade list matches the pinned backtest nearly exactly. The real
executor then sizes each signal from one rupee number (`risk_inr.txt`), places
real Bybit orders, trails stops in the DB, and keeps unsizeable min-qty signals
as "gray" shadow legs so the strategy's state machine still advances even when
the wallet cannot participate. Fees, slippage and funding are the only extra
layers live adds, and each trade's DB record is there to reconcile them against
the backtest R-series. Nothing here is guesswork or "one guess per bar" — the
same function produces both the backtest and live signals.

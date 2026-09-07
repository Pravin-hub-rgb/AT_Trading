# Swing Chain Mechanics - minBars, breaks, FS, trail (code-verified 2026-09-07)

> This is the ONE doc explaining how the swing chain actually works under the hood.
> Verified against `backend/src/firstswing.py` (FirstSwingEngine._confirm / bars_seen),
> `backend/src/btc/btc_swing.py` (compute_btc_swings stitching loop), and full-window
> 15m mb50 chain data. Read this before auditing any trade on the chart.

---

## 1. The ONE rule most people get wrong

**minBars is NOT a minimum leg length. It is a minimum cool-down between swings.**

The engine processes one swing at a time. When a swing's END extreme (its final
pivot) prints, the next engine instance starts chewing bars from that point -
and it is BLOCKED from declaring the next swing until it has processed
>= minBars bars:

```python
# firstswing.py :: _confirm
if self.bars_seen < self.min_bars:
    return                      # swing too young - confirmation BLOCKED
```

`bars_seen` counts bars since the PREVIOUS swing's end extreme (the stitching
loop in btc_swing.py re-seeds the engine at `end_pos + 1`).

**The verified invariant:**

> next swing's FS can print no earlier than minBars bars after the PREVIOUS
> swing's end pivot.

**The drawn zigzag segment (start extreme -> end extreme) can be ANY length:**
3 bars, 11 bars, 87 bars - 50 of the first 60 mb50 legs are shorter than 50
bars, and that is normal. The start extreme is picked retroactively: it is the
best high/low formed since the previous leg ended, wherever in the cool-down
window it happened.

## 2. minBars per chain (where the numbers live)

| Chain | minBars | Real-time cool-down | Used for |
|---|---|---|---|
| 15m LTF book | **50** | 12.5 hours | 15m B2/FLIP entries AND swing trail ("Decisive Trail 50" - the 50 in the name IS this knob) |
| 1h HTF book | **20** | 20 hours | 1h Flip entries (Book A). Fixed 3R exit - the trail never runs here, but minBars still defines which swings/flip-breaks exist |
| 5m LTF book | **14** | 3.5 hours | 5m decisive entries (htf_ltf=5m) |
| Chart overlay (no strategy) | UI setting, default 14 | - | display only - used by NOTHING in any strategy |

Sweeps: mb50 beat mb30/mb14 on 15m net R; mb20 beat 14/30/50 on 1h.

## 3. Breaks vs confirmation - the two event types

| Event | When | What it does |
|---|---|---|
| **B1 / B2 / FLIP** | DURING the leg, in real time - breaking a pivot that already exists (no future knowledge) | ENTRIES. B2/FLIP of the swing = the trade (one-swing-one-trade: first tradeable mark per swing wins) |
| **FS / SUS (confirmation)** | >= minBars bars after the previous swing's end pivot | Arms the TRAIL: the confirmed swing's start pivot becomes a trail level for same-direction trades (ratchet-only, touchable) |

So: **entries happen BEFORE confirmation, often dozens of bars before FS.**
minBars never gates entries - it gates when swings become official (which
controls future entries and trail pivots).

Live bar-by-bar state machine (no lookahead anywhere):

```
bar closes -> 1) pivot break?  -> maybe ENTER (B2/FLIP, own swing SL)
              2) leg >= minBars old + trigger? -> FS prints -> its start
                 pivot arms as trail level (fine path: armed next bar)
              3) price hit SL/trail? -> exit
```

Proof of live-faithfulness: "stream" entry selection mirrors marks-fired-so-far
(btc_engine.py _collect_signals docstring); trail arms at confirmed_at_idx+1;
walker parity test (commit 94cf573) replays bar-by-bar vs batch.

## 4. Verified examples (15m mb50, full window)

Invariant check (previous END pivot -> next FS, all >= 50 bars):

| Previous leg END pivot | Next FS | Gap | Next leg drawn span |
|---|---|---|---|
| 01-08 23:00 | 01-09 11:45 | 51 bars | 06:45 -> 07:30 = 3 bars |
| 01-10 15:15 | 01-11 03:45 | 50 bars | 20:30 -> 23:15 = 11 bars |
| 01-08 01:45 | 01-08 14:15 | 50 bars | 06:15 -> 12:30 = 25 bars |
| 01-13 06:00 | 01-13 18:30 | 50 bars | 06:15 -> 18:00 = 47 bars |

Short drawn legs (3, 11 bars) are NORMAL. What can never happen: two swings
confirming within minBars bars of each other's end pivots.

## 5. Case files (the trades we audited)

**13 Jan 2025 12:00 SHORT -1.0R (swing #28, down, start 06:15 @ 95782.4):**
B1 08:00, B2 12:00 -> entry @ 93861.82, SL = 95782.42 (swing start).
FS only at 18:30 (50 bars after 06:15). The 13:00 high (93947) is NOT a pivot
in mb50 (it is a wiggle inside the 06:15 leg - mb14 chart shows it, mb50 does
not). No trail ratchet possible -> SL never moved -> stopped 14 Jan 14:22.
NOT a bug: the mb14 chart overlay was showing a chain the strategy never uses.

**11 Jan 2025 05:45 SHORT -0.39R (swing #22, down, start 10 Jan 23:30 @ 95793.0):**
B1 00:30, B2 05:45 -> entry. FS 11:45. Trail DID ratchet here (a later sealed
pivot) -> soft exit -0.39R instead of -1R. The B2 was invisible on the chart
because the swing was born 23:30 the previous night on the mb50 chain.

**16 Jan 2025 22:45 LONG +1.13R (swing #36, up, start 20:45 @ 97741.1):**
B1 22:00, B2 22:45 -> entry @ 99868.92. FS 17 Jan 20:00. Invisible on mb14
chart for the same reason.

**Chain-count proof: 187/187 v3 LTF entries have their B2/FLIP mark on the
mb50 chain; only 160/187 on the mb14 chain. mb50 = 2212 B2/FLIP marks total,
mb14 = 3535.**

### 5b. Case file: swing #39 (18-19 Jan) - the minBars gate can shift FS by a bar

UP leg born 13:45 @ 102336, end extreme 21:15 @ 104988.88. The opposing break
fired on the 01:45 bar (low 103808.14 - crossed the whole cluster of pivot lows
103961 / 104004 / 104080 / 104116 / 104335 / 104340) - but that was bar #49 since
tracking began (previous swing END 13:30). Gate-blocked. First ungated bar =
02:00 (bar #50), condition still true -> FS stamped at 02:00, an INSIDE candle
that broke nothing itself.

**Audit rule of thumb: if FS sits on a do-nothing candle, the real break is
usually the previous bar - the one the 50-bar gate blocked.**

**FIX 2026-09-07 (engine, additive):** `fs_at_idx/fs_at_time` now stamp the
COMPLETING break - the transition into the chop cross (01:45 here) - tracked
via `last_chop_cross_idx` in SwingEngine (first cross can be stale: gate-
blocked pre-extreme, swing then extended). `confirmed_at_time` stays the legal
declaration (02:00; trail arming unchanged). 235 of 1304 markers moved, 0
trade numbers changed (v1 204/+165.50, v3 187/+175.93 base re-verified).
FS marks by at most a couple of bars and only affects trail arming / future
entries - never the trades already running.

### 5c. Case file: B1 arming (18 Jan 13:45 -> 17:00)

The 14:15 / 14:30 / 14:45 tops breaking each other (14:30 an inside candle,
14:45 a wide-range breaker) marked NOTHING: B1 = first break of the ARMED level
(the sealed structure pivot), and no pivot had sealed yet - the walker was
still building the leg (same-bar arm guard: no phantom B1). First seal = the
14:45 high (103455.89); price chopped under it ~2h (the 15:00 high missed the
level by 0.71) -> B1 at 17:00 breaking 103455.89, B2 at 17:45 (B2-only
1-candle gap rule b2_gap_bars=1 - B1 has no gap rule, it is defined by arming
order). Micro-top breaks inside a newborn leg are the leg constructing itself,
not tradeable breaks - chosen behavior, all backtest numbers include it.

## 6. HTF-LTF v3 gate (while we are here)

15m entries allowed while the 1h trade is unrealized in **[-1R, +1.5R]**.
Underwater is NOT blocked - the -1..0R bucket was the second-best (PF 2.49):
a pullback inside the window = better prices with structure still intact (the
1h swing SL not yet hit). Blocked only above +1.5R (the PF 0.02 zone). Window
closes when the 1h trade exits (SL / 3R / 16d cap). Numbers: v3 = 187tr 32.6%
+139.95 net PF 2.47 maxDD 13.15R vs v1 204tr +127.49 PF 2.25 DD 17.52R.
Combined book (1h + 15m): v3 +197.71R net, maxDD 22.75R, net/DD 8.69 (best at
full size - no downsizing needed).

## 7. Chart auditing rules

1. The chart swing overlay auto-syncs to the strategy chain when HTF-LTF is on
   (badge `overlay: strategy chain (mb50)` next to the selector): 15m chart =
   mb50, 5m = mb14, 1h = mb20. Master presets fetch their own minBars.
2. Trade boxes snap by timestamp - entry edge = signal-bar close on finer
   charts (entry_ts + 900s for 15m / +300s for 5m); exit edge = the exact 1m
   fill bar (exit_ts comes from the 1m fine walk).
3. To see Jan-2025 trades set limit high (All) - the window tail only covers
   recent bars.
4. Expect the mb50 zigzag to have FEWER, LONGER legs than mb14 - and short
   segments (< 50 bars) are normal per section 1.
5. If a trail exit looks like it gave back "too much": the trail level is the
   last FS-CONFIRMED same-direction swing's start pivot, not the freshest
   eyeball low/high. Unconfirmed pivots do not protect.

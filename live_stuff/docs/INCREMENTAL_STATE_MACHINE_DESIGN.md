# Incremental State Machine Design (Book 107)

**Status:** Design only. Implementation pending (Phase 1).
**Path:** `live_stuff/docs/INCREMENTAL_STATE_MACHINE_DESIGN.md`
**Goal:** Replace the unbounded-history batch sim (`simulate_htf_ltf_streak_halt` over all
candles/swings, ~5s at 3.8yr) with an O(1)-per-bar event-driven state machine.
**Parity gate:** new engine's trade list must be byte-identical to the batch sim's on
full IS (2023-01..2026-09) and OOS (2021-01..2022-12) history.

---

## 1. Why

`_run_v18_simulation` re-runs the walker + pivot + sim from the seed bar on every
15m close. Cost grows with history (0.07s @ 30d, 1.2s @ 1yr, ~5.0s @ 3.8yr).
It blocks the event loop and delays live entries. `all_candles_*` also grows
unbounded. Trimming breaks `g_idx` counters and the sim walk.

The fix: stop storing history. React to swing/marks as events. Keep only the
rolling state the engine actually needs.

---

## 2. Core principle (user-confirmed)

- HTF only **opens a window** per regime (flip / decisive / b2). Track per window:
  entry price, SL (-1R / ext_stop), start ts, end ts (exit or 16d cap).
  Multiple windows can be open in parallel (flip & b2).
- LTF keeps only **previous completed swing + current forming swing**. When FS
  completes the forming swing, it becomes `prev`; the new engine feeds from
  `prev.end_idx + 1` (the end extreme), NOT the FS bar. FS is the completion
  trigger only.
- On entry: SL = entry ∓ 1R. Trail on each completed swing in trade direction
  to the swing's **confirmed pivot** (Book 107 / v18 rule).
- Multiple legs: each new forming swing that fires can open a new leg
  (`max_positions=0`); all legs share the HTF window; each trails independently.

---

## 3. Data structure: `LiveEngineState`

```
LiveEngineState
├── swing_15m, swing_1h : PersistentSwingEngine   (already persists to DB)
├── prev_swing_15m, cur_swing_15m                 (LTF rolling pair)
├── prev_swing_1h, cur_swing_1h                   (HTF rolling pair)
├── open_ltf_legs : list[Leg]                     # entry_ts, dir, entry_px,
│                                                  # sl_initial, sl_current,
│                                                  # cap_ts, swing_no,
│                                                  # htf_regime, is_gray
├── open_htf_windows : {regime -> Window}          # entry_px, sl, start_ts,
│                                                  # end_ts, dir
├── gates: cooldown_remaining (8), consecutive_losses (0),
│          halt_skip_next (False), daily_pnl_r, daily_halted,
│          last_trade_date, last_loss_bar_ts, busy_until_ts
└── rolling: atr_15m[14], last_closed_1h_chop
```

No `all_candles_*` arrays. ATR/chop use a 14-bar ring buffer. Swings come
from the already-persistent `PersistentSwingEngine`. No full history stored.

---

## 4. Event processing (O(1) per bar)

### On each 15m bar close
1. Feed candle to `swing_15m` → may emit a new mark on `cur_swing` (B1/B2/FLIP)
   or a declaration (FS) completing it.
2. **New mark (B2/FLIP):** run LTF entry gate:
   - pre-FS: `prev_swing.confirmed_at_ts <= mark ts`
   - regime from containing 1h bar (chop flip/b2)
   - HTF window direction matches signal
   - cooldown (8 bars), ext_stop (3R), daily halt (n/a, max_consecutive_losses=0)
   If pass → open LTF leg (entry price, SL=entry∓1R, cap_ts=entry+16d).
3. **Declaration (FS):** finalize `cur_swing` → `prev_swing`; start new forming
   swing (`_new_engine`, feeds from `end_idx+1`). If open legs exist in matching
   direction → trail SL to the completed swing's confirmed pivot (v18 rule).
4. For each open LTF leg: evaluate SL/TP/cap against this bar's OHLC; close if
   hit → update cooldown/streak/daily pnl.
5. Decrement cooldown; reset daily on date change.

### On each 1h bar close
1. Feed to `swing_1h` → HTF marks/declarations.
2. HTF entries: open HTF trade → open HTF window for that regime.
3. HTF exits: close HTF trade → close HTF window.
4. Update regime (chop) from completed 1h bar; update HTF window current_r.

---

## 5. Persistence / crash recovery

Swing engine already persists to DB. Add minimal state saves: gates + open legs
(already in `trading_state` + `trade_store`). On boot, reload state and resume —
no history replay needed.

---

## 6. Phases

1. **Offline parity (build + test on full history first).** Build state machine
   behind a flag; run over full IS (2023-01..2026-09) and OOS (2021-01..2022-12);
   compare trade list to batch sim via `parity.py`. Gate: 0 diffs.
   Sub-step (low-risk, parallel): offload `_run_v18_simulation` to
   `asyncio.to_thread` to remove the 5s stall.
2. **Shadow (live, side-by-side).** Run new engine alongside batch sim in live;
   log diffs; N days with 0 diffs.
3. **Cutover.** Switch live path to state machine; remove batch sim from live.

Trailing = Book 107's v18 confirmed-pivot trailing (matched exactly).

---

## 7. Swing-start correction (recorded)

New swing feeds from `prev_swing.end_idx + 1` (the end extreme), not the FS bar.
FS completes the swing but does not reset the feed cursor. See
`persistent_swing.py` lines 247-254 (`new_start = self.eng.end_idx + 1`).

---

## 8. Open questions

- Trailing pivot: v18 confirmed pivot (matched). Flagged for chart verification.
- HTF `window_end`: keep "exit" (Book 107 pin) for parity.
- Shadow duration: 5-7 days with 0 diffs before cutover.

---

## 9. References

- `live/_vendored/persistent_swing.py` (swing production + persistence)
- `live/_vendored/btc_engine.py` (`_collect_signals`, `_trail_events_ts`)
- `live/_vendored/unified.py` (`simulate_htf_ltf_streak_halt`, `to_intervals`)
- `live/htf_windows.py`, `live/htf_tracker.py`
- `live/incremental.py`, `live/incremental_engine.py` (existing scaffolding)
- `live/parity.py` (trade-list diff)
- `live/book.py` (Book 107 params)
- `.kilo/plans/1792658668907-rolling-window-data-loss-plan.md`
- `live_stuff/docs/INCREMENTAL_REFACTOR_PLAN.md`

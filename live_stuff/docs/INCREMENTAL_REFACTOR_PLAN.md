# Incremental O(1) Sim Refactor — Plan (P1b done, C–E pending)

## Goal
Replace the unbounded-history batch sim (`simulate_htf_ltf_streak_halt` over all
candles/swings) with an incremental O(1)-per-candle update, gated on strict
parity: the incremental sim's trade list must exactly match the batch sim's
trade list on identical history (verified by `parity.py`).

## Why
- `all_candles_15m`/`all_candles_1h` grow forever; sim cost grows with history
  (30d 0.07s → 5yr 6.5s) and runs on every 15m close.
- Trimming breaks swing `g_idx` counters and the sim walk.
- P1b double-fire at 1h boundary was a real-money risk.

## Status
- [x] P1b idempotency guard at 1h boundary (`live/loop.py`): `_last_boundary_fired_ts`,
      stale-barrier cancel in non-boundary paths, direct-run when the other side
      moved past. Tests: `tests/test_p1b_boundary.py`.
- [x] Parity oracle harness: `live_stuff/parity.py` (`run_parity`, `trade_list_diff`).
- [x] Step A — bounded sim input retention (`live/retention.py`): `trim_candles_and_swings`
  re-indexes swings, validated by `tests/test_retention_parity.py`.
- [~] Step C — incremental driver scaffolding (`live/incremental.py`): `SimState` + `IncrementalSim.on_bar` with
  idempotency key + parity tests (`tests/test_incremental_parity.py`). Engine body still delegates to the
  batch oracle on the retained window; true O(1) rewrite remains pending parity history (Step D).
- [x] Step D — parity oracle run (offline replay): UNBLOCKED. History located at
  `C:/Users/Pravin/Desktop/main/btc_data/{is,oos}/BTCUSDT_{15m,1h}.csv`
  (IS: 133,747 15m bars 2023-01-01→2026-09-13; OOS: 2021-01-01→2022-12-31).
  Validated on real IS data (last 2000/4000 15m bars):
    - IncrementalSim.on_bar trade list byte-identical to direct batch sim (2/2 and 7/7 trades).
    - Idempotency: second identical call reports changed=False.
    - Retention (14-day trim): trades inside retained window match (1/1).
  Full-IS baseline (empty fine_ltf): 133,747 15m bars / 33,437 1h bars -> 529 trades,
    sim elapsed 5.59s; retention (90d) reduces input to ~8,640 bars (~0.2s).
  Guarded by `tests/test_real_data_parity.py` (skips when btc_data absent).
   - Retention fix (bulk swing removal): `trim_candles_and_swings` now pulls the
     calendar cutoff back to cover any retained swing that straddles it, so no
     retained swing keeps a negative `seg.start_idx` (which previously clamped
     the SL slice start to 0 and could corrupt the stop for that swing). Swings
     ending before the cutoff are still dropped in bulk. Verified: 0 mismatches
     on break-mark kinds (B1/B2/FLIP) and confirmed timestamps between full and
     trimmed chains on real IS data; all retained swings have start_idx >= 0.
   - IncrementalSim signature now also includes break-mark counts so a changed
     mark (without count change) cannot slip past the skip gate.
- [ ] Step E — cutover + split `loop.py`.

## Step C design (NOT yet implemented)

State to maintain per regime (flip / b2 / decisive), updated per new 15m bar:
- `htf_window_open`, `htf_window_dir`, `htf_window_start_ts`, `htf_entry_px`,
  `htf_sl`, `htf_hrisk`, `htf_current_r` (rolling R from live price).
- Open LTF trades: list of `{entry_ts, dir, sl, target, swing_no, htf_regime,
  cap_ts, status}`; on each bar, evaluate SL/TP against bar OHLC, close if hit.
- Cooldown counter (bars remaining), consecutive-loss streak, daily P&L R,
  daily-halted flag, last trade date.
- Swing chain: append-only `all_swings_*` (already unbounded-safe? swings grow
  slowly; cap via swing-aware retention if needed in a later pass).

Per-bar update (O(1) amortised):
1. Append new 15m candle to `all_candles_15m` (bounded ring of N bars for
   ATR/chop lookback; full store remains in DB).
2. Feed candle to `PersistentSwingEngine.process_bar` → maybe new swing/breaks.
   Append breaks to swing chain.
3. If a 1h candle closed this bar, feed to 1h swing engine.
4. HTF window tracker: detect new HTF flips from the 1h swing chain; open/close
   windows; persist via `open_htf_window`/`close_htf_window`.
5. LTF entry detection: walk the 15m swing chain for new B1/B2/FLIP marks not
   yet consumed; apply regime gate (chop, ext_stop, cooldown, daily halt); on
   pass, open LTF trade (DB + live order) exactly as `_journal_trades` does.
6. LTF exit evaluation: for each open trade, check SL/TP against this bar.
7. Update rolling R, chop (from latest closed 1h), ATR.

Parity gate: run `parity.run_parity` comparing incremental trade list vs batch
sim trade list on the same history window. Must be byte-identical (entry_ts,
dir, outcome, r_multiple, exit_ts, exit_price, entry_price, sl, target).

## Idempotency / safety
- Every state mutation must be re-derivable from DB + candles (crash recovery).
- `_journal_trades` already dedups by (entry_ts, dir); reuse that key.
- `close_ltf_trade` returns 0 if already closed (C4 guard); reuse.
- New entries must go through the same stale-entry / daily-halt / position-limit
  gates as today.

## Shadow run
- Offline replay of 3–6 months of history through both sims → parity check.
- Then 2–3 day live run with incremental sim in shadow (batch sim still
  authoritative) before cutover.

## Out of scope (this pass)
- Full incremental rewrite (Step C) — requires parity oracle green first.
- Splitting `loop.py` (Step E) — after cutover.
- Performance benchmarking numbers (measure after implementation).

## Files touched this pass
- `live/loop.py` (P1b guard)
- `live/parity.py` (new oracle harness)
- `tests/test_p1b_boundary.py` (new)
- `tests/test_candle_dedupe.py` (added `_last_boundary_fired_ts` init)
- `docs/INCREMENTAL_REFACTOR_PLAN.md` (this file)

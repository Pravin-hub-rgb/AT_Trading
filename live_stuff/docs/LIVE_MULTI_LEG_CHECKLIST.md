# Book 107 — Live Multi-Leg Execution Checklist

Status: paper multi-position is implemented and tested. Live per-leg wiring is implemented;
fake-trader entry/exit/reconcile and Bybit adapter v2 tests pass.
Phase 0 core mechanics passed on Bybit demo (3 legs, per-leg partial SL, amend, trigger, 10+ legs, exit sequencing).
Still pending: real demo partial-fill across restart, paper forward parity sample, gray restore with real legs.
No production live changes until Phase 0–6 are checked.

## Definitions (locked before coding)

- **CONFIRMED: 1R = |entry price − SL price|.** This is price risk only. Costs are NOT inside R.
- **$5/R means $5 gross price risk at the stop.** Fees, slippage and funding are deducted after the trade, exactly as the backtest does it.
- Backtest net R = gross R − fee_R − slippage_R − funding_R.
- Book 107 pin: gross +640.01R, fees+slip −72.31R, funding ≈ −29.3R, net **+538.40R** over 525 trades.
- Current live `_calculate_qty()` adds `fee_buffer` to the stop distance:
  `qty = risk / (stop_distance + fee_buffer)`.
  That makes **$5 the all-in loss**, not 1R price risk, and does not match the backtest. For exact 107 this must become `qty = risk / stop_distance`, with costs tracked separately.
- Consequence: at the median 1.2628% stop, all-in loss is about 1.10R; at the 0.0811% stop, all-in loss is about 2.54R. That is already inside the 538.40R net pin. Do not shrink qty to force all-in risk back to $5.

## Actual SL distribution (525 trades, pin basis)

| Stop % bucket | Trades | Notional at $5/R |
|---|---:|---:|
| 0.081–0.10% | 1 | $6,165.56 |
| 0.10–0.20% | 3 | $3,311–$3,919 |
| 0.20–0.30% | 13 | $1,677–$2,459 |
| 0.30–0.50% | 56 | $1,014–$1,605 |
| 0.50–1.00% | 125 | $501–$966 |
| 1.00–1.50% | 109 | $333–$495 |
| 1.50–2.00% | 76 | $251–$332 |
| 2.00–3.00% | 85 | $168–$248 |
| 3.00–5.00% | 48 | $102–$166 |
| 5.00–7.00% | 6 | $72–$100 |
| 7.00–9.17% | 3 | $54–$71 |

Percentiles:

- Stop %: min 0.0811, p1 0.2196, p5 0.3560, p10 0.4301, p25 0.7561, p50 1.2628, p75 2.1351, p90 3.0441, p95 4.0543, p99 5.7305, max 9.1676.
- Notional at $5: min $54.54, p1 $87.44, p5 $123.34, p10 $164.25, p25 $234.18, p50 $395.96, p75 $661.30, p90 $1,162.54, p95 $1,404.52, p99 $2,277.28, max $6,165.56.
- Notional range is **113×**. A fixed per-trade capital number is therefore wrong.
- **Risk is fixed at 1R; capital is not.** Size the account to the worst aggregate exposure and enforce a dynamic pre-entry notional/margin guard.

Aggregate exposure (all open legs, time-weighted):

- max aggregate notional **$6,165.56** at 2023-08-15 05:30 IST (the 0.0811% stop trade, alone).
- p90 $1,205.09, p95 $1,750.27, p99 $2,895.21, p99.9 $5,855.89.
- Max initial margin: 3x $2,055.19 ≈ ₹1.96 lakh; 5x $1,233.11 ≈ ₹1.18 lakh.
- Observed max + 28.38R DD reserve + 30% buffer: 3x ≈ ₹2.73 lakh; 5x ≈ ₹1.71 lakh.
- 2× stress case (two 0.08% stops open together): $12,331.12 notional; 3x margin $4,110.37; +DD +30% ≈ ₹5.28 lakh. 5x ≈ ₹3.24 lakh.
- Capital policy must therefore be one of:
  - [ ] Reserve for observed max ($6.2k notional / ~₹2.73L at 3x) and reject entries above an aggregate notional cap.
  - [ ] Reserve for 2× stress (~₹5.28L at 3x) so two tight-stop legs can coexist.
  - [ ] Cap per-leg notional (e.g. $1.6k) — changes 1R or skips trades.
  - [ ] Impose a 0.3% stop floor — changes the strategy (508 trades, not exact 107).
  - [ ] Run $10/R — exact 1R, doubles notional, fixes min-qty feasibility, ~₹5.5L at 3x.

## Phase 0 — Bybit demo spike (blocking)

- [x] Enter 3 legs with `tpslMode="Partial"` and SL only. **retCode 0.**
- [x] Confirm each entry creates its own partial SL with the correct qty. **3/3, qty 0.001 each, `stopOrderType=PartialStopLoss`, `reduceOnly=true`, `closeOnTrigger=true`.**
- [x] Capture entry order IDs, attached SL order IDs, `stopOrderType`, `parentOrderLinkId`. **Parent link matches each entry; attached SL `orderLinkId` is blank.**
- [x] Trigger one SL; confirm only that leg's qty closes. **Position 0.003 → 0.002; one partial SL removed.**
- [x] Trail one leg: test `set_trading_stop(Partial)` (expected: add-only), then `amend`, then cancel+recreate. **`amend_order(orderId, triggerPrice)` retCode 0 and moved the existing SL in place. `set_trading_stop(Partial)` retCode 0 but ADDED a new unlinked `PartialStopLoss`; it does not modify.**
- [x] Measure the unprotected window in cancel+recreate. **Not needed when amend succeeds; amend is in-place. Fallback cancel+recreate still has an unprotected window.**
- [x] Scale to 10 legs; verify whether the limit is 10 conditional orders or 20 TP/SL orders. **11 simultaneous partial SL orders accepted. 10-leg cap is safe; no evidence of the 10-conditional limit applying to partial TP/SL.**
- [ ] Test partial entry fill; attached SL qty must equal filled qty.
- [x] Restart; verify DB legs, exchange position sum, open SL orders, orphan qty. **Real demo: DB restore with 1 open leg, reconcile kept it, boot sync OK (`test_real_execution_demo.py`); 3/10-leg reconcile matched stops and only the triggered leg closed (`test_real_multi_leg.py`).**
- [x] Record exact retCodes for every failure path. **See Phase 0 findings below.**

### Phase 0 findings (demo, 2026-10-20)

- Entry with `tpslMode="Partial"` + `stopLoss` only: `retCode 0`; entry order ID returned; attached SL order ID discoverable through `get_open_orders(orderFilter="StopOrder")`.
- `amend_order(orderId=partial_sl_id, triggerPrice=...)`: `retCode 0`; same SL order ID and parent link retained. **Use amend for trail; do not add another SL.**
- `set_trading_stop(Partial)`: `retCode 0`; adds a separate partial SL with blank `parentOrderLinkId`. **Never use for modifying an existing leg.**
- 11th entry/partial SL: `retCode 0`; 11 open partial SLs. Cap 10 is safe.
- Reduce-only market close of 0.001 while three partial SLs exist: `retCode 0`; position 0.003 → 0.002; **all three SLs remain**, including the closed leg's SL. Orphan SL can later close another leg.
- Correct exit sequence: **cancel that leg's SL by `orderId` (`retCode 0`), verify it is gone, then reduce-only close that leg's qty.** Other SLs remain.
- `close_position_retry()` bug found and fixed: it reused the long position's SL on the Sell close order, which Bybit rejects (`StopLoss ... set for Sell position should greater base_price`). Close orders are now `reduceOnly=True` with no attached SL; a panic SL is added only when no protective stop exists.
- `set_trading_stop(Partial)` with `slSize="0.001"` can create an unlinked SL; if ever used, it must be discovered and adopted by qty/trigger.
- Demo cleanup: cancel all orders → close reduce-only; final position flat, zero open orders.

## Phase 1 — DB schema

- [x] Add `entry_order_id`, `entry_order_link_id`, `entry_fill_price`.
- [x] Add `sl_order_id`, `sl_order_link_id`, `sl_order_status`.
- [x] Add `exchange_state`, `exit_order_id`, `exit_fill_price`.
- [x] Add `fee_paid`, `funding_paid`, `last_sync_ts`.
- [x] Add idempotent migrations in `persistence/database.py`.
- [x] Add trade-store helpers for per-leg order state and actual fills.
- [x] Keep `qty` as actual filled leg qty.

## Phase 2 — Bybit adapter

- [x] Add `place_entry_with_partial_sl()` using `tpslMode="Partial"`, `stopLoss`, `slOrderType="Market"`, no TP. **Bybit adapter v2 test: attached partial SL, qty 0.001.**
- [x] Add `get_order_fill(link_id)` using order history/executions; never aggregate position size.
- [x] Add `get_open_stop_orders()` with `orderFilter="StopOrder"`; identify `PartialStopLoss`. **Active statuses only (New/Untriggered/PartiallyFilled/Triggered), so a just-filled stop cannot keep blocking reconcile.**
- [x] Add `cancel_order_by_id()`. **Demo verified.**
- [x] Add `place_partial_sl()` fallback. **Bybit adapter v2 test.**
- [x] Add `amend_partial_sl()` only if demo proves it works. **Demo verified: `amend_order` moves partial SL in place with retCode 0.**
- [x] Add `close_reduce_only(qty)`. **Demo verified. Cancel leg SL first.**
- [x] Add `get_order_executions(order_id)` for triggered partial-SL fills. **Bybit adapter v2 test: entry exec qty/price/fee; untriggered SL returns [].**
- [x] Add `get_order_by_id(order_id)` to resolve a stale close order.
- [x] Replace `update_sl()` live usage with per-leg `_sync_leg_sl()`; `update_sl()` remains only as a compatibility method.
- [x] Rewrite `verify_entry_order()` order-first; current position-first logic returns aggregate size.

## Phase 3 — Execution / trading / reconciliation

- [x] `_execute_entry`: place entry with attached partial SL; use the order fill, not `get_position()["size"]`. **Fake-trader test passed; stores entry order id, link id, fill px, fee, qty.**
- [x] `_execute_exit(trade)`: check that leg's SL status first; if triggered, reconcile; else **cancel that leg's SL, verify gone, then reduce-only close that leg's qty**. **Fake-trader tests: normal exit and exchange-triggered SL both passed.**
- [x] Never call `close_position_retry()` for a leg. Manual close without canceling the leg SL leaves an orphan stop that can close another leg.
- [x] `_trail_trade_sl`: update DB, then sync only that leg's SL; removed the `len(...)==1` guard.
- [x] `_reconcile_bybit_position`: compare sum of leg qty with exchange position; match open partial SLs; re-place missing SLs; reconcile triggered legs. **Fake-trader tests passed (both open, one SL fired, missing SL re-place, flat, orphan). Real demo rerun exposed a transient `Filled` stop in the open-stop query; reconcile now detects a triggered leg from its actual executions, not just the open-order snapshot.**
- [x] Never full-close on a multi-leg mismatch unless intentionally flattening. **Emergency entry close is capped to this leg's qty minus other open legs; if the leg is already flat, no close is sent.**
- [x] `_execute_entry` returns True only after the attached SL is confirmed; failures keep the DB leg open for reconcile if emergency close cannot be confirmed.
- [x] Reconciled/SL-triggered closes update daily-loss and streak state; R uses actual entry fill, not the signal price.
- [x] `_boot_sync_sl`: syncs every leg, amend-only (never places a new stop; reconcile owns repairs).
- [x] `_at_position_limit`: live cap `LIVE_MAX_LEGS` (10), not 1.
- [x] Per-leg exit serialization: tick and candle callbacks run synchronously on the single asyncio loop, so no two exit paths interleave; each exit re-reads its leg qty/position before closing.
- [x] Min-qty entries become internal gray shadow legs: `exchange_state="gray"`, `qty=0`, no entry/SL/TP order, shadow trail and tick SL/cap exits in DB only. The engine's own close is also used as a recovery/parity path for open shadows. Gray occupies a live leg slot, updates cooldown/streak, and is excluded from exchange reconcile, fees/funding, aggregate notional, and daily live-risk. Toggle: `GRAY_MIN_QTY_ENABLED`.

## Phase 4 — Sizing, margin and costs

- [x] Change `_calculate_qty()` to exact 1R: `qty = risk_usdt / stop_distance`.
- [ ] Move fee/slippage/funding to the cost ledger, not the denominator. **Fees recorded per entry/exit fill; funding feed still missing.**
- [x] Fix min-qty rounding: floor and reject; never force up to exchange min. **`min_qty` rejects now become gray shadows when enabled; `min_notional`, balance-sized min-qty, leverage and invalid-stop rejects still skip.**
- [x] Add aggregate notional/margin guard before entry; per-leg balance check is not enough.
- [x] Add `LIVE_MAX_LEGS` and `MAX_AGGREGATE_NOTIONAL` config.
- [ ] Track actual fees from orders and funding from transaction log. **Order fees done; funding not.**
- [ ] Add funding cost to live net R.
- [x] Record skipped trades and reasons (min qty, aggregate cap, halted). **Gray records the original reason and marks `exchange_state="gray"`.**

## Phase 5 — Tests

- [x] Fake-trader: two entries; SL-1 exits while SL-2 stays. **`test_reconcile_legs.py`.**
- [x] Fake-trader: trail leg 2 does not touch leg 1. **`test_trail_isolation.py`: leg-1 SL stays 95, leg-2 amends to 97.**
- [x] Fake-trader: restart/reconcile with multiple legs. **`test_reconcile_legs.py` (both open, one SL fired, missing SL replaced, exchange flat, orphan).**
- [x] Fake-trader: aggregate margin cap rejects the right entry. **`test_per_leg_execution.py`.**
- [x] Fake-trader: min-qty rejection and qty-step rounding. **`test_per_leg_execution.py` with gray disabled: qty 0 rejected, no order. `test_gray_legs.py`: min-qty opens gray, no exchange calls.**
- [x] Fake-trader: gray lifecycle. **`test_gray_legs.py`: tick SL closes with zero fees, cooldown 8 and streak 1, daily P&L untouched; trail is DB-only; flat reconcile keeps gray and closes real legs; toggle off restores `stale_skip`. LiveLoop integration covers journaling, cap occupancy, restart restore, and no duplicate journaling.**
- [x] Demo integration: 3 and 10 legs, one trigger, restart restore, exit the rest. **`test_real_multi_leg.py`: 3 legs and 10 legs (10 entries/10 stops at risk INR 800) -> leg-2 stop filled -> reconcile closed only that leg -> remaining legs exited; total flat, 0 stops. `test_real_execution_demo.py`: DB restore with open leg -> reconcile keeps it.**
- [x] Demo integration: hard-kill process restart with a real leg. **Two-phase test killed with `Stop-Process -Force` (no cleanup) after a real entry, then a fresh real `LiveLoop` booted on the same DB. Scenario 1: leg alive at boot -> `[ltf] Restored 1 open trade(s)`, `_boot_sync_sl` amended the exchange SL to the DB value, clean `_execute_exit("cap")`, account flat. Scenario 2: SL tightened to `cur - 2.0` before the kill -> it fired while the process was dead -> boot `_reconcile_bybit_position` found the SL executions ("SL already fired @ 82732.80 - closing DB"), closed the leg, re-armed cooldown 8 and streak.** **(`test_real_kill_open.py` + `test_real_kill_restore.py`.)** Real partial fill across restart still open.
- [ ] Demo/restart: gray restore with real legs, cap interaction, and forward shadow parity. **Fake coverage only.**
- [x] Paper regression: existing multi-position test passes. **`test_multi_position.py` updated for cap 10.**
- [ ] Live-data smoke still passes.
- [ ] Paper forward sample logs skipped/executed legs for parity.

## Phase 6 — Go-live gate

- [ ] Demo spike report attached.
- [ ] All 525 backtest trades reproducible in paper on live basis.
- [ ] Capital policy chosen and documented.
- [ ] Confirm live risk amount: `risk_inr.txt` is currently 250 INR (~$2.94 at INR 85), not the $5/R used in the capital/SL analysis; demo multi-leg tests monkeypatched 500/800 INR for sizing.
- [ ] Aggregate margin guard tested with 10 legs.
- [x] Restart/reconcile tested with an exchange-triggered SL. **Hard-kill restart scenario 2 (2026-10-21): boot reconcile closed the leg from the real SL executions.**
- [ ] No production live until forward evidence clears the gate.

## Open decisions

- [x] **1R = $5 price risk. Costs are separate.** Confirmed.
- [x] **Exact 107 selected.** No 0.3% stop floor; no `$10/R`.
- [ ] Confirm capital policy: observed max vs 2× stress vs hard notional cap.
- [x] **Live leg cap = 10.** Demo accepted 11 partial SLs.
- [x] **Gray trigger = `min_qty` only.** Gray has no exchange order, fee/funding, margin, or daily-limit impact; it counts toward the live leg cap and updates cooldown/streak. Do not gray `min_notional`, balance-sized min-qty, leverage, or invalid-stop rejects.
- [ ] Confirm one account, no sub-accounts.

## Critical code references

- `bybit_order.py` — `update_sl()` still uses `tpslMode="Full"` but is no longer called by live execution.
- `live/execution.py` — `_execute_entry()` records per-leg fills; `_execute_exit()` cancels the leg SL then reduce-only closes.
- `live/execution.py` — `_reconcile_bybit_position()` reconciles all legs; `_boot_sync_sl()` amends every leg.
- `live/execution.py` — `_size_entry()` exact 1R, floor/reject, margin-based balance cap; `_open_gray_leg()` shadow entry.
- `live/trading.py` — `_trail_trade_sl()` calls `_sync_leg_sl()` per leg; no single-leg guard. `_close_gray_leg()` is the DB-only shadow exit.
- `live/signals.py` — `_at_position_limit()` live gate uses `LIVE_MAX_LEGS` (gray included); `_journal_trades()` closes open shadows from engine outcomes and excludes gray from costs/daily counters.
- `persistence/database.py` — `ltf_trades` exchange fields + migration.
- `persistence/trade_store.py` — `update_trade_qty()`, `update_trade_exchange()`, `get_ltf_trade()`.

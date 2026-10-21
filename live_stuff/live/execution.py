"""Book 107 live engine - vendored unified simulation on rolling windows.

Runs the same vendored simulate_htf_ltf_streak_halt the backtest uses,
on rolling windows of Binance or Bybit data. Produces identical trades.
"""

import os
import sys
import math
import time
import asyncio
import logging
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta
import bisect

import config
from rate_manager import RateManager

RISK_INR_FILE = Path(__file__).resolve().parents[1] / "risk_inr.txt"


def read_risk_inr() -> float:
    """Read risk amount in INR from risk_inr.txt. Edit file to change (no restart needed)."""
    try:
        val = float(RISK_INR_FILE.read_text().strip())
        if val > 0:
            return val
    except Exception:
        pass
    return config.DEFAULT_RISK_INR

from _vendored.btc_engine import _trail_events, _trail_events_ts
from _vendored.unified import simulate_htf_ltf_streak_halt
from _vendored.walker import FlowCandle
from _vendored.persistent_swing import PersistentSwingEngine
from data_streamer import BinanceStreamer, backfill_klines
from bybit_streamer import BybitStreamer, backfill_klines_bybit

from book import BOOK_NAME, BOOK_PARAMS, SWING, SWING_1H_LABEL, get_book_params
from persistence.database import Database
from persistence.mark_store import get_marks
from persistence.trade_store import (
    open_ltf_trade, close_ltf_trade, get_open_ltf_trade, get_ltf_trades,
    update_trade_qty, update_trade_exchange,
)
from persistence.state_store import get_trading_state, save_trading_state, get_last_swing_end, set_last_swing_end
from .state import is_gray_leg

logger = logging.getLogger("live_loop")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Exchange routing
EXCHANGE_BINANCE = "binance"
EXCHANGE_BYBIT = "bybit"

SYMBOL = config.SYMBOL
WINDOW_DAYS_15M = config.WINDOW_DAYS_15M
WINDOW_DAYS_1H = config.WINDOW_DAYS_1H
CAP_DAYS = config.CAP_DAYS
IST = timedelta(hours=5, minutes=30)



class ExecutionMixin:
    """execution responsibilities."""

    def _boot_sync_sl(self):
        """Sync every restored leg's partial SL to the DB value."""
        if not (self._open_ltf_trades and self.trader and self.trader.is_connected):
            return
        for trade in list(self._open_ltf_trades.values()):
            if is_gray_leg(trade):
                continue
            sl_now = float(trade.get("sl_current", 0) or 0)
            if sl_now <= 0:
                continue
            ok = self._sync_leg_sl(trade, sl_now, allow_place=False)
            if not ok and self._tg:
                self._tg.error(f"Boot SL sync FAILED: leg {trade.get('id')} DB={sl_now:.2f}")

    def _find_leg_stop(self, trade: dict, open_stops: list[dict] | None = None) -> dict | None:
        if open_stops is None:
            ok, open_stops = self.trader.get_open_stop_orders()
            if not ok:
                return None
        sl_id = trade.get("sl_order_id")
        if sl_id:
            for o in open_stops:
                if o.get("orderId") == sl_id:
                    return o
        link = trade.get("entry_order_link_id")
        if link:
            for o in open_stops:
                if (o.get("parentOrderLinkId") == link
                        and o.get("stopOrderType") == "PartialStopLoss"):
                    return o
        return None

    def _sync_leg_sl(self, trade: dict, new_sl: float, allow_place: bool = True) -> bool:
        if not (self.trader and self.trader.is_connected):
            return False
        if is_gray_leg(trade):
            print(f"[sl] leg {trade.get('id')}: gray shadow has no exchange stop")
            return False
        trade_id = int(trade["id"])
        qty = float(trade.get("qty", 0) or 0)
        ok, open_stops = self.trader.get_open_stop_orders()
        if not ok:
            print(f"[sl] leg {trade_id}: stop query failed - not placing/amending")
            return False
        stop = self._find_leg_stop(trade, open_stops)
        if stop is None:
            if not allow_place:
                print(f"[sl] leg {trade_id}: no open partial SL - reconcile will handle")
                return False
            if qty <= 0:
                print(f"[sl] leg {trade_id}: no stop and qty=0 - cannot sync")
                return False
            resp = self.trader.place_partial_sl(qty, new_sl)
            stop = resp.get("_stop_order")
            if resp.get("retCode") != 0 or not stop:
                print(f"[sl] leg {trade_id}: re-place failed: {resp.get('retMsg', 'unknown')}")
                return False
        else:
            resp = self.trader.amend_partial_sl(stop["orderId"], new_sl)
            if resp.get("retCode") != 0:
                print(f"[sl] leg {trade_id}: amend failed: {resp.get('retMsg', 'unknown')}")
                return False
        now = int(time.time())
        update_trade_exchange(
            self.db, trade_id, sl_order_id=stop.get("orderId"),
            sl_order_status=stop.get("orderStatus"), last_sync_ts=now,
        )
        self._cache_ltf_trade_exchange(
            trade_id, sl_order_id=stop.get("orderId"),
            sl_order_status=stop.get("orderStatus"), last_sync_ts=now,
        )
        return True

    def _record_reconciled_close(self, trade: dict, price: float, reason: str,
                                 order_id: str | None = None, fee: float = 0.0):
        entry = float(trade.get("entry_fill_price") or trade.get("entry_price", 0) or 0)
        sl0 = float(trade.get("sl_initial", 0) or 0)
        risk = abs(entry - sl0)
        r = self._calc_r(trade.get("direction"), entry, price, risk) if risk > 0 else 0.0
        total_fee = float(trade.get("fee_paid", 0) or 0) + fee
        close_ltf_trade(
            self.db, int(trade["id"]), int(time.time()), price, reason, r,
            exit_order_id=order_id, exit_fill_price=price, fee_paid=total_fee,
        )
        self._cache_ltf_trade_close(int(trade["id"]))
        if r < 0 and hasattr(self, "_check_daily_loss_limit"):
            try:
                self._check_daily_loss_limit(r)
            except Exception as e:
                print(f"[daily] reconciled close update failed: {e}")
        if hasattr(self, "_persist_streak_state"):
            try:
                self._persist_streak_state()
            except Exception as e:
                print(f"[streak] reconciled close update failed: {e}")

    def _reconcile_bybit_position(self):
        """Reconcile all DB legs with the single exchange position and its stops."""
        if not self.trader or not self.trader.is_connected:
            return
        ok, pos = self.trader.get_position_checked()
        if not ok:
            print("[reconcile] Bybit position query failed - state unknown")
            return
        legs = [t for t in self._open_ltf_trades.values() if not is_gray_leg(t)]
        if not legs:
            if pos is not None:
                print(f"[reconcile] Bybit orphan {pos['side']} {pos['size']} - closing")
                self.trader.close_reduce_only(pos["size"],
                                              order_link_id=f"reconcile_orphan_{int(time.time())}")
            return

        ok_stops, open_stops = self.trader.get_open_stop_orders()
        if not ok_stops:
            print("[reconcile] stop-order query failed - state unknown")
            return

        remaining = []
        for trade in legs:
            sl_id = trade.get("sl_order_id")
            if sl_id:
                okx, execs = self.trader.get_order_executions(sl_id)
                if not okx:
                    print(f"[reconcile] leg {trade['id']}: SL execution query failed")
                    remaining.append(trade)
                    continue
                if execs:
                    qty = sum(e["execQty"] for e in execs)
                    px = sum(e["execPrice"] * e["execQty"] for e in execs) / qty if qty else float(trade["sl_current"])
                    fee = sum(e["execFee"] for e in execs)
                    print(f"[reconcile] leg {trade['id']}: SL already fired @ {px:.2f} - closing DB")
                    self._record_reconciled_close(trade, px, "sl_reconcile", sl_id, fee)
                    continue
            remaining.append(trade)

        if pos is None:
            for trade in remaining:
                px = float(trade.get("sl_current", 0) or trade.get("entry_price", 0))
                print(f"[reconcile] DB leg {trade['id']} open, exchange flat - closing at {px:.2f}")
                self._record_reconciled_close(trade, px, "reconcile_flat")
            return

        ex_dir = "long" if pos["side"] == "Buy" else "short"
        if any(t.get("direction") != ex_dir for t in remaining):
            print(f"[reconcile] SIDE MISMATCH DB/exchange={ex_dir} - not closing anything")
            return

        qty_step = getattr(self.trader, "qty_step", 0.001)
        db_sum = sum(float(t.get("qty", 0) or 0) for t in remaining)
        if len(remaining) == 1 and db_sum <= 0:
            db_sum = float(pos["size"])
            update_trade_qty(self.db, int(remaining[0]["id"]), db_sum)
            remaining[0]["qty"] = db_sum
            self._cache_ltf_trade_exchange(int(remaining[0]["id"]), qty=db_sum)
        if abs(db_sum - float(pos["size"])) > qty_step / 2:
            print(f"[reconcile] QTY MISMATCH DB={db_sum} exchange={pos['size']} - "
                  f"repairing stops only, not force-closing")

        stop_qty = sum(float(o.get("qty", 0) or 0) for o in open_stops
                       if o.get("stopOrderType") in ("StopLoss", "PartialStopLoss", "TrailingStop"))
        for trade in remaining:
            qty = float(trade.get("qty", 0) or 0)
            if qty <= 0:
                continue
            stop = self._find_leg_stop(trade, open_stops)
            if stop is not None:
                if trade.get("sl_order_id") != stop.get("orderId"):
                    update_trade_exchange(self.db, int(trade["id"]),
                                          sl_order_id=stop.get("orderId"),
                                          sl_order_status=stop.get("orderStatus"))
                    self._cache_ltf_trade_exchange(
                        int(trade["id"]), sl_order_id=stop.get("orderId"),
                        sl_order_status=stop.get("orderStatus"))
                continue
            if stop_qty + qty > float(pos["size"]) + qty_step / 2:
                print(f"[reconcile] leg {trade['id']}: no stop, but SL qty would exceed position - skipping")
                continue
            resp = self.trader.place_partial_sl(qty, float(trade["sl_current"]))
            new_stop = resp.get("_stop_order")
            if resp.get("retCode") == 0 and new_stop:
                stop_qty += qty
                update_trade_exchange(self.db, int(trade["id"]),
                                      sl_order_id=new_stop.get("orderId"),
                                      sl_order_status=new_stop.get("orderStatus"))
                self._cache_ltf_trade_exchange(
                    int(trade["id"]), sl_order_id=new_stop.get("orderId"),
                    sl_order_status=new_stop.get("orderStatus"))
                print(f"[reconcile] leg {trade['id']}: re-placed partial SL {qty} @ {trade['sl_current']:.2f}")
            else:
                print(f"[reconcile] leg {trade['id']}: re-place SL failed: {resp.get('retMsg', 'unknown')}")

    def _aggregate_open_notional(self, exclude_trade_id: int | None = None) -> float:
        total = 0.0
        for t in self._open_ltf_trades.values():
            if is_gray_leg(t):
                continue
            if exclude_trade_id is not None and int(t.get("id", 0)) == int(exclude_trade_id):
                continue
            qty = float(t.get("qty", 0) or 0)
            px = float(t.get("entry_fill_price") or t.get("entry_price") or 0)
            total += qty * px
        return total

    def _skip_live_entry(self, trade_id: int, reason: str, message: str):
        print(message)
        try:
            close_ltf_trade(
                self.db, trade_id=trade_id, exit_ts=int(time.time()),
                exit_price=0.0, exit_reason=reason, r_multiple=0.0,
            )
            self._cache_ltf_trade_close(trade_id)
        except Exception as e:
            print(f"[order] skip close failed: {e}")

    def _open_gray_leg(self, trade: dict, trade_id: int, entry_price: float,
                       sl_price: float, reason: str):
        """Keep an unsizeable entry as a shadow leg with no exchange order."""
        now = int(time.time())
        risk_inr = read_risk_inr()
        update_trade_qty(self.db, trade_id, 0.0)
        update_trade_exchange(
            self.db, trade_id, entry_fill_price=entry_price, fee_paid=0.0,
            funding_paid=0.0, exchange_state="gray", last_sync_ts=now,
        )
        self._cache_ltf_trade_exchange(
            trade_id, qty=0.0, entry_fill_price=entry_price, fee_paid=0.0,
            funding_paid=0.0, exchange_state="gray", last_sync_ts=now,
        )
        print(f"[trade] GRAY LEG (shadow): {trade['dir']} "
              f"sw{trade.get('swing_no', '?')} @ {entry_price:.2f} "
              f"SL={sl_price:.2f} risk=INR {risk_inr:.2f} ({reason}) - "
              f"no exchange order, slot and cooldown preserved")

    def _emergency_close_leg(self, trade_id: int, qty: float) -> bool:
        """Close only this leg's qty, never another leg's net position."""
        ok, pos = self.trader.get_position_checked()
        if not ok:
            print(f"[trade] EMERGENCY CLOSE BLOCKED: position query failed (leg {trade_id})")
            return False
        step = getattr(self.trader, "qty_step", 0.001)
        other_qty = sum(
            float(t.get("qty", 0) or 0)
            for tid, t in self._open_ltf_trades.items()
            if int(tid) != int(trade_id)
        )
        pos_qty = float(pos["size"]) if pos else 0.0
        if pos_qty <= other_qty + step / 2:
            print(f"[trade] EMERGENCY CLOSE: leg {trade_id} already flat - no close sent")
            return True
        close_qty = min(float(qty), pos_qty - other_qty)
        if close_qty <= 0:
            return True
        resp = self.trader.close_reduce_only(
            close_qty, order_link_id=f"emerg_{trade_id}_{int(time.time())}")
        if resp.get("retCode") != 0:
            print(f"[trade] EMERGENCY CLOSE FAILED: {resp.get('retMsg', 'unknown')} "
                  f"- leaving leg {trade_id} for reconcile")
            return False
        print(f"[trade] EMERGENCY CLOSE sent: leg {trade_id} qty={close_qty}")
        return True

    def _execute_entry(self, trade: dict, trade_id: int):
        """Place one leg with its own attached partial SL and record the actual fill."""
        if self._daily_halted:
            self._skip_live_entry(trade_id, "halted_skip",
                                  "[order] SKIPPED - daily loss limit active")
            return
        if not (self.trader and self.trader.is_connected):
            return
        try:
            direction = trade["dir"]
            side = "Buy" if direction == "long" else "Sell"
            entry_price = float(trade["entry_price"])
            sl_price = float(trade["sl"])
            qty, reject_reason = self._size_entry(entry_price, sl_price)
            if qty <= 0:
                if (reject_reason == "min_qty"
                        and getattr(config, "GRAY_MIN_QTY_ENABLED", True)):
                    self._open_gray_leg(trade, trade_id, entry_price, sl_price,
                                        reject_reason)
                    return True
                self._skip_live_entry(trade_id, "stale_skip",
                                      f"[order] SKIPPED - qty={qty} ({reject_reason})")
                return
            qty_str = self.trader.format_qty(qty)
            sl_str = self.trader.format_price(sl_price)
            notional = qty * entry_price
            cap = float(getattr(config, "MAX_AGGREGATE_NOTIONAL", 0) or 0)
            open_notional = self._aggregate_open_notional(exclude_trade_id=trade_id)
            if cap > 0 and open_notional + notional > cap:
                self._skip_live_entry(
                    trade_id, "stale_skip",
                    f"[order] SKIPPED - aggregate notional ${open_notional + notional:.2f} "
                    f"> cap ${cap:.2f} (open ${open_notional:.2f}, leg ${notional:.2f})")
                return
            stop_distance = abs(entry_price - sl_price)
            risk_inr = read_risk_inr()
            rate = self.rate_manager.get_rate()
            risk_usdt = risk_inr / rate
            print(f"[trade] ENTRY {direction} sw{trade.get('swing_no', '?')} @ {entry_price:.2f}")
            print(f"  SL={sl_str} dist={stop_distance:.2f} qty={qty_str} "
                  f"notional=${notional:.2f} agg=${open_notional + notional:.2f}")
            print(f"  Risk: INR {risk_inr:.0f} = ${risk_usdt:.2f} (rate INR {rate:.2f})")
            link_id = f"bb_{trade_id}_{int(time.time() * 1000)}"
            resp = self.trader.place_entry_with_partial_sl(
                side, qty_str, sl_price, order_link_id=link_id)

            fill = None
            state = "unknown"
            accepted = resp.get("retCode") == 0
            for _ in range(10 if accepted else 3):
                state, info = self.trader.get_order_fill(link_id)
                if state == "filled":
                    fill = info
                    break
                time.sleep(0.3)
            if fill is None and accepted:
                order_id_probe = resp.get("result", {}).get("orderId")
                if order_id_probe:
                    for _ in range(3):
                        okx, execs = self.trader.get_order_executions(order_id_probe)
                        if okx and execs:
                            filled = sum(e["execQty"] for e in execs)
                            fill = {
                                "orderId": order_id_probe,
                                "cumExecQty": filled,
                                "avgPrice": (sum(e["execPrice"] * e["execQty"] for e in execs) / filled
                                             if filled else 0.0),
                                "cumExecFee": sum(e["execFee"] for e in execs),
                            }
                            state = "filled"
                            break
                        time.sleep(0.3)

            if fill is None:
                if state == "flat" and not accepted:
                    msg = resp.get("retMsg", "order not filled")
                    self._skip_live_entry(trade_id, "order_failed",
                                          f"[trade] ENTRY FAILED (confirmed flat): {msg}")
                    if self._tg:
                        self._tg.error(f"ENTRY FAILED: {msg}")
                else:
                    update_trade_exchange(self.db, trade_id,
                                          entry_order_link_id=link_id,
                                          exchange_state="unknown")
                    self._cache_ltf_trade_exchange(
                        trade_id, entry_order_link_id=link_id, exchange_state="unknown")
                    print("[trade] ENTRY UNKNOWN - DB kept OPEN, VERIFY POSITION MANUALLY")
                    if self._tg:
                        self._tg.error("ENTRY UNKNOWN - verify position manually")
                return

            actual_qty = float(fill.get("cumExecQty", 0) or 0)
            fill_px = float(fill.get("avgPrice", 0) or entry_price)
            fee = float(fill.get("cumExecFee", 0) or 0)
            order_id = fill.get("orderId") or resp.get("result", {}).get("orderId")
            if actual_qty <= 0:
                self._skip_live_entry(trade_id, "order_failed",
                                      "[trade] ENTRY FAILED - zero fill")
                return
            if (actual_qty < qty * 0.99
                    and fill.get("status") in ("New", "PartiallyFilled", "Untriggered")):
                cr = self.trader.cancel_order_by_id(order_id)
                print(f"[trade] partial entry remainder cancel: {cr.get('retCode')} "
                      f"{cr.get('retMsg', '')}")

            update_trade_qty(self.db, trade_id, actual_qty)
            update_trade_exchange(
                self.db, trade_id,
                entry_order_id=order_id,
                entry_order_link_id=link_id,
                entry_fill_price=fill_px,
                fee_paid=fee,
                exchange_state="open",
                last_sync_ts=int(time.time()),
            )
            self._cache_ltf_trade_exchange(
                trade_id, qty=actual_qty, entry_order_id=order_id,
                entry_order_link_id=link_id, entry_fill_price=fill_px,
                fee_paid=fee, exchange_state="open",
                last_sync_ts=int(time.time()),
            )
            print(f"[trade] ENTRY FILLED: {order_id} {actual_qty} BTC @ {fill_px:.2f} fee=${fee:.4f}")
            if actual_qty < qty * 0.99:
                print(f"[trade] PARTIAL FILL: {actual_qty}/{qty} BTC")
                if self._tg:
                    self._tg.error(f"PARTIAL FILL: {actual_qty}/{qty} BTC")

            stop = resp.get("_stop_order")
            if stop is None:
                for _ in range(5):
                    ok, stops = self.trader.get_open_stop_orders()
                    if ok:
                        stop = next(
                            (o for o in stops
                             if o.get("parentOrderLinkId") == link_id
                             and o.get("stopOrderType") == "PartialStopLoss"),
                            None,
                        )
                    if stop is not None:
                        break
                    time.sleep(0.2)
            step = getattr(self.trader, "qty_step", 0.001)
            if stop is not None and abs(float(stop.get("qty", 0) or 0) - actual_qty) > step / 2:
                print(f"[trade] attached SL qty={stop.get('qty')} != fill {actual_qty} - replacing")
                cr = self.trader.cancel_order_by_id(stop.get("orderId"))
                if cr.get("retCode") != 0:
                    print(f"[trade] SL cancel failed: {cr.get('retMsg', 'unknown')} - emergency close")
                    if not self._emergency_close_leg(trade_id, actual_qty):
                        return
                    self._skip_live_entry(trade_id, "order_error",
                                          "[trade] EMERGENCY CLOSE - SL qty mismatch")
                    return
                stop = None
            if stop is None:
                resp2 = self.trader.place_partial_sl(actual_qty, sl_price)
                stop = resp2.get("_stop_order")
                if resp2.get("retCode") != 0 or stop is None:
                    print(f"[trade] SL PLACEMENT FAILED: {resp2.get('retMsg', 'unknown')} - emergency close")
                    if not self._emergency_close_leg(trade_id, actual_qty):
                        return
                    self._skip_live_entry(trade_id, "order_error",
                                          "[trade] EMERGENCY CLOSE - no protective SL")
                    if self._tg:
                        self._tg.error("ENTRY HAD NO SL - emergency close attempted")
                    return
            sl_id = stop.get("orderId")
            sl_status = stop.get("orderStatus")
            update_trade_exchange(
                self.db, trade_id, sl_order_id=sl_id, sl_order_link_id=stop.get("orderLinkId"),
                sl_order_status=sl_status, last_sync_ts=int(time.time()),
            )
            self._cache_ltf_trade_exchange(
                trade_id, sl_order_id=sl_id, sl_order_link_id=stop.get("orderLinkId"),
                sl_order_status=sl_status, last_sync_ts=int(time.time()))
            print(f"[trade] LEG READY: qty={actual_qty} SL order={sl_id} @ {sl_price:.2f}")
            if self._tg:
                self._tg.trade_entry(direction, entry_price, sl_price,
                                      self.trader.format_qty(actual_qty),
                                      risk_inr, risk_usdt, rate)
            return True
        except Exception as e:
            print(f"[trade] ENTRY ERROR: {e}")
            if self._tg:
                self._tg.error(f"ENTRY ERROR: {e}")
            try:
                close_ltf_trade(self.db, trade_id=trade_id,
                                exit_ts=int(time.time()), exit_price=0.0,
                                exit_reason="order_error", r_multiple=0.0)
                self._cache_ltf_trade_close(trade_id)
            except Exception:
                pass
        return False

    def _execute_exit(self, reason: str, fill_price: float, trade: dict | None = None) -> bool:
        """Cancel this leg's partial SL, then reduce-only close its qty.

        Returns True only when the leg's exchange fill is confirmed. The caller
        still records the DB exit; actual fill fields are stored here first.
        """
        trade = trade or self._open_ltf_trade
        if is_gray_leg(trade):
            print(f"[trade] EXIT BLOCKED: leg {trade.get('id')} is a gray shadow - "
                  f"no exchange order")
            return False
        if trade is None or not (self.trader and self.trader.is_connected):
            return False
        trade_id = int(trade["id"])
        qty = float(trade.get("qty", 0) or 0)
        qty_step = getattr(self.trader, "qty_step", 0.001)
        direction = trade.get("direction", "")
        entry_price = float(trade.get("entry_fill_price") or trade.get("entry_price", 0) or 0)
        sl_initial = float(trade.get("sl_initial", 0) or 0)
        risk = abs(entry_price - sl_initial)
        sl_id = trade.get("sl_order_id")
        link_id = trade.get("entry_order_link_id")

        def done(px: float, fee: float, order_id: str | None):
            r_mult = ((px - entry_price) / risk if direction == "long"
                      else (entry_price - px) / risk) if risk > 0 else 0.0
            total_fee = float(trade.get("fee_paid", 0) or 0) + fee
            update_trade_exchange(
                self.db, trade_id, exit_order_id=order_id,
                exit_fill_price=px, fee_paid=total_fee, exchange_state="closing",
                last_sync_ts=int(time.time()),
            )
            self._cache_ltf_trade_exchange(
                trade_id, exit_order_id=order_id, exit_fill_price=px,
                fee_paid=total_fee, exchange_state="closing", last_sync_ts=int(time.time()))
            print(f"[trade] EXIT FILLED: {reason} @ {px:.2f} ({r_mult:+.2f}R) fee=${fee:.4f}")
            self._exit_fail_count = 0
            if self._tg:
                self._tg.trade_exit(reason, px, r_mult, direction, entry_price)
            return True

        try:
            if qty <= 0:
                ok, pos = self.trader.get_position_checked()
                if not ok:
                    return False
                if pos is None:
                    self._record_reconciled_close(trade, fill_price, "reconcile_flat")
                    return True
                if len(self._open_ltf_trades) == 1:
                    qty = float(pos["size"])
                    update_trade_qty(self.db, trade_id, qty)
                    trade["qty"] = qty
                    self._cache_ltf_trade_exchange(trade_id, qty=qty)
                else:
                    print(f"[trade] EXIT BLOCKED: leg {trade_id} qty=0 with {len(self._open_ltf_trades)} legs")
                    return False

            prev_exit = trade.get("exit_order_id")
            if prev_exit and qty > 0:
                okx, execs = self.trader.get_order_executions(prev_exit)
                if not okx:
                    print(f"[trade] EXIT BLOCKED: cannot verify prior close {prev_exit} - retry")
                    return False
                if execs:
                    filled = sum(e["execQty"] for e in execs)
                    px = (sum(e["execPrice"] * e["execQty"] for e in execs) / filled
                          if filled else fill_price)
                    fee = sum(e["execFee"] for e in execs)
                    if filled + qty_step / 2 >= qty:
                        return done(px, fee, prev_exit)
                    qty -= filled
                    update_trade_qty(self.db, trade_id, qty)
                    self._cache_ltf_trade_exchange(
                        trade_id, qty=qty, exit_order_id=None, exchange_state="open")
                    trade["qty"] = qty
                else:
                    ok_ord, prev_ord = self.trader.get_order_by_id(prev_exit)
                    if not ok_ord:
                        print(f"[trade] EXIT BLOCKED: cannot query prior close {prev_exit}")
                        return False
                    status = (prev_ord or {}).get("status")
                    if prev_ord is None:
                        print(f"[trade] EXIT PENDING: prior close {prev_exit} not found yet - retry")
                        return False
                    if status in ("Cancelled", "Rejected", "Deactivated", "Expired"):
                        print(f"[trade] prior close {prev_exit} did not fill ({status}) - restoring SL")
                        update_trade_exchange(self.db, trade_id, exit_order_id=None,
                                              exchange_state="open")
                        self._cache_ltf_trade_exchange(
                            trade_id, exit_order_id=None, exchange_state="open")
                        trade["exit_order_id"] = None
                        rp = self.trader.place_partial_sl(
                            qty, float(trade.get("sl_current") or sl_initial))
                        new_stop = rp.get("_stop_order")
                        if rp.get("retCode") == 0 and new_stop:
                            update_trade_exchange(
                                self.db, trade_id, sl_order_id=new_stop.get("orderId"),
                                sl_order_status=new_stop.get("orderStatus"))
                            self._cache_ltf_trade_exchange(
                                trade_id, sl_order_id=new_stop.get("orderId"),
                                sl_order_status=new_stop.get("orderStatus"))
                    else:
                        print(f"[trade] EXIT PENDING: prior close {prev_exit} "
                              f"status={status} - retry")
                    return False

            if sl_id:
                okx, execs = self.trader.get_order_executions(sl_id)
                if not okx:
                    print(f"[trade] EXIT BLOCKED: cannot verify SL {sl_id} - retry")
                    return False
                if execs:
                    filled = sum(e["execQty"] for e in execs)
                    px = (sum(e["execPrice"] * e["execQty"] for e in execs) / filled
                          if filled else fill_price)
                    fee = sum(e["execFee"] for e in execs)
                    self._record_reconciled_close(trade, px, "sl_exchange", sl_id, fee)
                    return True

            ok, stops = self.trader.get_open_stop_orders()
            if not ok:
                print("[trade] EXIT BLOCKED: stop-order query failed - retry")
                return False
            stop = next((o for o in stops if sl_id and o.get("orderId") == sl_id), None)
            cancelled_stop = False
            if stop is None and link_id:
                stop = next(
                    (o for o in stops
                     if o.get("parentOrderLinkId") == link_id
                     and o.get("stopOrderType") == "PartialStopLoss"),
                    None,
                )
            if stop is not None:
                resp = self.trader.cancel_order_by_id(stop.get("orderId"))
                if resp.get("retCode") != 0 and "not found" not in str(resp.get("retMsg", "")).lower():
                    print(f"[trade] EXIT BLOCKED: SL cancel failed: {resp.get('retMsg', 'unknown')}")
                    return False
                time.sleep(0.2)
                ok2, stops2 = self.trader.get_open_stop_orders()
                if not ok2 or any(o.get("orderId") == stop.get("orderId") for o in stops2):
                    print("[trade] EXIT BLOCKED: SL still open after cancel - retry")
                    return False
                cancelled_stop = True
                update_trade_exchange(self.db, trade_id, sl_order_status="Cancelled")
                self._cache_ltf_trade_exchange(trade_id, sl_order_status="Cancelled")

            exit_link = f"exit_{trade_id}_{int(time.time() * 1000)}"
            resp = self.trader.close_reduce_only(qty, order_link_id=exit_link)
            accepted = resp.get("retCode") == 0
            state, info = self.trader.get_order_fill(exit_link)
            for _ in range(4):
                if state != "unknown":
                    break
                time.sleep(0.3)
                state, info = self.trader.get_order_fill(exit_link)
            close_order_id = resp.get("result", {}).get("orderId")
            filled = 0.0
            px = fill_price
            fee = 0.0
            if state == "filled":
                px = float(info.get("avgPrice", 0) or fill_price)
                fee = float(info.get("cumExecFee", 0) or 0)
                filled = float(info.get("cumExecQty", 0) or 0)
                close_order_id = info.get("orderId") or close_order_id
            elif accepted and close_order_id:
                for _ in range(3):
                    okx, execs = self.trader.get_order_executions(close_order_id)
                    if okx and execs:
                        filled = sum(e["execQty"] for e in execs)
                        px = (sum(e["execPrice"] * e["execQty"] for e in execs) / filled
                              if filled else fill_price)
                        fee = sum(e["execFee"] for e in execs)
                        break
                    time.sleep(0.3)
            if filled + qty_step / 2 < qty and filled > 0:
                update_trade_exchange(
                    self.db, trade_id, exit_order_id=close_order_id,
                    exchange_state="closing", last_sync_ts=int(time.time()))
                self._cache_ltf_trade_exchange(
                    trade_id, exit_order_id=close_order_id, exchange_state="closing")
                print(f"[trade] EXIT PARTIAL: {filled}/{qty} - remaining "
                      f"{qty - filled} unprotected; retry next tick")
                return False
            if filled + qty_step / 2 >= qty:
                update_trade_exchange(
                    self.db, trade_id, exit_order_id=close_order_id,
                    exit_fill_price=px, fee_paid=fee, exchange_state="closing",
                    last_sync_ts=int(time.time()))
                return done(px, fee, close_order_id)

            if accepted:
                ok, pos = self.trader.get_position_checked()
                if ok and pos is None:
                    return done(fill_price, 0.0, close_order_id)
                if ok and float(pos["size"]) + qty_step / 2 < qty:
                    return done(fill_price, 0.0, close_order_id)
                update_trade_exchange(
                    self.db, trade_id, exit_order_id=close_order_id,
                    exchange_state="closing", last_sync_ts=int(time.time()))
                self._cache_ltf_trade_exchange(
                    trade_id, exit_order_id=close_order_id, exchange_state="closing")
                print("[trade] EXIT UNKNOWN: close accepted but fill not confirmed - retry")
            else:
                print(f"[trade] EXIT FAILED: {resp.get('retMsg', 'unknown')} - retry")
                if sl_id or cancelled_stop:
                    rp = self.trader.place_partial_sl(qty, float(trade.get("sl_current") or sl_initial))
                    new_stop = rp.get("_stop_order")
                    if rp.get("retCode") == 0 and new_stop:
                        update_trade_exchange(
                            self.db, trade_id, sl_order_id=new_stop.get("orderId"),
                            sl_order_status=new_stop.get("orderStatus"))
                        self._cache_ltf_trade_exchange(
                            trade_id, sl_order_id=new_stop.get("orderId"),
                            sl_order_status=new_stop.get("orderStatus"))
            self._exit_fail_count = getattr(self, "_exit_fail_count", 0) + 1
            if self._tg and (self._exit_fail_count == 1 or self._exit_fail_count % 10 == 0):
                self._tg.error(f"EXIT FAILED (retry {self._exit_fail_count}): {resp.get('retMsg', 'unknown')}")
            return False
        except Exception as e:
            self._exit_fail_count = getattr(self, "_exit_fail_count", 0) + 1
            print(f"[trade] EXIT ERROR: {e}")
            if self._tg and (self._exit_fail_count == 1 or self._exit_fail_count % 10 == 0):
                self._tg.error(f"EXIT ERROR: {e}")
            return False

    def _size_entry(self, entry_price: float, sl_price: float) -> tuple[float, str]:
        """Exact price-risk sizing; return (qty, reject_reason)."""
        risk_inr = read_risk_inr()
        if self.rate_manager.is_stale():
            print(f"[order] WARNING: rate cache stale ({self.rate_manager.age_min():.0f} min) - "
                  f"sizing with cached INR {self.rate_manager.get_rate():.2f}/USDT")
        inr_usdt = self.rate_manager.get_rate()
        risk_usdt = risk_inr / inr_usdt

        stop_distance = abs(entry_price - sl_price)
        if stop_distance <= 0 or risk_usdt <= 0:
            return 0.0, "invalid_stop"

        qty_step = self.trader.qty_step if self.trader else 10 ** (-config.QTY_PRECISION)
        min_qty = self.trader.min_qty if self.trader else config.MIN_BTC_QTY
        raw_qty = risk_usdt / stop_distance
        qty = math.floor((raw_qty + 1e-12) / qty_step) * qty_step
        qty = round(qty, 10)
        if qty < min_qty:
            forced_risk = min_qty * stop_distance
            mult = forced_risk / risk_usdt if risk_usdt > 0 else float("inf")
            print(f"[order] REJECTED: computed qty {qty} < exchange min {min_qty} "
                  f"- forcing min would risk ${forced_risk:.2f} vs planned ${risk_usdt:.2f} ({mult:.1f}x planned)")
            return 0.0, "min_qty"
        min_notional = float(getattr(self.trader, "min_notional", 0) or 0)
        if min_notional > 0 and qty * entry_price < min_notional:
            print(f"[order] REJECTED: notional ${qty * entry_price:.2f} < exchange min "
                  f"${min_notional:.2f} - trade skipped")
            return 0.0, "min_notional"

        if self.trader and self.trader.is_connected:
            available = float(self.trader.get_wallet_balance().get("available", 0) or 0)
            if available <= 0:
                print("[order] WARNING: balance unavailable - skipping balance cap")
            else:
                max_notional = available * config.BALANCE_SAFETY_MARGIN * config.MAX_LEVERAGE
                required = qty * entry_price
                if required > max_notional:
                    qty = math.floor(
                        (available * config.SIZED_DOWN_FRACTION * config.MAX_LEVERAGE)
                        / entry_price / qty_step
                    ) * qty_step
                    qty = round(qty, 10)
                    if qty < min_qty:
                        print(f"[order] REJECTED: balance-sized qty {qty} < exchange min {min_qty} "
                              f"(available={available:.2f} USDT) - trade skipped")
                        return 0.0, "balance_min_qty"
                    print(f"[order] Position sized down: available={available:.2f} USDT, qty={qty}")
                implied_lev = (qty * entry_price) / available
                if implied_lev > config.MAX_LEVERAGE:
                    print(f"[order] REJECTED: implied leverage {implied_lev:.1f}x > max {config.MAX_LEVERAGE}x")
                    return 0.0, "leverage"

        print(f"[order] Risk: INR {risk_inr:.0f} = ${risk_usdt:.2f} USDT "
              f"(rate INR {inr_usdt:.2f}/USDT) qty={qty}")
        return qty, ""

    def _calculate_qty(self, entry_price: float, sl_price: float) -> float:
        return self._size_entry(entry_price, sl_price)[0]

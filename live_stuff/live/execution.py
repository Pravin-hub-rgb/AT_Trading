"""Book 107 live engine - vendored unified simulation on rolling windows.

Runs the same vendored simulate_htf_ltf_streak_halt the backtest uses,
on rolling windows of Binance or Bybit data. Produces identical trades.
"""

import os
import sys
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
from persistence.trade_store import open_ltf_trade, close_ltf_trade, get_open_ltf_trade, get_ltf_trades
from persistence.state_store import get_trading_state, save_trading_state, get_last_swing_end, set_last_swing_end

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
        """One-shot exchange SL sync after restore + reconcile (C3/H9)."""
        if not (self._open_ltf_trade and self.trader and self.trader.is_connected):
            return
        try:
            sl_now = float(self._open_ltf_trade.get("sl_current", 0) or 0)
            if sl_now <= 0:
                return
            resp = self.trader.update_sl(sl_now)
            ok = resp.get("retCode") == 0
            print(f"[restore] SL synced to Bybit: {sl_now:.2f} -> {'OK' if ok else resp.get('retMsg', 'failed')}")
            if not ok and self._tg:
                self._tg.error(f"Boot SL sync FAILED: DB={sl_now:.2f} exchange may differ")
        except Exception as e:
            print(f"[restore] SL sync failed: {e}")

    def _reconcile_bybit_position(self):
        """Phase 15: Reconcile DB trade state with Bybit exchange position on startup.
        
        Handles 4 cases:
          DB open + Bybit has position -> resume (OK)
          DB open + Bybit flat -> Bybit SL/TP hit during crash -> close DB record
          DB flat + Bybit has position -> orphan position -> close on Bybit
          DB flat + Bybit flat -> OK
        """
        if not self.trader or not self.trader.is_connected:
            return

        try:
            exchange_pos = self.trader.get_position()
        except Exception as e:
            print(f"[reconcile] Bybit position query failed: {e}")
            return

        db_trade = self._open_ltf_trade

        if db_trade and exchange_pos:
            # Both have positions — verify direction matches
            db_dir = db_trade["direction"]
            ex_dir = "long" if exchange_pos["side"] == "Buy" else "short"
            if db_dir == ex_dir:
                print(f"[reconcile] OK — DB and Bybit both have {db_dir} position")
            else:
                print(f"[reconcile] MISMATCH — DB={db_dir} but Bybit={ex_dir}. Closing DB record.")
                exit_price = float(db_trade["sl_current"])
                r = self._calc_r(
                    db_trade["direction"],
                    float(db_trade["entry_price"]),
                    exit_price,
                    float(db_trade["sl_initial"]),
                )
                close_ltf_trade(
                    self.db, db_trade["id"], int(time.time()),
                    exit_price, "reconcile", r,
                )
                self._cache_ltf_trade_close()


        elif db_trade and not exchange_pos:
            # DB says open but Bybit is flat — SL/TP hit during crash
            exit_price = float(db_trade["sl_current"])
            entry_price = float(db_trade["entry_price"])
            sl_initial = float(db_trade["sl_initial"])
            risk = abs(entry_price - sl_initial)
            direction = db_trade["direction"]
            r = self._calc_r(direction, entry_price, exit_price, risk) if risk > 0 else 0.0
            print(f"[reconcile] DB has open trade but Bybit is flat. Closing DB record (exit≈{exit_price:.2f}, {r:+.2f}R).")
            close_ltf_trade(
                self.db, db_trade["id"], int(time.time()),
                exit_price, "reconcile", r,
            )
            self._cache_ltf_trade_close()

        elif not db_trade and exchange_pos:
            # Orphan position on Bybit — close it
            ex_dir = "long" if exchange_pos["side"] == "Buy" else "short"
            print(f"[reconcile] Bybit has orphan {ex_dir} position (size={exchange_pos['size']}). Closing.")
            try:
                self.trader.close_position()
            except Exception as e:
                print(f"[reconcile] Failed to close orphan position: {e}")

        else:
            # Both flat — OK
            pass

    def _execute_entry(self, trade: dict, trade_id: int):
        """Place market order on Bybit for a new open trade."""
        # Daily loss limit check — don't enter if halted
        if self._daily_halted:
            print(f"[order] SKIPPED — daily loss limit breached, trading halted until tomorrow")
            return
        try:
            direction = trade["dir"]
            side = "Buy" if direction == "long" else "Sell"
            entry_price = float(trade["entry_price"])
            sl_price = float(trade["sl"])
            tp_price = float(trade["target"])

            # Position sizing: risk INR -> USDT -> qty
            qty = self._calculate_qty(entry_price, sl_price)
            if qty <= 0:
                print(f"[order] SKIPPED -- qty={qty} (check balance/risk)")
                return

            # Format using exchange precision
            qty_prec = self.trader.qty_precision if self.trader else config.QTY_PRECISION
            sl_str = f"{sl_price:.2f}"
            tp_str = f"{tp_price:.2f}"
            qty_str = f"{qty:.{qty_prec}f}"
            stop_distance = abs(entry_price - sl_price)
            notional = qty * entry_price
            risk_inr = read_risk_inr()
            rate = self.rate_manager.get_rate()
            risk_usdt = risk_inr / rate

            # Detailed entry log
            print(f"[trade] ENTRY {direction} sw{trade.get('swing_no', '?')} @ {entry_price:.2f}")
            print(f"  SL={sl_str} TP={tp_str} dist={stop_distance:.2f}")
            print(f"  Risk: INR {risk_inr:.0f} = ${risk_usdt:.2f} (rate INR {rate:.2f})")
            print(f"  Qty: {qty_str} BTC (notional ${notional:.2f})")
            print(f"  Fee buffer: ${notional * config.TAKER_FEE_RATE * 2:.4f}")
            # C8: NO exchange TP on LTF orders. The sim NEVER target-exits LTF
            # (trailing="swing" -> trail-only exits; _exit_on_fine checks target
            # only when trailing=="off"; D2: 186 trail / 0 target, avg winner
            # +5.02R). A 3R exchange TP would cap every live runner at +3R while
            # the backtest rides to +5R+ ? the biggest live-vs-backtest gap found.
            # SL stays attached (downtime protection). DB tp_price kept for audit.
            print(f"  Bybit PLACING: {side} {qty_str} BTC SL={sl_str} (no TP ? trail-only, C8)")

            link_id = f"bb_{trade_id}_{int(time.time() * 1000)}"
            resp = self.trader.place_market_order_retry(side, qty_str, stop_loss=sl_str,
                                                        take_profit=None, order_link_id=link_id)

            if resp.get("retCode") != 0:
                # C7: response lost or rejected — the order may have LANDED
                # (lost response / duplicate orderLinkId). Verify before
                # declaring failure: adopt / confirm-flat / hold-open.
                state, info = self.trader.verify_entry_order(link_id, expected_side=direction)
                if state == "filled":
                    actual_qty = float(info["qty"])
                    print(f"[trade] ENTRY ADOPTED after lost response: {actual_qty} BTC @ ~{info.get('avgPrice', 0) or 0:.2f}")
                    if self._tg:
                        self._tg.error(f"ENTRY ADOPTED after lost response — {actual_qty} BTC (fill px {info.get('avgPrice', 0) or 0:.2f})")
                    try:
                        from persistence.trade_store import update_trade_qty
                        update_trade_qty(self.db, trade_id, actual_qty)
                    except Exception:
                        pass
                    if self._tg:
                        self._tg.trade_entry(direction, entry_price, sl_price, qty_str,
                                             risk_inr, risk_usdt, rate)
                    return
                if state == "flat":
                    print(f"[trade] ENTRY FAILED (confirmed flat): {resp.get('retMsg', 'unknown')}")
                    if self._tg:
                        self._tg.error(f"ENTRY FAILED: {resp.get('retMsg', 'unknown')}")
                    try:
                        close_ltf_trade(self.db, trade_id=trade_id,
                                        exit_ts=int(time.time()), exit_price=entry_price,
                                        exit_reason="order_failed", r_multiple=0.0)
                        self._open_ltf_trade = None
                    except Exception:
                        pass
                    return
                # unknown — cannot determine. Keep DB open + cache: if a position
                # exists, its exchange-side SL is armed (bounded risk). Operator
                # must verify; next-boot reconcile resolves the books.
                print(f"[trade] ENTRY UNKNOWN: {resp.get('retMsg', 'unknown')} — DB kept OPEN, VERIFY POSITION MANUALLY")
                if self._tg:
                    self._tg.error("ENTRY UNKNOWN — could not verify order. VERIFY POSITION MANUALLY.")
                return

            order_id = resp["result"]["orderId"]
            # H4 (folded into C7): poll the position instead of a single
            # sleep(0.3) check — a slow fill would previously false-fail.
            intended_qty = float(qty_str)
            actual_qty = 0.0
            for _ in range(3):
                pos = self.trader.get_position()
                if pos and pos.get("side") == side:
                    actual_qty = pos["size"]
                    break
                time.sleep(0.3)
            if actual_qty == 0:
                # C7: no position after polling — a lost response may have
                # landed. Verify before declaring failure.
                state, info = self.trader.verify_entry_order(link_id, expected_side=direction)
                if state == "filled":
                    actual_qty = float(info["qty"])
                    print(f"[trade] ENTRY FILLED (late fill confirmed): {actual_qty} BTC")
                else:
                    print(f"[trade] PARTIAL FILL WARNING: 0/{intended_qty} filled — closing DB trade")
                    if self._tg:
                        self._tg.error(f"ORDER FILLED 0/{intended_qty} — closing")
                    try:
                        close_ltf_trade(self.db, trade_id=trade_id,
                                        exit_ts=int(time.time()), exit_price=entry_price,
                                        exit_reason="order_failed", r_multiple=0.0)
                        self._open_ltf_trade = None
                    except Exception:
                        pass
                    return
            if actual_qty < intended_qty * 0.99:
                print(f"[trade] PARTIAL FILL: {actual_qty}/{intended_qty} filled — updating DB")
                if self._tg:
                    self._tg.error(f"PARTIAL FILL: {actual_qty}/{intended_qty} BTC")
                try:
                    from persistence.trade_store import update_trade_qty
                    update_trade_qty(self.db, trade_id, actual_qty)
                except Exception:
                    pass
            else:
                print(f"[trade] ENTRY FILLED: {order_id} ({actual_qty} BTC)")
                try:
                    from persistence.trade_store import update_trade_qty
                    update_trade_qty(self.db, trade_id, actual_qty)
                except Exception:
                    pass
            if self._tg:
                self._tg.trade_entry(direction, entry_price, sl_price, qty_str,
                                      risk_inr, risk_usdt, rate)
        except Exception as e:
            print(f"[trade] ENTRY ERROR: {e}")
            if self._tg:
                self._tg.error(f"ENTRY ERROR: {e}")
            # Close the orphan DB trade — no position on exchange
            try:
                close_ltf_trade(self.db, trade_id=trade_id,
                                exit_ts=int(time.time()), exit_price=0.0,
                                exit_reason="order_error", r_multiple=0.0)
                self._open_ltf_trade = None
            except Exception:
                pass

    def _execute_exit(self, reason: str, fill_price: float) -> bool:
        """Close the exchange position for the open trade (C1/C2 fix).

        Returns:
            True  — exchange position confirmed closed (or was already flat).
                    Caller may record the exit in DB and clear the cache.
            False — close failed or state unknown. Caller MUST keep the DB
                    trade open and the cache intact; on_tick retries on the
                    next tick.
        """
        try:
            # Get current rate for PnL logging
            rate = self.rate_manager.get_rate()
            print(f"[trade] EXIT reason={reason} @ {fill_price:.2f} (rate INR {rate:.2f})")
            # Get trade info for alert
            direction = ""
            entry_price = 0.0
            r_mult = 0.0
            if self._open_ltf_trade:
                direction = self._open_ltf_trade.get("direction", "")
                entry_price = float(self._open_ltf_trade.get("entry_price", 0))
                sl_initial = float(self._open_ltf_trade.get("sl_initial", 0))
                risk = abs(entry_price - sl_initial)
                if risk > 0:
                    r_mult = (fill_price - entry_price) / risk if direction == "long" else (entry_price - fill_price) / risk
            resp = self.trader.close_position_retry()
            if resp.get("retCode") == 0:
                print(f"[trade] EXIT FILLED: {reason}")
                self._exit_fail_count = 0
                if self._tg:
                    self._tg.trade_exit(reason, fill_price, r_mult, direction, entry_price)
                return True
            # Throttle alerts: first failure + every 10th retry
            self._exit_fail_count = getattr(self, "_exit_fail_count", 0) + 1
            print(f"[trade] EXIT FAILED: {resp.get('retMsg', 'unknown')} — DB kept open, retrying next tick")
            if self._tg and (self._exit_fail_count == 1 or self._exit_fail_count % 10 == 0):
                self._tg.error(f"EXIT FAILED (retry {self._exit_fail_count}): {resp.get('retMsg', 'unknown')}")
            return False
        except Exception as e:
            self._exit_fail_count = getattr(self, "_exit_fail_count", 0) + 1
            print(f"[trade] EXIT ERROR: {e}")
            if self._tg and (self._exit_fail_count == 1 or self._exit_fail_count % 10 == 0):
                self._tg.error(f"EXIT ERROR: {e}")
            return False

    def _calculate_qty(self, entry_price: float, sl_price: float) -> float:
        """Calculate BTC quantity based on risk.

        Reads risk from risk_inr.txt (edit file to change, no restart needed).
        Converts INR -> USDT via cached rate (0ms, no network on trade).
        Formula: qty = risk_usdt / (|entry - sl| + fee_buffer)
        Uses trader.qty_step for precision (fetched from Bybit API).
        Rejects trade if implied leverage > MAX_LEVERAGE.
        """
        risk_inr = read_risk_inr()
        # M9: update() does blocking requests.get (up to ~20s across both rate
        # sources) — it must NEVER run on the tick/entry path. _session_watch
        # refreshes it off-loop every 30s (asyncio.to_thread). Here we size
        # with the cached rate and warn if it is stale.
        if self.rate_manager.is_stale():
            print(f"[order] WARNING: rate cache stale ({self.rate_manager.age_min():.0f} min) — "
                  f"sizing with cached INR {self.rate_manager.get_rate():.2f}/USDT")
        inr_usdt = self.rate_manager.get_rate()
        risk_usdt = risk_inr / inr_usdt

        stop_distance = abs(entry_price - sl_price)
        if stop_distance <= 0:
            return 0.0

        # Fee buffer: taker fee * 2 sides * entry price
        fee_buffer = entry_price * config.TAKER_FEE_RATE * 2
        qty = risk_usdt / (stop_distance + fee_buffer)

        # Round to exchange qty_step precision
        qty_step = self.trader.qty_step if self.trader else 10 ** (-config.QTY_PRECISION)
        min_qty = self.trader.min_qty if self.trader else config.MIN_BTC_QTY
        qty = round(qty / qty_step) * qty_step
        # M10: never force up to the exchange minimum — that silently multiplies
        # real risk (min_qty / computed can be several x risk_usdt on wide stops).
        # Reject instead; the caller skips the trade on qty <= 0.
        if qty < min_qty:
            forced_risk = min_qty * (stop_distance + fee_buffer)
            mult = forced_risk / risk_usdt if risk_usdt > 0 else float("inf")
            print(f"[order] REJECTED: computed qty {qty} < exchange min {min_qty} "
                  f"— forcing min would risk ${forced_risk:.2f} vs planned ${risk_usdt:.2f} ({mult:.1f}x planned)")
            return 0.0

        # Check available balance
        if self.trader and self.trader.is_connected:
            balance = self.trader.get_wallet_balance()
            available = balance.get("available", 0)
            required = qty * entry_price
            if required > available * config.BALANCE_SAFETY_MARGIN:
                qty = round(available * config.SIZED_DOWN_FRACTION / entry_price / qty_step) * qty_step
                if qty < min_qty:
                    # M10: balance-sized qty below exchange min — forcing min could
                    # exceed available balance (margin rejection) and inflates risk.
                    print(f"[order] REJECTED: balance-sized qty {qty} < exchange min {min_qty} "
                          f"(available={available:.2f} USDT) — trade skipped")
                    return 0.0
                print(f"[order] Position sized down: balance={available:.2f} USDT, qty={qty}")

            # Implied leverage check
            if available > 0:
                implied_lev = (qty * entry_price) / available
                if implied_lev > config.MAX_LEVERAGE:
                    print(f"[order] REJECTED: implied leverage {implied_lev:.1f}x > max {config.MAX_LEVERAGE}x")
                    return 0.0

        print(f"[order] Risk: INR {risk_inr:.0f} = ${risk_usdt:.2f} USDT (rate INR {inr_usdt:.2f}/USDT) qty={qty}")
        return qty

"""Bybit order execution — pybit library, demo/live switchable.

Usage:
    from bybit_order import BybitTrader
    trader = BybitTrader()  # reads .env, fetches instruments, sets leverage
    trader.place_market_order("Buy", "0.001", stop_loss="78000")
"""

import os
import sys
import math
import time
import random
import logging
import uuid
from typing import Optional
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import config

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

logger = logging.getLogger("bybit_order")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Retry config
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 30.0
# Errors that are safe to retry (network, rate limit, transient)
RETRYABLE_CODES = {10006, 10001, 10002, 10003, 10004, 10005, 10010, -1}
# Errors that should NOT be retried (order logic errors)
NON_RETRYABLE_CODES = {110003, 110012, 110013, 110014, 110015, 110016, 110017}


class BybitTrader:
    """Bybit order execution — demo or live based on .env."""

    def __init__(self):
        self.api_key = os.getenv("BYBIT_API_KEY", "")
        self.api_secret = os.getenv("BYBIT_API_SECRET", "")
        self.demo = os.getenv("BYBIT_DEMO", "true").lower() == "true"
        self.symbol = os.getenv("BYBIT_SYMBOL", "BTCUSDT")

        # Instrument info — fetched from Bybit API, fallback to config
        self.qty_precision = config.QTY_PRECISION
        self.qty_step = 10 ** (-config.QTY_PRECISION)  # e.g. 0.001
        self.min_qty = config.MIN_BTC_QTY
        self.tick_size = 0.1
        self.min_notional = 5.0

        if not self.api_key or not self.api_secret:
            logger.warning("No Bybit API keys in .env — order execution disabled")
            self.session = None
            return

        self.session = HTTP(
            testnet=False,
            demo=self.demo,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )
        mode = "DEMO" if self.demo else "LIVE"
        logger.info(f"Bybit {mode} mode — symbol={self.symbol}")

        # Fetch instrument info from exchange
        self._fetch_instruments()

    def _fetch_instruments(self):
        """Fetch tick size, qty step, min qty from Bybit API. Fallback to config."""
        if not self.is_connected:
            return
        try:
            resp = self.session.get_instruments_info(category="linear", symbol=self.symbol)
            info = resp["result"]["list"][0]
            lot = info.get("lotSizeFilter", {})
            price = info.get("priceFilter", {})

            self.min_qty = float(lot.get("minOrderQty", config.MIN_BTC_QTY))
            self.qty_step = float(lot.get("qtyStep", 10 ** (-config.QTY_PRECISION)))
            self.tick_size = float(price.get("tickSize", 0.1))
            self.min_notional = float(lot.get("minNotionalValue", 5))

            # Derive precision from qty_step (0.001 -> 3 decimals)
            if self.qty_step > 0:
                self.qty_precision = max(0, round(-math.log10(self.qty_step)))

            logger.info(f"Instruments: tick={self.tick_size} qty_step={self.qty_step} "
                        f"min_qty={self.min_qty} min_notional={self.min_notional}")
        except Exception as e:
            logger.warning(f"Instrument fetch failed (using config defaults): {e}")

    def format_price(self, price: float) -> str:
        tick = self.tick_size or 0.1
        decimals = max(0, round(-math.log10(tick))) if tick > 0 else 1
        return f"{price:.{decimals}f}"

    def format_qty(self, qty: float) -> str:
        return f"{qty:.{self.qty_precision}f}"

    def set_leverage(self, leverage: int = None) -> dict:
        """Set leverage on Bybit. Called once on startup."""
        if not self.is_connected:
            return {"retCode": -1, "retMsg": "no session"}

        lev = str(leverage or config.MAX_LEVERAGE)
        try:
            resp = self.session.set_leverage(
                category="linear",
                symbol=self.symbol,
                buyLeverage=lev,
                sellLeverage=lev,
            )
            if resp.get("retCode") == 0:
                logger.info(f"Leverage set: {lev}x")
            else:
                logger.warning(f"Leverage set failed: {resp.get('retMsg', 'unknown')} (may already be set)")
            return resp
        except Exception as e:
            logger.warning(f"Leverage set exception: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    def set_margin_mode(self, mode: str = None) -> dict:
        """Set margin mode on Bybit. Called once on startup.

        Args:
            mode: "isolated" (each position has own margin) or "cross" (shared).
                  Defaults to config.MARGIN_MODE.

        Isolated = safer: only that position's margin is at risk on liquidation.
        Cross = default on Bybit UNIFIED: entire account margin is shared.
        """
        if not self.is_connected:
            return {"retCode": -1, "retMsg": "no session"}

        mode = mode or config.MARGIN_MODE
        trade_mode = 1 if mode.lower() == "isolated" else 0  # 1=Isolated, 0=Cross
        lev = str(config.MAX_LEVERAGE)

        try:
            resp = self.session.switch_margin_mode(
                category="linear",
                symbol=self.symbol,
                tradeMode=trade_mode,
                buyLeverage=lev,
                sellLeverage=lev,
            )
            if resp.get("retCode") == 0:
                logger.info(f"Margin mode set: {mode.upper()} (tradeMode={trade_mode})")
            else:
                logger.warning(f"Margin mode set failed: {resp.get('retMsg', 'unknown')} (may already be set)")
            return resp
        except Exception as e:
            logger.warning(f"Margin mode set exception: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    @property
    def is_connected(self) -> bool:
        """Cheap local check — True if session object exists.

        Does NOT make a network call. Use _healthy() for liveness.
        Guards must never depend on live network state (H10 fix).
        """
        return self.session is not None

    @property
    def _healthy(self) -> bool:
        """Cached liveness probe — True if last _probe() succeeded.

        Updated by _session_watch every 30s. Do NOT call on hot paths.
        """
        return getattr(self, "_last_probe_ok", self.session is not None)

    def _set_probe_result(self, ok: bool):
        """Called by _session_watch and _probe in low-frequency paths."""
        self._last_probe_ok = ok

    def _probe(self) -> bool | None:
        """Ping the exchange via the cheapest real API call.

        Returns True if the API responds, False on a clean exception, and None
        if no session object exists at all.
        Also caches result for _healthy property.
        """
        if self.session is None:
            self._set_probe_result(False)
            return None
        try:
            resp = self.session.get_wallet_balance(accountType="UNIFIED")
            code = resp.get("retCode", -1)
            ok = code == 0
            self._set_probe_result(ok)
            return ok
        except Exception as exc:  # noqa: BLE001 — library can raise on network/auth
            logger.debug("Session probe failed: %s", exc)
            self._set_probe_result(False)
            return False

    def _reconnect(self) -> bool:
        """Re-create the HTTP session from stored credentials and refresh params.

        Returns True if the session came back AND a subsequent probe succeeds.
        """
        if not self.api_key or not self.api_secret:
            logger.error("No API credentials — cannot reconnect")
            return False
        try:
            self.session = HTTP(
                testnet=False,
                demo=self.demo,
                api_key=self.api_key,
                api_secret=self.api_secret,
            )
        except Exception as exc:
            logger.error("Re-connect (create session) failed: %s", exc)
            return False
        ok = self._probe()
        if ok:
            try:
                self._fetch_instruments()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Re-connect session alive but instrument refresh failed: %s",
                    exc,
                )
            logger.info("Session reconnected successfully")
            return True
        logger.error("Re-connect: session created but probe failed")
        return False

    def get_wallet_balance(self) -> dict:
        """Get account balance."""
        if not self.is_connected:
            return {}
        try:
            resp = self.session.get_wallet_balance(accountType="UNIFIED")
            coins = resp["result"]["list"][0]["coin"]
            for c in coins:
                if c["coin"] == "USDT":
                    return {
                        "equity": float(c.get("equity", 0) or 0),
                        "available": float(c.get("walletBalance", 0) or 0),
                        "unrealised_pnl": float(c.get("unrealisedPnl", 0) or 0),
                    }
            return {}
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return {}

    def get_position_checked(self) -> tuple[bool, Optional[dict]]:
        """Position query with an explicit failure flag.

        Returns:
            (True, pos_dict)  — open position exists
            (True, None)      — query succeeded, genuinely NO position
            (False, None)     — the QUERY ITSELF failed (network/API error)
                                → state UNKNOWN; callers must NOT treat this
                                as "flat"
        """
        if not self.is_connected:
            return False, None
        try:
            resp = self.session.get_positions(category="linear", symbol=self.symbol)
            positions = resp["result"]["list"]
            for p in positions:
                if p["symbol"] == self.symbol and float(p.get("size", 0)) > 0:
                    return True, {
                        "side": p["side"],
                        "size": float(p["size"]),
                        "entry_price": float(p["avgPrice"]),
                        "unrealised_pnl": float(p.get("unrealisedPnl", 0)),
                        "leverage": p.get("leverage", "1"),
                        "liq_price": float(p["liqPrice"]) if p.get("liqPrice") else None,
                        # M5: the position's exchange-side SL — re-attached to
                        # close orders so the position is never naked between
                        # close-order placement and fill.
                        "stop_loss": float(p.get("stopLoss", 0) or 0),
                    }
            return True, None
        except Exception as e:
            logger.error(f"Position check failed: {e}")
            return False, None

    def get_position(self) -> dict | None:
        """Get current BTCUSDT position.

        NOTE: returns None BOTH for "no position" and "query failed" —
        legacy behavior kept for compatibility. New code should use
        get_position_checked() to distinguish the two.
        """
        ok, pos = self.get_position_checked()
        return pos if ok else None

    def place_market_order(
        self,
        side: str,
        qty: str,
        stop_loss: str = None,
        take_profit: str = None,
        order_link_id: str = None,
        reduce_only: bool = False,
        tpsl_mode: str = None,
    ) -> dict:
        """Place a market order with optional SL/TP.

        Args:
            side: "Buy" or "Sell"
            qty: string, e.g. "0.001"
            stop_loss: SL price as string
            take_profit: TP price as string
            order_link_id: unique ID for dedup (auto-generated if None)
            reduce_only: close-only order; never flips or increases position
        """
        if not self.is_connected:
            logger.warning("No session — order not placed")
            return {"retCode": -1, "retMsg": "no session"}

        params = {
            "category": "linear",
            "symbol": self.symbol,
            "side": side,
            "orderType": "Market",
            "qty": qty,
            "positionIdx": 0,  # One-way mode
        }

        if order_link_id:
            params["orderLinkId"] = order_link_id
        if stop_loss:
            params["stopLoss"] = stop_loss
        if take_profit:
            params["takeProfit"] = take_profit
        if reduce_only:
            params["reduceOnly"] = True
        if tpsl_mode:
            params["tpslMode"] = tpsl_mode
            if tpsl_mode == "Partial" and stop_loss:
                params["slOrderType"] = "Market"

        try:
            resp = self.session.place_order(**params)
            if resp.get("retCode") == 0:
                order_id = resp["result"]["orderId"]
                logger.info(f"ORDER PLACED: {side} {qty} {self.symbol} SL={stop_loss} TP={take_profit} id={order_id}")
            else:
                logger.error(f"ORDER FAILED: code={resp.get('retCode')} msg={resp.get('retMsg', 'unknown')}")
            return resp
        except Exception as e:
            logger.error(f"Order exception: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    def place_market_order_retry(
        self,
        side: str,
        qty: str,
        stop_loss: str = None,
        take_profit: str = None,
        order_link_id: str = None,
        reduce_only: bool = False,
        tpsl_mode: str = None,
    ) -> dict:
        """Place market order with exponential backoff retry, with per-attempt
        session self-heal.

        Retries on network/rate-limit errors (max 3 attempts).
        Does NOT retry on: insufficient margin, invalid qty, auth errors.
        Uses a single orderLinkId across retries for idempotency.

        Before every attempt, if the session is dead, attempt a reconnect
        once (self._reconnect).  If reconnect also fails, skip this attempt
        and move on (outer callers / C7 verification handle the resulting
        "position may be live" case — never assume the exchange is reachable).
        """
        last_resp = None
        link_id = order_link_id or f"bb_{uuid.uuid4().hex[:12]}"
        for attempt in range(MAX_RETRIES):
            # --- per-order self-heal ---
            if self._probe() is False:
                if not self._reconnect():
                    logger.warning("place_market_order_retry: session dead, reconnect failed")
                    if attempt < MAX_RETRIES - 1:
                        delay = min(RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), RETRY_MAX_DELAY)
                        time.sleep(delay)
                    continue
            resp = self.place_market_order(side, qty, stop_loss, take_profit, order_link_id=link_id,
                                            reduce_only=reduce_only, tpsl_mode=tpsl_mode)
            resp["_order_link_id"] = link_id

            if resp.get("retCode") == 0:
                return resp

            last_resp = resp
            ret_code = resp.get("retCode", -1)
            ret_msg = resp.get("retMsg", "unknown")

            # Don't retry on order logic errors
            if ret_code in NON_RETRYABLE_CODES:
                logger.error(f"Order rejected (not retryable): code={ret_code} {ret_msg}")
                return resp

            # Don't retry if this is a duplicate order (it already went through)
            if "duplicate" in ret_msg.lower() or "already" in ret_msg.lower():
                logger.warning(f"Order may be duplicate: {ret_msg}")
                return resp

            # Retry on transient errors
            if attempt < MAX_RETRIES - 1:
                delay = min(RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), RETRY_MAX_DELAY)
                logger.warning(f"Order failed (attempt {attempt + 1}/{MAX_RETRIES}): {ret_msg} — retrying in {delay:.1f}s")
                time.sleep(delay)
            else:
                logger.error(f"Order failed after {MAX_RETRIES} attempts: {ret_msg}")

        return last_resp or {"retCode": -1, "retMsg": "all retries failed"}

    def place_entry_with_partial_sl(
        self,
        side: str,
        qty: str,
        stop_loss: float,
        order_link_id: str = None,
    ) -> dict:
        sl = self.format_price(stop_loss)
        resp = self.place_market_order_retry(
            side, qty, stop_loss=sl, order_link_id=order_link_id,
            tpsl_mode="Partial",
        )
        if resp.get("retCode") == 0:
            link_id = resp.get("_order_link_id")
            time.sleep(0.15)
            ok, stops = self.get_open_stop_orders()
            attached = []
            if ok:
                attached = [
                    o for o in stops
                    if o.get("parentOrderLinkId") == link_id
                    and o.get("stopOrderType") == "PartialStopLoss"
                ]
            resp["_stop_order"] = attached[0] if attached else None
        return resp

    def close_reduce_only(self, qty: float, order_link_id: str = None) -> dict:
        ok, pos = self.get_position_checked()
        if not ok:
            return {"retCode": -1, "retMsg": "position query failed"}
        if pos is None:
            return {"retCode": 0, "retMsg": "no position", "closed": False}
        close_side = "Sell" if pos["side"] == "Buy" else "Buy"
        return self.place_market_order_retry(
            close_side, self.format_qty(qty), reduce_only=True,
            order_link_id=order_link_id,
        )

    def close_position_retry(self, max_attempts: int = 3) -> dict:
        """Close current position at market, with retries.

        Retry semantics (C1/C2 fix):
          - Re-checks the position before EVERY close attempt (position may
            already be gone — e.g. exchange-side SL fired between ticks).
          - Uses place_market_order_retry (3 inner attempts, single
            orderLinkId) per outer attempt.
          - Distinguishes query-failure (state unknown → keep retrying) from
            genuinely-flat (nothing to close → success).

        Returns:
            {"retCode": 0, ...}  — exchange position confirmed closed (or was
                                   already flat)
            {"retCode": -1, ...} — still open / state unknown after all
                                   attempts; caller must NOT record the exit
        """
        import random
        import time as _time

        last_err = "unknown"
        for attempt in range(max_attempts):
            ok, pos = self.get_position_checked()
            if not ok:
                last_err = "position query failed (state unknown)"
            elif pos is None:
                # Genuinely flat — nothing to close (SL may have fired
                # exchange-side). Treat as success.
                logger.info("close_position_retry: no position — already closed")
                return {"retCode": 0, "retMsg": "no position", "closed": False}
            else:
                close_side = "Sell" if pos["side"] == "Buy" else "Buy"
                if not self._has_protective_stop(pos):
                    panic = self._panic_sl_price(pos)
                    if panic is not None:
                        resp = self.update_sl(panic)
                        if resp.get("retCode") != 0:
                            logger.warning("panic SL placement failed before close: %s",
                                           resp.get("retMsg", "unknown"))
                resp = self.place_market_order_retry(close_side, str(pos["size"]),
                                                     reduce_only=True)
                if resp.get("retCode") == 0:
                    return {"retCode": 0, "retMsg": "closed", "closed": True,
                            "order_id": resp.get("result", {}).get("orderId")}
                last_err = resp.get("retMsg", "close order failed")

            if attempt < max_attempts - 1:
                delay = min(1.0 * (2 ** attempt) + random.uniform(0, 0.5), 5.0)
                logger.warning(f"close attempt {attempt + 1}/{max_attempts} failed: {last_err} — retrying in {delay:.1f}s")
                _time.sleep(delay)

        logger.error(f"close_position_retry FAILED after {max_attempts} attempts: {last_err}")
        return {"retCode": -1, "retMsg": f"close failed after {max_attempts} attempts: {last_err}"}

    def _has_protective_stop(self, pos: dict) -> bool:
        if float(pos.get("stop_loss", 0) or 0) > 0:
            return True
        ok, orders = self.get_open_stop_orders()
        if not ok:
            return True
        for o in orders:
            if (o.get("stopOrderType") in ("StopLoss", "PartialStopLoss", "TrailingStop")
                    and float(o.get("qty", 0) or 0) > 0):
                return True
        return False

    def _panic_sl_price(self, pos: dict) -> float | None:
        entry = float(pos.get("entry_price", 0) or 0)
        if entry <= 0:
            return None
        if pos.get("side") == "Buy":
            return entry * (1 - config.PANIC_SL_PCT / 100.0)
        return entry * (1 + config.PANIC_SL_PCT / 100.0)

    def close_position(self, side: str = None) -> dict:
        """Close current position at market.

        NOTE: single attempt, and get_position() failure is indistinguishable
        from flat. New code should use close_position_retry().
        """
        if not self.is_connected:
            return {"retCode": -1, "retMsg": "no session"}

        pos = self.get_position()
        if not pos:
            logger.info("No position to close")
            return {"retCode": 0, "retMsg": "no position"}

        close_side = "Sell" if pos["side"] == "Buy" else "Buy"
        qty = str(pos["size"])

        return self.place_market_order(close_side, qty, reduce_only=True)

    def get_open_stop_orders(self) -> tuple[bool, list[dict]]:
        """Return open conditional/TP-SL orders for the symbol."""
        if not self.is_connected:
            return False, []
        try:
            resp = self.session.get_open_orders(
                category="linear", symbol=self.symbol,
                orderFilter="StopOrder", limit=50,
            )
            if resp.get("retCode") != 0:
                logger.error("open stop-order query failed: %s", resp.get("retMsg", "unknown"))
                return False, []
            active_statuses = {"New", "Untriggered", "PartiallyFilled", "Triggered", "PendingCancel"}
            out = []
            for o in resp.get("result", {}).get("list", []):
                status = o.get("orderStatus")
                if not status or status in active_statuses:
                    out.append(o)
            return True, out
        except Exception as e:
            logger.error(f"open stop-order query exception: {e}")
            return False, []

    def amend_partial_sl(self, order_id: str, trigger_price: float) -> dict:
        """Move an existing partial SL in place."""
        if not self.is_connected:
            return {"retCode": -1, "retMsg": "no session"}
        try:
            resp = self.session.amend_order(
                category="linear", symbol=self.symbol, orderId=order_id,
                triggerPrice=self.format_price(trigger_price),
            )
            if resp.get("retCode") == 0:
                logger.info("PARTIAL SL AMENDED: %s -> %s", order_id,
                            self.format_price(trigger_price))
            else:
                logger.error("PARTIAL SL AMEND FAILED: %s %s",
                             order_id, resp.get("retMsg", "unknown"))
            return resp
        except Exception as e:
            logger.error(f"partial SL amend exception: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    def place_partial_sl(self, qty: float, stop_loss: float) -> dict:
        """Add a partial SL when no amendable order exists."""
        if not self.is_connected:
            return {"retCode": -1, "retMsg": "no session"}
        ok, before = self.get_open_stop_orders()
        before_ids = {o.get("orderId") for o in before} if ok else set()
        try:
            resp = self.session.set_trading_stop(
                category="linear", symbol=self.symbol, tpslMode="Partial",
                positionIdx=0, stopLoss=self.format_price(stop_loss),
                slSize=self.format_qty(qty),
            )
            if resp.get("retCode") == 0:
                time.sleep(0.2)
                ok, after = self.get_open_stop_orders()
                new = [o for o in after if o.get("orderId") not in before_ids] if ok else []
                resp["_stop_order"] = new[0] if new else None
            else:
                logger.error("PARTIAL SL PLACE FAILED: %s", resp.get("retMsg", "unknown"))
            return resp
        except Exception as e:
            logger.error(f"partial SL place exception: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    def cancel_order_by_id(self, order_id: str) -> dict:
        """Cancel one open order by exchange orderId."""
        if not self.is_connected:
            return {"retCode": -1, "retMsg": "no session"}
        try:
            resp = self.session.cancel_order(
                category="linear", symbol=self.symbol, orderId=order_id,
            )
            if resp.get("retCode") == 0:
                logger.info("ORDER CANCELLED: %s", order_id)
            else:
                logger.error("ORDER CANCEL FAILED: %s %s",
                             order_id, resp.get("retMsg", "unknown"))
            return resp
        except Exception as e:
            logger.error(f"order cancel exception: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    def _order_info(self, o: dict) -> dict:
        return {
            "orderId": o.get("orderId"),
            "orderLinkId": o.get("orderLinkId"),
            "status": o.get("orderStatus"),
            "cumExecQty": float(o.get("cumExecQty", 0) or 0),
            "avgPrice": float(o.get("avgPrice", 0) or 0),
            "cumExecFee": float(o.get("cumExecFee", 0) or 0),
            "cumExecValue": float(o.get("cumExecValue", 0) or 0),
            "qty": float(o.get("qty", 0) or 0),
            "side": o.get("side"),
            "createdTime": o.get("createdTime"),
            "updatedTime": o.get("updatedTime"),
        }

    def get_order_by_id(self, order_id: str) -> tuple[bool, Optional[dict]]:
        """Query an order by exchange orderId (open first, then history)."""
        if not self.is_connected:
            return False, None
        query_ok = False
        for fn in (self.session.get_open_orders, self.session.get_order_history):
            try:
                resp = fn(category="linear", symbol=self.symbol, orderId=order_id)
                if resp.get("retCode") != 0:
                    continue
                query_ok = True
                for o in resp.get("result", {}).get("list", []):
                    if o.get("orderId") == order_id:
                        return True, self._order_info(o)
            except Exception as e:
                logger.error(f"order-by-id query failed: {e}")
        return query_ok, None

    def get_order_by_link_id(self, order_link_id: str) -> tuple[bool, Optional[dict]]:
        """C7: query open orders + order history for an orderLinkId."""
        if not self.is_connected:
            return False, None
        try:
            resp = self.session.get_open_orders(
                category="linear", symbol=self.symbol, orderLinkId=order_link_id)
            for o in resp.get("result", {}).get("list", []):
                if o.get("orderLinkId") == order_link_id:
                    return True, self._order_info(o)
        except Exception as e:
            logger.error(f"open-order query failed: {e}")
            return False, None
        try:
            resp = self.session.get_order_history(
                category="linear", symbol=self.symbol, orderLinkId=order_link_id)
            for o in resp.get("result", {}).get("list", []):
                if o.get("orderLinkId") == order_link_id:
                    return True, self._order_info(o)
            return True, None
        except Exception as e:
            logger.error(f"order-history query failed: {e}")
            return False, None

    def get_order_fill(self, order_link_id: str) -> tuple[str, Optional[dict]]:
        """Resolve an order's actual fill without using aggregate position size."""
        ok, order = self.get_order_by_link_id(order_link_id)
        if not ok:
            return "unknown", None
        if order is None:
            return "flat", None
        if order["cumExecQty"] > 0:
            return "filled", order
        if order["status"] in ("Cancelled", "Rejected", "Deactivated", "Expired"):
            return "flat", None
        return "unknown", None

    def get_order_executions(self, order_id: str) -> tuple[bool, list[dict]]:
        """Return fills for an order, including triggered partial SL orders."""
        if not self.is_connected:
            return False, []
        try:
            resp = self.session.get_executions(
                category="linear", symbol=self.symbol, orderId=order_id, limit=50,
            )
            if resp.get("retCode") != 0:
                logger.error("execution query failed: %s", resp.get("retMsg", "unknown"))
                return False, []
            out = []
            for e in (resp.get("result", {}) or {}).get("list", []):
                out.append({
                    "execId": e.get("execId"),
                    "orderId": e.get("orderId"),
                    "orderLinkId": e.get("orderLinkId"),
                    "execQty": float(e.get("execQty", 0) or 0),
                    "execPrice": float(e.get("execPrice", 0) or 0),
                    "execFee": float(e.get("execFee", 0) or 0),
                    "execTime": int(e.get("execTime", 0) or 0),
                    "closedSize": float(e.get("closedSize", 0) or 0),
                    "stopOrderType": e.get("stopOrderType"),
                    "side": e.get("side"),
                })
            return True, out
        except Exception as e:
            logger.error(f"execution query exception: {e}")
            return False, []

    def verify_entry_order(self, order_link_id: str,
                           expected_side: str = None) -> tuple[str, Optional[dict]]:
        """Resolve a market entry by its own order fill, never by aggregate size."""
        ok, order = self.get_order_by_link_id(order_link_id)
        if not ok:
            return "unknown", None
        if order is not None:
            want = ("Buy" if expected_side == "long"
                    else "Sell" if expected_side == "short" else None)
            if want and order.get("side") and order["side"] != want:
                logger.error("verify_entry_order: order side mismatch "
                             "(%s vs expected %s) — state unknown", order["side"], want)
                return "unknown", None
            if order["cumExecQty"] > 0:
                return "filled", order
            if order["status"] in ("Cancelled", "Rejected", "Deactivated", "Expired"):
                return "flat", None
            return "unknown", None
        ok_pos, pos = self.get_position_checked()
        if ok_pos and pos is None:
            return "flat", None
        return "unknown", None

    def cancel_all_orders(self) -> dict:
        """Cancel all open orders."""
        if not self.is_connected:
            return {"retCode": -1, "retMsg": "no session"}
        try:
            resp = self.session.cancel_all_orders(category="linear", symbol=self.symbol)
            logger.info("All orders cancelled")
            return resp
        except Exception as e:
            logger.error(f"Cancel failed: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    def update_sl(self, new_sl: float) -> dict:
        """Update stop loss on existing position via set_trading_stop.

        This syncs the exchange-side conditional SL order.
        Bybit creates a Market order by default (tpslMode=Full).
        Rate limit: 10 req/sec — safe for once per 15m candle.
        """
        if not self.is_connected:
            logger.warning("No session — SL not updated")
            return {"retCode": -1, "retMsg": "no session"}
        try:
            resp = self.session.set_trading_stop(
                category="linear",
                symbol=self.symbol,
                tpslMode="Full",
                positionIdx=0,
                stopLoss=f"{new_sl:.2f}",
            )
            if resp.get("retCode") == 0:
                logger.info(f"SL UPDATED: {new_sl:.2f}")
            else:
                logger.error(f"SL UPDATE FAILED: {resp.get('retMsg', 'unknown')}")
            return resp
        except Exception as e:
            logger.error(f"SL update exception: {e}")
            return {"retCode": -1, "retMsg": str(e)}

"""Bybit order execution — pybit library, demo/live switchable.

Usage:
    from bybit_order import BybitTrader
    trader = BybitTrader()  # reads .env
    trader.place_market_order("Buy", "0.001", stop_loss="78000")
"""

import os
import logging
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

logger = logging.getLogger("bybit_order")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class BybitTrader:
    """Bybit order execution — demo or live based on .env."""

    def __init__(self):
        self.api_key = os.getenv("BYBIT_API_KEY", "")
        self.api_secret = os.getenv("BYBIT_API_SECRET", "")
        self.demo = os.getenv("BYBIT_DEMO", "true").lower() == "true"
        self.symbol = os.getenv("BYBIT_SYMBOL", "BTCUSDT")
        self.qty_precision = 3  # BTCUSDT: 0.001

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

    @property
    def is_connected(self) -> bool:
        return self.session is not None

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

    def get_position(self) -> dict | None:
        """Get current BTCUSDT position."""
        if not self.is_connected:
            return None
        try:
            resp = self.session.get_positions(category="linear", symbol=self.symbol)
            positions = resp["result"]["list"]
            for p in positions:
                if p["symbol"] == self.symbol and float(p.get("size", 0)) > 0:
                    return {
                        "side": p["side"],
                        "size": float(p["size"]),
                        "entry_price": float(p["avgPrice"]),
                        "unrealised_pnl": float(p.get("unrealisedPnl", 0)),
                        "leverage": p.get("leverage", "1"),
                        "liq_price": float(p["liqPrice"]) if p.get("liqPrice") else None,
                    }
            return None
        except Exception as e:
            logger.error(f"Position check failed: {e}")
            return None

    def place_market_order(
        self,
        side: str,
        qty: str,
        stop_loss: str = None,
        take_profit: str = None,
    ) -> dict:
        """Place a market order with optional SL/TP.

        Args:
            side: "Buy" or "Sell"
            qty: string, e.g. "0.001"
            stop_loss: SL price as string
            take_profit: TP price as string
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
            "timeInForce": "GTC",
            "positionIdx": 0,  # One-way mode
        }

        if stop_loss:
            params["stopLoss"] = stop_loss
        if take_profit:
            params["takeProfit"] = take_profit

        try:
            resp = self.session.place_order(**params)
            if resp.get("retCode") == 0:
                order_id = resp["result"]["orderId"]
                logger.info(f"ORDER PLACED: {side} {qty} {self.symbol} SL={stop_loss} TP={take_profit} id={order_id}")
            else:
                logger.error(f"ORDER FAILED: {resp.get('retMsg', 'unknown')}")
            return resp
        except Exception as e:
            logger.error(f"Order exception: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    def close_position(self, side: str = None) -> dict:
        """Close current position at market."""
        if not self.is_connected:
            return {"retCode": -1, "retMsg": "no session"}

        pos = self.get_position()
        if not pos:
            logger.info("No position to close")
            return {"retCode": 0, "retMsg": "no position"}

        close_side = "Sell" if pos["side"] == "Buy" else "Buy"
        qty = str(pos["size"])

        return self.place_market_order(close_side, qty)

    def calculate_qty(self, entry_price: float, stop_loss: float, risk_usdt: float = 50.0) -> str:
        """Calculate position size based on risk.

        Args:
            entry_price: expected entry price
            stop_loss: stop loss price
            risk_usdt: risk in USDT per trade
        """
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance <= 0:
            return "0.001"

        qty = risk_usdt / stop_distance
        # Round to Bybit BTCUSDT precision (0.001)
        qty = max(0.001, round(qty, self.qty_precision))
        return str(qty)

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

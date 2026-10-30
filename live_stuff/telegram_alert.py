"""Telegram alerts for Backbencher book 107 — entry, exit, errors, status.

Usage:
    from telegram_alert import TelegramAlert
    tg = TelegramAlert()  # reads TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID from .env
    tg.send("Hello from Backbencher!")
"""

import os
import json
import urllib.request
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger("telegram_alert")


class TelegramAlert:
    """Send alerts to Telegram via Bot API (free, no paid service)."""

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.chat_id)
        if self.enabled:
            logger.info("Telegram alerts enabled")
        else:
            logger.info("Telegram alerts disabled (no token/chat_id in .env)")

    def send(self, text: str) -> bool:
        """Send a message to Telegram. Returns True on success."""
        if not self.enabled:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = json.dumps({"chat_id": self.chat_id, "text": text}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status == 200
        except Exception as e:
            logger.warning(f"Telegram send failed: {e}")
            return False

    def trade_entry(self, direction: str, entry: float, sl: float, qty: float,
                    risk_inr: float, risk_usdt: float, rate: float):
        """Alert on trade entry."""
        arrow = "🟢" if direction == "long" else "🔴"
        msg = (
            f"{arrow} TRADE ENTRY\n\n"
            f"BTCUSDT PERP\n"
            f"Direction: {direction.upper()}\n"
            f"Entry: {entry:,.2f}\n"
            f"SL: {sl:,.2f}\n"
            f"Qty: {qty} BTC\n"
            f"Risk: INR {risk_inr:.0f} = ${risk_usdt:.2f}\n"
            f"Rate: INR {rate:.2f}/USDT"
        )
        return self.send(msg)

    def trade_exit(self, reason: str, fill_price: float, r_multiple: float,
                   direction: str = "", entry_price: float = 0):
        """Alert on trade exit."""
        emoji = "✅" if r_multiple > 0 else "❌"
        msg = (
            f"{emoji} TRADE EXIT\n\n"
            f"BTCUSDT PERP\n"
            f"Direction: {direction.upper()}\n"
            f"Entry: {entry_price:,.2f}\n"
            f"Exit: {fill_price:,.2f}\n"
            f"Result: {r_multiple:+.2f}R\n"
            f"Reason: {reason.upper()}"
        )
        return self.send(msg)

    def error(self, message: str):
        """Alert on error."""
        return self.send(f"⚠️ ERROR\n\n{message}")

    def status(self, message: str):
        """Alert on status update."""
        return self.send(f"📊 STATUS\n\n{message}")

    def daily_halt(self, loss_r: float, limit_r: float, multiplier: int):
        """Alert when daily loss limit is breached."""
        msg = (
            f"🛑 DAILY LOSS LIMIT BREACHED\n\n"
            f"Loss: {loss_r:.0f}R\n"
            f"Limit: {limit_r:.0f}R ({multiplier}x risk)\n\n"
            f"Trading halted until tomorrow."
        )
        return self.send(msg)

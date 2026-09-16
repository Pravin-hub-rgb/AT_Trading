"""INR/USDT rate manager — singleton with disk cache + fallback chain.

Architecture (stolen from Ghoststreak):
  Startup: load from last_rate.json (instant, 0ms)
  On trade: if stale (>15 min), fetch in background
  Fallback chain: CoinGecko -> ExchangeRate-API -> disk cache -> emergency 95.0
  On trade: get_rate() returns cached value (0ms, no network)

Usage:
    from rate_manager import RateManager
    rm = RateManager()
    rate = rm.get_rate()  # instant, cached
"""

import json
import time
import logging
from pathlib import Path

import config

logger = logging.getLogger("rate_manager")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class RateManager:
    """Singleton USDT/INR rate manager with disk cache + fallback chain."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "initialized"):
            return
        self.initialized = True

        self.usdt_inr_rate = config.EMERGENCY_RATE
        self.rate_last_updated = 0
        self.rate_file = config.RATE_CACHE_FILE
        self._load_from_disk()

    def _load_from_disk(self):
        """Load cached rate from last_rate.json on startup."""
        if self.rate_file.exists():
            try:
                data = json.loads(self.rate_file.read_text())
                self.usdt_inr_rate = float(data["rate"])
                self.rate_last_updated = data["timestamp"]
                age_min = (time.time() - self.rate_last_updated) / 60
                logger.info(f"Rate loaded from disk: INR {self.usdt_inr_rate:.2f} ({age_min:.0f} min old)")
            except Exception as e:
                logger.warning(f"Failed to load cached rate: {e}")

    def _save_to_disk(self):
        """Save current rate to last_rate.json."""
        try:
            data = {"rate": self.usdt_inr_rate, "timestamp": self.rate_last_updated}
            self.rate_file.write_text(json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to save rate: {e}")

    def _fetch_rate(self) -> float | None:
        """Fetch fresh rate from APIs. Returns None if all fail."""
        import requests

        # Layer 1: CoinGecko (live crypto market price)
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "tether", "vs_currencies": "inr"},
                timeout=10,
            )
            resp.raise_for_status()
            rate = float(resp.json()["tether"]["inr"])
            logger.info(f"Rate fetched: INR {rate:.2f} (CoinGecko)")
            return rate
        except Exception as e:
            logger.debug(f"CoinGecko failed: {e}")

        # Layer 2: ExchangeRate-API (USD/INR fiat, updated daily)
        try:
            resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
            resp.raise_for_status()
            rate = float(resp.json()["rates"]["INR"])
            logger.info(f"Rate fetched: INR {rate:.2f} (ExchangeRate-API)")
            return rate
        except Exception as e:
            logger.debug(f"ExchangeRate-API failed: {e}")

        return None

    def update(self):
        """Fetch fresh rate if stale. Called on trade entry."""
        age = time.time() - self.rate_last_updated
        if age < config.RATE_UPDATE_INTERVAL:
            return  # still fresh

        new_rate = self._fetch_rate()
        if new_rate and new_rate > 0:
            old = self.usdt_inr_rate
            self.usdt_inr_rate = new_rate
            self.rate_last_updated = time.time()
            self._save_to_disk()
            if abs(new_rate - old) > 0.05:
                logger.info(f"Rate updated: INR {old:.2f} -> INR {new_rate:.2f}")
        else:
            logger.warning("All rate sources failed, using cached value")

        # Emergency: too stale?
        stale_hours = (time.time() - self.rate_last_updated) / 3600
        if stale_hours > 24 and self.usdt_inr_rate != config.EMERGENCY_RATE:
            logger.warning(f"RATE TOO STALE ({stale_hours:.0f}h) -- USING EMERGENCY {config.EMERGENCY_RATE}")
            print("\n" + "=" * 70)
            print(f"   USDT/INR RATE EMERGENCY -- USING {config.EMERGENCY_RATE}")
            print("   CHECK INTERNET OR COINGECKO API")
            print("=" * 70 + "\n")
            self.usdt_inr_rate = config.EMERGENCY_RATE
            self.rate_last_updated = time.time()

    def age_min(self) -> float:
        """Minutes since the cached rate was last refreshed."""
        return (time.time() - self.rate_last_updated) / 60.0

    def is_stale(self) -> bool:
        """True if the cached rate is older than RATE_UPDATE_INTERVAL."""
        return (time.time() - self.rate_last_updated) >= config.RATE_UPDATE_INTERVAL

    def get_rate(self) -> float:
        """Get cached rate instantly (0ms, no network). Call update() first if needed."""
        return self.usdt_inr_rate

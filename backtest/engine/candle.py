"""Candle data structure - holds OHLCV data only."""

from dataclasses import dataclass


@dataclass
class Candle:
    """Single OHLCV candle.
    
    Only closed candles are ever processed by the walker.
    The 'closed' flag ensures we never process incomplete data.
    """
    ts: int          # unix seconds, candle OPEN time
    date: str        # human-readable date string
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    closed: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "Candle":
        """Create Candle from a dict (e.g., from Binance REST API)."""
        return cls(
            ts=int(d["ts"]),
            date=d.get("date", ""),
            open=float(d["open"]),
            high=float(d["high"]),
            low=float(d["low"]),
            close=float(d["close"]),
            volume=float(d.get("volume", 0.0)),
            closed=bool(d.get("closed", True)),
        )

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "ts": self.ts,
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "closed": self.closed,
        }

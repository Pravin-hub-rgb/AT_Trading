"""Boot data — fetch the rolling candle window from Binance SPOT REST
(same source as data/btc CSVs: api.binance.com/api/v3/klines)."""
import json
import urllib.request

from src.live.aggregator import to_ist_wall

BASE = "https://api.binance.com/api/v3/klines"
_UA = {"User-Agent": "Mozilla/5.0"}


def fetch_klines(symbol: str, interval: str, total: int,
                 end_time_ms: int | None = None) -> list[dict]:
    """Fetch the last `total` closed candles (may include the running one —
    caller filters by is_closed / drops the last if needed)."""
    out: list[list] = []
    while len(out) < total:
        url = f"{BASE}?symbol={symbol}&interval={interval}&limit=1000"
        if end_time_ms is not None:
            url += f"&endTime={end_time_ms}"
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.loads(r.read())
        if not rows:
            break
        out = rows + out
        end_time_ms = int(rows[0][0]) - 1
        if len(rows) < 1000:
            break
    return [{"date": to_ist_wall(int(k[0]) // 1000), "ts": int(k[0]) // 1000,
             "open": float(k[1]), "high": float(k[2]),
             "low": float(k[3]), "close": float(k[4])} for k in out[-total:]]

"""Backbencher live feeder core — candle aggregation.

Adapted from the proven `BTC_GhostStreak_Strategy 3 / data_streamer.py`
(tick stream + official kline sync + bucket rollover detection), stripped
of websocket I/O so it can be replay-tested deterministically.

Conventions (D6, live_trading_doc.md):
    - ticks arrive with exchange UTC epoch ms
    - emitted candles carry BOTH:
        date: IST wall-clock string  (utc + 19800 s, formatted as if UTC)
        ts:   epoch seconds          (= utc epoch; nets out to the same
              convention btc_config.load_btc_df derives for the CSVs)
    - at an hour boundary the 1h close event is emitted BEFORE the 4th 15m
      close of the finished hour, so the engine always updates HTF window
      state before acting on the LTF decision of that boundary.

Timestamp math note: CSV ts = (IST wall-clock read as UTC epoch) - 19800
= true UTC epoch. So utc epoch in == ts out, and date = utc + 19800.
"""
from datetime import datetime, timezone

IST_OFFSET_SEC = 5 * 3600 + 30 * 60  # 19800

TF_SEC = {"15m": 900, "1h": 3600}


def to_ist_wall(utc_s: int) -> str:
    return datetime.fromtimestamp(utc_s + IST_OFFSET_SEC, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")


class LiveAggregator:
    """Forms 15m and 1h candles from ticks; emits close events on rollover.

    on_candle_close(candle: dict) is called with
        {"tf", "date", "ts", "open", "high", "low", "close"}
    """

    def __init__(self, on_candle_close):
        self.on_candle_close = on_candle_close
        self.forming = {}       # tf -> {"start_s", o,h,l,c}
        self.last_closed = {}   # tf -> last emitted candle
        self.n_ticks = 0
        self.n_closes = {"15m": 0, "1h": 0}

    def on_tick(self, price: float, utc_ms: int):
        """Feed one tick. Returns the list of candle-close events emitted
        by THIS tick (0, 1 or 2 events; order: 1h first, then 15m)."""
        self.n_ticks += 1
        events = []
        s = utc_ms // 1000
        for tf in ("1h", "15m"):  # hour boundary: 1h closes before 15m
            step = TF_SEC[tf]
            bucket = s - (s % step)
            f = self.forming.get(tf)
            if f is None:
                self.forming[tf] = {"start_s": bucket, "o": price, "h": price,
                                    "l": price, "c": price}
            elif bucket != f["start_s"]:
                out = self._emit(tf, f)
                events.append(out)
                self.forming[tf] = {"start_s": bucket, "o": price, "h": price,
                                    "l": price, "c": price}
            else:
                if price > f["h"]:
                    f["h"] = price
                if price < f["l"]:
                    f["l"] = price
                f["c"] = price
        for e in events:
            self.on_candle_close(e)
        return events

    def on_official_close(self, tf: str, o, h, l, c, utc_open_ms: int):
        """Official kline close (exchange truth) — overrides the tick-formed
        candle for the bucket (official-priority, same as the stolen
        streamer). Emits the close event for the bucket that just ended."""
        start_s = (utc_open_ms // 1000)
        f = self.forming.get(tf)
        if f is not None and f["start_s"] == start_s:
            f.update(o=float(o), h=float(h), l=float(l), c=float(c))
        out = self._emit(tf, {"start_s": start_s, "o": float(o), "h": float(h),
                              "l": float(l), "c": float(c)})
        self.forming.pop(tf, None)  # next tick re-seeds the new bucket
        return out

    def _emit(self, tf, f):
        out = {"tf": tf, "date": to_ist_wall(f["start_s"]), "ts": f["start_s"],
               "open": f["o"], "high": f["h"], "low": f["l"], "close": f["c"]}
        self.last_closed[tf] = out
        self.n_closes[tf] += 1
        return out

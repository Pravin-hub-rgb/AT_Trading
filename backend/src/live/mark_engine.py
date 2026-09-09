"""Backbencher live marks engine — rolling-window swing chains on live candles.

Every closed candle: append to rolling window -> recompute the full swing
chain (same compute_btc_swings as the backtester) -> collect the marks that
fired on the just-closed bar. No incremental state (D2, live_trading_doc.md).
"""
from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle


class MarkEngine:
    def __init__(self, tf: str, min_bars: int, window_bars: int):
        self.tf = tf
        self.min_bars = int(min_bars)
        self.window_bars = int(window_bars)
        self.candles = []          # dicts: date/ts/open/high/low/close
        self.n_recomputes = 0
        self.last_marks = []       # marks fired on the most recent close

    def seed(self, candles: list[dict]):
        self.candles = list(candles)[-self.window_bars:]

    def on_close(self, candle: dict):
        """Register a closed candle; return (new_marks, n_swings)."""
        self.candles.append(candle)
        if len(self.candles) > self.window_bars:
            self.candles = self.candles[-self.window_bars:]
        flow = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                           low=c["low"], close=c["close"]) for c in self.candles]
        swings = compute_btc_swings(flow, opts={"minBars": max(2, self.min_bars)},
                                    max_swings=max(1, len(flow) // 2))
        self.n_recomputes += 1
        last_idx = len(self.candles) - 1
        marks = []
        for s in swings:
            for b in s.get("breaks", []):
                if int(b.get("idx", -1)) == last_idx:
                    cidx = int(s.get("confirmed_at_idx", -1))
                    marks.append({
                        "tf": self.tf,
                        "kind": b["kind"],
                        "dir": b["dir"],
                        "px": float(b["px"]),
                        "swing_no": s.get("swing_index"),
                        "swing_kind": s.get("kind"),
                        "bar_date": self.candles[last_idx]["date"],
                        "swing_confirmed_at": s.get("confirmed_at_time", ""),
                        "note": "fired pre-confirmation (normal: marks print "
                                "before the swing's chop confirm)",
                    })
        self.last_marks = marks
        return marks, len(swings)

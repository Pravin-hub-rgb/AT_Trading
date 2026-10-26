"""Parity test: IncrementalSim driver vs direct batch sim."""
import os, sys, random, datetime, copy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "live"))

from _vendored.walker import FlowCandle
from _vendored.persistent_swing import PersistentSwingEngine
from _vendored.unified import simulate_htf_ltf_streak_halt
from book import get_book_params
from live.incremental import IncrementalSim
from parity import trade_list_diff


def make_series(n15, seed=1):
    random.seed(seed)
    candles15 = []
    ts = 1700000000
    for i in range(n15):
        ts += 900
        o = random.uniform(100, 110); c = random.uniform(100, 110)
        hi = max(o, c) + random.uniform(0, 2); lo = min(o, c) - random.uniform(0, 2)
        dt = datetime.datetime.utcfromtimestamp(ts)
        candles15.append({"date": dt.strftime("%Y-%m-%d %H:%M:%S"), "ts": ts, "open": o, "high": hi, "low": lo, "close": c})
    candles1h = []
    for i in range(0, len(candles15) - 3, 4):
        chunk = candles15[i:i+4]
        candles1h.append({"date": chunk[-1]["date"], "ts": chunk[-1]["ts"],
                          "open": chunk[0]["open"], "high": max(x["high"] for x in chunk),
                          "low": min(x["low"] for x in chunk), "close": chunk[-1]["close"]})
    def swings(candles):
        eng = PersistentSwingEngine("15m" if len(candles) == len(candles15) else "1h")
        out = []
        for i, cd in enumerate(candles):
            fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"], low=cd["low"], close=cd["close"])
            r = eng.process_bar(fc, i)
            if r: out.append(r)
        try:
            os_ = eng.get_open_swing()
            if os_ and os_.get("breaks"): out = out + [os_]
        except Exception:
            pass
        return out
    sw15 = swings(candles15); sw1h = swings(candles1h)
    return candles15, candles1h, sw15, sw1h


def test_incremental_matches_batch():
    v18 = get_book_params(None)
    for seed in (1, 2, 4):
        c15, c1h, sw15, sw1h = make_series(600, seed=seed)
        # direct batch
        direct = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **v18)
        direct_trades = direct.get("ltf_trades", [])
        # incremental driver
        inc = IncrementalSim(v18, keep_days=90)
        res, changed = inc.on_bar(c15, c1h, sw15, sw1h, force=True)
        inc_trades = (res or {}).get("ltf_trades", [])
        diff = trade_list_diff(direct_trades, inc_trades)
        assert diff["equal"], f"seed={seed} mismatch: {diff}"
        # idempotency: second call with same input returns unchanged
        res2, changed2 = inc.on_bar(c15, c1h, sw15, sw1h)
        assert changed2 is False
        print(f"seed={seed}: OK ({len(direct_trades)} trades, idempotent)")
    print("ALL PASS")


if __name__ == "__main__":
    test_incremental_matches_batch()

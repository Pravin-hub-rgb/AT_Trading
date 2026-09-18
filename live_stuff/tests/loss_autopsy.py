"""LOSS AUTOPSY — read-only study of every trade the shipped v18 engine takes.

No experiment here. We run the COMMITTED engine (as-is), then examine every
trade: what was knowable AT ENTRY (using only candles[:i+1]) vs what happened.

Causal discipline: exit info is used ONLY to bucket trades. Every feature is
computed from data up to and including the entry bar.
"""
import sys, time
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

import bisect as bs

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))       # live_stuff
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from replay_harness import load_candles, INSTRUMENT                 # repo canonical loader
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import (
    simulate_htf_ltf_streak_halt, _chop_series_1h, _atr_pct_15m,
)
from src.walker import FlowCandle

_p = dict(get_v18_params(INSTRUMENT)); _p.update(V18_ENGINE)
PARAMS = {k: _p[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                             "atr_low_thresh", "atr_high_thresh", "mode",
                             "cooldown_bars", "max_consecutive_losses",
                             "htf_rr", "window_end"] if k in _p}
MB15, MB1H = SWING["min_bars_15m"], SWING["min_bars_1h"]


def main():
    t0 = time.time()
    print("loading candles (causal_replay canonical)...")
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=MB1H)
    print("  15m: %d bars, %d swings | 1h: %d bars, %d swings"
          % (len(c15), len(sw15), len(c1h), len(sw1h)))

    print("running shipped engine (coarse)...")
    r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **PARAMS)
    trades = r["ltf_trades"] if isinstance(r, dict) else r
    rs = [float(t["r_multiple"]) for t in trades]
    print("  engine: %dt gross %+.1fR  (%.0fs)" % (len(trades), sum(rs), time.time() - t0))

    chop = _chop_series_1h(c1h, lb=14)
    atrp = _atr_pct_15m(c15)
    ts15 = [c["ts"] for c in c15]
    ts1h_close = [t + 3600 for t in [c["ts"] for c in c1h]]
    o15 = [c["open"] for c in c15]; c15c = [c["close"] for c in c15]
    hi15 = [c["high"] for c in c15]; lo15 = [c["low"] for c in c15]
    atr15 = [0.0] * len(c15)
    for i in range(1, len(c15)):
        tr = max(hi15[i] - lo15[i], abs(hi15[i] - c15c[i - 1]), abs(lo15[i] - c15c[i - 1]))
        atr15[i] = atr15[i - 1] + (tr - atr15[i - 1]) / 14 if i >= 14 else tr

    def chop_at(bar_ts):
        j = bs.bisect_right(ts1h_close, bar_ts + 900) - 1  # C14: 1h close-known
        return chop[j] if 0 <= j < len(chop) else 50.0

    rows = []
    consec = 0
    for t in trades:
        i = int(t["entry_idx"])
        d = 1 if t["dir"] == "long" else -1
        entry = float(t["entry_price"]); sl = float(t["sl"])
        risk = abs(entry - sl)
        bar_ts = ts15[i]
        rm = float(t["r_multiple"])
        chase = 0
        for j in range(i, 0, -1):
            if d == 1 and c15c[j] > o15[j]: chase += 1
            elif d == -1 and c15c[j] < o15[j]: chase += 1
            else: break
        slw = risk / atr15[i] if atr15[i] > 0 else 0.0
        if d == 1:
            ext_recent = max(hi15[max(0, i - 96):i + 1])
            room = (ext_recent - entry) / risk if risk > 0 else 0.0
        else:
            ext_recent = min(lo15[max(0, i - 96):i + 1])
            room = (entry - ext_recent) / risk if risk > 0 else 0.0
        ch = chop_at(bar_ts)
        ap = atrp[i] if i < len(atrp) else 0.5
        apct = 100.0 * sum(1 for x in atrp[max(0, i - 500):i + 1] if x <= ap) / max(min(i, 500), 1)
        hour = datetime.fromtimestamp(bar_ts, tz=timezone.utc).hour
        pre = consec                      # consecutive losses BEFORE this entry (causal)
        if rm < 0: consec += 1
        else: consec = 0
        rows.append({"i": i, "d": d, "r": rm, "win": rm > 0,
                     "chase": chase, "slw": slw, "room": room, "chop": ch,
                     "apct": apct, "hour": hour, "streak": pre,
                     "date": t.get("entry_date", "")})

    def bucket(name, pred):
        sel = [x for x in rows if pred(x)]
        if not sel:
            print("  %-28s n=%4d  (no trades)" % (name, 0)); return
        rs_ = sum(x["r"] for x in sel)
        wr = 100.0 * sum(x["win"] for x in sel) / len(sel)
        py = defaultdict(float)
        for x in sel: py[x["date"][:4]] += x["r"]
        h1 = sum(x["r"] for x in sel if x["date"][:4] in ("2023", "2024"))
        h2 = sum(x["r"] for x in sel if x["date"][:4] in ("2025", "2026"))
        print("  %-28s n=%4d  R=%+8.1f  WR=%4.1f%%  H1=%+7.1f H2=%+7.1f  %s"
              % (name, len(sel), rs_, wr, h1, h2,
                 {k: round(v, 1) for k, v in sorted(py.items())}))

    losses = [x for x in rows if not x["win"]]
    wins = [x for x in rows if x["win"]]
    print("\n=== POPULATION: %d trades | %d losses (avg %+.2f) | %d wins (avg %+.2f) ==="
          % (len(rows), len(losses), sum(x["r"] for x in losses) / len(losses),
             len(wins), sum(x["r"] for x in wins) / len(wins)))

    print("\n--- SL-width (risk/atr15) buckets ---")
    for lo, hi in [(0.0, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 0.8), (0.8, 99)]:
        bucket("slw %.2f-%.2f" % (lo, hi), lambda x, lo=lo, hi=hi: lo <= x["slw"] < hi)

    print("\n--- chase score buckets ---")
    for c in [(0, 1), (1, 2), (2, 3), (3, 5), (5, 99)]:
        bucket("chase %d-%d" % c, lambda x, c=c: c[0] <= x["chase"] < c[1])

    print("\n--- room buckets (24h opposing extreme, risk units) ---")
    for lo, hi in [(-99, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.5), (2.5, 4), (4, 999)]:
        bucket("room %.1f-%.1f" % (lo, hi), lambda x, lo=lo, hi=hi: lo <= x["room"] < hi)

    print("\n--- chop buckets ---")
    for lo, hi in [(0, 45), (45, 58), (58, 65), (65, 72), (72, 100)]:
        bucket("chop %d-%d" % (lo, hi), lambda x, lo=lo, hi=hi: lo <= x["chop"] < hi)

    print("\n--- ATRpct percentile buckets ---")
    for lo, hi in [(0, 25), (25, 50), (50, 75), (75, 101)]:
        bucket("apct %d-%d" % (lo, hi), lambda x, lo=lo, hi=hi: lo <= x["apct"] < hi)

    print("\n--- time-of-day (UTC) ---")
    for name, hset in [("00-04 UTC", set(range(0, 4))), ("04-08", set(range(4, 8))),
                       ("08-12", set(range(8, 12))), ("12-16", set(range(12, 16))),
                       ("16-20", set(range(16, 20))), ("20-24", set(range(20, 24)))]:
        bucket(name, lambda x, s=hset: x["hour"] in s)

    print("\n--- loss-streak position at entry ---")
    for lo, hi in [(0, 1), (1, 2), (2, 3), (3, 99)]:
        bucket("streak %d-%d" % (lo, hi), lambda x, lo=lo, hi=hi: lo <= x["streak"] < hi)

    print("\n=== CANDIDATE VETO RULES (R removed; negative = good veto) ===")
    rules = [
        ("chase>=3", lambda x: x["chase"] >= 3),
        ("chase>=4", lambda x: x["chase"] >= 4),
        ("slw<0.25 (tight SL)", lambda x: x["slw"] < 0.25),
        ("slw<0.35", lambda x: x["slw"] < 0.35),
        ("room<1.0 (no fuel)", lambda x: x["room"] < 1.0),
        ("room<1.5", lambda x: x["room"] < 1.5),
        ("chase>=3 & room<2.0", lambda x: x["chase"] >= 3 and x["room"] < 2.0),
        ("slw<0.35 & room<2.0", lambda x: x["slw"] < 0.35 and x["room"] < 2.0),
        ("chase>=3 | room<1.0", lambda x: x["chase"] >= 3 or x["room"] < 1.0),
        ("chop>65", lambda x: x["chop"] > 65),
        ("apct>75 (high vol)", lambda x: x["apct"] > 75),
        ("00-04 UTC", lambda x: x["hour"] in set(range(0, 4))),
        ("pre-streak>=3 (post-halt re-entry)", lambda x: x["streak"] >= 3),
        ("pre-streak>=2", lambda x: x["streak"] >= 2),
        ("pre-streak>=1", lambda x: x["streak"] >= 1),
        ("room<1.0 & chop>58", lambda x: x["room"] < 1.0 and x["chop"] > 58),
    ]
    for name, pred in rules:
        bucket(name, pred)

    print("\n(autopsy done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()

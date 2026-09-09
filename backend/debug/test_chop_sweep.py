"""Chop threshold + lookback sensitivity sweep for v18 (robustness: plateau vs knife-edge).

Runs:  chop_thresh in {55,58,60,61.8,64,66,70} at lb=14
       lb in {10,20,28} at chop_thresh=61.8   (14 already covered by the baseline)
Plus:  boundary materiality at 61.8 (+-2 chop) on the baseline run.

Appends one result line per run to backend/debug/_chop_sweep_results.txt (incremental).
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf import v18_streak_halt as v18
from src.walker import FlowCandle

OUT = Path(__file__).resolve().parent / "_chop_sweep_results.txt"

def log(s):
    print(s, flush=True)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(s + "\n")

open(OUT, "w").close()
log("start")

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)
log("data loaded")

_orig_chop = v18._chop_series_1h

def run(lb, thresh, label):
    def patched(candles, **kw):
        return _orig_chop(candles, lb=lb)
    v18._chop_series_1h = patched
    try:
        r = v18.simulate_htf_ltf_streak_halt(
            c1h, sw1h, c15, sw15, fine_ltf=fine,
            sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
            cooldown_bars=20, max_consecutive_losses=5, chop_thresh=thresh)
    finally:
        v18._chop_series_1h = _orig_chop
    tr = r["ltf_trades"]
    rs = [t["r_multiple"] for t in tr]
    tot = sum(rs)
    wins = sum(1 for r in rs if r > 0)
    eq = peak = dd = 0.0
    for r in rs:
        eq += r; peak = max(peak, eq); dd = max(dd, peak - eq)
    years = {}
    for t in tr:
        y = t["entry_date"][:4]
        years.setdefault(y, 0.0)
        years[y] += t["r_multiple"]
    nflip = sum(1 for t in tr if t.get("htf_regime") == "flip")
    nb2 = len(tr) - nflip
    log(json.dumps({"label": label, "lb": lb, "thresh": thresh, "trades": len(tr),
                    "totalR": round(tot, 1), "win%": round(100 * wins / max(1, len(tr)), 1),
                    "maxDD": round(dd, 1), "maxConsecL": max_consec(rs),
                    "flip_trades": nflip, "b2_trades": nb2,
                    "years": {k: round(v, 1) for k, v in sorted(years.items())},
                    "neg_years": sum(1 for v in years.values() if v <= 0)}))

def max_consec(rs):
    mx = cl = 0
    for r in rs:
        cl = cl + 1 if r <= 0 else 0
        mx = max(mx, cl)
    return mx

# --- threshold sweep at lb=14 ---
for th in (55, 58, 60, 61.8, 64, 66, 70):
    run(14, th, f"thresh={th}")
    log(f"done thresh={th}")

# --- lookback sweep at thresh=61.8 ---
for lb in (10, 20, 28):
    run(lb, 61.8, f"lb={lb}")
    log(f"done lb={lb}")

# --- boundary materiality on baseline (61.8, lb=14) ---
import bisect
chop = _orig_chop(c1h, lb=14)
hts = [int(c["ts"]) for c in c1h]
tr = v18.simulate_htf_ltf_streak_halt(
    c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5, chop_thresh=61.8)["ltf_trades"]
chops = []
for t in tr:
    j = bisect.bisect_right(hts, t["entry_ts"]) - 1
    chops.append(chop[j] if j >= 0 and j < len(chop) else 50.0)
near = [(t, c) for t, c in zip(tr, chops) if 59.8 <= c <= 63.8]
at_stake_60 = sum(t["r_multiple"] for t, c in zip(tr, chops) if 60 < c <= 61.8)
at_stake_64 = sum(t["r_multiple"] for t, c in zip(tr, chops) if 61.8 < c <= 63.8)
log(json.dumps({"label": "boundary", "near_61.8_+/-2": len(near),
                "near_R": round(sum(t["r_multiple"] for t, _ in near), 1),
                "flip_if_60": sum(1 for c in chops if 60 < c <= 61.8),
                "R_flip_if_60": round(at_stake_60, 1),
                "flip_if_64": sum(1 for c in chops if 61.8 < c <= 63.8),
                "R_flip_if_64": round(at_stake_64, 1),
                "chop_min_at_entry": round(min(chops), 1),
                "chop_max_at_entry": round(max(chops), 1)}))
log("ALL DONE")

import sys
sys.path.insert(0, ".")
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v16_entry_dist import simulate_htf_ltf_entry_dist
from src.walker import FlowCandle

df = load_btc_df("1h")
c1h, f1h = [], []
for r in df.itertuples():
    c1h.append({"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts), "open": float(r.open), "high": float(r.high), "low": float(r.low), "close": float(r.close), "volume": 0, "oi": 0})
    f1h.append(FlowCandle(date=r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), open=float(r.open), high=float(r.high), low=float(r.low), close=float(r.close)))

df2 = load_btc_df("15m")
c15, f15 = [], []
for r in df2.itertuples():
    c15.append({"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts), "open": float(r.open), "high": float(r.high), "low": float(r.low), "close": float(r.close), "volume": 0, "oi": 0})
    f15.append(FlowCandle(date=r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), open=float(r.open), high=float(r.high), low=float(r.low), close=float(r.close)))

sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)

b = simulate_htf_ltf_entry_dist(c1h, sw1h, c15, sw15, fine_ltf=fine, sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop", cooldown_bars=20, entry_dist_max=0.0)
t = b["ltf_trades"][0]
print("KEYS:", list(t.keys()))
print("TYPES:", {k: type(v).__name__ for k, v in t.items()})

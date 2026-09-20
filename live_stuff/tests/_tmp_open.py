import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from test_experiments import simulate_v18_experiments
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.walker import FlowCandle
from src.btc.btc_config import load_btc_df

df = load_btc_df("15m", "BTCUSDT_BYBIT")
c15, f15 = [], []
for row in df.itertuples():
    d = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    c15.append({"date":d,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),
                "low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
    f15.append(FlowCandle(date=d,open=float(row.open),high=float(row.high),
                          low=float(row.low),close=float(row.close)))
df2 = load_btc_df("1h", "BTCUSDT_BYBIT")
c1h, f1h = [], []
for row in df2.itertuples():
    d = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    c1h.append({"date":d,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),
                "low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
    f1h.append(FlowCandle(date=d,open=float(row.open),high=float(row.high),
                          low=float(row.low),close=float(row.close)))
fine = _load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),
                     max(c1h[-1]["ts"],c15[-1]["ts"]),symbol="BTCUSDT_BYBIT")

configs = [
    ("BASELINE", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,
                      cooldown_bars=10,max_consecutive_losses=3), 20, 50),
    ("OPTIMAL cd=0", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=55.0,
                          cooldown_bars=0,max_consecutive_losses=3,
                          exp_multi_ltf=True,exp_multi_ltf_cd=0,
                          exp_regime_persist=2), 10, 50),
    ("SAFE combo", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=55.0,
                        cooldown_bars=10,max_consecutive_losses=3,
                        exp_regime_persist=2), 10, 50),
    ("MLTF cd=0 only", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,
                            cooldown_bars=10,max_consecutive_losses=3,
                            exp_multi_ltf=True,exp_multi_ltf_cd=0), 20, 50),
]

for name, p, mb1h, mb15 in configs:
    sw1h = _compute_swings(f1h, "continuous", min_bars=mb1h)
    sw15 = _compute_swings(f15, "continuous", min_bars=mb15)
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine, **p)["ltf_trades"]
    all_r = [t["r_multiple"] for t in tr]
    closed = [t for t in tr if t["outcome"] != "open"]
    open_t = [t for t in tr if t["outcome"] == "open"]
    closed_r = [t["r_multiple"] for t in closed]
    open_r = [t["r_multiple"] for t in open_t]
    gross_all = sum(all_r)
    gross_closed = sum(closed_r)
    gross_open = sum(open_r)
    print(name + ":")
    print("  Total: %d | Closed: %d | Open: %d" % (len(tr), len(closed), len(open_t)))
    print("  Gross R (ALL):   %+.1f" % gross_all)
    print("  Gross R (closed):%+.1f" % gross_closed)
    print("  Open trades R:   %+.1f" % gross_open)
    if open_t:
        for t in open_t:
            print("    %s %s R=%+.2f" % (t["entry_date"], t["dir"], t["r_multiple"]))
    print()

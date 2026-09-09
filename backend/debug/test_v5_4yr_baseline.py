"""4yr FULL baseline verify — LTF legs net per year for v1/v3/v5/v6.
Uses same engines as btc_routes.py: htf_ltf 1h->15m, 1m fills, 0.05%+2pt, stream.
Data window is live CSVs (now 2023-01-01 -> 2026-09-06 = 1.93M 1m)."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_engine import trade_stats
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.btc.engines.htf_ltf.v3_ext_stop import simulate_htf_ltf_ext_stop
from src.btc.engines.htf_ltf.v5_sl_buffer import simulate_htf_ltf_sl_buffer
from src.btc.engines.htf_ltf.v6_sl_hhll import simulate_htf_ltf_sl_hhll
from src.walker import FlowCandle
import datetime

FEE = 0.05
SLIP = 2.0

def load_window(tf: str):
    df = load_btc_df(tf)
    candles = []
    flow = []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow, df

print("=== loading 1h/15m/1m (FULL 2023-2026) ===")
c1h, f1h, df1h = load_window("1h")
c15, f15, df15 = load_window("15m")
print(f"1h rows {len(c1h)} {df1h['timestamp'].min()} -> {df1h['timestamp'].max()}  ({len(c1h)} x1h)")
print(f"15m rows {len(c15)} {df15['timestamp'].min()} -> {df15['timestamp'].max()}")
import src.btc.btc_config as cfg
from src.btc.btc_config import BTC_DATA_DIR
for tf in ["1m","5m","15m","1h","4h"]:
    try:
        d = load_btc_df(tf)
        print(f"  {tf}: {len(d)} rows {d['timestamp'].min()} -> {d['timestamp'].max()}")
    except Exception as e:
        print(f"  {tf}: {e}")

sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
print(f"swings: 1h {len(sw1h)} (mb20), 15m {len(sw15)} (mb50)")

# fine 1m
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)
print(f"fine 1m bars in window: {len(fine) if fine else 0}")

def run_ver(label, fn):
    nested = fn(c1h, sw1h, c15, sw15, fine)
    ltf = nested["ltf_trades"]
    htf = nested["htf_trades"]
    _trade_costs(ltf, FEE, SLIP)
    _trade_costs(htf, FEE, SLIP)
    stats_ltf = trade_stats(ltf)
    stats_htf = trade_stats(htf)
    # net
    net_ltf = sum(float(t["r_multiple"]) - float(t.get("cost_r",0)) for t in ltf if t["outcome"]!="open")
    net_htf = sum(float(t["r_multiple"]) - float(t.get("cost_r",0)) for t in htf if t["outcome"]!="open")
    combined = net_ltf + net_htf
    print(f"\n--- {label} ---")
    print(f"  LTF legs: {len(ltf)} tr win {stats_ltf['win_rate']}% base {stats_ltf['total_r']} net {stats_ltf.get('net_total_r', net_ltf):.2f} PF {stats_ltf['profit_factor']} maxDD {stats_ltf['max_drawdown_r']} maxL {stats_ltf['max_consecutive_losses']}")
    print(f"  HTF 1h:   {len(htf)} tr win {stats_htf['win_rate']}% net {stats_htf.get('net_total_r', net_htf):.2f}")
    print(f"  Combined net (LTF+HTF): {combined:.2f}  (LTF net {net_ltf:.2f} + HTF net {net_htf:.2f})")
    # per-year net for LTF legs (by exit year)
    from collections import defaultdict
    yearly = defaultdict(float)
    ytr = defaultdict(int)
    for t in ltf:
        if t["outcome"]=="open":
            continue
        y = t["exit_date"][:4]
        yearly[y] += float(t["r_multiple"]) - float(t.get("cost_r",0))
        ytr[y] += 1
    print(f"  Per-year LTF net (by exit):")
    for y in sorted(yearly):
        print(f"    {y}: {ytr[y]}tr {yearly[y]:.2f}R")
    # yearly for HTF too
    y2 = defaultdict(float)
    for t in htf:
        if t["outcome"]=="open":
            continue
        y = t["exit_date"][:4]
        y2[y] += float(t["r_multiple"]) - float(t.get("cost_r",0))
    print(f"  Per-year HTF net:")
    for y in sorted(y2):
        print(f"    {y}: {y2[y]:.2f}R")
    return nested, yearly

for label, fn in [
    ("v1 plain window-gate", lambda a,b,c,d,f: simulate_htf_ltf_15m(a,b,c,d,f, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16)),
    ("v3 ext-stop 1.5R", lambda a,b,c,d,f: simulate_htf_ltf_ext_stop(a,b,c,d,f, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5)),
    ("v5 ext-stop + buf 0.25ATR", lambda a,b,c,d,f: simulate_htf_ltf_sl_buffer(a,b,c,d,f, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)),
    ("v6 ext-stop + hhll-30", lambda a,b,c,d,f: simulate_htf_ltf_sl_hhll(a,b,c,d,f, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_hhll_n=30)),
]:
    run_ver(label, fn)

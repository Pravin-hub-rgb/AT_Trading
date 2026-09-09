"""v13 cooldown engine validation — v5 baseline vs v13(cooldown=0) vs v13(cooldown=20).

v13(cooldown=0) must EXACTLY match v5 (442 tr, same net) — proves the standalone
exit sim is equivalent. v13(cooldown=20) is the live rule: after a loss, wait
20 x 15m bars (~5h) before the next LTF entry.
"""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_engine import trade_stats
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v5_sl_buffer import simulate_htf_ltf_sl_buffer
from src.btc.engines.htf_ltf.v13_cooldown import simulate_htf_ltf_cooldown
from src.walker import FlowCandle
from collections import defaultdict

FEE = 0.05
SLIP = 2.0

def load_window(tf: str):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

print("=== loading 1h/15m/1m (FULL 2023-2026) ===", flush=True)
c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
print(f"1h {len(c1h)} rows, 15m {len(c15)} rows", flush=True)

sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)
print(f"swings 1h {len(sw1h)}, 15m {len(sw15)}, fine {len(fine) if fine else 0}", flush=True)

def run_ver(label, nested):
    ltf = nested["ltf_trades"]
    htf = nested["htf_trades"]
    _trade_costs(ltf, FEE, SLIP)
    _trade_costs(htf, FEE, SLIP)
    net_ltf = sum(float(t["r_multiple"]) - float(t.get("cost_r", 0)) for t in ltf if t["outcome"] != "open")
    net_htf = sum(float(t["r_multiple"]) - float(t.get("cost_r", 0)) for t in htf if t["outcome"] != "open")
    print(f"\n--- {label} ---")
    print(f"  LTF: {len(ltf)} tr net {net_ltf:.2f} | HTF: {len(htf)} tr net {net_htf:.2f} | combined {net_ltf + net_htf:.2f}")
    yearly = defaultdict(float)
    ytr = defaultdict(int)
    for t in ltf:
        if t["outcome"] == "open":
            continue
        y = t["exit_date"][:4]
        yearly[y] += float(t["r_multiple"]) - float(t.get("cost_r", 0))
        ytr[y] += 1
    for y in sorted(yearly):
        print(f"    {y}: {ytr[y]}tr {yearly[y]:+.2f}R")
    return ltf

ltf_v5 = run_ver("v5 baseline", simulate_htf_ltf_sl_buffer(
    c1h, sw1h, c15, sw15, fine,
    htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing",
    rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0,
    htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25))

ltf_v13_0 = run_ver("v13 cooldown=0 (must match v5)", simulate_htf_ltf_cooldown(
    c1h, sw1h, c15, sw15, fine,
    htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing",
    rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0,
    htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25, cooldown_bars=0))

ltf_v13_20 = run_ver("v13 cooldown=20 (THE RULE)", simulate_htf_ltf_cooldown(
    c1h, sw1h, c15, sw15, fine,
    htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing",
    rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0,
    htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25, cooldown_bars=20))

# equivalence check: cooldown=0 vs v5 — same trades?
def sig(tr):
    return (int(tr["entry_ts"]), int(tr["exit_ts"]), tr["dir"], round(float(tr["entry_price"]), 2), round(float(tr["exit_price"]), 2))

s5 = [sig(t) for t in ltf_v5 if t["outcome"] != "open"]
s0 = [sig(t) for t in ltf_v13_0 if t["outcome"] != "open"]
if s5 == s0:
    print(f"\nEQUIVALENCE OK: cooldown=0 matches v5 exactly ({len(s5)} trades)")
else:
    print(f"\nEQUIVALENCE FAIL: v5 {len(s5)} vs cooldown=0 {len(s0)} trades")
    for a, b in zip(s5, s0):
        if a != b:
            print(f"  first diff:\n    v5: {a}\n    v13: {b}")
            break
print(f"\nv13@20 trades skipped vs v5: {len(s5) - len(s0) + len([sig(t) for t in ltf_v13_20 if t['outcome'] != 'open']) - len(s0)}")

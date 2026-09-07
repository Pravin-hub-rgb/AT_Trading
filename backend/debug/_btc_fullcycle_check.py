"""Full-cycle headline check on the MERGED main CSVs (bull 2025 + bear 2025-26)."""
import sys, warnings, time
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from src.btc.btc_config import load_btc_df
from src.btc.btc_engine import simulate_btc_trades, trade_stats
from src.btc.btc_routes import _trade_costs, _net_stats, _compute_swings, _load_window

for tf in ("1m", "5m", "15m"):
    df = load_btc_df(tf, "main")
    print(f"[{tf}] {len(df)} rows | {df['timestamp'].iloc[0]} -> {df['timestamp'].iloc[-1]}")

t0 = time.time()
win, err = _load_window("5m", None, "main")
assert err is None, err
candles, flow5 = win
swings = _compute_swings(flow5, "continuous", min_bars=20)
print(f"5m merged: {len(candles)} candles, {len(swings)} swings in {time.time()-t0:.1f}s")

CFG = dict(entry_break="decisive", sl_mode="swing", rr_target=3.0, trailing="swing",
           breakeven_r=1.0)
tr = simulate_btc_trades(candles, swings, **CFG)
s = trade_stats(tr)
print(f"5m trail_max FULL-CYCLE zero-cost: {s['trades']} tr | win {s['win_rate']}% | {s['total_r']}R | dd {s['max_drawdown_r']}R")
for fee, slip, tag in ((0.02, 0.0, "maker 0.02%"), (0.05, 2.0, "taker 0.05%+2pt")):
    tr2 = simulate_btc_trades(candles, swings, **CFG)
    _trade_costs(tr2, fee, slip)
    s2 = _net_stats(trade_stats(tr2), tr2)
    print(f"  net @{tag}: {s2['net_total_r']}R (costs {s2['total_costs_r']}R)")

# OOS preset on the merged window too (flip mb50 BE0 15m)
win15, err15 = _load_window("15m", None, "main")
assert err15 is None, err15
c15, flow15 = win15
sw15 = _compute_swings(flow15, "continuous", min_bars=50)
tr15 = simulate_btc_trades(c15, sw15, entry_break="flip", sl_mode="swing", rr_target=3.0,
                           trailing="swing", breakeven_r=0.0)
s15 = trade_stats(tr15)
print(f"15m flip50 FULL-CYCLE zero-cost: {s15['trades']} tr | win {s15['win_rate']}% | {s15['total_r']}R")
tr15b = simulate_btc_trades(c15, sw15, entry_break="flip", sl_mode="swing", rr_target=3.0,
                            trailing="swing", breakeven_r=0.0)
_trade_costs(tr15b, 0.05, 2.0)
s15b = _net_stats(trade_stats(tr15b), tr15b)
print(f"  net @taker: {s15b['net_total_r']}R (costs {s15b['total_costs_r']}R)")

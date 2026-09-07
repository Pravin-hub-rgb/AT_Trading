"""Sweep for 1-min engine - finds best profitable combo.
Usage: python sweep_1min.py [--quick] [--full]
quick = small grid for test (~200 combos)
full = larger grid (~3000 combos)
"""
import itertools
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# add src to path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from src import bias as bias_svc, config
from src.intraday_1m_standalone import run_backtest_1min

DATA_DIR = config.DATA_DIR
p1 = DATA_DIR / "nifty_1min.csv"
p5 = DATA_DIR / "nifty_5min.csv"
pdaily = DATA_DIR / "nifty_daily.csv"

print(f"[{datetime.now()}] Loading data...", flush=True)
df1 = pd.read_csv(p1)
df5 = pd.read_csv(p5)
daily = pd.read_csv(pdaily) if pdaily.exists() else None
print(f"  1min rows {len(df1)}, 5min {len(df5)}, daily {len(daily) if daily is not None else 0}", flush=True)
print(f"[{datetime.now()}] Computing bias labels...", flush=True)
labels = bias_svc.compute_bias(df5, daily)
print(f"  labels {len(labels)}", flush=True)

# Define grids
quick_grid = {
    "sl_mode": ["avg", "prev_pivot"],
    "rr_target": [2.0, 3.0],
    "min_sl_pts": [0, 13],
    "breakeven_r": [0, 1.0],
    "gap_pct": [0.0027],
    "ft_fail_enabled": [True],
    "max_entries": [1, 2],
    "entry_cutoff": ["15:15", "12:00"],
    "second_trade_after": ["sl_only", "always"],
}

default_grid = {
    "sl_mode": ["avg", "avg075", "prev_pivot", "swing_end"],
    "rr_target": [2.0, 3.0, 4.0],
    "min_sl_pts": [0, 13, 20],
    "breakeven_r": [0, 1.0, 1.5],
    "gap_pct": [0.0027, 0.0035],
    "ft_fail_enabled": [True, False],
    "max_entries": [1, 2],
    "entry_cutoff": ["15:15", "12:00"],
    "second_trade_after": ["sl_only", "always"],
}

full_grid = {
    "sl_mode": ["avg", "avg075", "avg05", "prev_pivot", "swing_end", "fixed8"],
    "rr_target": [1.5, 2.0, 3.0, 4.0],
    "min_sl_pts": [0, 8, 13, 20],
    "breakeven_r": [0, 1.0, 1.5, 2.0],
    "gap_pct": [0.0015, 0.0027, 0.0035],
    "ft_fail_enabled": [True, False],
    "swing_traverse": [True],
    "need_opp_swing": [True],
    "max_entries": [1, 2],
    "entry_cutoff": ["15:15", "14:00", "12:00", "11:30"],
    "second_trade_after": ["sl_only", "loss", "always"],
}

# Choose grid
arg = sys.argv[1] if len(sys.argv) > 1 else "--default"
if arg == "--quick":
    grid = quick_grid
elif arg == "--full":
    grid = full_grid
else:
    grid = default_grid

print(f"[{datetime.now()}] Using grid {arg}:", flush=True)
for k, v in grid.items():
    print(f"  {k}: {v}", flush=True)

# Generate combos
keys = list(grid.keys())
values = list(grid.values())
total_combos = 1
for v in values:
    total_combos *= len(v)
print(f"[{datetime.now()}] Total combos: {total_combos}", flush=True)

# Prepare combos list
combos = list(itertools.product(*values))
# For quick, limit
if total_combos > 5000 and arg != "--full":
    print(f"WARNING: {total_combos} combos is large, consider --quick", flush=True)

# Helper to run one combo
def run_one(combo):
    cfg = dict(zip(keys, combo))
    # gap_pct is already fraction, but our grid is fraction; ensure float
    # run expects gap_pct fraction, so keep as is
    # For sweep we pass directly
    try:
        # execution fixed to 1min
        cfg["execution"] = "1min"
        cfg["swing_traverse"] = cfg.get("swing_traverse", True)
        cfg["need_opp_swing"] = cfg.get("need_opp_swing", True)
        # ensure types
        res = run_backtest_1min(df1, labels, cfg=cfg)
        stats = res["stats"]
        # compute additional metrics
        trades = stats["trades"]
        wins = stats["wins"]
        total_r = stats["total_r"]
        win_rate = stats["win_rate"]
        avg_r = stats["avg_r"]
        # profit factor: sum wins / sum losses absolute
        # need per trade R to compute
        all_r = [t["r_multiple"] for d in res["days"] for t in d["trades"]]
        gross_win = sum(r for r in all_r if r > 0)
        gross_loss = sum(-r for r in all_r if r < 0)
        pf = gross_win / gross_loss if gross_loss > 0 else 999 if gross_win > 0 else 0
        pf = round(pf, 2)
        # expectancy per trade = avg_r
        # sort key
        return {
            "cfg": cfg,
            "stats": stats,
            "pf": pf,
            "gross_win": round(gross_win,2),
            "gross_loss": round(gross_loss,2),
            "trades": trades,
            "wins": wins,
            "win_rate": win_rate,
            "total_r": total_r,
            "avg_r": avg_r,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "cfg": cfg,
            "error": str(e),
            "total_r": -9999,
        }

# Run sweeps
import concurrent.futures

results = []
start = time.time()
# Use sequential for now to avoid pickle issues with pandas df (df is large, but we can share via global)
# We'll try ProcessPool but df1/labels need to be pickled. Instead use ThreadPool or sequential.
# For speed, sequential is okay for ~3000 combos *0.2s = 600s, but we can try to run with progress.

# Try to use concurrent with threads? Since run_backtest is CPU bound, threads may not help due to GIL, but we can try processes with initializer.

# We will do sequential with periodic print, but also try to use multiprocessing with shared data via global.

# Simple sequential with progress
print(f"[{datetime.now()}] Starting sweep...", flush=True)
for idx, combo in enumerate(combos):
    if idx % 100 == 0:
        elapsed = time.time() - start
        print(f"[{datetime.now()}] {idx}/{total_combos} elapsed {elapsed:.1f}s", flush=True)
    res = run_one(combo)
    results.append(res)

elapsed = time.time() - start
print(f"[{datetime.now()}] Done {total_combos} combos in {elapsed:.1f}s avg {elapsed/total_combos*1000:.0f}ms per combo", flush=True)

# Rank
# Filter out errors
valid = [r for r in results if "error" not in r]
print(f"Valid results: {len(valid)}/{len(results)}", flush=True)

# Sort by total_R descending, then win_rate, then pf
ranked = sorted(valid, key=lambda x: (x["total_r"], x["win_rate"], x["pf"]), reverse=True)

# Print top 20
print("\n" + "="*120, flush=True)
print(f"TOP 20 by total_R (out of {len(ranked)})", flush=True)
print("="*120, flush=True)
for i, r in enumerate(ranked[:20]):
    cfg = r["cfg"]
    stats = r["stats"]
    print(f"#{i+1:2d} total_R {r['total_r']:+7.2f} win_rate {r['win_rate']:4.1f}% pf {r['pf']:4.2f} trades {r['trades']:3d} avg {r['avg_r']:+5.2f} | sl:{cfg['sl_mode']:10s} rr:{cfg['rr_target']} minSL:{cfg['min_sl_pts']:2.0f} BE:{cfg['breakeven_r']} gap:{cfg['gap_pct']*100:.2f}% ft:{cfg['ft_fail_enabled']} max:{cfg['max_entries']} cutoff:{cfg['entry_cutoff']} 2nd:{cfg['second_trade_after']}", flush=True)

print("\n" + "="*120, flush=True)
print("TOP 20 by win_rate", flush=True)
print("="*120, flush=True)
ranked_wr = sorted(valid, key=lambda x: (x["win_rate"], x["total_r"]), reverse=True)
for i, r in enumerate(ranked_wr[:20]):
    cfg = r["cfg"]
    if r["trades"] < 50:
        continue
    print(f"#{i+1:2d} win_rate {r['win_rate']:4.1f}% total_R {r['total_r']:+7.2f} pf {r['pf']:4.2f} trades {r['trades']:3d} | sl:{cfg['sl_mode']:10s} rr:{cfg['rr_target']} minSL:{cfg['min_sl_pts']:2.0f} BE:{cfg['breakeven_r']} cutoff:{cfg['entry_cutoff']} 2nd:{cfg['second_trade_after']}", flush=True)
    if i >= 19:
        break

print("\n" + "="*120, flush=True)
print("TOP 20 by profit factor (pf) with trades>=50", flush=True)
print("="*120, flush=True)
ranked_pf = sorted([r for r in valid if r["trades"]>=50], key=lambda x: (x["pf"], x["total_r"]), reverse=True)
for i, r in enumerate(ranked_pf[:20]):
    cfg = r["cfg"]
    print(f"#{i+1:2d} pf {r['pf']:4.2f} total_R {r['total_r']:+7.2f} win_rate {r['win_rate']:4.1f}% trades {r['trades']:3d} | sl:{cfg['sl_mode']:10s} rr:{cfg['rr_target']} minSL:{cfg['min_sl_pts']:2.0f} BE:{cfg['breakeven_r']} cutoff:{cfg['entry_cutoff']} 2nd:{cfg['second_trade_after']}", flush=True)

# Save to json
out_path = Path(__file__).parent / f"sweep_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(out_path, "w") as f:
    # Convert ranked to serializable (stats already serializable)
    json.dump(ranked[:100], f, indent=2, default=str)
print(f"\nSaved top 100 to {out_path}", flush=True)

# Also save CSV for easy view
csv_path = out_path.with_suffix(".csv")
import csv
with open(csv_path, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["rank","total_R","win_rate","pf","trades","avg_R","sl_mode","rr","min_sl","breakeven","gap_pct","ft_fail","max_entries","cutoff","second_after"])
    for i, r in enumerate(ranked[:100]):
        cfg = r["cfg"]
        writer.writerow([i+1, r["total_r"], r["win_rate"], r["pf"], r["trades"], r["avg_r"], cfg["sl_mode"], cfg["rr_target"], cfg["min_sl_pts"], cfg["breakeven_r"], cfg["gap_pct"], cfg["ft_fail_enabled"], cfg["max_entries"], cfg["entry_cutoff"], cfg["second_trade_after"]])
print(f"Saved CSV to {csv_path}", flush=True)

# Print best per sl_mode
print("\n" + "="*120, flush=True)
print("BEST per sl_mode", flush=True)
print("="*120, flush=True)
for sl in sorted(set(r["cfg"]["sl_mode"] for r in valid)):
    best = max([r for r in valid if r["cfg"]["sl_mode"]==sl], key=lambda x: x["total_r"])
    cfg = best["cfg"]
    print(f"{sl:12s} best total_R {best['total_r']:+7.2f} win {best['win_rate']:4.1f}% pf {best['pf']:4.2f} trades {best['trades']:3d} | rr:{cfg['rr_target']} minSL:{cfg['min_sl_pts']} BE:{cfg['breakeven_r']} gap:{cfg['gap_pct']*100:.2f}% ft:{cfg['ft_fail_enabled']} max:{cfg['max_entries']} cutoff:{cfg['entry_cutoff']} 2nd:{cfg['second_trade_after']}", flush=True)

print("\nDone.", flush=True)

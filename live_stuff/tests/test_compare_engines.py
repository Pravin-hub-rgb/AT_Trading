"""Compare experiment harness vs production engine — trade-by-trade."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"
PARAMS = {"sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 10,
          "max_consecutive_losses": 3, "ext_stop_r": 1.5}


def load_window(tf):
    df = load_btc_df(tf, SYMBOL)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def stats(trades):
    closed = [t for t in trades if t["outcome"] != "open"]
    rs = [t["r_multiple"] for t in closed]
    wins = [r for r in rs if r > 0]
    wr = 100 * len(wins) / len(closed) if closed else 0
    pf = sum(wins) / abs(sum(r for r in rs if r <= 0)) if any(r <= 0 for r in rs) else 0
    cum = 0; peak = 0; mdd = 0
    for r in rs:
        cum += r
        if cum > peak: peak = cum
        dd = peak - cum
        if dd > mdd: mdd = dd
    return {"n": len(closed), "r": round(sum(rs), 2), "wr": round(wr, 1), "pf": round(pf, 2), "mdd": round(mdd, 2)}


# Load data
htf_c, htf_f = load_window("1h")
ltf_c, ltf_f = load_window("15m")
t0 = min(htf_c[0]["ts"], ltf_c[0]["ts"])
t1 = max(htf_c[-1]["ts"], ltf_c[-1]["ts"])
fine = _load_fine_1m(t0, t1, symbol=SYMBOL)
print(f"Data: {len(htf_c)} 1h, {len(ltf_c)} 15m, {len(fine)} 1m fine")

# Compute swings
htf_swings = _compute_swings(htf_f, "continuous", min_bars=20)
ltf_swings = _compute_swings(ltf_f, "continuous", min_bars=50)
print(f"Swings: {len(htf_swings)} 1h, {len(ltf_swings)} 15m")

# Run PRODUCTION engine
prod_result = simulate_htf_ltf_streak_halt(
    candles_htf=htf_c, swings_htf=htf_swings,
    candles_ltf=ltf_c, swings_ltf=ltf_swings,
    fine_ltf=fine,
    sl_buf_atr=PARAMS["sl_buf_atr"],
    ext_stop_r=PARAMS["ext_stop_r"],
    mode="b2_vs_flip_chop",
    chop_thresh=PARAMS["chop_thresh"],
    cooldown_bars=PARAMS["cooldown_bars"],
    max_consecutive_losses=PARAMS["max_consecutive_losses"],
)
prod_trades = prod_result["ltf_trades"]
ps = stats(prod_trades)
print(f"\nPRODUCTION: {ps['n']}t  {ps['r']:+.1f}R  WR {ps['wr']}%")

# Run EXPERIMENT harness
from test_experiments import simulate_v18_experiments
exp_result = simulate_v18_experiments(
    htf_c, htf_swings, ltf_c, ltf_swings, fine_ltf=fine,
    sl_buf_atr=PARAMS["sl_buf_atr"], ext_stop_r=PARAMS["ext_stop_r"],
    chop_thresh=PARAMS["chop_thresh"], cooldown_bars=PARAMS["cooldown_bars"],
    max_consecutive_losses=PARAMS["max_consecutive_losses"],
)
exp_trades = exp_result["ltf_trades"]
es = stats(exp_trades)
print(f"EXPERIMENT: {es['n']}t  {es['r']:+.1f}R  WR {es['wr']}%")

# Trade-by-trade comparison
prod_keys = {(t["entry_ts"], t["dir"]): t for t in prod_trades}
exp_keys = {(t["entry_ts"], t["dir"]): t for t in exp_trades}

common = set(prod_keys) & set(exp_keys)
prod_only = set(prod_keys) - set(exp_keys)
exp_only = set(exp_keys) - set(prod_keys)

print(f"\n--- DIFF ---")
print(f"Common entries: {len(common)}")
print(f"Production-only: {len(prod_only)}")
print(f"Experiment-only: {len(exp_only)}")

# Check if common trades have identical R
r_mismatches = 0
for key in common:
    pr = prod_keys[key]["r_multiple"]
    er = exp_keys[key]["r_multiple"]
    if abs(pr - er) > 0.001:
        r_mismatches += 1
        if r_mismatches <= 5:
            print(f"  R mismatch {key}: prod={pr:.3f} exp={er:.3f}")

if r_mismatches == 0:
    print("All common trades have IDENTICAL R")
else:
    print(f"{r_mismatches} R mismatches in common trades")

# Show first few prod-only and exp-only
print(f"\nFirst 10 production-only trades:")
for key in sorted(prod_only)[:10]:
    t = prod_keys[key]
    print(f"  {t['entry_date']} {t['dir']:5s} {t['r_multiple']:+.3f}R  sl={t.get('htf_regime','?')}")

print(f"\nFirst 10 experiment-only trades:")
for key in sorted(exp_only)[:10]:
    t = exp_keys[key]
    print(f"  {t['entry_date']} {t['dir']:5s} {t['r_multiple']:+.3f}R  sl={t.get('htf_regime','?')}")

# Summarize divergent trades
prod_only_r = sum(prod_keys[k]["r_multiple"] for k in prod_only)
exp_only_r = sum(exp_keys[k]["r_multiple"] for k in exp_only)
print(f"\n--- DIVERGENT TRADES IMPACT ---")
print(f"Prod-only: {len(prod_only)}t, {prod_only_r:+.1f}R")
print(f"Exp-only:  {len(exp_only)}t, {exp_only_r:+.1f}R")
print(f"Net divergence: {exp_only_r - prod_only_r:+.1f}R")

# Per-year breakdown
print(f"\n--- PER YEAR ---")
for year in ["2023", "2024", "2025", "2026"]:
    p = sum(t["r_multiple"] for t in prod_trades if t["entry_date"][:4] == year and t["outcome"] != "open")
    e = sum(t["r_multiple"] for t in exp_trades if t["entry_date"][:4] == year and t["outcome"] != "open")
    pc = len([t for t in prod_trades if t["entry_date"][:4] == year and t["outcome"] != "open"])
    ec = len([t for t in exp_trades if t["entry_date"][:4] == year and t["outcome"] != "open"])
    print(f"  {year}: prod={pc}t/{p:+.1f}R  exp={ec}t/{e:+.1f}R  delta={e-p:+.1f}R")

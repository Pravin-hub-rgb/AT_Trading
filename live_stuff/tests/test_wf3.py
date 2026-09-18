"""Expanding-window walk-forward validation."""
import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from test_experiments import load_window, simulate_v18_experiments, run_and_report
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"
def load_swing(tf):
    from src.btc.btc_config import load_btc_df
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

c15_full, f15_full = load_swing("15m")
c1h_full, f1h_full = load_swing("1h")

def eval_config(name, params, mb_1h, mb_15, train_end_pct):
    """Train up to train_end_pct, test on the rest."""
    mid = int(len(c15_full) * train_end_pct)
    mid_ts = c15_full[mid]["ts"]
    htf_ts = [c["ts"] for c in c1h_full]
    mid_h = min(bisect.bisect_right(htf_ts, mid_ts), len(c1h_full) - 1)

    c15_t, c15_v = c15_full[:mid], c15_full[mid:]
    f15_t, f15_v = f15_full[:mid], f15_full[mid:]
    c1h_t, c1h_v = c1h_full[:mid_h], c1h_full[mid_h:]
    f1h_t, f1h_v = f1h_full[:mid_h], f1h_full[mid_h:]

    fine_t = _load_fine_1m(c15_t[0]["ts"], c15_t[-1]["ts"], symbol=SYMBOL)
    fine_v = _load_fine_1m(c15_v[0]["ts"], c15_v[-1]["ts"], symbol=SYMBOL)
    sw15_t = _compute_swings(f15_t, "continuous", min_bars=mb_15)
    sw15_v = _compute_swings(f15_v, "continuous", min_bars=mb_15)
    sw1h_t = _compute_swings(f1h_t, "continuous", min_bars=mb_1h)
    sw1h_v = _compute_swings(f1h_v, "continuous", min_bars=mb_1h)

    train = simulate_v18_experiments(c1h_t, sw1h_t, c15_t, sw15_t, fine_t, **params)["ltf_trades"]
    val = simulate_v18_experiments(c1h_v, sw1h_v, c15_v, sw15_v, fine_v, **params)["ltf_trades"]

    r_t = sum(t["r_multiple"] for t in train)
    r_v = sum(t["r_multiple"] for t in val)
    wr_t = sum(1 for t in train if t["r_multiple"] > 0) / len(train) * 100 if train else 0
    wr_v = sum(1 for t in val if t["r_multiple"] > 0) / len(val) * 100 if val else 0
    return len(train), r_t, wr_t, len(val), r_v, wr_v

BASELINE = dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
                cooldown_bars=10, max_consecutive_losses=3)
OPTIMAL = dict(sl_buf_atr=0.001, ext_stop_r=1.5, chop_thresh=55.0,
               cooldown_bars=0, max_consecutive_losses=3,
               exp_multi_ltf=True, exp_multi_ltf_cd=0,
               exp_regime_persist=2)
OPTIMAL_SL01 = dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
               cooldown_bars=0, max_consecutive_losses=3,
               exp_multi_ltf=True, exp_multi_ltf_cd=0,
               exp_regime_persist=2)
OPTIMAL_CD5 = dict(sl_buf_atr=0.001, ext_stop_r=1.5, chop_thresh=55.0,
               cooldown_bars=5, max_consecutive_losses=3,
               exp_multi_ltf=True, exp_multi_ltf_cd=5,
               exp_regime_persist=2)

configs = [
    ("BASELINE (20/50)", BASELINE, 20, 50),
    ("OPTIMAL (10/50, sl=0.001, cd=0, chop=55)", OPTIMAL, 10, 50),
    ("OPTIMAL-sl01 (10/50, sl=0.01, cd=0, chop=55)", OPTIMAL_SL01, 10, 50),
    ("OPTIMAL-cd5 (10/50, sl=0.001, cd=5, chop=55)", OPTIMAL_CD5, 10, 50),
]

# Expanding window: train on 0-50%, test 50-100% | train 0-66%, test 66-100% | train 0-75%, test 75-100%
splits = [("50/50", 0.50), ("66/34", 0.66), ("75/25", 0.75)]

print("=" * 110)
print("EXPANDING-WINDOW WALK-FORWARD VALIDATION")
print("=" * 110)

for cfg_name, params, mb_1h, mb_15 in configs:
    print(f"\n  {cfg_name}:")
    print(f"  {'Split':>8} {'Train_t':>8} {'Train_R':>9} {'WR':>6} {'Test_t':>7} {'Test_R':>8} {'WR':>6} {'Degrad':>8}")
    print(f"  {'-' * 72}")
    for split_name, pct in splits:
        n_t, r_t, wr_t, n_v, r_v, wr_v = eval_config(cfg_name, params, mb_1h, mb_15, pct)
        deg = (1 - r_v / r_t) * 100 if r_t > 0 else float('inf')
        print(f"  {split_name:>8} {n_t:>8} {r_t:>+9.1f} {wr_t:>5.1f}% {n_v:>7} {r_v:>+8.1f} {wr_v:>5.1f}% {deg:>+7.1f}%")

# Also: sensitivity of chop across walk-forward
print()
print("=" * 110)
print("CHOP SENSITIVITY: Test-set R across walk-forward splits")
print("=" * 110)
print(f"  {'Chop':>5} {'50/50':>10} {'66/34':>10} {'75/25':>10} {'Avg':>10}")
print(f"  {'-' * 50}")
for ch in [50, 55, 58, 62, 65, 70]:
    rs = []
    for _, pct in splits:
        params = dict(sl_buf_atr=0.001, ext_stop_r=1.5, chop_thresh=ch,
                      cooldown_bars=0, max_consecutive_losses=3,
                      exp_multi_ltf=True, exp_multi_ltf_cd=0,
                      exp_regime_persist=2)
        _, _, _, _, r_v, _ = eval_config(f"ch{ch}", params, 10, 50, pct)
        rs.append(r_v)
    print(f"  {ch:>5} {rs[0]:>+10.1f} {rs[1]:>+10.1f} {rs[2]:>+10.1f} {sum(rs)/len(rs):>+10.1f}")

# Sensitivity of min_bars_1h across walk-forward
print()
print("=" * 110)
print("MIN_BARS 1h SENSITIVITY: Test-set R across walk-forward splits")
print("=" * 110)
print(f"  {'mb_1h':>6} {'50/50':>10} {'66/34':>10} {'75/25':>10} {'Avg':>10}")
print(f"  {'-' * 50}")
for mb in [10, 15, 20, 25, 30]:
    rs = []
    for _, pct in splits:
        params = dict(sl_buf_atr=0.001, ext_stop_r=1.5, chop_thresh=55.0,
                      cooldown_bars=0, max_consecutive_losses=3,
                      exp_multi_ltf=True, exp_multi_ltf_cd=0,
                      exp_regime_persist=2)
        _, _, _, _, r_v, _ = eval_config(f"mb{mb}", params, mb, 50, pct)
        rs.append(r_v)
    print(f"  {mb:>6} {rs[0]:>+10.1f} {rs[1]:>+10.1f} {rs[2]:>+10.1f} {sum(rs)/len(rs):>+10.1f}")

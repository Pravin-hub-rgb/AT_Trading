"""Deep diagnosis: what are cd=0 trades doing? Rolling WF. Bootstrap CI."""
import sys, bisect, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from test_experiments import load_window, simulate_v18_experiments, run_and_report
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.walker import FlowCandle
import statistics

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
fine_full = _load_fine_1m(c15_full[0]["ts"], c15_full[-1]["ts"], symbol=SYMBOL)

# ============================================================
# PART 1: Rolling walk-forward (non-overlapping windows)
# ============================================================
print("=" * 100)
print("PART 1: ROLLING WALK-FORWARD (4 non-overlapping OOS windows)")
print("=" * 100)

def get_slice(c15, f15, c1h, f1h, start_pct, end_pct):
    n = len(c15)
    s, e = int(n * start_pct), int(n * end_pct)
    ts_s, ts_e = c15[s]["ts"], c15[e - 1]["ts"]
    htf_ts = [c["ts"] for c in c1h]
    hs = min(bisect.bisect_left(htf_ts, ts_s), len(c1h) - 1)
    he = min(bisect.bisect_right(htf_ts, ts_e), len(c1h))
    return c15[s:e], f15[s:e], c1h[hs:he], f1h[hs:he]

BASELINE = dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
                cooldown_bars=10, max_consecutive_losses=3)
OPTIMAL = dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
               cooldown_bars=0, max_consecutive_losses=3,
               exp_multi_ltf=True, exp_multi_ltf_cd=0,
               exp_regime_persist=2)

windows = [(0.00, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 1.00)]

for cfg_name, params, mb_1h, mb_15 in [
    ("BASELINE", BASELINE, 20, 50),
    ("OPTIMAL-cd0", OPTIMAL, 10, 50),
]:
    print(f"\n  {cfg_name}:")
    print(f"  {'Win':>4} {'Period':>30} {'Trades':>7} {'R':>8} {'WR':>6} {'PF':>6} {'MaxDD':>7}")
    print(f"  {'-' * 80}")
    total_r = 0
    for wi, (s, e) in enumerate(windows):
        c15_s, f15_s, c1h_s, f1h_s = get_slice(c15_full, f15_full, c1h_full, f1h_full, s, e)
        fine_s = _load_fine_1m(c15_s[0]["ts"], c15_s[-1]["ts"], symbol=SYMBOL)
        sw15 = _compute_swings(f15_s, "continuous", min_bars=mb_15)
        sw1h = _compute_swings(f1h_s, "continuous", min_bars=mb_1h)
        tr = simulate_v18_experiments(c1h_s, sw1h, c15_s, sw15, fine_s, **params)["ltf_trades"]

        r_vals = [t["r_multiple"] for t in tr]
        wins = sum(1 for r in r_vals if r > 0)
        total_r += sum(r_vals)

        # PF
        gross_win = sum(r for r in r_vals if r > 0)
        gross_loss = abs(sum(r for r in r_vals if r <= 0))
        pf = gross_win / gross_loss if gross_loss > 0 else float('inf')

        # Max DD
        cum, peak, dd = 0, 0, 0
        for r in r_vals:
            cum += r
            peak = max(peak, cum)
            dd = max(dd, peak - cum)

        dates = f"{c15_s[0]['date'][:10]} to {c15_s[-1]['date'][:10]}"
        print(f"  {wi+1:>4} {dates:>30} {len(tr):>7} {sum(r_vals):>+8.1f} {wins/len(tr)*100 if tr else 0:>5.1f}% {pf:>5.2f} {dd:>6.1f}R")
    print(f"  {'TOTAL':>4} {'':>30} {'':>7} {total_r:>+8.1f}")

# ============================================================
# PART 2: cd=0 vs cd=10 trade-by-trade diff audit
# ============================================================
print()
print("=" * 100)
print("PART 2: cd=0 EXTRA TRADES — what are they doing?")
print("=" * 100)

sw1h = _compute_swings(f1h_full, "continuous", min_bars=10)
sw15 = _compute_swings(f15_full, "continuous", min_bars=50)

tr_cd0 = simulate_v18_experiments(c1h_full, sw1h, c15_full, sw15, fine_full,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
    cooldown_bars=0, max_consecutive_losses=3,
    exp_multi_ltf=True, exp_multi_ltf_cd=0,
    exp_regime_persist=2)["ltf_trades"]

tr_cd10 = simulate_v18_experiments(c1h_full, sw1h, c15_full, sw15, fine_full,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_multi_ltf=True, exp_multi_ltf_cd=10,
    exp_regime_persist=2)["ltf_trades"]

tr_base = simulate_v18_experiments(c1h_full,
    _compute_swings(f1h_full, "continuous", min_bars=20), c15_full,
    _compute_swings(f15_full, "continuous", min_bars=50), fine_full,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3)["ltf_trades"]

# Find trades in cd0 that are NOT in cd10 (by entry_ts + dir)
cd0_keys = {(t["entry_ts"], t["dir"]) for t in tr_cd0}
cd10_keys = {(t["entry_ts"], t["dir"]) for t in tr_cd10}
extra_trades = [t for t in tr_cd0 if (t["entry_ts"], t["dir"]) not in cd10_keys]

print(f"  cd=0 total: {len(tr_cd0)} trades")
print(f"  cd=10 total: {len(tr_cd10)} trades")
print(f"  cd=0 extra: {len(extra_trades)} trades")
print()

# Audit the extra trades
extra_r = [t["r_multiple"] for t in extra_trades]
extra_wins = sum(1 for r in extra_r if r > 0)
print(f"  Extra trades R: {sum(extra_r):+.1f}R  WR: {extra_wins/len(extra_r)*100:.1f}%")
print(f"  Extra trades avg R: {statistics.mean(extra_r):.3f}")
print()

# Distribution of extra trades by window type
print(f"  Extra trades by window type:")
etypes = {}
for t in extra_trades:
    k = t["break_kind"]
    etypes[k] = etypes.get(k, 0) + 1
for k, v in sorted(etypes.items()):
    print(f"    {k}: {v}")

# Distribution by hour of day
print(f"  Extra trades by hour (IST):")
hours = {}
for t in extra_trades:
    h = int(t["entry_date"][11:13]) + 5  # UTC to IST
    if h >= 24: h -= 24
    hours[h] = hours.get(h, 0) + 1
for h in range(24):
    cnt = hours.get(h, 0)
    if cnt > 0:
        bar = '#' * (cnt // 2)
        print(f"    {h:02d}:00  {cnt:>3} {bar}")

# How many extra trades are re-entries within same window?
print(f"\n  Extra trade context (first 30):")
print(f"  {'Entry':>20} {'Dir':>4} {'Window':>8} {'R':>7} {'Outcome':>8} {'Bars':>5} {'Risk':>10}")
for t in extra_trades[:30]:
    if t["dir"] == "long":
        risk_usd = t["entry_price"] - t["sl"]
    else:
        risk_usd = t["sl"] - t["entry_price"]
    print(f"  {t['entry_date']:>20} {t['dir']:>4} {t['break_kind']:>8} {t['r_multiple']:>+7.2f} "
          f"{t['outcome']:>8} {t['bars_held']:>5} ${risk_usd:>9.0f}")

# ============================================================
# PART 3: Bootstrap confidence intervals
# ============================================================
print()
print("=" * 100)
print("PART 3: BOOTSTRAP 95% CI (1000 resamples)")
print("=" * 100)

random.seed(42)

for cfg_name, params, mb_1h, mb_15 in [
    ("BASELINE", BASELINE, 20, 50),
    ("OPTIMAL-cd0", OPTIMAL, 10, 50),
]:
    tr = simulate_v18_experiments(c1h_full, sw1h if "OPTIMAL" in cfg_name else _compute_swings(f1h_full, "continuous", min_bars=20),
                                  c15_full, sw15 if "OPTIMAL" in cfg_name else _compute_swings(f15_full, "continuous", min_bars=50),
                                  fine_full, **params)["ltf_trades"]
    r_vals = [t["r_multiple"] for t in tr]
    n = len(r_vals)
    obs_r = sum(r_vals)
    obs_wr = sum(1 for r in r_vals if r > 0) / n * 100

    boot_rs = []
    boot_wrs = []
    for _ in range(1000):
        sample = [r_vals[random.randint(0, n-1)] for _ in range(n)]
        boot_rs.append(sum(sample))
        boot_wrs.append(sum(1 for r in sample if r > 0) / n * 100)

    boot_rs.sort()
    boot_wrs.sort()
    ci_lo_r = boot_rs[24]
    ci_hi_r = boot_rs[974]
    ci_lo_wr = boot_wrs[24]
    ci_hi_wr = boot_wrs[974]

    print(f"\n  {cfg_name}:")
    print(f"    Observed: {obs_r:+.1f}R  WR {obs_wr:.1f}%  ({n} trades)")
    print(f"    Bootstrap 95% CI for R: [{ci_lo_r:+.1f}, {ci_hi_r:+.1f}]")
    print(f"    Bootstrap 95% CI for WR: [{ci_lo_wr:.1f}%, {ci_hi_wr:.1f}%]")
    print(f"    CI width: {ci_hi_r - ci_lo_r:.1f}R")

"""Deep validation: Is the v18 backtest for real?

Checks R bounds, streaks, timing, 16-day cap, overlaps, SL sanity,
trail exits, per-year consistency, exit reasons, suspicious patterns.

Run: python backtest/tests/test_deep_validate.py
"""
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"
PARAMS = {"sl_buf_atr": 0.10, "chop_thresh": 58.0, "cooldown_bars": 0,
          "max_consecutive_losses": 3, "ext_stop_r": 1.5, "htf_rr": 3.0}


def load_window(tf):
    df = load_btc_df(tf, SYMBOL)
    candles, flow = [], []
    for row in df.itertuples():
        d = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": d, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low),
                        "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=d, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def main():
    print("=" * 80)
    print("DEEP VALIDATION: Is this backtest for real?")
    print("=" * 80)

    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=SYMBOL)

    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=PARAMS["sl_buf_atr"], ext_stop_r=PARAMS["ext_stop_r"],
        mode="b2_vs_flip_chop", chop_thresh=PARAMS["chop_thresh"],
        cooldown_bars=PARAMS["cooldown_bars"],
        max_consecutive_losses=PARAMS["max_consecutive_losses"],
        htf_rr=PARAMS["htf_rr"])
    trades = result["ltf_trades"]
    htf_trades = result.get("htf_trades", [])
    violations = 0

    # 1. R bounds
    print("\n[1] R-VALUE BOUNDS")
    rs = [t["r_multiple"] for t in trades]
    worst = min(rs); best = max(rs)
    below_neg1 = [t for t in trades if t["r_multiple"] < -1.001]
    print("  Worst trade: {:.3f}R".format(worst))
    print("  Best trade: {:.3f}R".format(best))
    print("  Trades < -1R: {}".format(len(below_neg1)))
    if below_neg1:
        violations += 1
        for t in below_neg1:
            print("    VIOLATION: {} -> {} = {:.3f}R".format(
                t["entry_date"], t["exit_date"], t["r_multiple"]))
    else:
        print("  PASS: All trades >= -1R")

    # 2. Streak analysis
    print("\n[2] STREAK ANALYSIS")
    max_loss_streak = 0; curr = 0; max_win_streak = 0; wc = 0
    for r in rs:
        if r <= 0:
            curr += 1
            max_loss_streak = max(max_loss_streak, curr)
            wc = 0
        else:
            wc += 1
            max_win_streak = max(max_win_streak, wc)
            curr = 0
    print("  Max loss streak: {} (halt=3, must be <= 3)".format(max_loss_streak))
    print("  Max win streak: {}".format(max_win_streak))
    if max_loss_streak > 3:
        violations += 1
        print("  VIOLATION: loss streak {} > 3!".format(max_loss_streak))
    else:
        print("  PASS")

    # 3. 16-day cap check
    print("\n[3] 16-DAY CAP CHECK")
    cap_violations = []
    for t in trades:
        try:
            ed = datetime.strptime(t["entry_date"], "%Y-%m-%d %H:%M:%S")
            xd = datetime.strptime(t["exit_date"], "%Y-%m-%d %H:%M:%S")
            hold = (xd - ed).total_seconds() / 86400
            if hold > 16.5:
                cap_violations.append((t["entry_date"], t["exit_date"], hold))
        except Exception:
            pass
    print("  Trades held > 16.5 days: {}".format(len(cap_violations)))
    if cap_violations:
        violations += 1
        for e, x, h in cap_violations[:5]:
            print("    VIOLATION: {} -> {} = {:.1f} days".format(e, x, h))
    else:
        print("  PASS: All trades within 16-day cap")

    # 4. Overlapping trades
    print("\n[4] OVERLAPPING TRADES")
    overlaps = 0
    for i in range(len(trades)):
        for j in range(i + 1, min(i + 20, len(trades))):
            try:
                e1 = datetime.strptime(trades[i]["entry_date"], "%Y-%m-%d %H:%M:%S")
                x1 = datetime.strptime(trades[i]["exit_date"], "%Y-%m-%d %H:%M:%S")
                e2 = datetime.strptime(trades[j]["entry_date"], "%Y-%m-%d %H:%M:%S")
                x2 = datetime.strptime(trades[j]["exit_date"], "%Y-%m-%d %H:%M:%S")
                if e1 < x2 and e2 < x1:
                    overlaps += 1
            except Exception:
                pass
    print("  Overlapping trades: {}".format(overlaps))
    if overlaps > 0:
        violations += 1
        print("  VIOLATION: {} overlapping trades!".format(overlaps))
    else:
        print("  PASS")

    # 5. SL = exactly -1R
    print("\n[5] SL EXITS = -1R EXACTLY")
    sl_trades = [t for t in trades if t["outcome"] == "sl"]
    sl_rs = [t["r_multiple"] for t in sl_trades]
    sl_bad = [r for r in sl_rs if abs(r - (-1.0)) > 0.001]
    print("  SL exits: {}".format(len(sl_trades)))
    if sl_rs:
        print("  SL R range: {:.4f} to {:.4f}".format(min(sl_rs), max(sl_rs)))
    print("  SL != -1R: {}".format(len(sl_bad)))
    if sl_bad:
        violations += 1
        print("    Values: {}".format(sl_bad[:10]))
    else:
        print("  PASS: All SL exits exactly -1R")

    # 6. Trail exits > 0R
    print("\n[6] TRAIL EXITS > 0R")
    trail_trades = [t for t in trades if t["outcome"] == "trail"]
    trail_rs = [t["r_multiple"] for t in trail_trades]
    trail_bad = [r for r in trail_rs if r <= 0]
    print("  Trail exits: {}".format(len(trail_trades)))
    if trail_rs:
        print("  Trail R range: {:.3f} to {:.3f}".format(min(trail_rs), max(trail_rs)))
    print("  Trail R <= 0: {}".format(len(trail_bad)))
    if trail_bad:
        violations += 1
        print("    VIOLATION: {}".format(trail_bad[:10]))
    else:
        print("  PASS: All trail exits positive")

    # 7. Per-year consistency
    print("\n[7] PER-YEAR CONSISTENCY")
    yearly = defaultdict(list)
    for t in trades:
        y = t["entry_date"][:4]
        yearly[y].append(t["r_multiple"])
    for y in sorted(yearly):
        yrs = yearly[y]
        tot = sum(yrs); n = len(yrs)
        print("  {}: {}t {:+.1f}R avg {:+.2f}R".format(y, n, tot, tot / n))

    # 8. HTF trades
    print("\n[8] HTF TRADES")
    print("  HTF trades generated: {}".format(len(htf_trades)))
    if htf_trades:
        for h in htf_trades[:3]:
            print("    {} -> {} R={}".format(
                h.get("entry_date", "?"), h.get("exit_date", "?"),
                h.get("r_multiple", "?")))

    # 9. Exit reason distribution
    print("\n[9] EXIT REASONS")
    reasons = defaultdict(int)
    for t in trades:
        reasons[t["outcome"]] += 1
    for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
        pct = 100 * c / len(trades)
        print("  {}: {} ({:.1f}%)".format(r, c, pct))

    # 10. Direction distribution
    print("\n[10] LONG vs SHORT")
    longs = [t for t in trades if t.get("dir", "") == "long"]
    shorts = [t for t in trades if t.get("dir", "") == "short"]
    print("  Long: {} | Short: {}".format(len(longs), len(shorts)))
    long_r = sum(t["r_multiple"] for t in longs)
    short_r = sum(t["r_multiple"] for t in shorts)
    print("  Long R: {:+.1f} | Short R: {:+.1f}".format(long_r, short_r))

    # 11. SL vs entry sanity
    print("\n[11] SL vs ENTRY SANITY")
    bad_sl = 0
    for t in trades:
        entry = float(t.get("entry_price", 0))
        sl = float(t.get("sl", 0))
        direction = t.get("dir", "")
        risk = abs(entry - sl)
        if risk <= 0:
            bad_sl += 1
            continue
        if direction == "long" and sl >= entry:
            bad_sl += 1
            print("  VIOLATION: LONG SL={} >= entry={}".format(sl, entry))
        elif direction == "short" and sl <= entry:
            bad_sl += 1
            print("  VIOLATION: SHORT SL={} <= entry={}".format(sl, entry))
    print("  Bad SL placements: {}".format(bad_sl))
    if bad_sl == 0:
        print("  PASS: All SLs correctly placed")
    else:
        violations += 1

    # 12. Hold time distribution
    print("\n[12] HOLD TIME DISTRIBUTION")
    hold_times = []
    for t in trades:
        try:
            ed = datetime.strptime(t["entry_date"], "%Y-%m-%d %H:%M:%S")
            xd = datetime.strptime(t["exit_date"], "%Y-%m-%d %H:%M:%S")
            hold_times.append((xd - ed).total_seconds() / 3600)
        except Exception:
            pass
    if hold_times:
        hold_times.sort()
        print("  Min: {:.1f}h | Median: {:.1f}h | Max: {:.1f}h".format(
            min(hold_times), hold_times[len(hold_times) // 2], max(hold_times)))
        print("  <1h: {} | 1-8h: {} | 8-24h: {} | 1-3d: {} | 3-7d: {} | 7-16d: {}".format(
            sum(1 for h in hold_times if h < 1),
            sum(1 for h in hold_times if 1 <= h < 8),
            sum(1 for h in hold_times if 8 <= h < 24),
            sum(1 for h in hold_times if 24 <= h < 72),
            sum(1 for h in hold_times if 72 <= h < 168),
            sum(1 for h in hold_times if 168 <= h)))

    # 13. R distribution shape
    print("\n[13] R DISTRIBUTION")
    bins = [(-1.01, -0.99, "= -1R (SL)"), (-0.99, 0, "loss"), (0, 1, "0-1R"),
            (1, 2, "1-2R"), (2, 3, "2-3R"), (3, 5, "3-5R"), (5, 10, "5-10R"),
            (10, 20, "10-20R"), (20, 50, "20-50R"), (50, 200, "50R+")]
    for lo, hi, label in bins:
        count = sum(1 for r in rs if lo <= r < hi)
        bar = "#" * count
        print("  {:>12}: {:>3} {}".format(label, count, bar))

    # 14. Monthly trade frequency
    print("\n[14] MONTHLY TRADE FREQUENCY")
    monthly = defaultdict(int)
    for t in trades:
        ym = t["entry_date"][:7]
        monthly[ym] += 1
    counts = list(monthly.values())
    if counts:
        print("  Min: {} | Max: {} | Avg: {:.1f}".format(
            min(counts), max(counts), sum(counts) / len(counts)))
        print("  Months with 0 trades: {}".format(
            sum(1 for c in counts if c == 0)))

    # FINAL
    print("\n" + "=" * 80)
    if violations == 0:
        print("ALL CHECKS PASSED — BACKTEST IS LEGITIMATE")
    else:
        print("VIOLATIONS FOUND: {}".format(violations))
    print("=" * 80)


if __name__ == "__main__":
    main()

"""Deep truncation test: full config with ALL filters enabled.
Test at multiple truncation points to be thorough."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle

# Full config with ALL filters
FULL = {
    "mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
    "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 0,
    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
    "exp_partial_r": 0.0, "exp_swingpause": 1, "exp_skip_weekend": 1,
    "exp_wage_h": 10, "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
    "exp_atr_ratio_max": 1.4, "exp_bias_momentum_min": 0.0,
    "window_end": "exit",
}


def truncate_and_run(data, sim, c15, c1h, sw10, sw15, fine, trades_full, truncate_at):
    """Truncate c15 at bar, recompute sw15, run, compare."""
    c15_trunc = c15[:truncate_at]

    f15_trunc = [FlowCandle(date=c["date"], open=float(c["open"]), high=float(c["high"]),
                             low=float(c["low"]), close=float(c["close"])) for c in c15_trunc]
    sw15_trunc = _compute_swings(f15_trunc, "continuous", min_bars=50)

    r_trunc = sim(c1h, sw10, c15_trunc, sw15_trunc, fine_ltf=fine, **FULL)
    trades_trunc = r_trunc["ltf_trades"] if isinstance(r_trunc, dict) else r_trunc

    match = 0
    mismatches = []
    for i, tt in enumerate(trades_trunc):
        if i < len(trades_full):
            if (tt["entry_date"] == trades_full[i]["entry_date"] and
                tt["exit_date"] == trades_full[i]["exit_date"] and
                abs(float(tt["r_multiple"]) - float(trades_full[i]["r_multiple"])) < 0.01):
                match += 1
            else:
                mismatches.append(i)
    return len(trades_trunc), match, mismatches


def main():
    print("=" * 80)
    print("  DEEP TRUNCATION TEST: ALL FILTERS ENABLED")
    print("=" * 80)

    data = get_data()
    sim = build_module()

    r_full = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                 fine_ltf=data["fine"], **FULL)
    trades_full = r_full["ltf_trades"] if isinstance(r_full, dict) else r_full
    print(f"\n  Full run: {len(trades_full)} trades")

    # Find entry bar indices
    entry_bars = []
    for t in trades_full:
        bar_date = t.get("entry_date", "")[:19]
        for j, c in enumerate(data["c15"]):
            if c["date"][:19] == bar_date:
                entry_bars.append(j)
                break

    # Test at multiple truncation points: 25%, 50%, 75% of trades
    test_points = [0.25, 0.5, 0.75]
    all_pass = True

    for pct in test_points:
        trade_idx = int(len(entry_bars) * pct)
        truncate_at = entry_bars[trade_idx] + 50
        print(f"\n  Truncation at {pct*100:.0f}% of trades (bar {truncate_at}, trade {trade_idx + 1}/{len(entry_bars)}):")

        n, match, mismatches = truncate_and_run(
            data, sim, data["c15"], data["c1h"], data["sw10"], data["sw15"],
            data["fine"], trades_full, truncate_at)

        if match == n:
            print(f"    {n} trades, {match} exact matches: PASS")
        else:
            print(f"    {n} trades, {match} matches, {len(mismatches)} MISMATCHES: FAIL")
            all_pass = False
            for i in mismatches[:5]:
                ft = trades_full[i]
                tt = trades_trunc[i] if i < len(trades_trunc) else None
                print(f"      Trade {i}: full={ft['entry_date'][:16]}->{ft['exit_date'][:16]} "
                      f"R={float(ft['r_multiple']):+.2f}")

    # Also test with BM enabled
    print(f"\n  Testing with bias_momentum_min=0.7...")
    full_bm = dict(FULL, exp_bias_momentum_min=0.7)
    r_full_bm = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                    fine_ltf=data["fine"], **full_bm)
    trades_full_bm = r_full_bm["ltf_trades"] if isinstance(r_full_bm, dict) else r_full_bm

    truncate_at = entry_bars[len(entry_bars) // 2] + 50
    c15_trunc = data["c15"][:truncate_at]
    f15_trunc = [FlowCandle(date=c["date"], open=float(c["open"]), high=float(c["high"]),
                             low=float(c["low"]), close=float(c["close"])) for c in c15_trunc]
    sw15_trunc = _compute_swings(f15_trunc, "continuous", min_bars=50)

    r_trunc_bm = sim(data["c1h"], data["sw10"], c15_trunc, sw15_trunc,
                     fine_ltf=data["fine"], **full_bm)
    trades_trunc_bm = r_trunc_bm["ltf_trades"] if isinstance(r_trunc_bm, dict) else r_trunc_bm

    match_bm = 0
    for i, tt in enumerate(trades_trunc_bm):
        if i < len(trades_full_bm):
            if (tt["entry_date"] == trades_full_bm[i]["entry_date"] and
                tt["exit_date"] == trades_full_bm[i]["exit_date"] and
                abs(float(tt["r_multiple"]) - float(trades_full_bm[i]["r_multiple"])) < 0.01):
                match_bm += 1

    if match_bm == len(trades_trunc_bm):
        print(f"    {len(trades_trunc_bm)} trades, {match_bm} matches: PASS")
    else:
        print(f"    {len(trades_trunc_bm)} trades, {match_bm} matches: FAIL")
        all_pass = False

    print(f"\n{'='*80}")
    if all_pass:
        print("  ALL TRUNCATION TESTS PASS — NO LOOK-AHEAD BIAS")
    else:
        print("  SOME TESTS FAILED — POSSIBLE LOOK-AHEAD BIAS!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

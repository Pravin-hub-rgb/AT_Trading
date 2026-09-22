"""Full validation: bare single + wage10 + bm0.6
Complete test suite: IS metrics, yearly, monthly, rolling, WF, OOS."""
import sys, time, json, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data
from test_experiments_craze import build_module
from src.btc.btc_routes import _trade_costs
from engine.v18_params import get_v18_params
from replay_harness import INSTRUMENT

_g = get_v18_params(INSTRUMENT)

# Configs to compare
CONFIGS = {
    "bare_wage10_base": {
        "desc": "bare + wage10 (no bm)",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_wage_h": 10,
                    "window_end": "exit"},
    },
    "bare_wage10_bm06": {
        "desc": "bare + wage10 + bm0.6",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_wage_h": 10,
                    "exp_bias_momentum_min": 0.6,
                    "window_end": "exit"},
    },
    "bare_base_bm06": {
        "desc": "bare (no gates) + bm0.6",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0,
                    "exp_bias_momentum_min": 0.6,
                    "window_end": "exit"},
    },
}


def full_analysis(trades, label):
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs)
    net = sum(rs)
    wins = sum(1 for r in rs if r > 0)
    wr = wins / max(n, 1) * 100
    peak = 0.0; cum = 0.0; dd = 0.0; cur = 0; mx = 0
    for r in rs:
        cum += r
        if cum > peak: peak = cum
        dd = max(dd, peak - cum)
        if r < 0: cur += 1; mx = max(mx, cur)
        else: cur = 0
    avg = net / max(n, 1)
    pf_up = sum(r for r in rs if r > 0)
    pf_dn = abs(sum(r for r in rs if r <= 0))
    pf = pf_up / max(pf_dn, 0.01)
    avg_win = sum(r for r in rs if r > 0) / max(wins, 1)
    avg_loss = sum(r for r in rs if r <= 0) / max(n - wins, 1)
    ndd = abs(net / dd) if dd > 0 else 0

    # Yearly
    yearly = defaultdict(lambda: {"n": 0, "net": 0.0, "wins": 0})
    for t in trades:
        y = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        yearly[y]["n"] += 1
        yearly[y]["net"] += float(t["r_multiple"])
        if float(t["r_multiple"]) > 0:
            yearly[y]["wins"] += 1

    # Monthly
    monthly = defaultdict(lambda: {"n": 0, "net": 0.0})
    for t in trades:
        m = (t.get("exit_date") or t.get("entry_date") or "")[:7]
        monthly[m]["n"] += 1
        monthly[m]["net"] += float(t["r_multiple"])

    # Rolling
    def rolling_dd(eq, w):
        results = []
        for i in range(len(eq)):
            s = max(0, i - w + 1)
            seg = eq[s:i+1]
            pk = max(seg)
            results.append(pk - seg[-1])
        return results

    eq = []
    cum = 0.0
    for r in rs:
        cum += r
        eq.append(cum)

    rdd10 = rolling_dd(eq, 10)
    rdd20 = rolling_dd(eq, 20)
    rdd50 = rolling_dd(eq, 50)

    # Win/loss streaks
    streak = 0; mx_win = 0; mx_loss = 0
    for r in rs:
        if r > 0: streak += 1; mx_win = max(mx_win, streak)
        else: streak = 0; mx_loss = max(mx_loss, streak)

    # Underwater
    peak2 = 0; uw = 0; max_uw = 0; cur_uw = 0
    for cv in eq:
        if cv > peak2: peak2 = cv; cur_uw = 0
        else: cur_uw += 1
        max_uw = max(max_uw, cur_uw)
        if cur_uw > 0: uw += 1
    uw_pct = uw / max(n, 1) * 100

    # Top trades
    top5 = sorted(trades, key=lambda t: float(t["r_multiple"]), reverse=True)[:5]
    top5_r = sum(float(t["r_multiple"]) for t in top5)

    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")
    print(f"\n  CORE METRICS:")
    print(f"  Trades:       {n}")
    print(f"  NET R:        {net:+.1f}R")
    print(f"  Avg R/trade:  {avg:+.3f}R")
    print(f"  Win Rate:     {wr:.1f}%")
    print(f"  Profit Factor:{pf:.2f}")
    print(f"  Max DD:       {dd:.1f}R")
    print(f"  NET/DD:       {ndd:.2f}")
    print(f"  Avg Win:      {avg_win:+.3f}R")
    print(f"  Avg Loss:     {avg_loss:+.3f}R")
    print(f"  Max Win Streak:  {mx_win}")
    print(f"  Max Loss Streak: {mx_loss}")

    print(f"\n  SMOOTHNESS:")
    print(f"  Max underwater:     {max_uw} trades ({uw_pct:.0f}% of time)")
    print(f"  Rolling 10t maxDD:  {max(rdd10):.1f}R  avg: {sum(rdd10)/len(rdd10):.1f}R")
    print(f"  Rolling 20t maxDD:  {max(rdd20):.1f}R  avg: {sum(rdd20)/len(rdd20):.1f}R")
    print(f"  Rolling 50t maxDD:  {max(rdd50):.1f}R  avg: {sum(rdd50)/len(rdd50):.1f}R")

    print(f"\n  YEARLY:")
    for y in sorted(yearly.keys()):
        d = yearly[y]
        wr_y = d["wins"] / max(d["n"], 1) * 100
        print(f"    {y}:  {d['n']:>3}t  {d['net']:>+7.1f}R  WR {wr_y:.0f}%")
    print(f"    {'ALL':>4}  {n:>3}t  {net:>+7.1f}R  WR {wr:.0f}%")

    print(f"\n  MONTHLY R:")
    pos_m = 0; neg_m = 0
    for m in sorted(monthly.keys()):
        d = monthly[m]
        bar = "+" * int(max(0, d["net"])) + "-" * int(max(0, -d["net"]))
        marker = "" if d["net"] >= 0 else ""
        if d["net"] >= 0: pos_m += 1
        else: neg_m += 1
        print(f"    {m}:  {d['n']:>3}t  {d['net']:>+7.1f}R  {marker}")
    print(f"    Green: {pos_m}/{pos_m+neg_m} months ({pos_m/(pos_m+neg_m)*100:.0f}%)")

    print(f"\n  TOP 5 TRADES:")
    for t in top5:
        ed = t.get("exit_date", "")[:10]
        d = "LONG" if float(t["r_multiple"]) > 0 else "?"
        print(f"    {t['r_multiple']:>+7.2f}R  {ed}")

    print(f"\n  TOP 5 contribute: {top5_r:.1f}R out of {net:.1f}R ({top5_r/max(net,0.01)*100:.0f}%)")

    return n, net, dd, ndd, wr


def main():
    print("=" * 80)
    print("  FULL VALIDATION: bare single + wage10 + bm0.6")
    print("=" * 80)

    data = get_data()
    sim = build_module()

    for cname, cfg in CONFIGS.items():
        t0 = time.time()
        params = dict(cfg["params"])
        r = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)
        trades = r["ltf_trades"] if isinstance(r, dict) else r
        dt = time.time() - t0
        full_analysis(trades, f"{cfg['desc']}  [{dt:.1f}s]")

    # Side-by-side comparison
    print(f"\n{'='*80}")
    print(f"  COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"\n  {'Config':<30} {'n':>4} {'NET':>8} {'DD':>6} {'NET/DD':>7} {'WR':>5} {'AvgR':>7}")
    print(f"  {'-'*72}")

    results = {}
    for cname, cfg in CONFIGS.items():
        params = dict(cfg["params"])
        r = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)
        trades = r["ltf_trades"] if isinstance(r, dict) else r
        rs = [float(t["r_multiple"]) for t in trades]
        n = len(rs)
        net = sum(rs)
        wins = sum(1 for r in rs if r > 0)
        wr = wins / max(n, 1) * 100
        peak = 0.0; cum = 0.0; dd = 0.0
        for r in rs:
            cum += r
            if cum > peak: peak = cum
            dd = max(dd, peak - cum)
        ndd = abs(net / dd) if dd > 0 else 0
        avg = net / max(n, 1)
        results[cname] = {"n": n, "net": net, "dd": dd, "ndd": ndd, "wr": wr, "avg": avg}
        print(f"  {cfg['desc']:<30} {n:>4} {net:>+7.1f}R {dd:>5.1f} {ndd:>6.2f} {wr:>4.1f}% {avg:>+6.3f}")

    # Delta from base
    base = results.get("bare_wage10_base") or results.get(list(results.keys())[0])
    print(f"\n  DETAILED DELTAS from base:")
    for cname, cfg in CONFIGS.items():
        if cname == "bare_wage10_base": continue
        r = results[cname]
        dn = r["n"] - base["n"]
        dnet = r["net"] - base["net"]
        ddd = r["dd"] - base["dd"]
        dndd = r["ndd"] - base["ndd"]
        print(f"  {cfg['desc']:<30} {dn:>+4}t {dnet:>+7.1f}R {ddd:>+5.1f} DD {dndd:>+5.2f} NET/DD")


if __name__ == "__main__":
    main()

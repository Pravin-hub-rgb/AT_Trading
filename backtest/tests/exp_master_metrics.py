"""Full metrics for master leaderboard: champion_multi + utcsat_multi on IS and true OOS."""
import sys, json, math, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _trade_costs, _load_fine_1m, _compute_swings
from test_experiments_craze import build_module as build_craze, BASE as CRAZE_BASE
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from experiment_registry import EXPERIMENTS, BP

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)


def full_metrics(trades, label, is_gross_only=False):
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs)
    if n == 0:
        print(f"  {label}: NO TRADES")
        return None
    gross = sum(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    nw, nl = len(wins), len(losses)
    wr = 100.0 * nw / n
    aw = sum(wins) / max(nw, 1)
    al = sum(losses) / max(nl, 1)
    awal = aw / max(abs(al), 1e-9)
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)
    exp = gross / n
    peak = 0.0; cum = 0.0; dd = 0.0; cur = 0; mcl = 0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x < 0: cur += 1; mcl = max(mcl, cur)
        else: cur = 0
    mean_r = gross / n
    var_r = sum((x - mean_r) ** 2 for x in rs) / max(n - 1, 1)
    std_r = math.sqrt(var_r) if var_r > 0 else 1e-9
    sharpe = mean_r / std_r * math.sqrt(n)
    # costs
    try:
        g_costs, _ = _trade_costs(trades, _P["fee_pct"], 0.0, _P["entry_slip_pct"], _P["exit_slip_pct"])
    except Exception:
        g_costs = 0.0
    funding = 0.0
    for t in trades:
        e, sl = float(t["entry_price"]), float(t["sl"]); rk = abs(e - sl)
        if rk > 0 and e > 0:
            funding += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    costs = g_costs + funding
    net = gross - costs
    # yearly / monthly
    py = defaultdict(float); pyn = defaultdict(int)
    pm = defaultdict(float); pmn = defaultdict(int)
    for t, r in zip(trades, rs):
        y = (t.get("exit_date") or "")[:4]; py[y] += r; pyn[y] += 1
        m = (t.get("exit_date") or "")[:7]; pm[m] += r; pmn[m] += 1
    green_m = sum(1 for v in pm.values() if v >= 0)
    # rolling worst by trade index (approx by cumulative)
    # rolling 12-month by calendar
    months_sorted = sorted(pm.keys())
    worst_3 = worst_6 = worst_12 = 0.0
    for i in range(len(months_sorted)):
        for w, name in [(3, "w3"), (6, "w6"), (12, "w12")]:
            seg = months_sorted[i:i+w]
            if len(seg) == w:
                s = sum(pm[m] for m in seg)
                if name == "w3": worst_3 = min(worst_3, s) if worst_3 else s; worst_3 = s if worst_3 == 0 else min(worst_3, s)
                elif name == "w6": worst_6 = s if worst_6 == 0 else min(worst_6, s)
                else: worst_12 = s if worst_12 == 0 else min(worst_12, s)
    # fix: initialize properly
    def worst_window(size):
        if len(months_sorted) < size: return 0.0
        vals = [sum(pm[m] for m in months_sorted[i:i+size]) for i in range(len(months_sorted)-size+1)]
        return min(vals) if vals else 0.0
    w3, w6, w12 = worst_window(3), worst_window(6), worst_window(12)
    # tail dependence
    srt = sorted(rs, reverse=True)
    top1 = gross - (gross - srt[0]) if n else 0  # net without top1 = gross - top1 - costs... simpler:
    net_wo = lambda k: sum(srt[k:]) - costs  # remove top k winners from gross, keep costs
    tail = {
        "full": net,
        "wo1": sum(srt[1:]) - costs,
        "wo5": sum(srt[5:]) - costs if n > 5 else 0,
        "wo10": sum(srt[10:]) - costs if n > 10 else 0,
    }
    # avg bars held
    bars = [int(t.get("bars_held") or 0) for t in trades]
    abh = sum(bars) / max(len(bars), 1)
    # short/long
    longs = [r for t, r in zip(trades, rs) if str(t.get("dir", "")).lower() in ("long", "1", "buy")]
    shorts = [r for t, r in zip(trades, rs) if str(t.get("dir", "")).lower() in ("short", "-1", "sell")]
    print(f"\n  === {label} ===")
    print(f"  Tr={n}  Gross={gross:+.1f}  Costs={costs:.1f}  NET={net:+.1f}")
    print(f"  WR={wr:.1f}%  W/L={nw}/{nl}  AvgW={aw:+.2f}  AvgL={al:+.2f}  W/Lratio={awal:.2f}  PF={pf:.2f}  E[R]={exp:+.3f}")
    print(f"  DD={dd:.1f}  MCL={mcl}  Sharpe(trade)={sharpe:.2f}  NET/DD={net/max(dd,0.01):.2f}  AvgBars={abh:.0f}")
    print(f"  Longs: {len(longs)}t {sum(longs):+.1f}R   Shorts: {len(shorts)}t {sum(shorts):+.1f}R")
    print(f"  Yearly: " + "  ".join(f"{y}:{py[y]:+.1f}({pyn[y]}t)" for y in sorted(py)))
    print(f"  Months: {len(pm)} total, {green_m} green ({100*green_m/max(len(pm),1):.0f}%)")
    print(f"  Worst rolling: 3m={w3:+.1f}  6m={w6:+.1f}  12m={w12:+.1f}")
    print(f"  Tail: full={tail['full']:+.1f}  -top1={tail['wo1']:+.1f}  -top5={tail['wo5']:+.1f}  -top10={tail['wo10']:+.1f}")
    print(f"  Monthly R: " + " ".join(f"{m}:{pm[m]:+.1f}" for m in months_sorted))
    return {"n": n, "gross": gross, "net": net, "costs": costs, "wr": wr, "pf": pf,
            "dd": dd, "mcl": mcl, "sharpe": sharpe, "yearly": dict(py),
            "green": green_m, "months": len(pm), "w12": w12, "tail": tail}


def load_is_trades(key):
    p = ROOT / "backtest/tests" / f"_exp_{key}_results.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data["trades"], data["results"]


def main():
    t0 = time.time()
    sim = build_craze()

    # ---- IS from saved JSON ----
    print("=" * 100)
    print("  IS (2023-2026) — from registry result JSONs")
    print("=" * 100)
    for key in ["champion_multi_sw10", "utcsat_multi_sw10"]:
        trades, res = load_is_trades(key)
        full_metrics(trades, f"IS {key}")

    # ---- OOS 2021-2022 ----
    print("\nLoading OOS...")
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    # registry champions use swing=sw10 -> min_bars_1h=10 (NOT engine default 20)
    sw1ho = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])

    print("=" * 100)
    print("  TRUE OOS (2021-2022) — fresh run, sw10")
    print("=" * 100)
    for key in ["champion_multi_sw10", "utcsat_multi_sw10"]:
        cfg = EXPERIMENTS[key]
        # Match test_oos_2022.py / registry: BP base + cfg params, ext_stop_r from params
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        r = sim(c1ho, sw1ho, c15o, sw15o, fine_ltf=fineo, **params)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        full_metrics(tr, f"OOS {key}")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()

"""Independent validation of D3 structural alignment (other bot's research).

Battery (same playbook as every prior find):
  1. Temporal split — per-year NET on IS for multi + singles
  2. Cross-chain — same configs on sw20 (min_bars_1h=20)
  3. True OOS — 2021-2022 unseen data (dir-match / age gates)

Run: python -m backtest.tests.exp_alignment_validate
"""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from test_experiments_craze import build_module as build_craze
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from experiment_registry import EXPERIMENTS, BP

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)


def metrics(trades):
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs)
    if n == 0:
        return dict(n=0, net=0, wr=0, dd=0, yearly={})
    gross = sum(rs)
    try:
        g, _ = _trade_costs(trades, _P["fee_pct"], 0.0, _P["entry_slip_pct"], _P["exit_slip_pct"])
    except Exception:
        g = 0.0
    funding = 0.0
    for t in trades:
        e, sl = float(t["entry_price"]), float(t["sl"])
        rk = abs(e - sl)
        if rk > 0 and e > 0:
            funding += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    costs = g + funding
    net = gross - costs
    wr = 100 * sum(1 for x in rs if x > 0) / n
    peak = cum = dd = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    # yearly gross R (path order preserved)
    py = defaultdict(float)
    pyn = defaultdict(int)
    for t, r in zip(trades, rs):
        y = (t.get("exit_date") or "")[:4]
        py[y] += r
        pyn[y] += 1
    # yearly NET via per-trade cost_r if present else allocate by count share
    # compute per-trade costs same as master
    pyc = defaultdict(float)
    fee = _P["fee_pct"] / 100.0  # match _trade_costs: fee_pct/100
    # wait - master passes fee_pct=0.055 and function does /100 -> 0.00055
    # entry_slip_pct is passed as 0.005 meaning 0.005% ? function: entry_px * entry_slip_pct / 100
    # So slip values are in percent units (0.005 = 0.005%)
    es = _P["entry_slip_pct"]
    xs = _P["exit_slip_pct"]
    for t in trades:
        y = (t.get("exit_date") or "")[:4]
        risk = abs(float(t["entry_price"]) - float(t["sl"]))
        if risk <= 0:
            continue
        ep = abs(float(t["entry_price"]))
        xp = abs(float(t.get("exit_price", t["entry_price"])))
        fee_r = (ep * fee + xp * fee) / risk
        slip_r = (ep * es / 100.0 + xp * xs / 100.0) / risk
        bars = int(t.get("bars_held", 0))
        # funding: funding_rate_pct default from master formula uses 0.01/8h
        # master: (bars * 0.25 / 8.0) * 0.0001 * (e/rk) = bars * 0.000003125 * e/rk
        # _trade_costs with funding_rate_pct=0.01: funding_per_bar = 0.01/100/32
        fund_r = (ep * (0.01 / 100.0 / 32.0) * bars) / risk
        pyc[y] += fee_r + slip_r + fund_r
    yearly_net = {y: py[y] - pyc[y] for y in py}
    return dict(n=n, net=net, gross=gross, costs=costs, wr=wr, dd=dd, yearly=dict(yearly_net), yearly_n=dict(pyn))


def run(sim, c1h, sw, c15, sw15, fine, params):
    r = sim(c1h, sw, c15, sw15, fine_ltf=fine, **params)
    return r["ltf_trades"] if isinstance(r, dict) else r


def show(label, m):
    ys = "  ".join(f"{y}:{m['yearly'][y]:+.1f}" for y in sorted(m["yearly"]))
    print(f"  {label:<42} n={m['n']:>3} NET={m['net']:>+7.1f} WR={m['wr']:5.1f}% "
          f"DD={m['dd']:5.1f}  {ys}")


def main():
    t0 = time.time()
    print("=" * 100)
    print("  D3 ALIGNMENT VALIDATION — temporal / sw20 / true OOS")
    print("=" * 100)

    sim = build_craze()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    sw20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine_is = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                            max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)

    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    sw20o = _compute_swings(f1ho, "continuous", min_bars=SWING["min_bars_1h"])
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])

    keys = [
        "champion_multi_sw10",
        "dirmatch_multi_sw10",
        "age25_dirmatch_multi_sw10",
        "age10_dirmatch_multi_sw10",
        "dirmatch_swingpause_single_sw10",
        "age10_dirmatch_swingpause_single_sw10",
        "dirmatch_single_sw10",
    ]

    def params_for(key, swing_tag="sw10"):
        cfg = EXPERIMENTS[key]
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        if swing_tag == "sw20":
            p.pop("swing", None)  # swing not a kwarg
        return p

    # ---- 1) IS temporal (sw10) ----
    print("\n--- 1) IS temporal split (sw10, NET by exit year) ---")
    is_m = {}
    for key in keys:
        p = params_for(key)
        tr = run(sim, c1h, sw10, c15, sw15, fine_is, p)
        m = metrics(tr)
        is_m[key] = m
        show(key, m)

    # ---- 2) Cross-chain sw20 ----
    print("\n--- 2) Cross-chain sw20 (IS) ---")
    for key in keys:
        p = params_for(key)
        tr = run(sim, c1h, sw20, c15, sw15, fine_is, p)
        m = metrics(tr)
        show(key + " [sw20]", m)

    # ---- 3) True OOS sw10 ----
    print("\n--- 3) TRUE OOS 2021-2022 (sw10) ---")
    oos_m = {}
    for key in keys:
        p = params_for(key)
        tr = run(sim, c1ho, sw10o, c15o, sw15o, fineo, p)
        m = metrics(tr)
        oos_m[key] = m
        show(key, m)

    # ---- 4) True OOS sw20 ----
    print("\n--- 4) TRUE OOS 2021-2022 (sw20) ---")
    for key in keys:
        p = params_for(key)
        tr = run(sim, c1ho, sw20o, c15o, sw15o, fineo, p)
        m = metrics(tr)
        show(key + " [sw20]", m)

    # ---- 5) retention OOS/IS ----
    print("\n--- 5) Retention OOS/IS NET (annualized) ---")
    print(f"  {'config':<42} {'IS':>8} {'OOS':>8} {'raw%':>6} {'ann%':>6}")
    for key in keys:
        a, b = is_m[key], oos_m[key]
        if a["net"] <= 0:
            continue
        raw = 100 * b["net"] / a["net"]
        # IS ~3.7y, OOS 2y
        ann = 100 * (b["net"] / 2.0) / (a["net"] / 3.7)
        print(f"  {key:<42} {a['net']:>+8.1f} {b['net']:>+8.1f} {raw:>5.0f}% {ann:>5.0f}%")

    # ---- 6) dir-match effect isolated on OOS (pure gate delta) ----
    print("\n--- 6) dir-match isolated: champion vs dirmatch (same base) ---")
    for tag, args in [
        ("IS ", (c1h, sw10, c15, sw15, fine_is)),
        ("OOS", (c1ho, sw10o, c15o, sw15o, fineo)),
    ]:
        p0 = params_for("champion_multi_sw10")
        p1 = params_for("dirmatch_multi_sw10")
        m0 = metrics(run(sim, *args, p0))
        m1 = metrics(run(sim, *args, p1))
        print(f"  {tag} base n={m0['n']} NET={m0['net']:+.1f}  "
              f"dirmatch n={m1['n']} NET={m1['net']:+.1f}  "
              f"delta n={m1['n']-m0['n']:+d} dNET={m1['net']-m0['net']:+.1f} "
              f"dDD={m1['dd']-m0['dd']:+.1f}")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()

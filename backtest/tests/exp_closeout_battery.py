"""Closeout battery — last open research items from experiments_craze §660:

(i)   anchor-lb30 stress battery: per-year, both-halves, cost stress 1x/2x/3x
(ii)  concurrency-cap design for mltf leaders — document (already path-true)
(iii) cd0 latency validation for OPTIMAL: re-entry timing after losses + stats

Mirrors exp43/exp40c Phase C: fine 1m fills, BP (BASE+chop58), ext_stop_r=1.5,
net = gross - fee/slip - fund(). Pins POST trail-fix ee574f9 (fine nets -26R
vs pre-fix exp40c; n unchanged): lb30 w0 (349,170.5); OPT-cd10 w0 (453,233.5).
Run: python backtest/tests/exp_closeout_battery.py
"""
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from exp40c_wage_gate import BP, fund
from test_experiments_craze import (
    build_module, load_candles, _compute_swings, SWING, MB15, INSTRUMENT, stats,
)
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

LB30 = {"exp31_lb": 30}
OPT_CD0 = {"exp_mltf": True, "exp_persist": 2, "chop_thresh": 55.0, "cooldown_bars": 0}
OPT_CD10 = {"exp_mltf": True, "exp_persist": 2, "chop_thresh": 55.0, "cooldown_bars": 10}
PIN_LB30 = (349, 170.5)   # post ee574f9 (was 196.3 pre trail-fix)
PIN_OPT10 = (453, 233.5)  # post ee574f9 (was 259.4 pre trail-fix)


def run_fine(sim, c1h, sw, c15, sw15, fine, params, wage=0.0):
    w = {"exp_wage_h": wage} if wage else {}
    r = sim(c1h, sw, c15, sw15, fine_ltf=fine,
            **{**BP, **params, **w, "ext_stop_r": 1.5})
    return r["ltf_trades"]


def net_of(tr, g):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def full_stats(tr, g):
    if not tr:
        return dict(n=0, gross=0.0, net=0.0, wr=0.0, rpt=0.0, aw=0.0, al=0.0,
                    pf=0.0, dd=0.0)
    nets = [net_of([t], g) for t in tr]
    rs = [float(t["r_multiple"]) for t in tr]
    wins = [x for x in nets if x > 0]
    loss = [x for x in nets if x <= 0]
    net = sum(nets)
    gp = sum(wins) if wins else 0.0
    gl = -sum(loss) if loss else 0.0
    eq = peak = dd = 0.0
    for v in nets:
        eq += v
        if eq > peak:
            peak = eq
        d = peak - eq
        if d > dd:
            dd = d
    return dict(
        n=len(nets), gross=sum(rs), net=net,
        wr=100.0 * len(wins) / max(len(nets), 1),
        rpt=net / max(len(nets), 1),
        aw=sum(wins) / len(wins) if wins else 0.0,
        al=sum(loss) / len(loss) if loss else 0.0,
        pf=gp / gl if gl > 0 else float("inf"),
        dd=dd,
    )


def fmt(s):
    pfs = "inf" if s["pf"] == float("inf") else f"{s['pf']:.2f}"
    return (f"n={s['n']:>4} G={s['gross']:+7.1f} NET={s['net']:+7.1f} "
            f"WR={s['wr']:5.1f}% R/t={s['rpt']:+.3f} "
            f"avgW={s['aw']:+.2f} avgL={s['al']:+.2f} PF={pfs:>5} DD={s['dd']:5.1f}")


def year_split(tr):
    out = {}
    for t in tr:
        y = str(t["entry_date"])[:4]
        out.setdefault(y, []).append(t)
    return out


def half_split(tr):
    n = len(tr)
    return tr[: n // 2], tr[n // 2:]


def cost_stress(tr, g, mult):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, g["fee_pct"] * mult, 0.0,
                         g["entry_slip_pct"] * mult, g["exit_slip_pct"] * mult)
    return sum(rs) - c2 - fund(tr)


def post_loss_latency(tr):
    lags = []
    pending_exit = None
    for t in tr:
        if pending_exit is not None:
            try:
                e = int(t["entry_ts"])
                x = int(pending_exit)
                if e >= x:
                    lags.append(round((e - x) / 900.0))
            except (KeyError, TypeError, ValueError):
                pass
            pending_exit = None
        if float(t["r_multiple"]) <= 0:
            pending_exit = t.get("exit_ts")
    return lags


def max_loss_streak(tr):
    st = mx = 0
    for t in tr:
        if float(t["r_multiple"]) <= 0:
            st += 1
            mx = max(mx, st)
        else:
            st = 0
    return mx


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  CLOSEOUT BATTERY — anchor-lb30 stress + OPT cd0 latency + cap design", flush=True)
    print("=" * 100, flush=True)

    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    sim = build_module()
    g = _gvp(INSTRUMENT)

    # identity gate (coarse, flags-off == shipped)
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw20, c15, sw15, fine_ltf=[], **dict(
        {k: BP[k] for k in BP}))  # wrong basis — use craze BASE
    # use same as exp43: BASE not BP for identity
    from test_experiments_craze import BASE as CRAZE_BASE
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw20, c15, sw15, fine_ltf=[], **dict(CRAZE_BASE))
    r0 = sim(c1h, sw20, c15, sw15, fine_ltf=[], **dict(CRAZE_BASE))
    s_ship, s0 = stats(r_ship["ltf_trades"]), stats(r0["ltf_trades"])
    assert s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (flags-off == shipped, n=%d)" % s0["n"], flush=True)

    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    assert fine and len(fine) > 1000, "fine fills empty (%r)" % (len(fine) if fine else 0,)
    print("fine bars: %d" % len(fine), flush=True)

    # ---------- (i) anchor-lb30 stress battery ----------
    print("\n" + "-" * 100, flush=True)
    print("  (i) ANCHOR-lb30 STRESS BATTERY (fine fills, ext1.5)", flush=True)
    print("-" * 100, flush=True)
    tr = run_fine(sim, c1h, sw20, c15, sw15, fine, LB30)
    s = full_stats(tr, g)
    print(f"  baseline                 {fmt(s)}", flush=True)
    en, eg = PIN_LB30
    pin_ok = (s["n"] == en and abs(s["net"] - eg) <= 0.15)
    print(f"  PIN lb30 w0 {en}t {eg:+.1f}  {'OK' if pin_ok else 'MISMATCH'}", flush=True)
    if not pin_ok:
        raise SystemExit("PIN FAIL — abort")

    print("\n  per-year NET:", flush=True)
    py = year_split(tr)
    all_pos = True
    for y in sorted(py):
        ys = full_stats(py[y], g)
        mark = " +" if ys["net"] > 0 else " -"
        if ys["net"] <= 0:
            all_pos = False
        print(f"    {y}: {fmt(ys)}{mark}", flush=True)
    print(f"  all years positive: {'PASS' if all_pos else 'FAIL'}", flush=True)

    h1, h2 = half_split(tr)
    s1, s2 = full_stats(h1, g), full_stats(h2, g)
    bh = s1["net"] > 0 and s2["net"] > 0
    print("\n  both-halves (chronological 50/50):", flush=True)
    print(f"    H1: {fmt(s1)}", flush=True)
    print(f"    H2: {fmt(s2)}", flush=True)
    print(f"    both positive: {'PASS' if bh else 'FAIL'}", flush=True)

    print("\n  cost stress (fee+slip x M, funding fixed):", flush=True)
    for m in (1.0, 1.5, 2.0, 3.0):
        n = cost_stress(tr, g, m)
        mark = " PASS" if n > 0 else " FAIL"
        print(f"    x{m:.1f}  NET {n:+7.1f}{mark}", flush=True)

    # ---------- (iii) OPT cd0 latency validation ----------
    print("\n" + "-" * 100, flush=True)
    print("  (iii) OPT cd0 vs cd10 — stats + post-loss re-entry latency", flush=True)
    print("-" * 100, flush=True)
    tr0 = run_fine(sim, c1h, sw10, c15, sw15, fine, OPT_CD0)
    tr10 = run_fine(sim, c1h, sw10, c15, sw15, fine, OPT_CD10)
    s0o, s10 = full_stats(tr0, g), full_stats(tr10, g)
    print(f"  OPT cd0  w0 ext1.5  {fmt(s0o)}", flush=True)
    print(f"  OPT cd10 w0 ext1.5  {fmt(s10)}", flush=True)
    en, eg = PIN_OPT10
    pin10 = (s10["n"] == en and abs(s10["net"] - eg) <= 0.15)
    print(f"  PIN OPT-cd10 w0 {en}t {eg:+.1f}  {'OK' if pin10 else 'MISMATCH'}", flush=True)

    print("\n  per-year NET:", flush=True)
    for label, tx in (("cd0", tr0), ("cd10", tr10)):
        py = year_split(tx)
        row = " ".join(f"{y}:{full_stats(py[y], g)['net']:+.1f}" for y in sorted(py))
        print(f"    {label:5} {row}", flush=True)

    lags0 = post_loss_latency(tr0)
    lags10 = post_loss_latency(tr10)
    print("\n  post-loss re-entry lag (15m bars from loss exit -> next entry):", flush=True)
    for label, lags in (("cd0", lags0), ("cd10", lags10)):
        if not lags:
            print(f"    {label}: (no pairs)", flush=True)
            continue
        c = Counter(lags)
        med = sorted(lags)[len(lags) // 2]
        same_or_next = sum(1 for b in lags if b <= 1)
        print(f"    {label}: n_pairs={len(lags)} median={med} "
              f"mean={sum(lags)/len(lags):.1f} "
              f"same/next bar(<=1)={same_or_next} "
              f"({100.0*same_or_next/len(lags):.0f}%)", flush=True)
        top = sorted(c.items())[:8]
        print(f"           dist: {top}", flush=True)

    print(f"\n  max consecutive losing trades: cd0={max_loss_streak(tr0)}  "
          f"cd10={max_loss_streak(tr10)}  (engine halt still at max_consecutive_losses=3)",
          flush=True)

    # ---------- (ii) concurrency-cap design — document only ----------
    print("\n" + "-" * 100, flush=True)
    print("  (ii) CONCURRENCY-CAP DESIGN — already validated (document only)", flush=True)
    print("-" * 100, flush=True)
    ivs = sorted((int(t["entry_ts"]), int(t["exit_ts"])) for t in tr0 if t.get("exit_ts"))
    events = []
    for a, b in ivs:
        events.append((a, 1))
        events.append((b, -1))
    events.sort()
    cur = mx = 0
    for _, d in events:
        cur += d
        mx = max(mx, cur)
    print(f"  OPT cd0 max concurrent positions observed: {mx}", flush=True)
    print("  Path-true exp_max_concurrent: cap=5 FREE on champion/king multi "
          "(dIS +1.1 / dOOS 0.0); cap=4 near-free; cap=2/3 cost real R; single no-op.",
          flush=True)
    print("  Offline: their-OPTIMAL+cap3 = +326.8 NET / DD 21.8 (pure improvement "
          "vs uncapped +322.5 / DD 23.3).", flush=True)
    print("  RECOMMEND: live multi uses exp_max_concurrent=5 (risk cap, zero edge cost).",
          flush=True)

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()

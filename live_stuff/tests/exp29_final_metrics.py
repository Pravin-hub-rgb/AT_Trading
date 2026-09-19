"""Exp 29 — FINAL COMPARISON: all viable configs (both lanes) at production params.

Fine fills, full metric set. Costs distributed uniformly per trade (c2/n) so
NET-based metrics (per-trade, per-year, DD, H1/H2) stay consistent.
Writes live_stuff/docs/'all combined experiment trade metric.md'.
"""
import sys, time, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, BASE, \
    load_candles, _compute_swings, SWING, MB15, INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE)
BP["chop_thresh"] = 58.0  # PRODUCTION
B3 = dict(b3_k=8, b3_mode="close")
MB10 = 10
_g = _gvp(INSTRUMENT)
FEE = (_g["fee_pct"], _g["entry_slip_pct"], _g["exit_slip_pct"])

CONFIGS = [
    ("v18 anchor (production)", {}, {}, "sw1h"),
    ("B3 k8-close", B3, {}, "sw1h"),
    ("B3+halt6 combo", B3, dict(max_consecutive_losses=6), "sw1h"),
    ("multi-LTF alone", dict(exp_mltf=True), {}, "sw1h"),
    ("multi-LTF+persist5", dict(exp_mltf=True, exp_persist=5), {}, "sw1h"),
    ("mltf+mb1h10+chop55 (S9)", dict(exp_mltf=True), dict(chop_thresh=55.0), "sw1h10"),
    ("their-OPTIMAL (mltf+persist2+cd0+chop55+mb1h10)",
     dict(exp_mltf=True, exp_persist=2),
     dict(chop_thresh=55.0, cooldown_bars=0), "sw1h10"),
    ("OPTIMAL+halt6 (S19)", dict(exp_mltf=True, exp_persist=2),
     dict(chop_thresh=55.0, cooldown_bars=0, max_consecutive_losses=6), "sw1h10"),
    ("B3-OPT cd0 (no mltf)", {**B3, "exp_persist": 2},
     dict(chop_thresh=55.0, cooldown_bars=0), "sw1h10"),
    ("B3-OPT cd10 (prod cooldown)", {**B3, "exp_persist": 2},
     dict(chop_thresh=55.0), "sw1h10"),
    ("B3-OPT+halt6 cd10", {**B3, "exp_persist": 2},
     dict(chop_thresh=55.0, max_consecutive_losses=6), "sw1h10"),
]


def metrics(tr, c2):
    n = len(tr)
    rs_g = [float(t["r_multiple"]) for t in tr]
    cpt = c2 / n if n else 0.0
    rs = [r - cpt for r in rs_g]  # net per trade
    gross = sum(rs_g)
    net = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 0.0
    peak = cum = dd = 0.0
    pk_i = tr_i = 0
    pk_ts = tr_ts = 0
    b_pk_i = b_pk_ts = 0
    mc = cur = 0
    for i, r in enumerate(rs):
        cum += r
        if cum > peak:
            peak, pk_i, pk_ts = cum, i, int(tr[i].get("exit_ts") or 0)
        d = peak - cum
        if d > dd:
            dd, tr_i, tr_ts = d, i, int(tr[i].get("exit_ts") or 0)
            b_pk_i, b_pk_ts = pk_i, pk_ts
        if r <= 0:
            cur += 1
            mc = max(mc, cur)
        else:
            cur = 0
    py = defaultdict(float)
    for t, r in zip(tr, rs):
        d = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        py[d] += r
    hold = sum(int(t.get("bars_held") or 0) for t in tr) / n if n else 0.0
    span_days = (int(tr[-1].get("exit_ts") or 0) - int(tr[0].get("entry_ts") or 0)) / 86400.0
    return dict(n=n, gross=gross, net=net, npt=net / n if n else 0,
                gpt=gross / n if n else 0,
                wr=100.0 * len(wins) / n if n else 0,
                aw=aw, al=al, payo=aw / abs(al) if al else 0, pf=pf,
                dd=dd, ddt=tr_i - b_pk_i, ddd=(tr_ts - b_pk_ts) / 86400.0,
                mc=mc, hold_h=hold * 0.25, tpy=n / (span_days / 365.0) if span_days else 0,
                h1=py.get("2023", 0) + py.get("2024", 0),
                h2=py.get("2025", 0) + py.get("2026", 0),
                py={k: round(v, 1) for k, v in sorted(py.items())})


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    chains = {"sw1h": _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
              "sw1h10": _compute_swings(f1h, "continuous", min_bars=MB10)}
    sim = build_module()
    print("chains ready (%0.0fs); loading fine..." % (time.time() - t0))
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)

    # identity gate
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(
        c1h, chains["sw1h"], c15, sw15, fine_ltf=[], **BP)
    s_ship = stats(r_ship["ltf_trades"])
    assert s_ship["n"] == 351, "ANCHOR MISMATCH"
    r0 = sim(c1h, chains["sw1h"], c15, sw15, fine_ltf=[], **BP)
    s0 = stats(r0["ltf_trades"])
    assert s0["n"] == 351 and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (351t exact)\n")

    results = []
    for tag, hflags, pover, chain in CONFIGS:
        r = sim(c1h, chains[chain], c15, sw15, fine_ltf=fine,
                **{**BP, **pover, **hflags})
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        c2, _ = _trade_costs(tr, FEE[0], 0.0, FEE[1], FEE[2])
        m = metrics(tr, c2)
        m["tag"] = tag
        results.append(m)
        print("  %-45s %4dt NET %+8.1f  npt %+.3f  WR %4.1f%%  PF %4.2f  DD %5.1f"
              % (tag, m["n"], m["net"], m["npt"], m["wr"], m["pf"], m["dd"]))

    (ROOT / "live_stuff/tests/_exp29_results.json").write_text(
        json.dumps(results, indent=1))
    print("\n(exp29 done %.0fs — results saved)" % (time.time() - t0))


if __name__ == "__main__":
    main()

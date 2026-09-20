"""Exp 35 — POST-FIX B3 RE-SWEEP (fine fills, funding-inclusive NET).

The B3 fill bug (entry at signal-bar close instead of trigger-bar close) is
fixed in the harness. Re-measure the whole B3 family honestly:
  k{8,4} x halt{6,3} x lb{50,14} x persist{2,0}  (chop55, mb1h10, cd10)
Plus: B3-OPT with cd=0, B3+mltf re-check, and references (anchor,
their-OPTIMAL) measured in the same run. Full metrics for every config.
"""
import sys, time, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, BASE, \
    load_candles, _compute_swings, SWING, MB15, INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE)
BP["chop_thresh"] = 58.0
_g = _gvp(INSTRUMENT)


def funding_of(tr):
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"])
        rk = abs(e - sl)
        if rk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return f


def full_metrics(tr):
    n = len(tr)
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    fr = funding_of(tr)
    gross = sum(rs)
    net = gross - c2 - fr
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 0.0
    peak = cum = dd = 0.0
    pk_i = pk_ts = tr_i = tr_ts = b_pk_i = b_pk_ts = 0
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
        py[(t.get("exit_date") or t.get("entry_date") or "")[:4]] += r
    hold = sum(int(t.get("bars_held") or 0) for t in tr) / n if n else 0.0
    span = (int(tr[-1].get("exit_ts") or 0) - int(tr[0].get("entry_ts") or 0)) / 86400.0
    return dict(n=n, gross=gross, fees=c2, fund=fr, net=net,
                npt=net / n if n else 0,
                wr=100.0 * len(wins) / n if n else 0,
                aw=aw, al=al, payo=aw / abs(al) if al else 0, pf=pf,
                dd=dd, ddt=tr_i - b_pk_i, ddd=(tr_ts - b_pk_ts) / 86400.0,
                mc=mc, hold_h=hold * 0.25,
                tpy=n / (span / 365.0) if span else 0,
                h1=py.get("2023", 0) + py.get("2024", 0),
                h2=py.get("2025", 0) + py.get("2026", 0),
                py={k: round(v, 1) for k, v in sorted(py.items())})


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
    sw1h20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sim = build_module()
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)

    # identity gate (shipped, production params, coarse, mb20 chain)
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h20, c15, sw15,
                                                      fine_ltf=[], **BP)
    ss = [(t["entry_ts"], t["r_multiple"]) for t in r_ship["ltf_trades"]]
    assert len(ss) == 351, "ANCHOR MISMATCH"
    r0 = sim(c1h, sw1h20, c15, sw15, fine_ltf=[], **BP)
    assert [(t["entry_ts"], t["r_multiple"]) for t in r0["ltf_trades"]] == ss, "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (351t exact)\n", flush=True)

    out = []

    def run(tag, hflags, pover=None, mltf=False):
        kw = {**BP, **(pover or {}), **hflags}
        if mltf:
            kw["exp_mltf"] = True
        r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw)
        tr = r["ltf_trades"]
        m = full_metrics(tr)
        m["tag"] = tag
        out.append(m)
        print("  %-30s %4dt NET %+8.1f  npt %+.3f  WR %4.1f%%  PF %4.2f  DD %5.1f (%dt/%.0fd)  H1 %+7.1f H2 %+7.1f"
              % (tag, m["n"], m["net"], m["npt"], m["wr"], m["pf"], m["dd"],
                 m["ddt"], m["ddd"], m["h1"], m["h2"]), flush=True)

    run("v18 anchor", {})
    run("their-OPTIMAL (no B3)",
        dict(exp_mltf=True, exp_persist=2),
        dict(chop_thresh=55.0, cooldown_bars=0))

    print("", flush=True)
    for k in (8, 4):
        for halt in (6, 3):
            for lb in (50, 0):
                for pers in (2, 0):
                    h = dict(b3_k=k, b3_mode="close",
                             max_consecutive_losses=halt)
                    if pers:
                        h["exp_persist"] = pers
                    if lb:
                        h["exp31_lb"] = lb
                    run("B3 k%d h%d lb%d p%d" % (k, halt, lb or 14, pers), h)

    print("", flush=True)
    run("B3-OPT k8 h6 lb50 p2 cd0", dict(b3_k=8, b3_mode="close",
        exp_persist=2, max_consecutive_losses=6, exp31_lb=50),
        dict(cooldown_bars=0))
    run("B3-OPT k8 h3 lb50 p2 cd0", dict(b3_k=8, b3_mode="close",
        exp_persist=2, max_consecutive_losses=3, exp31_lb=50),
        dict(cooldown_bars=0))
    run("B3 k8 h6 lb50 p2 +mltf", dict(b3_k=8, b3_mode="close",
        exp_persist=2, max_consecutive_losses=6, exp31_lb=50), None, True)

    out.sort(key=lambda m: -m["net"])
    (ROOT / "live_stuff/tests/_exp35_results.json").write_text(json.dumps(out, indent=1))
    print("\nTOP 8 by NET (post-fix, funding-inclusive):", flush=True)
    for m in out[:8]:
        print("  %-30s %4dt NET %+8.1f  npt %+.3f  WR %4.1f%%  DD %5.1f  per-year %s"
              % (m["tag"], m["n"], m["net"], m["npt"], m["wr"], m["dd"], m["py"]))
    print("\n(exp35 done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()

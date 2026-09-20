"""Exp 28 fine — Q2/Q3: cd0-within-stack isolation + coarse->fine reconciliation.

Q2 : OPTIMAL with cd=10 (S10 config) vs cd=0 — isolates cd0's in-stack value.
Q3 : trade-level coarse->fine reconciliation for OPTIMAL and S15 — where do
     the coarse R go? matched per-trade drift vs vanished/extra trades.
Also fine NET for Q1 config (B3+params without mltf).
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
BP["chop_thresh"] = 58.0
B3 = dict(b3_k=8, b3_mode="close")
OPT_P = dict(chop_thresh=55.0, cooldown_bars=0)
OPT_H = dict(exp_mltf=True, exp_persist=2)
S15_H = {**B3, **OPT_H}
_g = _gvp(INSTRUMENT)
FEE = ( _g["fee_pct"], _g["entry_slip_pct"], _g["exit_slip_pct"] )


def net_of(tr):
    c2, _ = _trade_costs(tr, FEE[0], 0.0, FEE[1], FEE[2])
    return sum(float(t["r_multiple"]) for t in tr) - c2


def reconcile(tag, tr_c, tr_f):
    key = lambda t: (int(t["entry_ts"]), t["dir"])
    fc = {key(t): t for t in tr_c}
    ff = {key(t): t for t in tr_f}
    matched = set(fc) & set(ff)
    drift = sum(float(ff[k]["r_multiple"]) - float(fc[k]["r_multiple"]) for k in matched)
    vanish = sum(float(fc[k]["r_multiple"]) for k in set(fc) - set(ff))
    added = sum(float(ff[k]["r_multiple"]) for k in set(ff) - set(fc))
    out_c = defaultdict(int)
    for k in set(fc) - set(ff):
        out_c[fc[k]["outcome"]] += 1
    print("  %-9s coarse %3dt %+8.1f | fine %3dt %+8.1f" %
          (tag, len(tr_c), sum(float(t["r_multiple"]) for t in tr_c),
           len(tr_f), sum(float(t["r_multiple"]) for t in tr_f)))
    print("            matched %3d: R drift %+7.1f | vanished %+7.1f (%s) | added %+7.1f"
          % (len(matched), drift, vanish, dict(out_c), added))


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
    sim = build_module()
    print("loading fine 1m...")
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)

    def run(hflags, pover, fl):
        r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fl, **{**BP, **pover, **hflags})
        return r["ltf_trades"] if isinstance(r, dict) else r

    print("=== Q2: cd0 inside OPTIMAL stack — OPTIMAL vs cd=10 variant (fine NET) ===")
    for tag, pover in [("OPTIMAL cd0", OPT_P), ("OPTIMAL cd10", {**OPT_P, "cooldown_bars": 10})]:
        tr = run(OPT_H, pover, fine)
        s = stats(tr)
        print("  %-13s %4dt NET %+8.1f  WR %4.1f%%  DD %5.1f  H1 %+7.1f H2 %+7.1f"
              % (tag, s["n"], net_of(tr), s["wr"], s["dd"], s["h1"], s["h2"]))

    print("\n=== Q1 fine: B3+params WITHOUT mltf (NET) ===")
    tr = run({**B3, "exp_persist": 2}, OPT_P, fine)
    s = stats(tr)
    print("  Q1-no-mltf %4dt NET %+8.1f  WR %4.1f%%  DD %5.1f" % (s["n"], net_of(tr), s["wr"], s["dd"]))

    print("\n=== Q3: coarse->fine trade reconciliation (which trades eat the drop) ===")
    for tag, hflags, pover in [("OPTIMAL", OPT_H, OPT_P), ("S15", S15_H, OPT_P)]:
        reconcile(tag, run(hflags, pover, []), run(hflags, pover, fine))
    print("\n(exp28 fine done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()

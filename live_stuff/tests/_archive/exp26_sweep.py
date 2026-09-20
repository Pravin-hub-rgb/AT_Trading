"""Exp 26 — GRAND SWEEP: their levers x our levers, all at PRODUCTION params.

Base: v18 351t / +211.7 coarse (chop=58, btc_routes 914-941 params).
Levers: multi-LTF (mltf), cooldown (cd), persist, mb1h (10/20), chop (55/58),
halt (3/6), B3 k8-close. Coarse fills; fine NET for survivors (separate run).
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, show, BASE, \
    load_candles, _compute_swings, SWING, MB15
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE)
BP["chop_thresh"] = 58.0  # PRODUCTION

B3 = dict(b3_k=8, b3_mode="close")

RUNS = [
    ("S0 anchor", {}, {}, sw := "20"),
    ("S1 mltf", dict(exp_mltf=True), {}, sw),
    ("S2 mltf+cd0", dict(exp_mltf=True), dict(cooldown_bars=0), sw),
    ("S3 mltf+cd5", dict(exp_mltf=True), dict(cooldown_bars=5), sw),
    ("S4 mltf+cd15", dict(exp_mltf=True), dict(cooldown_bars=15), sw),
    ("S5 mltf+persist2", dict(exp_mltf=True, exp_persist=2), {}, sw),
    ("S6 mltf+persist5", dict(exp_mltf=True, exp_persist=5), {}, sw),
    ("S7 mltf+cd0+persist5", dict(exp_mltf=True, exp_persist=5),
     dict(cooldown_bars=0), sw),
    ("S8 mltf+mb1h10", dict(exp_mltf=True), {}, "10"),
    ("S9 mltf+mb1h10+chop55", dict(exp_mltf=True), dict(chop_thresh=55.0), "10"),
    ("S10 mltf+persist2+mb1h10+chop55", dict(exp_mltf=True, exp_persist=2),
     dict(chop_thresh=55.0), "10"),
    ("S11 their-OPTIMAL", dict(exp_mltf=True, exp_persist=2),
     dict(chop_thresh=55.0, cooldown_bars=0), "10"),
    ("S12 B3 k8 alone", B3, {}, sw),
    ("S13 B3+mltf", {**B3, "exp_mltf": True}, {}, sw),
    ("S14 B3+mltf+cd0", {**B3, "exp_mltf": True}, dict(cooldown_bars=0), sw),
    ("S15 B3+their-OPTIMAL", {**B3, "exp_mltf": True, "exp_persist": 2},
     dict(chop_thresh=55.0, cooldown_bars=0), "10"),
    ("S16 B3+mltf+persist5", {**B3, "exp_mltf": True, "exp_persist": 5}, {}, sw),
    ("S17 B3+halt6+mltf", {**B3, "exp_mltf": True},
     dict(max_consecutive_losses=6), sw),
    ("S18 B3+halt6+mltf+cd0", {**B3, "exp_mltf": True},
     dict(max_consecutive_losses=6, cooldown_bars=0), sw),
    ("S19 their-OPTIMAL+halt6", dict(exp_mltf=True, exp_persist=2),
     dict(chop_thresh=55.0, cooldown_bars=0, max_consecutive_losses=6), "10"),
]


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    chains = {m: _compute_swings(f1h, "continuous", min_bars=m) for m in (10, SWING["min_bars_1h"])}
    sim = build_module()
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, chains[20], c15, sw15,
                                                      fine_ltf=[], **BP)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    s_ship = stats(t_ship)
    assert s_ship["n"] == 351, "ANCHOR MISMATCH %dt" % s_ship["n"]
    print("ANCHOR OK: 351t / %+.2f coarse\n" % s_ship["gross"])
    out = []
    for tag, hflags, pover, m1h in RUNS:
        s1h = chains[int(m1h)]
        r = sim(c1h, s1h, c15, sw15, fine_ltf=[], **{**BP, **pover, **hflags})
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr)
        s["tag"] = tag
        out.append(s)
        show(tag, s)
    print("\n=== TOP 8 BY GROSS ===")
    for s in sorted(out, key=lambda z: -z["gross"])[:8]:
        show(s["tag"], s)


if __name__ == "__main__":
    main()

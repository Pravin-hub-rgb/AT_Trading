"""Exp 26b — COMPREHENSIVE stats table for the grand sweep (all metrics)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, BASE, \
    load_candles, _compute_swings, SWING, MB15
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE)
BP["chop_thresh"] = 58.0

B3 = dict(b3_k=8, b3_mode="close")
RUNS = [
    ("S0 anchor", {}, {}, "20"),
    ("S1 mltf", dict(exp_mltf=True), {}, "20"),
    ("S2 mltf+cd0", dict(exp_mltf=True), dict(cooldown_bars=0), "20"),
    ("S3 mltf+cd5", dict(exp_mltf=True), dict(cooldown_bars=5), "20"),
    ("S4 mltf+cd15", dict(exp_mltf=True), dict(cooldown_bars=15), "20"),
    ("S5 mltf+persist2", dict(exp_mltf=True, exp_persist=2), {}, "20"),
    ("S6 mltf+persist5", dict(exp_mltf=True, exp_persist=5), {}, "20"),
    ("S7 mltf+cd0+persist5", dict(exp_mltf=True, exp_persist=5),
     dict(cooldown_bars=0), "20"),
    ("S8 mltf+mb1h10", dict(exp_mltf=True), {}, "10"),
    ("S9 mltf+mb1h10+chop55", dict(exp_mltf=True), dict(chop_thresh=55.0), "10"),
    ("S10 mltf+persist2+mb1h10+chop55", dict(exp_mltf=True, exp_persist=2),
     dict(chop_thresh=55.0), "10"),
    ("S11 their-OPTIMAL", dict(exp_mltf=True, exp_persist=2),
     dict(chop_thresh=55.0, cooldown_bars=0), "10"),
    ("S12 B3 k8 alone", B3, {}, "20"),
    ("S13 B3+mltf", {**B3, "exp_mltf": True}, {}, "20"),
    ("S14 B3+mltf+cd0", {**B3, "exp_mltf": True}, dict(cooldown_bars=0), "20"),
    ("S15 B3+their-OPTIMAL", {**B3, "exp_mltf": True, "exp_persist": 2},
     dict(chop_thresh=55.0, cooldown_bars=0), "10"),
    ("S16 B3+mltf+persist5", {**B3, "exp_mltf": True, "exp_persist": 5}, {}, "20"),
    ("S17 B3+halt6+mltf", {**B3, "exp_mltf": True},
     dict(max_consecutive_losses=6), "20"),
    ("S18 B3+halt6+mltf+cd0", {**B3, "exp_mltf": True},
     dict(max_consecutive_losses=6, cooldown_bars=0), "20"),
    ("S19 their-OPTIMAL+halt6", dict(exp_mltf=True, exp_persist=2),
     dict(chop_thresh=55.0, cooldown_bars=0, max_consecutive_losses=6), "10"),
]
NET_KNOWN = {
    "S0 anchor": 163.7, "S1 mltf": 217.0, "S12 B3 k8 alone": 258.3,
    "S6 mltf+persist5": 307.2, "S9 mltf+mb1h10+chop55": 335.6,
    "S11 their-OPTIMAL": 348.0, "S15 B3+their-OPTIMAL": 300.4,
}


def fullstats(tr):
    rs = [float(x["r_multiple"]) for x in tr]
    n = len(rs); tot = sum(rs)
    wins = [x for x in rs if x > 0]; losses = [x for x in rs if x < 0]
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    peak = cum = dd = 0.0
    wcur = lcur = wmx = lmx = 0
    months = set()
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x > 0: wcur += 1; lcur = 0; wmx = max(wmx, wcur)
        elif x < 0: lcur += 1; wcur = 0; lmx = max(lmx, lcur)
    for t in tr:
        months.add((t.get("entry_date") or "")[:7])
    return dict(n=n, tot=tot,
                wr=100.0 * len(wins) / n if n else 0.0, pf=pf,
                avgw=(sum(wins) / len(wins)) if wins else 0.0,
                avgl=(sum(losses) / len(losses)) if losses else 0.0,
                rpt=tot / n if n else 0.0, dd=dd, wmx=wmx, lmx=lmx,
                tpm=n / max(len(months), 1))


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    chains = {m: _compute_swings(f1h, "continuous", min_bars=m)
              for m in (10, SWING["min_bars_1h"])}
    sim = build_module()
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(
        c1h, chains[SWING["min_bars_1h"]], c15, sw15, fine_ltf=[], **BP)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    assert len(t_ship) == 351, "ANCHOR MISMATCH"

    print("#  | Config | Tr | GrossR | WR | PF | AvgW | AvgL | R/tr | MaxDD | WStr | LStr | Tr/mo | NET(fine)")
    rows = []
    for tag, hflags, pover, m1h in RUNS:
        r = sim(c1h, chains[int(m1h)], c15, sw15, fine_ltf=[],
                **{**BP, **pover, **hflags})
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = fullstats(tr)
        s["tag"] = tag; s["net"] = NET_KNOWN.get(tag)
        rows.append(s)
        print("%-31s %4dt %+8.1fR  WR %4.1f%%  PF %4.2f  avgW %+5.2f  avgL %+5.2f  R/t %5.3f  DD %5.1f  WSt %2d  LSt %2d  %5.1f/mo  NET %s"
              % (tag, s["n"], s["tot"], s["wr"], s["pf"], s["avgw"], s["avgl"],
                 s["rpt"], s["dd"], s["wmx"], s["lmx"], s["tpm"],
                 ("+%0.1f" % s["net"]) if s["net"] else "-"))


if __name__ == "__main__":
    main()

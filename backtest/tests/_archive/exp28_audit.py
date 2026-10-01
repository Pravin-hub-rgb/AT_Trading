"""Exp 28 — AUDIT RESPONSE (other bot's 10-question audit), coarse part.

Q1  : B3+chop55+mb1h10+persist2+cd0 WITHOUT mltf (their exact ask)
Q5  : halt 4/5/6 on OPTIMAL stack and on S15 (B3+OPTIMAL)
Q6  : persist5 vs persist2 head-to-head inside OPTIMAL stack
Q7  : Exp 27 opposite-mark stop accelerator, 3 arms, on anchor and B3 base
Q4  : multi-cut temporal stability (50/66/75%) anchor vs B3 vs OPTIMAL vs S15
Q9  : B3 2026 monthly breakdown
Q10 : S15 max-DD duration (trades + days)
Production params throughout (chop=58 base). Identity gate enforced.
"""
import sys, time, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, show, BASE, \
    load_candles, _compute_swings, SWING, MB15
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE)
BP["chop_thresh"] = 58.0
B3 = dict(b3_k=8, b3_mode="close")
OPT_P = dict(chop_thresh=55.0, cooldown_bars=0)
OPT_H = dict(exp_mltf=True, exp_persist=2)
S15_H = {**B3, **OPT_H}
MB10 = 10


def run(sim, c1h, s1h, c15, sw15, hflags, pover):
    r = sim(c1h, s1h, c15, sw15, fine_ltf=[], **{**BP, **pover, **hflags})
    return r["ltf_trades"] if isinstance(r, dict) else r


def monthly(tr, ym):
    d = defaultdict(lambda: [0, 0.0])
    for t in tr:
        k = (t.get("exit_date") or t.get("entry_date") or "")[:7]
        if k.startswith(ym):
            d[k][0] += 1
            d[k][1] += float(t["r_multiple"])
    return {k: (v[0], round(v[1], 1)) for k, v in sorted(d.items())}


def dd_duration(tr):
    """Max DD window: peak-to-trough in trades and days (equity over exit order)."""
    tr = sorted(tr, key=lambda t: int(t.get("exit_ts") or 0))
    peak, best = 0.0, 0.0
    pk_i, pk_ts, tr_i, tr_ts = 0, 0, 0, 0
    b_pk_i, b_pk_ts = 0, 0
    cum = 0.0
    for i, t in enumerate(tr):
        cum += float(t["r_multiple"])
        if cum > peak:
            peak, pk_i, pk_ts = cum, i, int(t["exit_ts"])
        dd = peak - cum
        if dd > best:
            best, tr_i, tr_ts = dd, i, int(t["exit_ts"])
            b_pk_i, b_pk_ts = pk_i, pk_ts
    return best, tr_i - b_pk_i, (tr_ts - b_pk_ts) / 86400.0


def stability(tr, t0, t1):
    """R within [start, cut) segments at 50/66/75% of the time span."""
    out = {}
    for f in (0.50, 0.66, 0.75):
        cut = t0 + (t1 - t0) * f
        a = sum(float(t["r_multiple"]) for t in tr if int(t["entry_ts"]) < cut)
        b = sum(float(t["r_multiple"]) for t in tr if int(t["entry_ts"]) >= cut)
        na = len([t for t in tr if int(t["entry_ts"]) < cut])
        out[f] = (round(a, 1), na, round(b, 1), len(tr) - na)
    return out


def main():
    t0w = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=MB10)
    sim = build_module()
    print("chains ready (%0.0fs)" % (time.time() - t0w))

    # ---------- IDENTITY GATE ----------
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **BP)
    s_ship = stats(r_ship["ltf_trades"])
    assert s_ship["n"] == 351 and abs(s_ship["gross"] - 211.7) < 0.5, "ANCHOR MISMATCH"
    r0 = sim(c1h, sw1h, c15, sw15, fine_ltf=[], **BP)
    s0 = stats(r0["ltf_trades"])
    assert s0["n"] == 351 and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (351t exact)\n")

    T0, T1 = int(c15[0]["ts"]), int(c15[-1]["ts"]) + 900
    keep = {}

    print("=== Q1: B3+chop55+mb1h10+persist2+cd0 WITHOUT mltf (vs S15 with mltf) ===")
    tr = run(sim, c1h, sw1h10, c15, sw15,
             {**B3, "exp_persist": 2}, {**OPT_P})
    show("Q1 B3+params NO mltf", s := stats(tr))
    keep["q1"] = {"n": s["n"], "gross": s["gross"], "ts": [t["entry_ts"] for t in tr],
                  "r": [t["r_multiple"] for t in tr]}
    tr = run(sim, c1h, sw1h10, c15, sw15, S15_H, OPT_P)
    show("   S15 B3+OPTIMAL (ref)", stats(tr))

    print("\n=== Q5: halt sweep on OPTIMAL and S15 ===")
    for h in (3, 4, 5, 6):
        tr = run(sim, c1h, sw1h10, c15, sw15, OPT_H,
                 {**OPT_P, "max_consecutive_losses": h})
        show("OPTIMAL halt=%d" % h, stats(tr))
    for h in (3, 4, 5, 6):
        tr = run(sim, c1h, sw1h10, c15, sw15, S15_H,
                 {**OPT_P, "max_consecutive_losses": h})
        show("S15 halt=%d" % h, stats(tr))

    print("\n=== Q6: persist2 vs persist5 inside OPTIMAL stack ===")
    tr = run(sim, c1h, sw1h10, c15, sw15, {**OPT_H, "exp_persist": 5}, OPT_P)
    show("OPTIMAL persist5", stats(tr))
    tr = run(sim, c1h, sw1h10, c15, sw15, OPT_H, OPT_P)
    show("OPTIMAL persist2", stats(tr))

    print("\n=== Q7 / EXP 27: opposite-mark stop accelerator (coarse) ===")
    for base_tag, hflags, pover, s_htf in [
            ("anchor", {}, {}, sw1h), ("B3", B3, {}, sw1h)]:
        tr = run(sim, c1h, s_htf, c15, sw15, hflags, pover)
        show("%s base" % base_tag, stats(tr))
        for mode in ("all", "loss", "fliploss"):
            tr = run(sim, c1h, s_htf, c15, sw15, {**hflags, "exp27_mode": mode}, pover)
            s = stats(tr)
            show("%s accel-%s" % (base_tag, mode), s)
            print("        outcomes: %s" % {k: len([x for x in tr if x["outcome"] == k])
                                            for k in ("sl", "trail", "accel27", "open")})

    print("\n=== Q4: multi-cut temporal stability (coarse R by entry-ts bucket) ===")
    stab = {}
    for tag, hflags, pover, s_htf in [
            ("anchor", {}, {}, sw1h), ("B3", B3, {}, sw1h),
            ("OPTIMAL", OPT_H, OPT_P, sw1h10), ("S15", S15_H, OPT_P, sw1h10)]:
        tr = run(sim, c1h, s_htf, c15, sw15, hflags, pover)
        stab[tag] = stability(tr, T0, T1)
        print("  %-8s %s" % (tag, {k: "seg1 %+.1f (%dt) | seg2 %+.1f (%dt)" % v
                                   for k, v in stab[tag].items()}))
    keep["stab"] = {k: {str(f): v for f, v in d.items()} for k, d in stab.items()}

    print("\n=== Q9: B3 2026 monthly breakdown (production params) ===")
    tr = run(sim, c1h, sw1h, c15, sw15, B3, {})
    for k, (n, r) in monthly(tr, "2026").items():
        print("  %s: %2dt  %+7.1fR" % (k, n, r))

    print("\n=== Q10: S15 max-DD duration ===")
    tr = run(sim, c1h, sw1h10, c15, sw15, S15_H, OPT_P)
    ddn, ddt, dddays = dd_duration(tr)
    print("  S15 max DD %.1fR over %d trades, %.1f days (peak->trough)" % (ddn, ddt, dddays))
    tr = run(sim, c1h, sw1h, c15, sw15, {}, {})
    ddn, ddt, dddays = dd_duration(tr)
    print("  anchor max DD %.1fR over %d trades, %.1f days (ref)" % (ddn, ddt, dddays))

    (ROOT / "backtest/tests/_exp28_coarse.json").write_text(json.dumps(keep))
    print("\n(exp28 audit coarse done %.0fs)" % (time.time() - t0w))


if __name__ == "__main__":
    main()

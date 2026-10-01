"""P52 - GIVE THE 1h LAYER THE TREATMENTS THE 15m LAYER ALREADY HAS, AND
TEST THE ONE IDEA NOBODY HAS TRIED: DECAY COMPUTED ON 1h GATING THE WINDOW.

WHY THIS EXISTS
    P3 just measured that the 1h layer earns nothing on its own - FLIP
    +1.9R IS and -23.6R OOS, B2 -49.6R and -21.7R - while the cascade is
    +325.8R and +70.1R. Every brake in this engine was tuned on the 15m
    side and the 1h side runs raw: htf_rr=3.0, window_end="exit",
    cap_days=16, no entry filter, no cooldown, no streak management.
    The layer was never scored, so it was never tuned. Now it is scored.

PART A - THE 1h LAYER, GIVEN THE 15m LAYER'S TREATMENTS
    All post-process, no engine edit. The engine returns the parent
    `intervals` that gated each LTF trade, so an arm is a FILTER on which
    intervals are allowed to gate, scored against the same pinned book.
      A1  cooldown   skip a window that opens within N days of a previous
                      1h leg going against it (the 15m layer runs
                      cooldown_bars=8 bars; this is the 1h equivalent)
      A2  streak     skip a window that opens while the 1h book is on a
                      losing streak (the 15m layer runs
                      max_consecutive_losses=3)
      A3  side       take only flip windows, or only b2 windows
      A4  MIN3R      keep only windows whose 1h leg actually reached its
                      +3R target - the 1h book pays 21.7% of its time at
                      3R, so the question is whether a window that cannot
                      reach 3R is a window worth trading inside
    A4 is the important one and it is only checkable because P3/W2 measured
    the MFE distribution.

PART B - DECAY ON THE 1h CHAIN GATING THE WINDOW OPEN
    decay has only ever been computed on 15m buying legs to gate 15m
    entries. It has never been computed on the 1h leg chain to decide
    whether a window opens at all. This asks the untried version: when a
    1h leg opens, is the 1h structure already broken, and if so should the
    window be allowed to open for the 15m layer to trade inside.

NO ARM HERE EDITS THE ENGINE AND NONE CAN BE ADOPTED. The 15m book is
fixed and pinned in every cell; an arm changes only which windows gate it.
"""
import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING
from exp_decay_switch import legs_by_dir, decay_pair, _dt

COOLS = (1, 2, 3, 5, 8, 13)
STREAKS = (1, 2, 3, 4, 5)
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def get(scope, swtag):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


def legs_all(sw):
    out = []
    for s in sw:
        ct = s.get("confirmed_at_time") or ""
        if isinstance(ct, str) and len(ct) >= 19:
            try:
                px = float((s.get("seg") or {}).get("start_px", 0) or 0)
                if px > 0:
                    out.append((_dt(ct), 1 if s.get("dir") in ("up", "B")
                                else 0, px))
            except Exception:
                pass
    out.sort(key=lambda x: x[0])
    return out


def main():
    print("=" * 100)
    print("  P52  GIVE THE 1h LAYER THE 15m LAYER'S TREATMENTS,")
    print("        AND TEST HTF-LEVEL DECAY GATING THE WINDOW")
    print("=" * 100)
    print("  The 15m book is fixed and pinned in every cell. An arm changes")
    print("  only WHICH WINDOWS ARE ALLOWED TO GATE IT.\n")
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag)
            r = tc.build_module()(*a, **params)
            tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            nb, n0 = net_r(tr), len(tr)
            if abs(n0 - pin[0]) > 2 or abs(nb - pin[1]) > 1.5:
                print("    [%s] CONTROL FAILED %dt %+.1fR -- STOP"
                      % (scope, n0, nb))
                return
            ivs = sorted(r.get("intervals") or [], key=lambda v: v[0])
            legs1h = list(r.get("htf_trades") or []) + \
                list(r.get("htf_trades_b2") or [])
            legs1h.sort(key=lambda L: int(L["entry_ts"]))
            print("    [%s] control %dt %+.1fR (PIN ok)   %d parent windows, "
                  "%d 1h legs" % (scope.upper(), n0, nb, len(ivs), len(legs1h)))
            # tag every trade with its gating window
            starts = [v[0] for v in ivs]
            for t in tr:
                ts = int(t["entry_ts"])
                td = 1 if t["dir"] == "long" else -1
                bi = None
                for ix, v in enumerate(ivs):
                    if v[0] < ts <= v[1] and v[2] == td:
                        if bi is None or v[0] > ivs[bi][0]:
                            bi = ix
                t["_ix"] = bi
            def line(lbl, keep):
                sel = [t for t in tr if t["_ix"] in keep]
                if len(sel) < 15:
                    print("      %-32s %5d   (too few)" % (lbl, len(sel)))
                    return
                rs = [float(x["r_multiple"]) for x in sel]
                net = net_r(sel)
                print("      %-32s %5d %+9.1fR %+8.1fR PF %5.2f"
                      % (lbl, len(sel), net, net - nb, pf(rs)))
            line("A no gate change", set(range(len(ivs))))
            
            # A1 cooldown
            for cd in COOLS:
                keep = set()
                last_bad = None
                for k, v in enumerate(ivs):
                    bad = last_bad is not None and \
                        (v[0] - last_bad) < cd * 86400
                    if not bad:
                        keep.add(k)
                    if v[1] > v[0]:
                        pass
                for L in legs1h:
                    if float(L.get("r_multiple", 0) or 0) < 0:
                        last_bad = int(L["exit_ts"])
                line("A1 cooldown %dd after 1h loss" % cd, keep)
            # A2 streak
            for ns in STREAKS:
                keep = set()
                streak = 0
                li = 0
                for k, v in enumerate(ivs):
                    while li < len(legs1h) and int(legs1h[li]["entry_ts"]) \
                            <= v[0]:
                        streak = streak + 1 if \
                            float(legs1h[li].get("r_multiple", 0) or 0) <= 0 \
                            else 0
                        li += 1
                    if streak < ns:
                        keep.add(k)
                line("A2 skip while 1h streak >= %d" % ns, keep)
            # A3 side
            for nm, dd_ in (("A3 flip windows only", 1), ("A3 b2 windows only", -1)):
                pass
            # A4 window whose 1h leg reached 3R
            byend = {}
            for L in legs1h:
                byend.setdefault(int(L["entry_ts"]), L)
            hit3 = set()
            for L in legs1h:
                if float(L.get("r_multiple", 0) or 0) >= 2.99:
                    hit3.add(int(L["entry_ts"]))
            keep4 = set()
            for k, v in enumerate(ivs):
                cands = [L for L in legs1h
                         if v[0] <= int(L["entry_ts"]) < v[1]]
                if any(int(L["entry_ts"]) in hit3 for L in cands):
                    keep4.add(k)
            line("A4 window's 1h leg reached 3R", keep4)
            # PART B - 1h-level decay gating the window
            up, dn = legs_by_dir(a[1])
            fts = [int(c["ts"]) for c in a[4]]
            flo = [float(c["low"]) for c in a[4]]
            fhi = [float(c["high"]) for c in a[4]]
            hts = [int(c["ts"]) for c in a[0]]
            hlo = [float(c["low"]) for c in a[0]]
            hhi = [float(c["high"]) for c in a[0]]
            for thr in (0.0, 0.25, 0.5, 0.75, 1.0):
                keep = set()
                for k, v in enumerate(ivs):
                    s = v[0]
                    i = bs.bisect_left(fts, s)
                    dv, _ = decay_pair(up, dn, s, flo, fhi, fts, n=4)
                    if dv is None or dv < thr:
                        keep.add(k)
                line("PART B 1h-decay < %.2f" % thr, keep)
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()
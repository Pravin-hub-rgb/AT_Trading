"""P44 - P3-B, THE EARLY-READ TEST (run 2 - the first run was void).

VOID RUN, AND WHY IT IS RECORDED
    Run 1 computed the parent leg's excursion as
        (max_high - risk) / risk
    using `risk` where `parent_entry` belonged. Every bucket was therefore
    measured from a meaningless baseline and the whole run was discarded.
    The giveaway was the built-in causality probe: pushing the read +1h
    moved 0/499 buckets, which looked like "the read reads nothing" but was
    actually a broken expression. The probe is what caught it - it is kept
    in this file for that reason, and now a run whose probe moves nothing
    is treated as suspect rather than as a result.

THE MECHANISM, AND WHY IT IS NOT r_touch AGAIN
    r_touch CLOSED the window at the first 1.5R touch and the LTF lost 130R
    (closed 2026-09-08). This closes nothing. It only READS where the
    hypothetical parent leg stands at the instant a 15m entry fires, and
    either takes or skips. Windows end exactly as in the control.

    Parent leg = the v7 HTF trade: entry `parent_entry`, stop `parent_sl`,
    risk = |parent_entry - parent_sl|. Live R at time t is the best
    favourable excursion on fine 1m bars from parent_entry through t:
        long  leg: (max high  - parent_entry) / risk
        short leg: (parent_entry - min low)  / risk

    Buckets: DEAD <= -1R, PROVED >= +1.5R, NEUTRAL otherwise.

CAUSALITY
    Fine 1m bars with ts <= t only.

PRE-REGISTERED FALSIFIER (from OPEN_RESEARCH_QUEUE.md:227)
    "ye live-oracle arm, wahi arm jo sirf window-open information use karti
    hai, se better hona chahiye - dono eras me."
    Part 3 builds a window-OPEN-ONLY arm at matched coverage and that
    comparison is the verdict, not the oracle's own net.
"""
import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING

PROVED_R = 1.5
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


def parent_of(ivs, t, direction):
    best = None
    for iv in ivs:
        if iv[0] < t <= iv[1] and iv[2] == direction:
            if best is None or iv[0] > best[0]:
                best = iv
    return best


def leg_r_at(fts, flo, fhi, t, pstart, direction, pe, psl, advance=0):
    """Live R of the parent leg at or before t. advance = probe only."""
    risk = abs(float(pe) - float(psl))
    if risk <= 0:
        return 0.0
    entry = float(pe)
    t_eff = t + advance
    i = bs.bisect_left(fts, pstart)
    j = bs.bisect_right(fts, t_eff) - 1
    if j <= i:
        return 0.0
    if direction > 0:
        return (max(fhi[i:j + 1]) - entry) / risk
    return (entry - min(flo[i:j + 1])) / risk


def bucket(r):
    if r <= -1.0:
        return "DEAD"
    if r >= PROVED_R:
        return "PROVED"
    return "NEUTRAL"


def row(lbl, sel, nb):
    if len(sel) < 15:
        print("      %-40s %5d   (too few)" % (lbl, len(sel)))
        return None
    rs = [float(x["r_multiple"]) for x in sel]
    net = net_r(sel)
    hit = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
    print("      %-40s %5d %+9.1fR %+8.1fR %6.2f %7.1f%%"
          % (lbl, len(sel), net, net - nb, pf(rs), hit))
    return net - nb


def main():
    print("=" * 100)
    print("  P44  P3-B - CAN THE 1h LEG BE READ WHILE THE WINDOW IS OPEN?")
    print("        (run 2 - run 1 void, baseline used risk as entry price)")
    print("=" * 100)
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
            fts = [int(c["ts"]) for c in a[4]]
            flo = [float(c["low"]) for c in a[4]]
            fhi = [float(c["high"]) for c in a[4]]
            ivs = r.get("intervals") or []
            matched = 0
            for t in tr:
                tdir = 1 if t["dir"] == "long" else -1
                iv = parent_of(ivs, int(t["entry_ts"]), tdir)
                if iv is None:
                    t["_b"] = "NOIV"
                    continue
                matched += 1
                rr = leg_r_at(fts, flo, fhi, int(t["entry_ts"]),
                              iv[0], iv[2], iv[3], iv[4])
                t["_b"] = bucket(rr)
                t["_r"] = rr
                t["_risk"] = abs(float(iv[3]) - float(iv[4]))
            print("    [%s] control %dt %+.1fR (PIN ok)   %d/%d matched a "
                  "parent" % (scope.upper(), n0, nb, matched, n0))
            print("      BUCKET CENSUS")
            for bk in ("DEAD", "NEUTRAL", "PROVED", "NOIV"):
                sel = [t for t in tr if t["_b"] == bk]
                if not sel:
                    continue
                rs = [float(x["r_multiple"]) for x in sel]
                hit = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
                avgr = sum(t["_r"] for t in sel if "_r" in t) / len(sel)
                print("      %-40s %5d %+9.1fR  legR %6.2f  PF %5.2f %6.1f%%"
                      % (bk, len(sel), net_r(sel), avgr, pf(rs), hit))
            print("      LIVE-ORACLE ARMS")
            row("A no filter", tr, nb)
            row("skip DEAD", [t for t in tr if t["_b"] != "DEAD"], nb)
            row("only PROVED (prove-it-first)", [t for t in tr
                 if t["_b"] == "PROVED"], nb)
            row("only NEUTRAL", [t for t in tr if t["_b"] == "NEUTRAL"], nb)
            print("      WINDOW-OPEN-ONLY, coverage matched to skip-DEAD")
            n_tgt = len([t for t in tr if t["_b"] != "DEAD"])
            keyed = [t for t in tr if "_risk" in t]
            if 0 < n_tgt < len(keyed):
                row("open-only: tightest %d by magnitude" % n_tgt,
                    sorted(keyed, key=lambda t: -t["_risk"])[:n_tgt], nb)
                row("open-only: widest %d by magnitude" % n_tgt,
                    sorted(keyed, key=lambda t: t["_risk"])[:n_tgt], nb)
            print("      CAUSALITY PROBE  (advance the read +1h)")
            moved = 0
            tot = 0
            for t in tr:
                if t["_b"] == "NOIV":
                    continue
                tot += 1
                iv = parent_of(ivs, int(t["entry_ts"]),
                               1 if t["dir"] == "long" else -1)
                rr = leg_r_at(fts, flo, fhi, int(t["entry_ts"]), iv[0],
                              iv[2], iv[3], iv[4], advance=3600)
                if bucket(rr) != t["_b"]:
                    moved += 1
            print("      buckets that move when the read is pushed +1h: "
                  "%d/%d" % (moved, tot))
            print("      (run 1 gave 0/499 here - that was the bug, not a "
                  "null result)")
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()
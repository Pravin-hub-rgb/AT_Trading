"""The HTF window floor, and an autopsy of negative vs positive half-years.

THREE JOBS, because the owner's follow-up pointed at all three at once.

1. WINDOW FLOOR SWEEP. unified.py carried a hardcoded `s + 2700` gate - the one
   axis of the HTF window that was never a parameter, so it had never been swept.
   It answers a different question from exp_htf_fs_entry: that one changes WHEN the
   window opens (FS print vs break), this one changes how long you wait after it
   opened. Both were untested; only one had been.

2. FLOOR ANCHORED AT FS. The owner's original ask - "opening the HTF window on FS"
   - was tested as a change to the ENTRY TRIGGER. This tests it as a change to the
   GATE: the window becomes tradeable from the moment its own structure confirmed
   rather than 45 minutes after the break that opened it. Mode "fs". Mode "max"
   takes whichever is later and is therefore strictly tighter than either.

3. NEGATIVE vs POSITIVE AUTOPSY. The observation was that some books are negative
   in a half-year and others are not, and that this should be compared rather than
   asserted. So every book is profiled on its negative cells and its positive ones,
   across the same dimensions: R per trade, win rate, trade size, winner size,
   holding time, streak structure, and the share of the loss sitting in the worst
   few trades. If the negative halves are a regime with a name, that shows up here.
   If they are just cells where the book happened to land slightly red, that shows
   up here too - and that is the more useful answer.
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402


def cell(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def run(sim, E, book, swing, over):
    p = {**EXPERIMENTS[book]["params"], **over}
    per = defaultdict(list)
    dur = []
    for era in ("is", "oos"):
        d = E[era]
        o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                fine_ltf=d["fine"], **p)
        for t in sorted([t for t in o["ltf_trades"] if t.get("outcome") != "open"],
                        key=lambda t: int(t["entry_ts"])):
            r = net_r([t])
            per[cell(t["entry_ts"])].append(r)
            h = t.get("duration_h")
            if h is not None:
                dur.append((cell(t["entry_ts"]), float(h)))
    return per, dur


def profile(rs):
    n = len(rs)
    if not n:
        return None
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    streak = mx = 0
    for r in rs:
        streak = streak + 1 if r <= 0 else 0
        mx = max(mx, streak)
    sl = sorted(l)
    conc = 0.0
    run_s = 0.0
    k = 0
    for r in sl:
        run_s += r
        k += 1
        if abs(run_s) >= abs(sum(l)) * 0.5:
            break
    return dict(
        n=n, net=round(sum(rs), 2), r_per_trade=round(sum(rs) / n, 3),
        wr=round(100.0 * len(w) / n, 1),
        avg_win=round(sum(w) / len(w), 2) if w else 0.0,
        avg_loss=round(sum(l) / len(l), 2) if l else 0.0,
        payoff=round((sum(w) / len(w)) / abs(sum(l) / len(l)), 3) if w and l else None,
        max_win=round(max(rs), 2), max_loss=round(min(rs), 2),
        max_loss_streak=mx,
        worst_half_of_loss=round(100.0 * k / len(l), 1) if l else None,
    )


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}

    # ------------------------------------------------------------------ 1 & 2
    print("=" * 104)
    print("1+2. WINDOW FLOOR - the hardcoded 45-minute wait after a window opens")
    print("=" * 104)
    print("    default 2700 is the shipped gate. floor_mode 'fs' = tradeable from the")
    print("    window's own structure confirming. 'max' = later of the two.\n")

    ARMS = [
        ("champ_long", "fsent_champ_long", "sw10", {}),
        ("htf15", "fsent_champ_long_htf15", "htf15", {}),
        ("sig_multi", "fsent_sig_multi", "sw10", {}),
    ]
    floors = [0, 900, 1800, 2700, 3600, 5400, 7200, 14400]

    for label, book, swing, fixed in ARMS:
        print("  --- %s ---" % label)
        print("     %-22s %5s %9s %8s %8s  %s"
              % ("arm", "n", "net", "ddIS", "ddOOS", "neg"))
        rows = []
        for f in floors:
            over = {**fixed, "exp_window_floor_s": f}
            per, _ = run(sim, E, book, swing, over)
            n = sum(len(v) for v in per.values())
            net = sum(sum(v) for v in per.values())
            neg = sorted(c for c in per if sum(per[c]) < 0)
            cur = " <- shipped" if f == 2700 else ""
            print("     floor %-15d %5d %+9.1f %8s %8s  %d%s"
                  % (f, n, net, "", "", len(neg), cur))
            rows.append(dict(mode="fixed", floor=f, n=n, net=round(net, 2), neg=neg))
        for mode in ("fs", "max"):
            over = {**fixed, "exp_window_floor_mode": mode}
            per, _ = run(sim, E, book, swing, over)
            n = sum(len(v) for v in per.values())
            net = sum(sum(v) for v in per.values())
            neg = sorted(c for c in per if sum(per[c]) < 0)
            print("     mode %-16s %5d %+9.1f %8s %8s  %d"
                  % (mode, n, net, "", "", len(neg)))
            rows.append(dict(mode=mode, floor=None, n=n, net=round(net, 2), neg=neg))
        print()
        out.setdefault("floor", {})[label] = rows

    # -------------------------------------------------------------------- 3
    print("=" * 104)
    print("3. AUTOPSY - negative half-years vs positive ones, same books")
    print("=" * 104)
    print("    If the negative cells are a REGIME, the profile differs. If they are")
    print("    just cells where the book landed red, the profile is the same.\n")

    BOOKSET = [
        ("champ_long", "fsent_champ_long", "sw10", {}),
        ("mcloff", "fsent_champ_long_mcloff", "sw10", {}),
        ("mcloff_htf15", "fsent_champ_long_mcloff_htf15", "htf15", {}),
        ("sig_multi", "fsent_sig_multi", "sw10", {}),
        ("sig_full", "fsent_sig_full", "sw10", {}),
        ("mode_fd", "fsent_champ_long_mode_fd", "sw10", {}),
        ("flip_quality", "fsent_champ_long_mode_flip_quality", "sw10", {}),
        ("utcsat_short", "fsent_utcsat_short", "sw10", {}),
        ("utcsat_trailhalf", "fsent_utcsat_trailhalf", "sw10", {}),
        ("htfesmcl4", "fsent_champ_long_htfesmcl4", "sw10", {}),
    ]

    print("  %-16s %-9s %5s %8s %7s %7s %8s %7s %6s"
          % ("book", "cell", "n", "net", "R/tr", "WR", "payoff", "worst%", "streak"))
    print("  %-16s %-9s %5s %8s %7s %7s %8s %7s %6s"
          % ("", "(neg/pos)", "", "", "", "", "", "in loss", ""))
    autopsy = {}
    for label, book, swing, over in BOOKSET:
        per, dur = run(sim, E, book, swing, over)
        rec = {}
        for c in sorted(per):
            p = profile(per[c])
            if not p or abs(p["net"]) < 0.5:
                continue
            kind = "neg" if p["net"] < 0 else "pos"
            rec[c] = dict(p, kind=kind)
            print("  %-16s %-9s %5d %+8.2f %7.3f %6.1f%% %8s %6s%% %6d"
                  % (label, c, p["n"], p["net"], p["r_per_trade"], p["wr"],
                     ("%.2f" % p["payoff"]) if p["payoff"] else "-",
                     p["worst_half_of_loss"] if p["worst_half_of_loss"] is not None else "-",
                     p["max_loss_streak"]))
        negs = [c for c, v in rec.items() if v["kind"] == "neg"]
        poss = [c for c, v in rec.items() if v["kind"] == "pos"]
        if negs and poss:
            def avg(kind, k):
                vals = [rec[c][k] for c in rec if rec[c]["kind"] == kind and rec[c][k] is not None]
                return sum(vals) / len(vals) if vals else float("nan")
            print("      -> %-16s  neg vs pos:  R/trade %.3f vs %.3f | WR %.1f%% vs %.1f%% "
                  "| payoff %s vs %s" % (label, avg("neg", "r_per_trade"),
                                         avg("pos", "r_per_trade"),
                                         avg("neg", "wr"), avg("pos", "wr"),
                                         "%.2f" % avg("neg", "payoff"),
                                         "%.2f" % avg("pos", "payoff")))
        autopsy[label] = {c: v for c, v in rec.items()}
        print()

    out["autopsy"] = autopsy
    with open("_floor_and_autopsy.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("  wrote _floor_and_autopsy.json")


if __name__ == "__main__":
    main()
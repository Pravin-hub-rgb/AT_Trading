"""Negative-cell autopsy follow-up + brainstorm sweeps.

WHAT THE AUTOPSY FOUND
----------------------
champ_long's negative cell 2025-H1 is -0.69R over 60 trades. Mean trade -0.011R.
20 winners making +29.6R against 40 losers making -30.3R. The MAX LOSING STREAK
in that cell is 7.

THE BOOK SETS max_consecutive_losses = 3.

A 7-trade losing streak inside a book that declares a 3-trade limit is either the
limit is not being enforced, or it counts something other than consecutive
closed losses. That is the first thing to check, because a working
max_consecutive_losses is the cheapest possible fix to a negative cell: it does
not need a new signal, it just stops the book taking the 4th, 5th and 6th coin
flip while it is on a losing run.
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


def half(epoch):
    d = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def dd_of(rs):
    c = pk = m = 0.0
    for x in rs:
        c += x
        pk = max(pk, c)
        m = max(m, pk - c)
    return m


def stats(sim, d, book, swing, over):
    p = {**EXPERIMENTS[book]["params"], **over}
    o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
    tr = sorted([t for t in o["ltf_trades"] if t.get("outcome") != "open"],
                key=lambda t: int(t["entry_ts"]))
    rs = [net_r([t]) for t in tr]
    per = defaultdict(list)
    for t, r in zip(tr, rs):
        per[half(t["entry_ts"])].append(r)
    streak = mx = 0
    for r in rs:
        streak = streak + 1 if r <= 0 else 0
        mx = max(mx, streak)
    neg = sorted(c for c in per if sum(per[c]) < 0)
    return dict(n=len(rs), net=sum(rs), dd=dd_of(rs), neg=neg, max_streak=mx,
                per=per, worst=sorted(per, key=lambda c: sum(per[c]))[:3])


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}

    # ------------------------------------------------------------------
    # 1. IS max_consecutive_losses BEING ENFORCED?
    # ------------------------------------------------------------------
    print("=" * 100)
    print("1. IS max_consecutive_losses ENFORCED?  champ_long declares 3.")
    print("=" * 100)
    base = EXPERIMENTS["fsent_champ_long"]["params"]
    print("   registry value: max_consecutive_losses = %r"
          % base.get("max_consecutive_losses"))
    for label, over in (("as registered", {}),
                        ("limit forced to 1", {"max_consecutive_losses": 1}),
                        ("limit forced to 99 (off)", {"max_consecutive_losses": 99})):
        n = net = 0
        mx = 0
        per = defaultdict(list)
        for era in ("is", "oos"):
            s = stats(sim, E[era], "fsent_champ_long", "sw10", over)
            n += s["n"]
            net += s["net"]
            mx = max(mx, s["max_streak"])
            for c, v in s["per"].items():
                per[c] += v
        neg = sorted(c for c in per if sum(per[c]) < 0)
        print("   %-22s n=%4d  net=%+9.2fR  max_losing_streak=%2d  neg_cells=%d %s"
              % (label, n, net, mx, len(neg), neg))
        out["mcl_%s" % label] = dict(n=n, net=net, mx=mx, neg=neg)
    print("\n   If 'limit 1' and 'limit 99' print the SAME n, the limit is inert in")
    print("   this architecture and the 7-streak is expected, not a bug.")

    # ------------------------------------------------------------------
    # 2. BRAINSTORM SWEEP - the cheap structural knobs, scored on neg cells
    # ------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("2. BRAINSTORM SWEEP - knobs scored on the owner's rule (0 negative cells)")
    print("=" * 100)

    SWEEPS = [
        ("max_consecutive_losses", [0, 1, 2, 3, 4, 6], "fsent_champ_long", "sw10", {}),
        ("max_consecutive_losses", [0, 1, 2, 3, 4, 6], "fsent_champ_long", "sw10",
         {"exp_htf_fs_entry": "all"}),
        ("max_consecutive_losses", [0, 2, 3, 4], "fsent_sig_multi", "sw10", {}),
        ("cooldown_bars", [0, 4, 8, 16, 24], "fsent_champ_long", "sw10", {}),
        ("cooldown_bars", [0, 8, 16, 24], "fsent_champ_long", "sw10",
         {"exp_htf_fs_entry": "all"}),
        ("chop_thresh", [46.0, 50.0, 54.0, 58.0, 62.0, 70.0], "fsent_champ_long", "sw10", {}),
        ("chop_thresh", [46.0, 54.0, 62.0, 70.0], "fsent_champ_long", "sw10",
         {"exp_htf_fs_entry": "all"}),
        ("exp_persist", [0, 3, 5, 7, 9, 12], "fsent_champ_long", "sw10", {}),
        ("atr_high_thresh", [0.5, 0.58, 0.65, 0.72, 0.8], "fsent_champ_long", "sw10", {}),
        ("atr_low_thresh", [0.2, 0.28, 0.35, 0.42, 0.5], "fsent_champ_long", "sw10", {}),
        ("ext_stop_r", [0.0, 2.0, 3.0, 4.0, 5.0], "fsent_champ_long", "sw10", {}),
        ("exp_cap_days", [3, 7, 10, 14, 21], "fsent_champ_long", "sw10", {}),
    ]

    results = []
    for knob, vals, book, swing, fixed in SWEEPS:
        tag = "%s %s%s" % (knob, book.replace("fsent_", ""),
                           " +htf_fs" if fixed else "")
        print("\n   --- %s ---" % tag)
        print("      %-10s %5s %10s %7s %6s  %s"
              % (knob, "n", "net", "ddIS", "neg", "worst cells"))
        for v in vals:
            over = dict(fixed)
            over[knob] = v
            n = net = 0
            dd_is = 0.0
            per = defaultdict(list)
            for era in ("is", "oos"):
                s = stats(sim, E[era], book, swing, over)
                n += s["n"]
                net += s["net"]
                if era == "is":
                    dd_is = s["dd"]
                for c, lst in s["per"].items():
                    per[c] += lst
            neg = sorted(c for c in per if sum(per[c]) < 0)
            worst3 = sorted(per, key=lambda c: sum(per[c]))[:3]
            print("      %-10s %5d %+10.2f %7.2f %6d  %s"
                  % (v, n, net, dd_is, len(neg),
                     ", ".join("%s %+.1f" % (c, sum(per[c])) for c in worst3)))
            results.append(dict(knob=knob, value=v, book=book,
                                fixed=dict(fixed), n=n, net=net, dd_is=dd_is,
                                neg=len(neg), neg_cells=neg))
    out["sweeps"] = results

    print("\n" + "=" * 100)
    print("3. EVERY ZERO-NEGATIVE-CELL ARM FOUND, ranked by net")
    print("=" * 100)
    clean = [r for r in results if r["neg"] == 0]
    clean.sort(key=lambda r: -r["net"])
    if not clean:
        print("   none")
    for r in clean[:20]:
        print("   %+9.2fR  n=%4d  ddIS=%5.2f  %s=%s %s"
              % (r["net"], r["n"], r["dd_is"], r["knob"], r["value"],
                 ("+htf_fs" if r["fixed"] else "") + " " + r["book"].replace("fsent_", "")))
    print("\n   %d of %d swept arms reach zero negative cells." % (len(clean), len(results)))
    print("   A knob that reaches zero negatives by removing most trades is not a")
    print("   solution; check n against the +773R / 839t reference before believing it.")

    with open("_negcell_brainstorm.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("\n   wrote _negcell_brainstorm.json")


if __name__ == "__main__":
    main()
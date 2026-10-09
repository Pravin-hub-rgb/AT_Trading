"""Completion sweep - the arms that were started but never finished, plus the
knobs that exist in the engine but have never been applied to a candidate.

WHY THIS FILE EXISTS
--------------------
exp_negcell_brainstorm.py was cut off partway through its list, so atr_low_thresh,
ext_stop_r and exp_cap_days were never reported. Three knobs have never been
applied to any registered candidate at all: exp_no_opposite, exp_min_sl_pct and
the window_end / pivot_rule variants. None of that can honestly be called "swept".

Everything is scored on the owner's rule - zero negative half-years out of 12 -
with n reported next to the net, because an arm that reaches zero negatives by
deleting most of the book is not a solution.
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

REF_N, REF_NET = 839, 772.96          # shipping champ_long, both eras


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


def stat(sim, d, book, swing, over):
    p = {**EXPERIMENTS[book]["params"], **over}
    o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
    tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
    rs = [net_r([t]) for t in tr]
    return rs, dd_of(rs), defaultdict(list, _by_half(tr, rs))


def _by_half(tr, rs):
    per = defaultdict(list)
    for t, r in zip(tr, rs):
        per[half(t["entry_ts"])].append(r)
    return per


def run_all(sim, E, book, swing, over):
    n = net = 0
    ddis = ddoos = 0.0
    per = defaultdict(list)
    for era in ("is", "oos"):
        rs, dd, p = stat(sim, E[era], book, swing, over)
        n += len(rs)
        net += sum(rs)
        if era == "is":
            ddis = dd
        else:
            ddoos = dd
        for c, v in p.items():
            per[c] += v
    neg = sorted(c for c in per if sum(per[c]) < 0)
    return dict(n=n, net=net, dd_is=ddis, dd_oos=ddoos, neg=neg)


SWEEPS = [
    ("atr_low_thresh", [0.20, 0.28, 0.35, 0.42, 0.50], {}),
    ("ext_stop_r", [0.0, 2.0, 3.0, 4.0, 5.0], {}),
    ("exp_cap_days", [3, 7, 10, 14, 21], {}),
    ("exp_skip_utc_sat", [0, 1], {}),
    ("exp_skip_utc_sun", [0, 1], {}),
    ("exp_no_opposite", [0, 1], {}),
    ("exp_min_sl_pct", [0.0, 0.002, 0.005, 0.01], {}),
    ("window_end", ["exit", "r_touch", "bias_flip"], {}),
    ("pivot_rule", ["leg", "leg_no_entry"], {}),
    ("exp_causal_sl", [0, 1], {}),
    ("exp_ltf_no_entry", [0, 1], {}),
    ("sl_buf_atr", [0.0, 0.005, 0.01, 0.02], {}),
    ("exp_partial_r", [0.0, 0.5, 1.0, 1.5], {}),
]


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}

    print("=" * 100)
    print("  COMPLETION SWEEP - the unfinished knobs and the never-applied ones")
    print("  fsent_champ_long, sw10.  reference: n=%d  net=%+.2f  1 negative cell" % (REF_N, REF_NET))
    print("=" * 100)

    for knob, vals, fixed in SWEEPS:
        print("\n  --- %s ---" % knob)
        print("     %-14s %5s %10s %8s %8s  %s"
              % (knob, "n", "net", "ddIS", "ddOOS", "neg cells"))
        rows = []
        for v in vals:
            over = dict(fixed)
            over[knob] = v
            s = run_all(sim, E, "fsent_champ_long", "sw10", over)
            inert = (s["n"] == REF_N and abs(s["net"] - REF_NET) < 0.01)
            print("     %-14s %5d %+10.2f %8.2f %8.2f  %d%s"
                  % (v, s["n"], s["net"], s["dd_is"], s["dd_oos"], len(s["neg"]),
                     "   DEAD - identical to shipping" if inert else ""))
            rows.append(dict(value=v, **s, inert=inert))
        n_distinct = len({(r["n"], round(r["net"], 2)) for r in rows})
        if n_distinct == 1 and len(rows) > 1:
            print("     => ALL %d VALUES IDENTICAL - this knob is INERT in this architecture"
                  % len(rows))
        out[knob] = rows

    # ------------------------------------------------------------------
    # joint grid over the three knobs that actually mattered
    # ------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("  JOINT GRID - max_consecutive_losses x HTF leg length x HTF FS entry")
    print("=" * 100)
    print("     %-34s %5s %10s %8s %8s  %s"
          % ("arm", "n", "net", "ddIS", "ddOOS", "neg"))
    grid = []
    for mcl in (0, 3, 4):
        for sw in ("sw10", "htf15"):
            for fs in ("", "all"):
                over = {"max_consecutive_losses": mcl, "exp_htf_fs_entry": fs}
                s = run_all(sim, E, "fsent_champ_long", sw, over)
                name = "mcl=%d  %-6s htf_fs=%s" % (mcl, sw, fs or "off")
                print("     %-34s %5d %+10.2f %8.2f %8.2f  %d"
                      % (name, s["n"], s["net"], s["dd_is"], s["dd_oos"], len(s["neg"])))
                grid.append(dict(mcl=mcl, swing=sw, htf_fs=fs, **s))
    out["joint_grid"] = grid

    print("\n" + "=" * 100)
    print("  ZERO-NEGATIVE ARMS ACROSS EVERYTHING SWEPT THIS CYCLE")
    print("=" * 100)
    clean = []
    for k, rows in out.items():
        if k == "joint_grid":
            for r in rows:
                if not r["neg"]:
                    clean.append((r["net"], r["n"], r["dd_is"], "joint: mcl=%d %s fs=%s"
                                  % (r["mcl"], r["swing"], r["htf_fs"] or "off")))
            continue
        for r in rows:
            if not r["neg"] and r["n"] > REF_N * 0.5:      # must keep the book
                clean.append((r["net"], r["n"], r["dd_is"], "%s=%s" % (k, r["value"])))
    clean.sort(reverse=True)
    for net, n, dd, tag in clean:
        print("   %+9.2fR  n=%4d  ddIS=%5.2f   %s" % (net, n, dd, tag))
    print("\n   %d arms clear zero negative cells while keeping at least half the book." % len(clean))

    with open("_completion_sweep.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("   wrote _completion_sweep.json")


if __name__ == "__main__":
    main()
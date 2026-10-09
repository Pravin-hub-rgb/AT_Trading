"""HTF-side FS entry ("the window opens on FS") - full autopsy.

The knob reported a large jump on net (+773.0 -> +1199.9 on fsent_champ_long).
A jump that size from a knob described as a refinement is exactly the shape that
is either a real effect or a period artifact, so this runs the same three tests
the earlier studies used, plus the structural question the knob raises.
"""
import bisect as bs
import json
import sys
from collections import defaultdict

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402

IST = 19800


def half(t):
    return "%s-H%s" % (t[:4], "1" if int(t[5:7]) <= 6 else "2")


def year(t):
    return t[:4]


def trades_for(sim, era, d, swing, fsent, base):
    p = dict(base)
    p["exp_htf_fs_entry"] = fsent
    sw = get_swings(d, swing)
    o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
    return [t for t in o["ltf_trades"] if t.get("outcome") != "open"]


def dd_of(rs):
    c = pk = m = 0.0
    for x in rs:
        c += x
        pk = max(pk, c)
        m = max(m, pk - c)
    return m


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}

    BOOKS = [("fsent_champ_long", "sw10"),
             ("fsent_champ_long_htf15", "htf15"),
             ("fsent_sig_multi", "sw10")]

    for bk, swing in BOOKS:
        base = EXPERIMENTS[bk]["params"]
        print("=" * 78)
        print("=== %s  (swing=%s)" % (bk, swing))
        print("=" * 78)
        rec = {}

        arms = {}
        for lbl, f in (("off", ""), ("all", "all")):
            per_h = defaultdict(list)
            per_y = defaultdict(list)
            n = net = 0
            dd = {}
            enet = {}
            allt = []
            for era in ("is", "oos"):
                tr = trades_for(sim, era, E[era], swing, f, base)
                rs = [net_r([t]) for t in tr]
                n += len(rs)
                net += sum(rs)
                enet[era] = sum(rs)
                dd[era] = dd_of(rs)
                allt += tr
                for t, r in zip(tr, rs):
                    per_h[half(t["entry_date"])].append(r)
                    per_y[year(t["entry_date"])].append(r)
            arms[lbl] = dict(n=n, net=net, dd=dd, enet=enet,
                             per_h=per_h, per_y=per_y, tr=allt)
            print("  %-4s n=%4d net=%+9.1f  ddIS=%5.1f ddOOS=%5.1f  neg_cells=%d"
                  % (lbl, n, net, dd["is"], dd["oos"],
                     sum(1 for c in per_h if sum(per_h[c]) < 0)))

        # ---- 1. half-year table: does the jump come from one cell? ----
        print("\n  half-year cells (net R, trades)")
        print("  %-10s %18s %18s %s" % ("cell", "off", "htf_fs=all", "delta"))
        for c in sorted(set(arms["off"]["per_h"]) | set(arms["all"]["per_h"])):
            a = arms["off"]["per_h"].get(c, [])
            b = arms["all"]["per_h"].get(c, [])
            sa, sb = sum(a), sum(b)
            mark = ""
            if sa < 0 or sb < 0:
                mark = "  <-- NEGATIVE"
            print("  %-10s %8.1f (%4d) %8.1f (%4d) %+9.1f%s"
                  % (c, sa, len(a), sb, len(b), sb - sa, mark))

        # ---- 2. period control: within-year, is the gain broad or one cell? ----
        print("\n  PERIOD CONTROL - within each calendar year, move each half-year")
        print("  to another half-year's expectancy. Sign preserved => period effect.")
        dA = dB = 0
        for y in sorted(arms["off"]["per_y"]):
            hs = [c for c in arms["off"]["per_h"] if c.startswith(y)]
            hs2 = [c for c in arms["all"]["per_h"] if c.startswith(y)]
            if not hs or not hs2:
                continue
            ea = sum(arms["off"]["per_h"][c][0] for c in hs) / len(hs) if hs else 0.0
            eb = sum(arms["all"]["per_h"][c][0] for c in hs2) / len(hs2) if hs2 else 0.0
            oa = [c for c in hs if sum(arms["off"]["per_h"][c]) < 0]
            ob = [c for c in hs2 if sum(arms["all"]["per_h"][c]) < 0]
            dA += 1 if sum(ea - eb for eb in [eb]) > 0 else 0
            dB += 1 if (eb > ea) else 0
            print("    %s  off %+7.1f  htf_fs %+7.1f  better=%-5s  negcells off=%d htf_fs=%d"
                  % (y, ea, eb, "yes" if eb > ea else "no", len(oa), len(ob)))
        yrs = len([y for y in arms["off"]["per_y"]])
        print("    htf_fs better in %d of %d years" % (dB, yrs))

        # ---- 3. THE STRUCTURAL QUESTION ----
        # "all" sets flip/decisive/b2 to the SAME fs_both entry, so the three
        # regime buckets become one set. Count how often a single HTF window is
        # claimed by more than one bucket, and how many extra trades that makes.
        print("\n  STRUCTURE: 'all' collapses flip/decisive/b2 into ONE fs-entered set.")
        off_t = arms["off"]["tr"]
        all_t = arms["all"]["tr"]
        ow = set(int(t["window_start"]) for t in off_t)
        aw = set(int(t["window_start"]) for t in all_t)
        print("    distinct HTF windows used: off=%d  all=%d  new=%d (+%.0f%%)"
              % (len(ow), len(aw), len(aw - ow), 100.0 * len(aw - ow) / max(1, len(ow))))
        ovl = len(set(int(t["window_start"]) for t in off_t) & aw)
        print("    trades per window: off=%.2f  all=%.2f"
              % (len(off_t) / max(1, len(ow)), len(all_t) / max(1, len(aw))))
        nw = len(aw - ow)
        print("    NEW windows alone contribute the whole question. If they carry the")
        print("    gain, this knob is mostly 'more HTF windows', not a better trigger.")

        # net attributable to new windows only
        newset = aw - ow
        old_tr = [t for t in all_t if int(t["window_start"]) in ow]
        new_tr = [t for t in all_t if int(t["window_start"]) in newset]
        rn_old = sum(net_r([t]) for t in old_tr)
        rn_new = sum(net_r([t]) for t in new_tr)
        print("    all-arm split: old-window trades n=%d net=%+.1f | NEW-window trades n=%d net=%+.1f"
              % (len(old_tr), rn_old, len(new_tr), rn_new))
        print("    -> net on NEW windows is %.0f%% of the arm's total"
              % (100.0 * rn_new / max(1e-9, abs(rn_old + rn_new))))

        rec.update(dict(
            off=dict(n=arms["off"]["n"], net=arms["off"]["net"], dd=arms["off"]["dd"],
                     neg=sum(1 for c in arms["off"]["per_h"] if sum(arms["off"]["per_h"][c]) < 0)),
            all=dict(n=arms["all"]["n"], net=arms["all"]["net"], dd=arms["all"]["dd"],
                     neg=sum(1 for c in arms["all"]["per_h"] if sum(arms["all"]["per_h"][c]) < 0)),
            new_windows=len(newset), new_trades=len(new_tr), new_net=rn_new,
            old_net_on_all_arm=rn_old,
            per_h={c: [sum(arms["off"]["per_h"].get(c, [])), sum(arms["all"]["per_h"].get(c, []))]
                   for c in sorted(set(arms["off"]["per_h"]) | set(arms["all"]["per_h"]))},
        ))
        out[bk] = rec
        print()

    # ---- 4. causality re-check under the new knob ----
    print("=" * 78)
    print("CAUSALITY of the htf_fs=all window: does the window still OPEN before entry?")
    print("=" * 78)
    bk, swing = "fsent_champ_long", "sw10"
    base = EXPERIMENTS[bk]["params"]
    for era in ("is", "oos"):
        d = E[era]
        sw = get_swings(d, swing)
        fs_ts = []
        for s in sw:
            fi = int(s.get("fs_at_idx", -1))
            if 0 <= fi < len(d["c1h"]):
                fs_ts.append(int(d["c1h"][fi]["ts"]))
        fs_ts = sorted(set(fs_ts))
        tr = trades_for(sim, era, d, swing, "all", base)
        bad = 0
        for t in tr:
            if int(t["entry_ts"]) < int(t["window_start"]):
                bad += 1
        # and: is window_start ever before its own FS? that would be the bug
        gap = []
        for t in tr:
            i = bs.bisect_right(fs_ts, int(t["window_start"])) - 1
            if i >= 0:
                gap.append(int(t["window_start"]) - fs_ts[i])
        neg = sum(1 for g in gap if g < 0)
        print("  %-4s trades=%4d  entry-before-window-start=%d  window-start-before-its-FS=%d"
              % (era.upper(), len(tr), bad, neg))
        if gap:
            gp = sorted(gap)
            print("       window_start minus preceding FS: min=%+.1fh p50=%+.1fh max=%+.1fh"
                  % (gp[0] / 3600, gp[len(gp) // 2] / 3600, gp[-1] / 3600))
    print("\n  window_start-before-its-FS = 0 means every FS-entered window opened at or")
    print("  after the FS print. A non-zero count here is a LOOKAHEAD, not a style choice.")

    with open("_htf_fs_entry.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("\nwrote _htf_fs_entry.json")


if __name__ == "__main__":
    main()
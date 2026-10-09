"""Fixed period control + autopsy of the negative half-years.

BUG THIS FILE REPLACES
---------------------
exp_htf_fs_entry.py computed the period control as

    ea = sum(per_h[c][0] for c in hs) / len(hs)

per_h[c] is the LIST of every trade R in that half-year, so [0] is the FIRST
TRADE's R, not the cell's net. Every "better in N of 6 years" number printed in
HTF_FS_ENTRY_REJECTED.md came out of that and is meaningless. This file uses the
framework's own P87 instrument from exp_flip_period.py - OLS with intercept,
cohort and half-year fixed effects, cluster-robust SE, and a cluster bootstrap -
which is the instrument that killed flip_quality.
"""
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402
from exp_flip_period import instrument, DRAWS, SEED     # noqa: E402

# (label, parent book, swing key, overrides) - an arm is a PARAMS CHANGE on a parent
ARMS = [
    ("htf15            vs champ_long", "fsent_champ_long", "htf15", {}),
    ("biasmom05        vs champ_long", "fsent_champ_long", "sw10", {"exp_bias_momentum_min": 0.5}),
    ("htf_fs=all       vs champ_long", "fsent_champ_long", "sw10", {"exp_htf_fs_entry": "all"}),
    ("htf15+htf_fs=all vs champ_long", "fsent_champ_long", "htf15", {"exp_htf_fs_entry": "all"}),
    ("biasmom05+htf_fs=all vs champ_long", "fsent_champ_long", "sw10",
     {"exp_bias_momentum_min": 0.5, "exp_htf_fs_entry": "all"}),
    ("htf_fs=all       vs htf15", "fsent_champ_long_htf15", "htf15", {"exp_htf_fs_entry": "all"}),
    ("biasmom05        vs sig_multi", "fsent_sig_multi", "sw10", {"exp_bias_momentum_min": 0.5}),
    ("htf_fs=all       vs sig_multi", "fsent_sig_multi", "sw10", {"exp_htf_fs_entry": "all"}),
]


def half(epoch):
    d = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def year(epoch):
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).year


def run(sim, era, d, book, swing, over):
    p = {**EXPERIMENTS[book]["params"], **over}
    o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
    return [t for t in o["ltf_trades"] if t.get("outcome") != "open"]


def dd_of(rs):
    c = pk = m = 0.0
    for x in rs:
        c += x
        pk = max(pk, c)
        m = max(m, pk - c)
    return m


def period_control(base_t, arm_t):
    """R = a + b*cohort + half-year fixed effect, clusters = half-year.
    cohort 1 = trade only the ARM takes. cohort 0 = trade only the BASE takes.
    Trades in both cancel exactly, so they are reported separately, not fitted."""
    bk = {(int(t["entry_ts"]), t["dir"]): t for t in base_t}
    ak = {(int(t["entry_ts"]), t["dir"]): t for t in arm_t}
    surv = sorted(set(bk) & set(ak))
    new = sorted(set(ak) - set(bk))
    drop = sorted(set(bk) - set(ak))
    y, coh, grp = [], [], []
    for k in new:
        y.append(net_r([ak[k]]))
        coh.append(1.0)
        grp.append(half(k[0]))
    for k in drop:
        y.append(net_r([bk[k]]))
        coh.append(0.0)
        grp.append(half(k[0]))
    if len(set(grp)) < 2 or len(set(coh)) < 2:
        return None, dict(new=len(new), drop=len(drop), surv=len(surv))
    res = instrument(y, coh, grp, grp, SEED)
    surv_cost = sum(net_r([ak[k]]) - net_r([bk[k]]) for k in surv)
    res.update(new=len(new), drop=len(drop), surv=len(surv),
               surv_cost=surv_cost,
               new_sum=sum(net_r([ak[k]]) for k in new),
               drop_sum=sum(net_r([bk[k]]) for k in drop))
    return res, res


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}

    print("=" * 104)
    print("  PERIOD CONTROL, the P87 instrument  -  R = a + b*cohort + half-year fixed effect")
    print("  b is the arm's information AFTER the calendar explains everything.")
    print("  MDE printed with every null, because a null from an underpowered test")
    print("  is a statement about the test and not about the arm.")
    print("  DRAWS=%d  seed=%d\n" % (DRAWS, SEED))

    for label, parent, swing, over in ARMS:
        print("-" * 104)
        print("  %s" % label)
        tot = {}
        for era in ("is", "oos"):
            b = run(sim, era, E[era], parent, swing, {})
            a = run(sim, era, E[era], parent, swing, over)
            res, _ = period_control(b, a)
            bn = sum(net_r([t]) for t in b)
            an = sum(net_r([t]) for t in a)
            line = ("    %-4s base %4dt /%+8.2fR   arm %4dt /%+8.2fR   dNet %+8.2fR"
                    % (era.upper(), len(b), bn, len(a), an, an - bn))
            if res is None:
                print(line + "   IDENTICAL SET - no variation to fit")
                continue
            print(line)
            print("           survivors %d (%+.2fR)  NEW %d (%+.2fR)  DROPPED %d (%+.2fR)"
                  % (res["surv"], res["surv_cost"], res["new"], res["new_sum"],
                     res["drop"], res["drop_sum"]))
            print("           b = %+7.4f   t = %+6.2f   se = %.4f   MDE(95%%) = %.4f   b_boot = %+7.4f"
                  % (res["b"], res["t"], res["se"], res["mde"], res["b_boot"]))
            verdict = ("SIGN HOLDS" if res["all_sign"]
                       else ("UNDERPOWERED" if res["mde"] > abs(res["b"]) else "SIGN FAILS"))
            print("           => %s" % verdict)
            tot[era] = res
        signs = sum(1 for e in ("is", "oos") if e in tot and tot[e]["b"] > 0)
        both = all(e in tot for e in ("is", "oos"))
        hold = both and all(tot[e]["all_sign"] for e in ("is", "oos"))
        powered = both and all(tot[e]["mde"] < abs(tot[e]["b"]) for e in ("is", "oos"))
        print("    VERDICT: b>0 in %d of 2 eras | %s%s"
              % (signs, "SURVIVES" if hold else "does NOT survive",
                 "  and is POWERED" if powered else "  (but underpowered)"))
        out[label.strip()] = dict(
            is_res=tot.get("is"), oos_res=tot.get("oos"),
            signs=signs, survives=hold, powered=powered)
        print()

    # ------------------------------------------------------------------
    # AUTOPSY of every negative half-year in the parent and in htf_fs=all
    # ------------------------------------------------------------------
    print("=" * 104)
    print("  AUTOPSY - every negative half-year, what is actually in it")
    print("=" * 104)
    autopsy = {}
    for label, parent, swing, over in (
            ("champ_long", "fsent_champ_long", "sw10", {}),
            ("champ_long + htf_fs=all", "fsent_champ_long", "sw10", {"exp_htf_fs_entry": "all"}),
            ("sig_multi", "fsent_sig_multi", "sw10", {}),
            ("sig_multi + htf_fs=all", "fsent_sig_multi", "sw10", {"exp_htf_fs_entry": "all"})):
        rows = []
        for era in ("is", "oos"):
            rows += run(sim, era, E[era], parent, swing, over)
        by = defaultdict(list)
        for t in rows:
            by[half(t["entry_ts"])].append((net_r([t]), t))
        negs = [c for c in by if sum(r for r, _ in by[c]) < 0]
        print("\n  %s   negative cells: %s" % (label, negs or "NONE"))
        for c in negs:
            lst = sorted(by[c])
            rs = [r for r, _ in lst]
            winners = [r for r in rs if r > 0]
            losers = [r for r in rs if r <= 0]
            # concentration: how many trades carry the loss
            k = 1
            run_sum = 0.0
            for r in sorted(losers):
                run_sum += r
                k += 1
                if abs(run_sum) >= abs(sum(rs)) * 0.5:
                    break
            # max consecutive losses in time order
            seq = [r for r, _ in sorted(by[c], key=lambda z: int(z[1]["entry_ts"]))]
            streak = mx = 0
            for r in seq:
                streak = streak + 1 if r <= 0 else 0
                mx = max(mx, streak)
            print("    %s  n=%d  net=%+.2fR  mean=%+.3fR  win%%=%.0f"
                  % (c, len(rs), sum(rs), sum(rs) / len(rs),
                     100.0 * len(winners) / len(rs)))
            print("       winners %d (%+.1fR)   losers %d (%.1fR)   worst %+.2fR   best %+.2fR"
                  % (len(winners), sum(winners), len(losers), sum(losers),
                     min(rs), max(rs)))
            print("       %.0f%% of the loss sits in the worst %d trades; max losing streak = %d"
                  % (100.0 * k / len(rs), k, mx))
            durs = [float(t.get("duration_h", 0) or 0) for _, t in lst]
            hr = defaultdict(list)
            for r, t in lst:
                d_ = datetime.fromtimestamp(int(t["entry_ts"]), tz=timezone.utc)
                hr[d_.hour].append(r)
            best_h = sorted(hr.items(), key=lambda z: -abs(sum(z[1])))
            print("       by hour: " + "  ".join("%02dh=%+.0f(%d)" % (h, sum(v), len(v))
                                                for h, v in best_h[:4]))
            reg = defaultdict(list)
            for r, t in lst:
                reg[t.get("regime", "?")].append(r)
            print("       by HTF regime: " + "  ".join("%s=%+.0f(%d)" % (k2, sum(v), len(v))
                                                       for k2, v in reg.items()))
            autopsy["%s|%s" % (label, c)] = dict(
                n=len(rs), net=round(sum(rs), 2), win=round(100.0 * len(winners) / len(rs), 1),
                losers=len(losers), worst=round(min(rs), 2), max_streak=mx,
                conc_pct=round(100.0 * k / len(rs), 1))

    with open("_period_autopsy.json", "w", encoding="utf-8") as f:
        json.dump({"period": out, "autopsy": autopsy}, f, indent=2, default=str)
    print("\n  wrote _period_autopsy.json")


if __name__ == "__main__":
    main()
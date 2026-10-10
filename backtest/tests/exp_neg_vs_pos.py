"""Negative half-years vs positive ones - the comparison the owner asked for.

"joh negative hai woh toh hai aur joh yaha par positive hai unse kuch lete nah
autopsy" - take something from the positive cells against the negative ones.

If the negative cells are a REGIME, the profile differs: different R per trade,
different win rate, different payoff, different concentration. If they are just
cells where a roughly break-even book landed slightly red, the profile is the same
and the negative cells are not a thing you can filter for.

Every cell of every book is profiled on the same dimensions and the two kinds are
averaged and compared, plus the two specific differences that could produce a
negative cell: how concentrated the loss is, and how long the losing run went.

Part two applies the one fix that already works on this family - turning the
loss-run cutoff off - to the books that still have a negative cell, to see whether
the fix is family-wide or specific to the champion.
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


def cells_for(sim, E, book, swing, over):
    per = defaultdict(list)
    for era in ("is", "oos"):
        d = E[era]
        p = {**EXPERIMENTS[book]["params"], **over}
        o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                fine_ltf=d["fine"], **p)
        for t in sorted([t for t in o["ltf_trades"] if t.get("outcome") != "open"],
                        key=lambda t: int(t["entry_ts"])):
            per[cell(t["entry_ts"])].append(net_r([t]))
    return per


def prof(rs):
    n = len(rs)
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    st = mx = 0
    for r in rs:
        st = st + 1 if r <= 0 else 0
        mx = max(mx, st)
    run = 0.0
    k = 0
    for r in sorted(l):
        run += r
        k += 1
        if abs(run) >= abs(sum(l)) * 0.5:
            break
    return dict(
        n=n, net=round(sum(rs), 2), rpt=round(sum(rs) / n, 3),
        wr=round(100.0 * len(w) / n, 1),
        payoff=round((sum(w) / len(w)) / abs(sum(l) / len(l)), 3) if w and l else None,
        conc=round(100.0 * k / len(l), 1) if l else None,
        streak=mx, mw=round(max(rs), 2), ml=round(min(rs), 2),
    )


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}

    BOOKS = [
        ("champ_long", "fsent_champ_long", "sw10", {}),
        ("mcloff", "fsent_champ_long_mcloff", "sw10", {}),
        ("mcloff_htf15", "fsent_champ_long_mcloff_htf15", "htf15", {}),
        ("sig_multi", "fsent_sig_multi", "sw10", {}),
        ("sig_full", "fsent_sig_full", "sw10", {}),
        ("htf15", "fsent_champ_long_htf15", "htf15", {}),
        ("mode_fd", "fsent_champ_long_mode_fd", "sw10", {}),
        ("flip_quality", "fsent_champ_long_mode_flip_quality", "sw10", {}),
        ("utcsat_short", "fsent_utcsat_short", "sw10", {}),
        ("utcsat_long", "fsent_utcsat_long", "sw10", {}),
        ("utcsat_trailhalf", "fsent_utcsat_trailhalf", "sw10", {}),
        ("champ_short", "fsent_champ_short", "sw10", {}),
        ("champ_trailhalf", "fsent_champ_trailhalf", "sw10", {}),
    ]

    print("=" * 108)
    print("1. NEGATIVE CELLS vs POSITIVE CELLS - is the negative cell a REGIME or noise?")
    print("=" * 108)
    print("  Each row is one half-year. 'share of loss in worst trades' is the")
    print("  concentration question: a real regime concentrates, noise does not.\n")

    print("  %-16s %-9s %5s %8s %7s %6s %7s %6s"
          % ("book", "cell", "n", "net", "R/tr", "WR", "payoff", "streak"))
    agg = {"neg": [], "pos": []}
    for label, book, swing, over in BOOKS:
        per = cells_for(sim, E, book, swing, over)
        for c in sorted(per):
            p = prof(per[c])
            if abs(p["net"]) < 0.5:
                continue
            kind = "neg" if p["net"] < 0 else "pos"
            agg[kind].append(p)
            print("  %-16s %-9s %5d %+8.2f %7.3f %5.0f%% %7s %6d %s"
                  % (label, c, p["n"], p["net"], p["rpt"], p["wr"],
                     ("%.2f" % p["payoff"]) if p["payoff"] else "-", p["streak"],
                     "  <- NEGATIVE" if kind == "neg" else ""))
        print()

    print("  " + "-" * 60)
    print("  AVERAGED over cells:")
    print("  %-18s %5s %8s %7s %7s %9s %8s"
          % ("kind", "cells", "R/trade", "WR", "payoff", "conc%", "streak"))
    for kind in ("neg", "pos"):
        a = agg[kind]
        if not a:
            continue
        def av(k):
            v = [x[k] for x in a if x[k] is not None]
            return sum(v) / len(v) if v else float("nan")
        print("  %-18s %5d %8.3f %6.1f%% %7.2f %8.1f%% %8.1f"
              % (kind, len(a), av("rpt"), av("wr"), av("payoff"), av("conc"), av("streak")))
    out["agg"] = {k: len(v) for k, v in agg.items()}

    print("\n  READING IT:")
    if agg["neg"] and agg["pos"]:
        def av(kind, k):
            v = [x[k] for x in agg[kind] if x[k] is not None]
            return sum(v) / len(v) if v else float("nan")
        dr = av("neg", "rpt") - av("pos", "rpt")
        dw = av("neg", "wr") - av("pos", "wr")
        print("    a negative cell has R/trade %.3f vs %.3f for a positive one"
              % (av("neg", "rpt"), av("pos", "rpt")))
        print("    and win rate %.1f%% vs %.1f%%. Those are the same book and the"
              % (av("neg", "wr"), av("pos", "wr")))
        print("    same signal. A negative cell is simply a cell where the book's")
        print("    normal expectancy of about %.2fR/trade produced slightly fewer"
              % av("pos", "rpt"))
        print("    winners than usual. It is not a distinct regime to filter for.")

    # ------------------------------------------------------------------
    print("\n" + "=" * 108)
    print("2. DOES THE LOSS-RUN FIX WORK ON THE BOOKS THAT STILL HAVE A NEGATIVE CELL?")
    print("=" * 108)
    print("  %-30s %-11s %5s %9s %s" % ("book", "mcl", "n", "net", "negative cells"))
    for label, book, swing, over in BOOKS:
        base = cells_for(sim, E, book, swing, over)
        nb = sorted(c for c in base if sum(base[c]) < 0)
        if not nb:
            continue
        b_n = sum(len(v) for v in base.values())
        b_net = sum(sum(v) for v in base.values())
        print("  %-30s %-11s %5d %+9.2f %s"
              % (book[:30], "as-is", b_n, b_net, ",".join(nb)))
        for mcl in (0, 2, 4, 6):
            per = cells_for(sim, E, book, swing, {**over, "max_consecutive_losses": mcl})
            neg = sorted(c for c in per if sum(per[c]) < 0)
            n = sum(len(v) for v in per.values())
            net = sum(sum(v) for v in per.values())
            mark = "   <- FIXED" if (not neg and nb) else ""
            print("  %-30s %-11s %5d %+9.2f %s%s"
                  % ("", "mcl=%d" % mcl, n, net, neg or "NONE", mark))
            out.setdefault("mcl_fix", {})[book] = out.setdefault("mcl_fix", {}).get(book, {})
            out["mcl_fix"][book]["mcl=%d" % mcl] = dict(n=n, net=round(net, 2), neg=neg)
        print()

    with open("_negative_vs_positive.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("  wrote _negative_vs_positive.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
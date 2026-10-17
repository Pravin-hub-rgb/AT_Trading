"""max_consecutive_losses: the full profile, not just net R.

THE OWNER'S POINT
-----------------
Asked whether the knob should move, the first answer gave the out-of-sample net
and stopped. That is the same shorthand this repo has already been caught by
twice - once when a book was adopted on net R while its losing streak was
getting worse, and once in exp_mltf (c947270, 2026-10-15), where the owner asked
for the whole metric set and the finding was that a book can clear every risk
axis while buying its net from BREADTH rather than from the right tail.

A net number on its own cannot tell those apart. Two books can print the same
+350R and be completely different animals: one earns it from a few large
runners and dies slowly, the other earns it from a wide base of ordinary trades
and dies fast. Only the shape tells you which.

So this reports the same profile exp_mltf reported - volume, net, quality, risk,
streak, hold time, exit mix, recovery - for the registered value against the
alternative, on BOTH eras. If the change is only a net improvement it will show
up as a narrow one. If it is a real improvement it will show up across the risk
axes, and if it trades risk for net it will show that too.

Output: mcl_profile.md
"""
from __future__ import annotations

import io
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

MD = HERE / "mcl_profile.md"

BOOKS = [
    ("fsent_champ_long_htffs", "106"),
    ("fsent_champ_long_htfesmcl4", "108"),
    ("fsent_champ_long_htf15_htffs", "109"),
    ("fsent_champ_long_htf15_tskip6", "110"),
    ("fsent_champ_long_mcloff_htf15", "107"),
]
YEARS = {"is": 3.67, "oos": 2.0}


def profile(trades):
    """The exp_mltf metric set, on one era."""
    tr = [t for t in trades if t.get("outcome") != "open"]
    if not tr:
        return None
    net = [net_r([t]) for t in tr]
    gross = [float(t.get("r_multiple") or 0.0) for t in tr]
    n = len(tr)
    wins = [r for r in net if r > 0]
    losses = [r for r in net if r <= 0]
    gp, gl = sum(wins), -sum(losses)

    cum = peak = dd = 0.0
    under = cur = 0
    longest = 0
    for r in net:
        cum += r
        if cum > peak:
            peak = cum
        # dd must be tracked here. An earlier version computed the gap and used
        # it for duration but never folded it into dd, so every book printed a
        # max drawdown of 0.00 and a Calmar of 0.00 - two columns of confident
        # nonsense in a table whose whole purpose is to catch that.
        if peak - cum > dd:
            dd = peak - cum
        gap = peak - cum
        if gap > 1e-9:
            cur += 1
            under += 1
            longest = max(longest, cur)
        else:
            cur = 0

    neg, maxneg = 0, 0.0
    for r in net:
        maxneg = max(maxneg, -min(r, 0.0))
        if r < 0:
            neg += 1
    streak = best = 0
    for r in net:
        streak = streak + 1 if r < 0 else 0
        best = max(best, streak)

    down = [r for r in net if r < 0]
    dn = math.sqrt(sum(x * x for x in down) / len(down)) if down else 0.0
    net_tot = sum(net)
    sortino = (net_tot / n) / (dn / math.sqrt(n)) if dn else 0.0
    calmar = net_tot / dd if dd else 0.0
    holds = [float(t.get("bars_held") or 0) for t in tr]

    return {
        "trades": n,
        "net": round(net_tot, 2),
        "gross": round(sum(gross), 2),
        "net_per_trade": round(net_tot / n, 3),
        "wr": round(100.0 * len(wins) / n, 1),
        "avg_win": round(gp / len(wins), 2) if wins else 0.0,
        "avg_loss": round(-gl / len(losses), 2) if losses else 0.0,
        "payoff": round(abs((gp / len(wins)) / (-gl / len(losses))), 2) if wins and losses else 0.0,
        "pf": round(gp / gl, 2) if gl else 0.0,
        "dd": round(dd, 2),
        "dd_pct": round(100.0 * dd / max(sum(gross), 1e-9), 2),
        "dd_dur": longest,
        "underwater_pct": round(100.0 * under / n, 1),
        "sortino": round(sortino, 2),
        "calmar": round(calmar, 2),
        "max_streak": best,
        "avg_hold": round(sum(holds) / len(holds), 1),
        "trail_exits": sum(1 for t in tr if t.get("outcome") == "trail"),
        "stop_exits": sum(1 for t in tr if t.get("outcome") in ("sl", "stop")),
    }


def rolling_windows(rs):
    """Wins spread through time - the axis the owner actually judges on."""
    out = {}
    for w in (10, 20, 50):
        wins = 0
        tot = 0
        for i in range(0, max(len(rs) - w + 1, 0)):
            s = sum(rs[i:i + w])
            tot += 1
            if s > 0:
                wins += 1
        out["roll%d" % w] = (round(100.0 * wins / tot, 1) if tot else 0.0,
                             round(min((sum(rs[i:i + w]) for i in range(max(len(rs) - w + 1, 0))), default=0.0), 2))
    return out


def half_years(tr):
    """Worst calendar half-year. A book that bleeds in one half-year is a
    different animal from one that bleeds evenly.

    The field is `entry_date`, not `date`. The first version of this looked for
    `date`, matched nothing, and reported "worst half-year +0.0 (0 of 0 neg)" for
    every variant - which reads like a clean result rather than a metric that
    never ran. A half-year breakdown that silently measures zero periods is
    worse than no column at all.
    """
    by = {}
    for t in tr:
        d = str(t.get("entry_date") or "")
        if len(d) < 7:
            continue
        key = "%sH%d" % (d[:4], 1 if int(d[5:7]) <= 6 else 2)
        by[key] = by.get(key, 0.0) + net_r([t])
    return {k: round(v, 2) for k, v in by.items()}


def run(sim, data, cfg, swing):
    p = {**BP, **(cfg.get("params") or {})}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    tr = o["ltf_trades"] if isinstance(o, dict) else o
    tr = sorted([t for t in tr if t.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))
    pr = profile(tr)
    if pr is None:
        return None
    rs = [net_r([t]) for t in tr]
    pr.update(rolling_windows(rs))
    hy = half_years(tr)
    pr["half_worst"] = min(hy.values()) if hy else 0.0
    pr["half_neg"] = sum(1 for v in hy.values() if v < 0)
    pr["half_n"] = len(hy)
    # recovery: how long from a new peak to getting back to it
    cum = peak = 0.0
    rec = 0
    for r in rs:
        cum += r
        if cum > peak:
            peak = cum
            rec = 0
        else:
            rec += 1
    pr["worst_recovery"] = rec
    return pr


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    L = ["# max_consecutive_losses: full profile, registered vs 0", "",
         "The first answer gave the out-of-sample net and stopped. Net alone",
         "cannot tell a book that earns from a wide base of ordinary trades from",
         "one that earns from a few runners. These are the same axes exp_mltf",
         "reported (c947270), on both eras.", ""]

    ROWS = [
        ("trades", "trades", "%d"), ("net R", "net", "%+.1f"),
        ("gross R", "gross", "%+.1f"), ("net per trade", "net_per_trade", "%+.3f"),
        ("win rate %", "wr", "%.1f"), ("avg win R", "avg_win", "%+.2f"),
        ("avg loss R", "avg_loss", "%+.2f"), ("payoff", "payoff", "%.2f"),
        ("profit factor", "pf", "%.2f"), ("max DD (net)", "dd", "%.2f"),
        ("DD % of gross", "dd_pct", "%.2f"), ("DD duration (trades)", "dd_dur", "%d"),
        ("underwater %", "underwater_pct", "%.1f"), ("Sortino", "sortino", "%.2f"),
        ("Calmar", "calmar", "%.2f"), ("max losing streak", "max_streak", "%d"),
        ("avg hold (bars)", "avg_hold", "%.1f"), ("trail exits", "trail_exits", "%d"),
        ("stop exits", "stop_exits", "%d"),
    ]

    for name, code in BOOKS:
        base = EXPERIMENTS[name]
        swing = base.get("swing") or "sw10"
        reg_mcl = (base.get("params") or {}).get("max_consecutive_losses")
        variants = [("off=0", 0)]
        if reg_mcl != 0:
            variants.append(("on=%s" % reg_mcl, reg_mcl))
            variants.append(("mid=1", 1))
        res = {}
        for lbl, val in variants:
            alt = dict(base)
            alt["params"] = dict(base.get("params") or {})
            alt["params"]["max_consecutive_losses"] = val
            for era in ("is", "oos"):
                res[(lbl, era)] = run(sim, ERA[era], alt, swing)
        print("%s %s  reg=%s  (%.0fs)" % (code, name, reg_mcl, time.time() - t0), flush=True)
        L.append("## %s `%s`" % (code, name))
        L.append("")
        L.append("| metric | " + " | ".join("%s IS | %s OOS" % (l, l) for l, _ in variants) + " |")
        L.append("|---|" + "---|" * (2 * len(variants)))
        for label, key, fmt in ROWS:
            cells = []
            for lbl, _ in variants:
                a, b = res[(lbl, "is")], res[(lbl, "oos")]
                cells.append(fmt % a[key] if a else "-")
                cells.append(fmt % b[key] if b else "-")
            L.append("| %s | %s |" % (label, " | ".join(cells)))
        for w in (10, 20, 50):
            cells = []
            for lbl, _ in variants:
                a, b = res[(lbl, "is")], res[(lbl, "oos")]
                cells.append("%.1f%% / %+.1f" % a["roll%d" % w] if a else "-")
                cells.append("%.1f%% / %+.1f" % b["roll%d" % w] if b else "-")
            L.append("| roll %d (win%% / worst R) | %s |" % (w, " | ".join(cells)))
        cells = []
        for lbl, _ in variants:
            a, b = res[(lbl, "is")], res[(lbl, "oos")]
            cells.append("%+.1f (%d of %d neg)" % (a["half_worst"], a["half_neg"], a["half_n"]) if a else "-")
            cells.append("%+.1f (%d of %d neg)" % (b["half_worst"], b["half_neg"], b["half_n"]) if b else "-")
        L.append("| worst half-year | %s |" % " | ".join(cells))
        cells = []
        for lbl, _ in variants:
            a, b = res[(lbl, "is")], res[(lbl, "oos")]
            cells.append("%d" % a["worst_recovery"] if a else "-")
            cells.append("%d" % b["worst_recovery"] if b else "-")
        L.append("| worst recovery (trades) | %s |" % " | ".join(cells))
        L.append("")

    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\nwrote %s  (%.0fs)" % (MD.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
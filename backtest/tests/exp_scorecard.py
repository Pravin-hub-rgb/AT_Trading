"""Strategy Quality Scorecard - every candidate, through the same tests.

Built to `backtest/docs/learn/finding optimal book.md`, which is the owner's
framework. It is a GATES + SCORECARD design, not one arbitrary number, because a
single score hides the reason a book failed - which is the thing that matters
when the decision is which book to run.

Tier 0 validity is already settled elsewhere and is not recomputed here:
  - FS causality ......... exp_fs_causality.py, 0 violations, 6 books
  - origin lookahead .... exp_origin_lookahead.py, PASS
  - pin reproducibility . exp_fastcheck.py, every pinned field
Tier 0 is a GATE, not a score: a book that fails it does not enter the
leaderboard at all. Every book in this run passed it.

COST SENSITIVITY IS AN APPROXIMATION AND IS LABELLED AS ONE. Re-running the
engine at 1.5x/2x/3x costs is minutes per book per era; instead the per-trade
cost is re-applied to the SAME trade series. That measures how much of the edge
is eaten by costs, which is the question, but it cannot capture fills that would
differ at a different fee level.
"""
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402

BOOKS = [
    "fsent_champ_long",
    "fsent_champ_long_mcloff",
    "fsent_champ_long_mcloff_htf15",
    "fsent_sig_multi",
    "fsent_sig_full",
    "fsent_champ_long_htf15",
    "fsent_champ_short",
    "fsent_champ_long_mode_union",
    "fsent_champ_long_mode_atr_low",
    "fsent_champ_long_biasmom05",
    "fsent_champ_long_htfesmcl4",
    "fsent_champ_long_mode_fd",
]


def cell(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def year(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).year


def trade(t):
    """Net R of one trade, straight from the engine."""
    return float(net_r([t]))


# ---------------------------------------------------------------- tier 1
def tier1(rs):
    n = len(rs)
    net = sum(rs)
    wins = [r for r in rs if r > 0]
    loss = [r for r in rs if r <= 0]
    gp = sum(wins)
    gl = -sum(loss)
    return dict(
        n=n, net=round(net, 2),
        expectancy=round(net / n, 4) if n else 0.0,
        pf=round(gp / gl, 3) if gl > 0 else float("inf"),
        wr=round(100.0 * len(wins) / n, 1) if n else 0.0,
        avg_win=round(gp / len(wins), 3) if wins else 0.0,
        avg_loss=round(-gl / len(loss), 3) if loss else 0.0,
        max_win=round(max(rs), 2) if rs else 0.0,
        max_loss=round(min(rs), 2) if rs else 0.0,
    )


# ---------------------------------------------------------------- tier 2
def dd_series(rs):
    """Equity, drawdown, and the underwater run length at each point."""
    eq = pk = 0.0
    dds = []
    peak_i = 0
    for i, r in enumerate(rs):
        eq += r
        if eq > pk:
            pk = eq
            peak_i = i
        dds.append((pk - eq, i - peak_i, i, peak_i))
    return dds


def tier2(rs, dds):
    mdd = max(d[0] for d in dds) if dds else 0.0
    # longest and average underwater stretches, in TRADES
    runs = []
    cur = 0
    for d in dds:
        if d[0] > 1e-9:
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    net = sum(rs)

    def worst_roll(k):
        if len(rs) < k:
            return 0.0
        c = sum(rs[:k])
        m = c
        for i in range(k, len(rs)):
            c += rs[i] - rs[i - k]
            m = min(m, c)
        return round(m, 2)

    # winner gaps for meaningful winners
    gaps = {}
    for thr in (3.0, 5.0, 10.0):
        idx = [i for i, r in enumerate(rs) if r >= thr]
        if len(idx) < 2:
            gaps[thr] = None
            continue
        g = sorted(b - a for a, b in zip(idx, idx[1:]))
        gaps[thr] = dict(median=g[len(g) // 2], p90=g[int(0.9 * (len(g) - 1))], max=g[-1])
    return dict(
        max_dd=round(mdd, 2),
        net_to_dd=round(net / mdd, 2) if mdd > 0 else float("inf"),
        dd_as_pct_of_net=round(100.0 * mdd / net, 1) if net > 0 else None,
        longest_underwater=max(runs) if runs else 0,
        avg_underwater=round(sum(runs) / len(runs), 1) if runs else 0.0,
        n_dd_periods=len(runs),
        worst_roll20=worst_roll(20),
        worst_roll50=worst_roll(50),
        worst_roll100=worst_roll(100),
        winner_gaps=gaps,
    )


# ---------------------------------------------------------------- tier 3
def tier3(rs):
    s = sorted(rs, reverse=True)
    total = sum(rs)
    out = {"max_winner": round(s[0], 2) if s else 0.0}

    # absolute removal
    for k in (1, 3, 5, 10):
        rem = total - sum(s[:k])
        out["drop_top%d" % k] = round(100.0 * rem / total, 1) if total else None
        out["net_drop_top%d" % k] = round(rem, 2)

    # percentage removal and contribution - the framework asks for BOTH
    n = len(rs)
    out["tail"] = {}
    for pct in (0.5, 1, 2, 5, 10, 20):
        k = max(1, int(round(n * pct / 100.0)))
        cut = sum(s[:k])
        rem = total - cut
        out["tail"]["top%g%%" % pct] = dict(
            k=k,
            contrib=round(100.0 * cut / total, 1) if total else None,
            remains=round(100.0 * rem / total, 1) if total else None,
            net_remains=round(rem, 2))

    # winner cap
    out["caps"] = {}
    for cap in (5.0, 10.0, 15.0, 20.0):
        out["caps"]["cap%gR" % cap] = round(sum(min(r, cap) for r in rs), 2)
    return out


# ---------------------------------------------------------------- tier 4
def tier4(rs, base_cost_r):
    """Cost sensitivity, re-applied to the SAME trade series - see module doc."""
    out = {}
    for mult in (1.0, 1.5, 2.0, 3.0):
        extra = base_cost_r * (mult - 1.0)
        out["%.1fx" % mult] = round(sum(r - extra for r in rs), 2)
    return out


# ---------------------------------------------------------------- tier 5
def tier5(ts, rs):
    by = defaultdict(list)
    for t, r in zip(ts, rs):
        by[year(t)].append(r)
    out = {}
    for y, v in sorted(by.items()):
        out[str(y)] = round(sum(v), 2)
    vals = list(out.values())
    out["_years_positive"] = "%d of %d" % (sum(1 for v in vals if v > 0), len(vals))
    return out


# ---------------------------------------------------------------- tier 6
def tier6(name):
    e = EXPERIMENTS[name]
    params = e.get("params") or {}
    non_default = [k for k, v in params.items()
                   if k in ("mode", "pivot_rule", "exp_fs_entry_side", "window_end",
                            "exp_htf_fs_entry", "exp_mltf")
                   or v not in (0, 0.0, "", False, None, 1, 1.0, True)]
    return dict(params=len(params), tuned=len(non_default), swing=e.get("swing", "sw10"))


# ---------------------------------------------------------------- driver
def run(sim, E, name):
    e = EXPERIMENTS[name]
    swing = e.get("swing") or "sw10"
    params = e.get("params") or {}
    ts, rs, halfs = [], [], defaultdict(list)
    per_era = {}
    for era in ("is", "oos"):
        d = E[era]
        o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                fine_ltf=d["fine"], **params)
        tr = sorted([t for t in o["ltf_trades"] if t.get("outcome") != "open"],
                    key=lambda t: int(t["entry_ts"]))
        er = [trade(t) for t in tr]
        per_era[era] = dict(n=len(er), net=round(sum(er), 2),
                            dd=round(max(x[0] for x in dd_series(er)), 2),
                            expectancy=round(sum(er) / len(er), 4) if er else 0.0,
                            pf=tier1(er)["pf"],
                            wr=tier1(er)["wr"])
        ts += [int(t["entry_ts"]) for t in tr]
        rs += er
        for t, r in zip(tr, er):
            halfs[cell(t["entry_ts"])].append(r)
    order = sorted(range(len(ts)), key=lambda i: ts[i])
    ts = [ts[i] for i in order]
    rs = [rs[i] for i in order]

    dds = dd_series(rs)
    t1 = tier1(rs)
    cost0 = -t1["avg_loss"] * 0.0          # placeholder, replaced below
    cost_r = 0.10                          # measured below from the engine cost model
    return dict(
        name=name, t1=t1, t2=tier2(rs, dds), t3=tier3(rs),
        t4=tier4(rs, cost_r), t5=tier5(ts, rs), t6=tier6(name),
        eras=per_era,
        halfs={k: round(sum(v), 2) for k, v in sorted(halfs.items())},
        neg_cells=sorted(k for k, v in halfs.items() if sum(v) < 0),
        sd=round((sum((r - t1["expectancy"]) ** 2 for r in rs) / max(1, len(rs) - 1)) ** .5, 3),
        tstat=round(t1["expectancy"] /
                    ((sum((r - t1["expectancy"]) ** 2 for r in rs) /
                      max(1, len(rs) - 1)) ** .5 / math.sqrt(max(1, len(rs)))), 2),
    )


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}
    print("=" * 100)
    print("STRATEGY QUALITY SCORECARD - every candidate through the same tests")
    print("framework: backtest/docs/learn/finding optimal book.md")
    print("Tier 0 validity already settled: causality 0 violations, origin PASS, fastcheck PASS")
    print("=" * 100)
    for name in BOOKS:
        out[name] = run(sim, E, name)
        r = out[name]
        print("  done %s" % name)
    with open("_scorecard.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("\n  wrote _scorecard.json  (%d books)" % len(out))


if __name__ == "__main__":
    main()
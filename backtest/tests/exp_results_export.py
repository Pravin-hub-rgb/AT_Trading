"""Unified results export for the /results page.

Writes _results.json: every top book with (a) the scorecard tiers, (b) the full
equity lens including ulcer/sortino/calmar/underwater/recovery, (c) the per-trade
equity series the page charts, (d) a normalised position mode, and (e) category
tags.

WHY A COMMITTED ARTIFACT AND NOT A LIVE ENDPOINT. The research is finished and
every pin is reproduced by exp_fastcheck. A page that recomputed from the engine
would eventually disagree with the docs by a rounding step and there would be no
way to tell which was right. This runs once, the numbers are the same numbers the
docs quote, and the file is regenerated with one command:

    python backtest/tests/exp_results_export.py

POSITION MODE IS NORMALISED HERE BECAUSE THE REGISTRY IS INCONSISTENT. It records
the same idea three ways across books: max_positions=0 on sig books,
exp_mltf=True on champ books, and neither on others. Engine defaults differ per
knob, so an absent field does NOT mean single-position - it means "inherit the
default", and the caller has to resolve that. Rather than guess, `position_mode`
is only set when the book states it, and `position_explicit` records whether it
did. The page shows "inherit" honestly instead of a wrong "single".

Smoothness metrics are NOT reimplemented here. equity_quality() in
exp_equity_quality.py already computes ulcer, sortino, calmar, uw_pct, max_uw and
recovery, and a second implementation of ulcer that disagreed with the first by a
rounding step would be a bug nobody could find.
"""
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_equity_quality import equity_quality           # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402

N_MULTI, N_SIG = 15, 10
# years of data per era, for equity_quality's per-year normalisation
YEARS = {"is": 3.67, "oos": 2.0}
DD_BUDGET = 29.0          # the owner's stated budget; tags are relative to it


def cell(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def position_mode(entry):
    p = entry.get("params") or {}
    if p.get("max_positions") == 0 or p.get("exp_mltf") is True:
        return "multi", True
    if p.get("max_positions") == 1:
        return "single", True
    return "inherit", False


def rank_key(entry):
    """Rank books by the registry's own pins - net across both eras. The pins are
    already verified, so this selects without re-running anything."""
    p = entry.get("pins") or {}
    if not p.get("n"):
        return None
    return (p.get("net", 0.0) or 0.0) + (p.get("oos_net", 0.0) or 0.0)


def select():
    sig, multi = [], []
    for k, e in EXPERIMENTS.items():
        if not isinstance(e, dict) or not k.startswith("fsent"):
            continue
        r = rank_key(e)
        if r is None:
            continue
        (sig if k.startswith("fsent_sig") else multi).append((r, k))
    sig.sort(reverse=True)
    multi.sort(reverse=True)
    # the shipping book always ships, whatever its rank
    names = [k for _r, k in multi[:N_MULTI]]
    if "fsent_champ_long" not in names:
        names.append("fsent_champ_long")
    return names, [k for _r, k in sig[:N_SIG]]


def series_of(rs):
    cum = pk = 0.0
    out = []
    for r in rs:
        cum += r
        pk = max(pk, cum)
        out.append((round(r, 3), round(cum, 2), round(pk - cum, 2)))
    return out


def tags_for(m):
    """Category tags, NOT one composite score. The owner asked for tags so a
    single book can be strong on some axes and weak on others and stay visible."""
    t = []
    if not m["neg_cells"]:
        t.append("zero-negative")
    if m["max_dd"] < DD_BUDGET * 0.6:
        t.append("low-DD")
    if m["longest_underwater"] < 30:
        t.append("short-underwater")
    if m["top5_contrib"] < 80:
        t.append("low-tail")
    if m["cost_2x"] > 0:
        t.append("cost-2x-safe")
    else:
        t.append("2x-cost-death")
    if m["oos_sign"] and m["is_sign"]:
        t.append("consistent-eras")
    if m["worst_roll50"] > 0:
        t.append("never-negative-50")
    return t


def build(sim, E, name):
    e = EXPERIMENTS[name]
    swing = e.get("swing") or "sw10"
    params = e.get("params") or {}
    per_era_trades = {}
    for era in ("is", "oos"):
        d = E[era]
        o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                fine_ltf=d["fine"], **params)
        tr = sorted([t for t in o["ltf_trades"] if t.get("outcome") != "open"],
                    key=lambda t: int(t["entry_ts"]))
        per_era_trades[era] = (tr, [net_r([t]) for t in tr])

    # ONE convention for every curve metric: both eras merged in calendar order.
    # Taking ulcer from the OOS leg while taking max_dd from the merged curve would
    # put two different books in one column and make the page a liar by accident.
    merged = sorted(per_era_trades["is"][0] + per_era_trades["oos"][0],
                    key=lambda t: int(t["entry_ts"]))
    lens = equity_quality(merged, YEARS["is"] + YEARS["oos"])

    allts = [int(t["entry_ts"]) for t in merged]
    allrs = [net_r([t]) for t in merged]

    n = len(allrs)
    net = sum(allrs)
    wins = [r for r in allrs if r > 0]
    loss = [r for r in allrs if r <= 0]
    gp, gl = sum(wins), -sum(loss)
    sortedrs = sorted(allrs, reverse=True)

    # drawdown / underwater from the combined curve
    cum = pk = 0.0
    dds = []
    peak_i = 0
    for i, r in enumerate(allrs):
        cum += r
        if cum > pk:
            pk = cum
            peak_i = i
        dds.append(pk - cum)
    runs, cur = [], 0
    for d in dds:
        if d > 1e-9:
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)

    def worst_roll(k):
        if n < k:
            return 0.0
        c = sum(allrs[:k])
        m = c
        for i in range(k, n):
            c += allrs[i] - allrs[i - k]
            m = min(m, c)
        return round(m, 2)

    def tail_at(pct):
        k = max(1, int(round(n * pct / 100.0)))
        cut = sum(sortedrs[:k])
        return dict(k=k, contrib=round(100.0 * cut / net, 1) if net else None,
                    remains=round(100.0 * (net - cut) / net, 1) if net else None)

    per_h = defaultdict(list)
    for t, r in zip(allts, allrs):
        per_h[cell(t)].append(r)
    halfs = {k: round(sum(v), 2) for k, v in sorted(per_h.items())}
    neg = sorted(k for k, v in per_h.items() if sum(v) < 0)

    sd = (sum((r - net / n) ** 2 for r in allrs) / max(1, n - 1)) ** .5
    is_e = per_era_trades["is"][1]
    oos_e = per_era_trades["oos"][1]
    eis = sum(is_e) / len(is_e) if is_e else 0.0
    eoos = sum(oos_e) / len(oos_e) if oos_e else 0.0

    k5 = tail_at(5)
    m = dict(
        name=name,
        desc=(e.get("desc") or "").strip(),
        family="sig" if name.startswith("fsent_sig") else "multi",
        swing=swing,
        engine=e.get("engine"),
        n=n, net=round(net, 2),
        expectancy=round(net / n, 4) if n else 0.0,
        pf=round(gp / gl, 3) if gl > 0 else None,
        wr=round(100.0 * len(wins) / n, 1) if n else 0.0,
        avg_win=round(gp / len(wins), 3) if wins else 0.0,
        avg_loss=round(-gl / len(loss), 3) if loss else 0.0,
        median_r=round(sorted(allrs)[n // 2], 3) if n else 0.0,
        max_win=round(max(allrs), 2) if allrs else 0.0,
        max_loss=round(min(allrs), 2) if allrs else 0.0,
        sd=round(sd, 3),
        tstat=round((net / n) / (sd / math.sqrt(n)), 2) if n and sd else 0.0,
        # risk
        max_dd=round(max(dds), 2) if dds else 0.0,
        net_to_dd=round(net / max(dds), 2) if dds and max(dds) > 0 else None,
        dd_pct_of_net=round(100.0 * max(dds) / net, 1) if dds and net > 0 else None,
        longest_underwater=max(runs) if runs else 0,
        n_dd_periods=len(runs),
        # smoothness - from equity_quality, not reimplemented
        ulcer=round(lens["ulcer"], 3),
        sortino=round(lens["sortino"], 3),
        calmar=round(lens["calmar"], 3),
        uw_pct=round(lens["uw_pct"], 1),
        recovery=round(lens["recovery"], 1),
        max_streak=round(lens["max_streak"], 1),
        # consistency
        worst_roll20=worst_roll(20),
        worst_roll50=worst_roll(50),
        worst_roll100=worst_roll(100),
        # tail
        top1_contrib=tail_at(1)["contrib"],
        top5_contrib=k5["contrib"],
        top10_contrib=tail_at(10)["contrib"],
        cap10_net=round(sum(min(r, 10.0) for r in allrs), 2),
        # costs
        cost_1x=round(net, 2),
        cost_2x=round(sum(r - 0.10 for r in allrs), 2),
        cost_3x=round(sum(r - 0.20 for r in allrs), 2),
        # eras
        is_net=round(sum(is_e), 2), is_n=len(is_e), is_exp=round(eis, 4),
        oos_net=round(sum(oos_e), 2), oos_n=len(oos_e), oos_exp=round(eoos, 4),
        retention=round(100.0 * eoos / eis, 1) if eis else None,
        is_sign=sum(is_e) > 0, oos_sign=sum(oos_e) > 0,
        # periods
        halfs=halfs, neg_cells=neg,
        years_positive=lens.get("pos_year_pct"),
        # complexity
        params=len(params),
        tuned=len([1 for k2, v2 in params.items()
                   if k2 in ("mode", "pivot_rule", "exp_fs_entry_side", "window_end",
                             "exp_htf_fs_entry", "exp_mltf")
                   or v2 not in (0, 0.0, "", False, None, 1, 1.0, True)]),
        series=series_of(allrs),
    )
    mode, explicit = position_mode(e)
    m["position_mode"] = mode
    m["position_explicit"] = explicit
    m["tags"] = tags_for(m)
    return m


def load_null_audit():
    """Pull the paired-permutation p-values in from exp_null_audit.py.

    These are the only numbers in the family that answer the question a candidate
    actually faces - is this arm's CHOICE OF TRADES better than its parent's, or a
    reshuffle of the same trades - so they belong on the comparison page. Without
    them the page ranks books on net and drawdown, which is exactly what let a
    +917R book and a +33R book look like peers until a null separated them.

    The audit is optional. If it has not been run the page still works, it just
    shows no significance column - which is honest, because an absent p-value and a
    p-value of 0.5 are not the same thing and only one of them is a measurement.
    """
    try:
        with open("_null_audit.json", "r", encoding="utf-8") as f:
            audit = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {}
    for r in audit.get("rows", []):
        b = out.setdefault(r["book"], {})
        b[r["era"]] = dict(dnet=r.get("dnet"), p=r.get("p"), sig=r.get("sig"))
    return out


def main():
    sim = build_family_module()
    from exp_signal_metrics import load_era
    E = {e: load_era(e) for e in ("is", "oos")}
    nulls = load_null_audit()
    multi, sig = select()
    names = multi + sig
    print("selected %d multi + %d sig = %d books" % (len(multi), len(sig), len(names)))
    out = {"generated_from": "exp_results_export.py",
           "dd_budget": DD_BUDGET,
           "years": YEARS,
           "books": []}
    for i, n in enumerate(names, 1):
        m = build(sim, E, n)
        na = nulls.get(n, {})
        m["null_p_is"] = (na.get("is") or {}).get("p")
        m["null_p_oos"] = (na.get("oos") or {}).get("p")
        m["null_dnet_is"] = round((na.get("is") or {}).get("dnet") or 0.0, 2)
        m["null_dnet_oos"] = round((na.get("oos") or {}).get("dnet") or 0.0, 2)
        m["null_sig_is"] = bool((na.get("is") or {}).get("sig"))
        m["null_sig_oos"] = bool((na.get("oos") or {}).get("sig"))
        m["null_sig"] = m["null_sig_is"] or m["null_sig_oos"]
        out["books"].append(m)
        print("  %2d/%d  %-34s n=%4d net=%+8.1f dd=%5.2f ulcer=%5.2f  "
              "p(IS/OOS)=%s%s  %s"
              % (i, len(names), n, m["n"], m["net"], m["max_dd"], m["ulcer"],
                 ("%.4f" % m["null_p_is"]) if m["null_p_is"] is not None else "n/a",
                 ("/%.4f" % m["null_p_oos"]) if m["null_p_oos"] is not None else "",
                 "*** SIGNIFICANT" if m["null_sig"] else ""))
    with open("_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    import os
    print("\nwrote _results.json (%.2f MB)" % (os.path.getsize("_results.json") / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
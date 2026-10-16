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

# DRAWDOWN BUDGET - NONE. THERE IS NO FIXED NUMBER.
#
# This started as a flat 29.0R ceiling, which was wrong twice over. It is now
# removed rather than replaced by another invented constant.
#
# Removing it is the owner's call and it is what the risk-adjustment review said
# to do: "Koi universal number nahi hai. Main bina context ke ye nahi bolunga
# ki 10% DD good hai aur 20% bad." A ceiling that disqualifies a book for its
# drawdown also disqualifies it for being large - fsent_champ_long_htf15_htffs
# was rejected at 29.76R, which is 2.7% of its net, and passed
# fsent_both_trail_half at 26.13R, which is 39.4%.
#
# What replaces it is not a better number, it is more axes and no verdict:
#   net_to_dd          net R per unit of drawdown
#   dd_pct_of_peak     drawdown against the equity peak it fell from (scale free)
#   dd_days            how long the water was under it
#   recover_days       how long to get the peak back
#   worst_3m/6m/12m    calendar-time bad stretches
#   worst_roll20/50/100 trade-count bad stretches
#   dd_pct_1 / _2      the same drawdown as a share of account at 1% and 2% risk
#
# DD_BUDGET_R_LEGACY is kept only so an export can still say what the old rule
# would have said. It gates nothing.
DD_BUDGET_R_LEGACY = 29.0


def dd_flags(m):
    """No percentage gate any more. The legacy verdict is reported, not applied."""
    return (m["dd_pct_of_peak"], m["max_dd"] >= DD_BUDGET_R_LEGACY)


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


def is_sig(entry):
    """Is this book one-position-at-a-time? Asked of the PARAMS, never the name.

    Was `k.startswith("fsent_sig")`, which mis-filed four registered books:

        fsent_sig_multi        name says sig, max_positions=0
        fsent_sig_multi_htffs  name says sig, max_positions=0
        fsent_sig_multi_acc    name says sig, max_positions=0
        fsent_both_trail_half  name says multi, max_positions=1

    The first three are multi books whose names carry the word "multi", and the
    exporter filed all three under sig purely because they start with fsent_sig.
    That is the same class of mistake as exp_results_export.py's own position_mode
    helper below exists to avoid, and BASELINE.md:63 is explicit that comparing a
    signal book against a multi-position book is off by a hundred R. A book named
    for the mechanism it uses is not evidence of how many positions it holds.

    max_positions is also the right key because it is the one the engine reads.
    1 = serial, 0 = concurrent.
    """
    p = entry.get("params") or {}
    return p.get("max_positions") == 1


def select():
    sig, multi = [], []
    for k, e in EXPERIMENTS.items():
        if not isinstance(e, dict) or not k.startswith("fsent"):
            continue
        r = rank_key(e)
        if r is None:
            continue
        (sig if is_sig(e) else multi).append((r, k))
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
    if m["dd_pct_of_peak"] < 3.0:
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
    peak_r = 0.0
    for i, r in enumerate(allrs):
        cum += r
        if cum > pk:
            pk = cum
            peak_i = i
        if cum > peak_r:
            peak_r = cum
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

    def roll_prof(k):
        """Share of k-trade windows that ended profitable."""
        if n < k:
            return 0.0
        c = sum(allrs[:k])
        pos = 1 if c > 0 else 0
        for i in range(k, n):
            c += allrs[i] - allrs[i - k]
            if c > 0:
                pos += 1
        return 100.0 * pos / (n - k + 1)

    def tail_at(pct):
        k = max(1, int(round(n * pct / 100.0)))
        cut = sum(sortedrs[:k])
        return dict(k=k, contrib=round(100.0 * cut / net, 1) if net else None,
                    remains=round(100.0 * (net - cut) / net, 1) if net else None)

    per_h = defaultdict(list)
    for t, r in zip(allts, allrs):
        per_h[cell(t)].append(r)
    halfs = {k: round(sum(v), 2) for k, v in sorted(per_h.items())}

    # A HALF-YEAR THAT HAS NOT FINISHED IS NOT A HALF-YEAR.
    #
    # 2026-H2 is Jul-Dec and this export was generated on 2026-10-15, so every
    # book was being judged on roughly 3.5 months of a 6-month period. Counting
    # it put a negative mark on books for a period they had barely lived
    # through: all four serial books in the shortlist carried their ONLY
    # negative half-year there, and dropping it leaves them at zero negatives.
    # 2026-H1 is complete and stays in.
    #
    # A cell is counted only if the whole period is behind the data. The cutoff
    # is derived from the last trade's own timestamp rather than hardcoded, so
    # this keeps working as the data grows instead of needing a date edit.
    data_end = max(int(t["exit_ts"]) for t in merged) if merged else 0
    end_dt = datetime.fromtimestamp(data_end, tz=timezone.utc) if data_end else None

    def period_complete(key):
        if end_dt is None:
            return True
        y, half = key.split("-")
        y = int(y)
        half = 1 if half.endswith("1") else 2
        last_month = 6 if half == 1 else 12
        # period is complete once the data reaches the END of its final month
        return (y, last_month) <= (end_dt.year, end_dt.month)

    neg = sorted(k for k, v in per_h.items()
                 if sum(v) < 0 and period_complete(k))
    partial = sorted(k for k in per_h if not period_complete(k))

    # Calendar-time drawdown shape.
    #
    # TWO PASSES ON PURPOSE, because the single-pass version was wrong and gave
    # 1014 and 1160 days to books whose equity curve never spends that long
    # under water. It measured the first recovery against the DEEPEST trough,
    # which may not have happened yet at that point in the scan, so the base
    # moved underneath it and the result was the gap between two unrelated
    # points. The owner caught it by looking at the equity curve on /results.
    #
    # Pass 1 finds the deepest drawdown and the exact peak and trough that made
    # it. Pass 2 asks a single question about that one drawdown: how long from
    # its peak to its trough, and how long from that trough until equity was
    # back at that peak. Both are about ONE episode, so neither can borrow a
    # number from a different one.
    cum = pk = 0.0
    pk_ts = None
    worst_dd = 0.0
    dd_peak_ts = dd_peak_val = dd_trough_ts = None
    dd_trough_i = None
    dd_trough_val = 0.0
    for i, (t, r) in enumerate(zip(merged, allrs)):
        cum += r
        ts = int(t["exit_ts"])
        if cum > pk:
            pk = cum
            pk_ts = ts
        else:
            d = pk - cum
            if d > worst_dd:
                worst_dd = d
                dd_peak_ts = pk_ts
                dd_peak_val = pk
                dd_trough_ts = ts
                dd_trough_i = i
                dd_trough_val = cum

    dd_days = 0.0
    recover_days = None
    if worst_dd > 0 and dd_peak_ts is not None and dd_trough_ts is not None:
        dd_days = (dd_trough_ts - dd_peak_ts) / 86400.0
        # Walk forward FROM THE TROUGH, by list position, carrying the equity
        # level the trough actually left.
        #
        # Two bugs lived here and both are now tested in exp_dd_recovery_test.py.
        #
        # The first walked the whole list asking "is this trade's exit_ts after
        # the trough". merged is sorted by ENTRY time so its exit times are NOT
        # monotonic, and a trade sitting earlier in the list but closing later
        # satisfied that test - at which point equity was still near the peak and
        # the condition matched immediately. That is how a book that recovered two
        # rows after its worst drawdown reported 1064 days.
        #
        # The second started cum at zero, so it was comparing a running total
        # that had not yet reached the peak against a peak value it would reach
        # later, and returned None for every book.
        cum = dd_trough_val
        for i in range(dd_trough_i + 1, len(merged)):
            cum += allrs[i]
            if cum >= dd_peak_val - 1e-9:
                recover_days = (int(merged[i]["exit_ts"]) - dd_trough_ts) // 86400
                break

    # EVERY drawdown, not just the worst one.
    #
    # recover_days alone answers one question about one episode. The review asked
    # for five: the longest, the median, the 90th percentile, what share of
    # drawdowns ever recovered, and how long the book has been unrecovered as of
    # the last bar. A book can have a good worst case and a bad distribution, and
    # the reverse, so neither number stands alone.
    #
    # One drawdown is one peak-to-recovery period. Consecutive dips inside one
    # prolonged underwater stretch are NOT counted separately - the review was
    # explicit that splitting them "artificially flatters recovery quality". So a
    # drawdown opens when equity first falls below a peak and closes only when
    # that same peak is regained.
    dd_episodes = []          # (peak_ts, trough_ts, trough_val, peak_val, rec_ts)
    pk2 = -1e18
    pk2_ts = None
    open_peak_ts = None
    open_peak_val = None
    trough_ts = None
    trough_val = None
    cum = 0.0
    for t, r in zip(merged, allrs):
        cum += r
        ts = int(t["exit_ts"])
        if cum > pk2:
            # a new high: any open drawdown is now recovered at this bar
            if open_peak_ts is not None:
                dd_episodes.append((open_peak_ts, trough_ts, trough_val,
                                    open_peak_val, ts))
                open_peak_ts = None
            pk2 = cum
            pk2_ts = ts
        else:
            if open_peak_ts is None:
                open_peak_ts = pk2_ts
                open_peak_val = pk2
                trough_ts = ts
                trough_val = cum
            elif cum < trough_val:
                trough_ts = ts
                trough_val = cum
    if open_peak_ts is not None:
        # still unrecovered at the end of the data
        dd_episodes.append((open_peak_ts, trough_ts, trough_val, open_peak_val, None))

    recs = sorted((e[4] - e[1]) // 86400 for e in dd_episodes if e[4] is not None)
    n_open = sum(1 for e in dd_episodes if e[4] is None)
    n_eps = len(dd_episodes)

    def _pct(vals, q):
        if not vals:
            return None
        i = min(int(len(vals) * q), len(vals) - 1)
        return vals[i]

    med_rec = _pct(recs, 0.5)
    p90_rec = _pct(recs, 0.9)
    pct_recovered = (100.0 * len(recs) / n_eps) if n_eps else 100.0
    # how long the LAST bar has been below its own peak
    current_underwater = None
    if n_open:
        current_underwater = (int(merged[-1]["exit_ts"]) - dd_episodes[-1][1]) // 86400 if merged else None
    # bands, from the review. Screening labels, not pass/fail.
    def band(d):
        if d is None:
            return "unresolved"
        if d <= 7:
            return "fast"
        if d <= 30:
            return "manageable"
        if d <= 90:
            return "prolonged"
        if d <= 180:
            return "serious"
        return "major"

    # worst N-month calendar windows, because a 20-trade rolling window answers
    # a different question than "was there a bad quarter".
    def worst_window(months):
        pts = [(int(t["exit_ts"]), r) for t, r in zip(merged, allrs)]
        if not pts:
            return None
        first = datetime.fromtimestamp(pts[0][0], tz=timezone.utc)
        best = None
        j = 0
        for i in range(len(pts)):
            while j < len(pts):
                d0 = datetime.fromtimestamp(pts[j][0], tz=timezone.utc)
                if (d0.year - first.year) * 12 + (d0.month - first.month) >= months:
                    break
                j += 1
            s = sum(r for _ts, r in pts[i:j])
            if best is None or s < best:
                best = s
        return round(best, 2) if best is not None else None

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
        # DRAWDOWN AS A PERCENTAGE. The owner was right that a bare R ceiling is
        # not comparable across books of different size: 29.62R on a book that
        # ended at +295R and 29.62R on one that ended at +1,230R are different
        # things. Industry standard is (equity - peak) / peak, and a percentage
        # needs a position size, so 1% of account per R is stated rather than
        # assumed. Hurst/Ooi/Pedersen put trend following at 20-40% max DD.
        dd_pct_1=round(max(dds), 2) if dds else 0.0,
        dd_pct_2=round(max(dds) * 2.0, 2) if dds else 0.0,
        dd_pct_of_peak=round(100.0 * max(dds) / peak_r, 2) if dds and peak_r > 0 else None,
        dd_recover_pct=(round(100.0 * max(dds) / (100.0 - max(dds)), 1)
                        if dds and max(dds) < 100 else None),
        # ROLLING PROFITABILITY. A book can make money across the whole sample and
        # still bleed inside every 20-trade stretch; since it is held a year at a
        # time, what matters is how many rolling windows are profitable, not just
        # the single worst one.
        roll10_prof_pct=round(roll_prof(10), 1),
        roll20_prof_pct=round(roll_prof(20), 1),
        roll50_prof_pct=round(roll_prof(50), 1),
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
        halfs=halfs, neg_cells=neg, partial_cells=partial,
        years_positive=lens.get("pos_year_pct"),
        # calendar-time drawdown shape. max_dd in R is the primary measure here
        # because the engine risks a FIXED amount per R, not a share of equity -
        # r_multiple = move/risk in unified.py. So R IS the account unit and
        # these are how long that unit was under water.
        dd_days=round(dd_days, 1),
        recover_days=recover_days,
        recover_band=band(recover_days),
        # The five numbers the review asked for. recover_days answers about ONE
        # drawdown; these describe the whole distribution.
        dd_episodes=n_eps,
        dd_episodes_recovered=len(recs),
        pct_dd_recovered=round(pct_recovered, 1),
        med_recover_days=med_rec,
        p90_recover_days=p90_rec,
        current_underwater_days=current_underwater,
        unrecovered_now=(n_open > 0),
        worst_3m=worst_window(3),
        worst_6m=worst_window(6),
        worst_12m=worst_window(12),
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
           "dd_budget": None,              # no universal ceiling exists
           "dd_budget_note": "no fixed drawdown limit is applied; see net_to_dd, dd_pct_of_peak, dd_days, recover_days, worst_3m/6m/12m",
           "dd_budget_r_legacy": DD_BUDGET_R_LEGACY,
           "years": YEARS,
           "books": []}
    for i, n in enumerate(names, 1):
        m = build(sim, E, n)
        over_pct, over_r = dd_flags(m)
        m["over_dd_budget_r_legacy"] = over_r
        na = nulls.get(n, {})
        m["null_p_is"] = (na.get("is") or {}).get("p")
        m["null_p_oos"] = (na.get("oos") or {}).get("p")
        m["null_dnet_is"] = round((na.get("is") or {}).get("dnet") or 0.0, 2)
        m["null_dnet_oos"] = round((na.get("oos") or {}).get("dnet") or 0.0, 2)
        m["null_sig_is"] = bool((na.get("is") or {}).get("sig"))
        m["null_sig_oos"] = bool((na.get("oos") or {}).get("sig"))
        m["null_sig"] = m["null_sig_is"] or m["null_sig_oos"]
        out["books"].append(m)
        print("  %2d/%d  %-34s n=%4d net=%+8.1f dd=%5.2f (%.1f%% of peak) N/DD=%5.1f"
              "  ulcer=%5.2f  p(IS/OOS)=%s%s  %s"
              % (i, len(names), n, m["n"], m["net"], m["max_dd"],
                 m["dd_pct_of_peak"], m["net_to_dd"], m["ulcer"],
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
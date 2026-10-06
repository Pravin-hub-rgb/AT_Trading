"""Strategy Quality Scorecard for the SIGNAL plane, per
backtest/docs/learn/finding optimal book.md.

Gate first (from the committed _signal_metrics.json): both-eras positive,
n >= 30 in both eras. Then run the engine for just those books and compute
the trade-level scorecard: OOS retention, DD quality, worst rolling windows,
tail dependence (removal + caps + top-X% contribution), winner spacing,
profitability-through-time, and simplicity (number of non-default knobs).

Output: _sig_scorecard.json + _sig_scorecard.md
Run: python -u _sig_scorecard.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

from exp_signal_metrics import load_era, quarantine_reason, signal_books  # noqa: E402
from exp_full_metrics import compute  # noqa: E402


def closed(tr):
    return [t for t in tr if t.get("outcome") != "open"]


def era_nets(tr, net_r):
    return [net_r([t]) for t in tr]


def removal(sorted_rs, k):
    if not sorted_rs:
        return None, None
    rem = sum(sorted_rs[:-k]) if k else sum(sorted_rs)
    orig = sum(sorted_rs)
    return round(rem, 1), round(100.0 * rem / orig, 1) if orig else None


def capped(rs, cap):
    return sum(min(r, cap) for r in rs)


def top_pct_contrib(sorted_rs, pct):
    n = len(sorted_rs)
    k = max(1, round(n * pct))
    orig = sum(sorted_rs)
    return round(100.0 * sum(sorted_rs[-k:]) / orig, 1) if orig else None


def dd_duration_table(rs, dates):
    peak = None
    dds = []
    cur = 0.0
    eq = 0.0
    high = 0.0
    for r in rs:
        eq += r
        high = max(high, eq)
        cur = high - eq
        dds.append(cur)
    dur = 0
    max_dur = 0
    in_dd = False
    for d in dds:
        if d > 0:
            dur += 1
            max_dur = max(max_dur, dur)
        else:
            dur = 0
    return max_dur


def worst_rolling(rs, w):
    if len(rs) < w:
        return None
    return round(min(sum(rs[i:i + w]) for i in range(len(rs) - w + 1)), 1)


def winner_gaps(rs, thresh):
    idx = [i for i, r in enumerate(rs) if r >= thresh]
    gaps = []
    for a, b in zip(idx, idx[1:]):
        gaps.append(b - a)
    if not gaps:
        return None, None, None
    gaps.sort()
    return gaps[len(gaps) // 2], gaps[int(len(gaps) * 0.9)] if len(gaps) >= 10 else gaps[-1], gaps[-1]


def profitable_years(rs, dates):
    years = {}
    for r, d in zip(rs, dates):
        y = str(d)[:4]
        years[y] = years.get(y, 0.0) + r
    if not years:
        return 0.0, 0
    good = sum(1 for v in years.values() if v > 0)
    return round(100.0 * good / len(years), 1), len(years)


def knob_count(params, default_keys):
    n = 0
    for k, v in params.items():
        if k in default_keys:
            continue
        n += 1
    return n


def main() -> int:
    from run_experiment import BP, net_r, get_swings
    from exp_tf_family import build_family_module
    from experiment_registry import EXPERIMENTS

    metrics = json.loads((ROOT / "backtest/tests/_signal_metrics.json").read_text())
    books, skipped = signal_books()
    gate = []
    for b in books:
        is_m = metrics["configs"]["is"].get(b, {})
        oos_m = metrics["configs"]["oos"].get(b, {})
        if not isinstance(is_m, dict) or not isinstance(oos_m, dict):
            continue
        if (is_m.get("n") or 0) >= 30 and (oos_m.get("n") or 0) >= 30 \
                and (is_m.get("net") or 0) > 0 and (oos_m.get("net") or 0) > 0:
            gate.append(b)
    print("gate: %d books (both-eras positive, n>=30 both eras)" % len(gate), flush=True)

    sim = build_family_module()
    rows = []
    for era in ("is", "oos"):
        print("=== %s ===" % era.upper(), flush=True)
        data = load_era(era)
        for i, key in enumerate(gate, 1):
            cfg = EXPERIMENTS[key]
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            sw = get_swings(data, cfg.get("swing") or "sw10")
            try:
                out = sim(data["c1h"], sw, data["c15"], data["sw15"],
                          fine_ltf=data["fine"], **p)
            except Exception as e:
                print("  ERR %s %s" % (key, e), flush=True)
                continue
            tr = out["ltf_trades"] if isinstance(out, dict) else out
            tr = closed(tr)
            rs = [net_r([t]) for t in tr]
            ds = [t.get("entry_date", "") for t in tr]
            rows.append((key, era, rs, ds, cfg))
            print("  [%d/%d] %s %s n=%d net=%+.1f" % (i, len(gate), era, key, len(rs), sum(rs)),
                  flush=True)

    # assemble per-book scorecard
    by = {}
    for key, era, rs, ds, cfg in rows:
        by.setdefault(key, {})[era] = (rs, ds, cfg)

    cards = []
    for key, e in by.items():
        is_rs, is_ds, cfg = e["is"]
        oos_rs, oos_ds, cfg = e["oos"]
        is_m = metrics["configs"]["is"][key]
        oos_m = metrics["configs"]["oos"][key]
        is_sorted = sorted(is_rs)
        oos_sorted = sorted(oos_rs)

        def metric_for(rs, dates, m):
            sr = sorted(rs)
            card = {
                "n": len(rs), "net": round(sum(rs), 1),
                "avgR": round(sum(rs) / len(rs), 3) if rs else None,
                "wr": m.get("wr"), "pf": m.get("pf"), "max_dd": m.get("max_dd"),
                "ulcer": m.get("ulcer"), "calmar": m.get("calmar"),
                "sortino": m.get("sortino"), "dd_dur": m.get("dd_dur"),
                "pos_month_pct": m.get("pos_month_pct"),
                "worst_month": m.get("worst_month"),
                "max_streak": m.get("max_streak"),
                "top5": m.get("top5_share_pct"),
                "median": m.get("median"), "trimmed": m.get("trimmed"),
                "worst20": worst_rolling(rs, 20), "worst50": worst_rolling(rs, 50),
                "worst100": worst_rolling(rs, 100),
                "med_gap_3R": winner_gaps(rs, 3.0)[0],
                "max_gap_3R": winner_gaps(rs, 3.0)[2],
                "max_gap_10R": winner_gaps(rs, 10.0)[2],
                "pos_year_pct": profitable_years(rs, dates)[0],
                "rem_top1": removal(sr, 1)[1], "rem_top3": removal(sr, 3)[1],
                "rem_top5": removal(sr, 5)[1], "rem_top10": removal(sr, 10)[1],
                "cap5": round(100 * capped(rs, 5) / sum(rs), 1) if sum(rs) else None,
                "cap10": round(100 * capped(rs, 10) / sum(rs), 1) if sum(rs) else None,
                "cap20": round(100 * capped(rs, 20) / sum(rs), 1) if sum(rs) else None,
                "top1pct": top_pct_contrib(sr, 0.01),
                "top5pct": top_pct_contrib(sr, 0.05),
                "max_win": round(max(rs), 1) if rs else None,
            }
            return card

        is_card = metric_for(is_rs, is_ds, is_m)
        oos_card = metric_for(oos_rs, oos_ds, oos_m)
        card = {
            "book": key,
            "swing": cfg.get("swing") or "sw10",
            "knobs": len(cfg.get("params") or {}),
            "is": is_card, "oos": oos_card,
            "expectancy_retention": round((oos_m["avgR"] / is_m["avgR"]), 2) if is_m.get("avgR") else None,
            "pf_retention": round((oos_m["pf"] / is_m["pf"]), 2) if (is_m.get("pf") and oos_m.get("pf")) else None,
            "dd_expansion": round((oos_m["max_dd"] / is_m["max_dd"]), 2) if (is_m.get("max_dd") and oos_m.get("max_dd")) else None,
        }
        cards.append(card)

    # Rank per doc priority: validity(all pass) -> OOS net (keeps it in) ->
    # expectancy retention -> PF retention -> DD expansion -> OOS ulcer ->
    # OOS worst50 -> top5 concentration -> cap10 remaining -> pos_month_pct
    def score(c):
        oos = c["oos"]
        return (
            -(c["expectancy_retention"] or 0),
            -(c["pf_retention"] or 0),
            c["dd_expansion"] or 99,
            oos.get("ulcer") or 99,
            oos.get("worst50") or 0,          # more negative = worse, so sort ascending puts worst last? we want less-worst first
            oos.get("top5") or 999,           # lower tail concentration better
            -(oos.get("cap10") or 0),         # higher remaining better
            -(oos.get("pos_month_pct") or 0),
            c["knobs"],
        )

    cards.sort(key=score)

    out = ROOT / "backtest/tests/_sig_scorecard.json"
    out.write_text(json.dumps(cards, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d cards)" % (out, len(cards)), flush=True)

    lines = []
    lines.append("# SIGNAL PLANE - strategy quality scorecard")
    lines.append("")
    lines.append("Gate: both-eras net>0, n>=30 both eras. Ranked by expectancy "
                 "retention, PF retention, DD expansion, OOS ulcer, worst-50, "
                 "top-5% concentration, cap-10R survival, positive months, knob count.")
    lines.append("")
    hdr = ("| # | book | IS avgR | OOS avgR | expRet | PfRet | DDexp | IS net | OOS net | "
           "OOS PF | OOS DD | ulcer | worst50 | top5% | cap10% | medGap3R | posYr% | knobs |")
    sep = "|".join(["---"] * 18)
    lines.append(hdr)
    lines.append(sep)
    for i, c in enumerate(cards, 1):
        oos = c["oos"]
        lines.append("| %d | `%s` | %.3f | %.3f | %.2f | %s | %s | %+.1f | %+.1f | %s | %s | %s | %s | %s | %s | %s | %s | %d |" % (
            i, c["book"], c["is"]["avgR"], oos["avgR"],
            c["expectancy_retention"], c["pf_retention"], c["dd_expansion"],
            c["is"]["net"], oos["net"],
            ("%.2f" % oos["pf"]) if oos.get("pf") else "-",
            ("%.1f" % oos["max_dd"]) if oos.get("max_dd") else "-",
            ("%.2f" % oos["ulcer"]) if oos.get("ulcer") is not None else "-",
            ("%+.1f" % oos["worst50"]) if oos.get("worst50") is not None else "-",
            ("%.0f" % oos["top5"]) if oos.get("top5") is not None else "-",
            ("%.0f" % oos["cap10"]) if oos.get("cap10") is not None else "-",
            str(oos.get("med_gap_3R")), str(oos.get("pos_year_pct")), c["knobs"]))
    md = ROOT / "backtest/tests/_sig_scorecard.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote %s" % md, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

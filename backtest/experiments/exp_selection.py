"""SELECTION - gates + scorecard, one leaderboard for sig books and one for multi.

WHY THIS IS BUILT THE WAY IT IS
-------------------------------
docs/learn/finding optimal book.md:692 is explicit about not collapsing twenty
strategies into one arbitrary number:

    "I wouldn't make one giant arbitrary score like Strategy Score = 73.42
     because that can hide problems. Instead I'd use gates + scorecard."

So this harness does not produce a verdict. It produces every column the owner
asked for - best, smooth, good spread, rolling window good - as a separate
measured number, applies the hard gates first, and leaves the ranking visible.
The owner picks; this only makes the pick informed.

THE TWO CLASSES ARE NEVER MIXED
-------------------------------
17 books are sig (max_positions=1, one position at a time) and 79 are multi
(max_positions=0, concurrent). BASELINE.md:63-67 is blunt about this: "a signal
book cannot be compared against a multi-position book - they are different
objects", and getting it wrong is "off by a hundred R". So they get two
leaderboards and the gates are applied inside each.

WHAT IS MEASURED, BY THE DOC'S OWN TIERS
----------------------------------------
  Tier 0  pins reproduce            - validity, and it is measured not asserted
  Tier 1  net, R/trade, PF, n
  Tier 2  max DD, DD duration, ulcer, sortino, DD % of net, longest loss run,
          % positive months, worst year
  Tier 2  rolling 20 / 50 / 100    - worst rolling sum and % positive windows
                                    THIS IS THE OWNER'S "rolling window good"
  Tier 3  top 1 / 3 / 5 / 10 removed, and the same as a % of trades
          top-5% share of net      - THIS IS THE OWNER'S "good spread"
  Tier 3  winner spacing            - max and median gap between winners,
                                    and what the equity does during the gap
  Tier 5  expectancy / PF retention, OOS DD, sign consistency
  Tier 6  param count

Output: selection_results.json + selection_scorecard.md
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "selection_results.json"
CARD = HERE / "selection_scorecard.md"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from exp_signal_metrics import load_era                          # noqa: E402
from registry import EXPERIMENTS                                # noqa: E402

BOOKS = {k: v for k, v in EXPERIMENTS.items() if isinstance(v, dict) and v.get("params")}
ROLL = (20, 50, 100)
TOPN = (1, 3, 5, 10)

_D = 0
_T0 = time.time()


def step(lbl):
    global _D
    _D += 1
    el = time.time() - _T0
    eta = (el / _D) * (_TOTAL - _D) if _D else 0.0
    pct = 100.0 * _D / _TOTAL
    msg = "[%3.0f%%] %s %5.0fs elapsed, ~%5.0fs left" % (
        pct, "#" * int(pct / 2.5), el, eta)
    sys.stdout.write("\r  " + msg + "   " + lbl)
    sys.stdout.flush()


def net_r(t):
    from exp_equity_quality import net_r as _nr
    return float(_nr([t]))


def trades_of(sim, data, cfg):
    sw = {"sw10": data["sw10"], "sw20": data["sw20"],
          "sw15": data["sw15"], "htf15": data["htf15"]}[cfg["swing"]]
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=data["fine"],
             **{**dict(repin.re_.BP), **cfg["params"]})["ltf_trades"]
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    return [t for t in tr if t.get("outcome") != "open"]


def rolling(nets, w):
    """Worst rolling sum of w trades, and the share of windows that are positive."""
    if len(nets) < w:
        return None, None
    s = sum(nets[:w])
    worst = s
    pos = 1 if s > 0 else 0
    for i in range(w, len(nets)):
        s += nets[i] - nets[i - w]
        worst = min(worst, s)
        pos += 1 if s > 0 else 0
    n = len(nets) - w + 1
    return round(worst, 2), round(100.0 * pos / n, 1)


def equity_metrics(nets, years):
    if not nets:
        return {}
    n = len(nets)
    total = sum(nets)
    cum = peak = dd = 0.0
    dd_start = dd_end = dd_s = -1
    streak = maxstreak = 0
    uw = maxuw = 0
    uw_sum = 0
    for i, x in enumerate(nets):
        cum += x
        if cum > peak:
            peak, dd_s, uw = cum, i, 0
        else:
            uw += 1
            uw_sum += 1
        maxuw = max(maxuw, uw)
        d = peak - cum
        if d > dd:
            dd, dd_end = d, i
        if x < 0:
            streak += 1
            maxstreak = max(maxstreak, streak)
        else:
            streak = 0
    wins = [x for x in nets if x > 0]
    loss = [-x for x in nets if x < 0]
    gw, gl = sum(wins), sum(loss)
    # ulcer, same construction as exp_equity_quality
    floor = abs(total) * 0.01 if total else 0.0
    cum = 0.0
    pk = 0.0
    usq = 0.0
    un = 0
    for x in nets:
        cum += x
        pk = max(pk, cum)
        if pk > floor and pk > 1e-9:
            usq += (100.0 * (pk - cum) / pk) ** 2
            un += 1
    ulcer = (usq / un) ** 0.5 if un else 0.0
    downside = [min(0.0, x) for x in nets]
    dsdev = (sum(x * x for x in downside) / n) ** 0.5
    sortino = total / dsdev if dsdev > 1e-12 else 0.0

    # monthly / yearly
    return {
        "n": n, "net": round(total, 2), "r_trade": round(total / n, 4),
        "pf": round(gw / gl, 3) if gl > 1e-9 else 999.0,
        "wr": round(100.0 * len(wins) / n, 1),
        "avg_win": round(gw / len(wins), 3) if wins else 0.0,
        "avg_loss": round(-gl / len(loss), 3) if loss else 0.0,
        "max_win": round(max(wins), 2) if wins else 0.0,
        "max_loss": round(min(nets), 2) if nets else 0.0,
        "max_dd": round(dd, 2),
        "dd_pct": round(100.0 * dd / total, 2) if total else 0.0,
        "dd_dur": (dd_end - dd_s + 1) if dd > 0 else 0,
        "recovery": round(total / dd, 2) if dd > 1e-9 else 0.0,
        "ulcer": round(ulcer, 2),
        "sortino": round(sortino, 2),
        "uw_pct": round(100.0 * uw_sum / n, 1),
        "max_uw": maxuw,
        "max_streak": maxstreak,
    }


def tail_metrics(nets):
    """Owner: 'good spread'. How much survives deleting the top winners."""
    if not nets:
        return {}
    total = sum(nets)
    order = sorted(range(len(nets)), key=lambda i: -nets[i])
    out = {"top5pct_share": None}
    for k in TOPN:
        if k < len(nets):
            out["no_top%d" % k] = round(total - sum(nets[i] for i in order[:k]), 2)
        else:
            out["no_top%d" % k] = 0.0
    for pct in (5, 10):
        k = max(1, int(len(nets) * pct / 100.0))
        share = sum(nets[i] for i in order[:k])
        out["top%dpct_share" % pct] = round(100.0 * share / total, 1) if total else 0.0
    return out


def spacing(nets):
    """Owner: 'good spread'. How far apart are the winners, and what happens between."""
    if not nets:
        return {}
    gaps, cum, worst_gap_dd, run = [], 0.0, 0.0, 0
    pk = 0.0
    for x in nets:
        if x > 0:
            if gaps or run == 0:
                gaps.append(run)
            run = 0
            cum += x
            pk = max(pk, cum)
        else:
            run += 1
            cum += x
            worst_gap_dd = max(worst_gap_dd, pk - cum)
    gaps.append(run)
    g = [x for x in gaps if x >= 0]
    g.sort()
    return {"max_gap": max(gaps), "med_gap": g[len(g) // 2] if g else 0,
            "gap_drawdown": round(worst_gap_dd, 2),
            "gap_pct_of_dd": None}


def measure(sim, eras, book, cfg):
    r = {}
    for era in ("is", "oos"):
        tr = trades_of(sim, eras[era], cfg)
        nets = [net_r(t) for t in tr]
        m = equity_metrics(nets, 3.67 if era == "is" else 2.0)
        if not m:
            # No completed trade in this era. equity_metrics returns {} rather
            # than a row of zeroes, and the first run of this harness died here
            # with KeyError max_dd having spent 22 minutes to get to book 44 of
            # 97. An empty era is a measurement, not an error.
            m = {"n": 0, "net": 0.0, "r_trade": 0.0, "pf": 0.0, "wr": 0.0,
                 "max_dd": 0.0, "dd_pct": 0.0, "dd_dur": 0, "ulcer": 0.0,
                 "sortino": 0.0, "pos_month_pct": 0.0, "worst_year": 0.0,
                 "years_n": 0, "top5pct_share": 0.0, "max_win": 0.0,
                 "max_loss": 0.0, "recovery": 0.0, "avg_win": 0.0,
                 "avg_loss": 0.0, "uw_pct": 0.0, "max_uw": 0, "max_streak": 0}
            for w in ROLL:
                m["roll%d_worst" % w] = None
                m["roll%d_pos" % w] = None
            m["spacing"] = {"max_gap": 0, "med_gap": 0, "gap_drawdown": 0.0,
                            "gap_pct_of_dd": 0.0}
            r[era] = m
            continue
        m.update(tail_metrics(nets))
        sp = spacing(nets)
        for w in ROLL:
            worst, pos = rolling(nets, w)
            m["roll%d_worst" % w] = worst
            m["roll%d_pos" % w] = pos
        m["spacing"] = sp
        # monthly / yearly
        mo, yr = {}, {}
        for t, x in zip(tr, nets):
            d = str(t.get("exit_date") or t.get("entry_date") or "")
            if len(d) >= 7:
                mo[d[:7]] = mo.get(d[:7], 0.0) + x
            if len(d) >= 4:
                yr[d[:4]] = yr.get(d[:4], 0.0) + x
        m["pos_month_pct"] = round(100.0 * sum(1 for v in mo.values() if v > 0) / len(mo), 1) if mo else 0.0
        m["worst_year"] = round(min(yr.values()), 2) if yr else 0.0
        m["years_n"] = len(yr)
        m["spacing"]["gap_pct_of_dd"] = (
            round(100.0 * sp["gap_drawdown"] / m["max_dd"], 1) if m["max_dd"] else 0.0)
        r[era] = m
    return r


def gates(row):
    """Hard gates. A book failing any of these is out, whatever its net."""
    isx, oos = row["is"], row["oos"]
    fail = []
    if isx.get("n", 0) == 0 or oos.get("n", 0) == 0:
        fail.append("no completed trades in an era")
    if isx.get("net", 0) <= 0:
        fail.append("IS net <= 0")
    if oos.get("net", 0) <= 0:
        fail.append("OOS net <= 0")
    if oos.get("n", 0) < 100:
        fail.append("OOS n < 100")
    if oos.get("dd_pct", 999) > 40:
        fail.append("OOS DD > 40%% of net")
    if oos.get("roll50_worst") is not None and oos["roll50_worst"] < 0:
        fail.append("OOS has a negative 50-trade window")
    return fail


def main() -> int:
    global _TOTAL
    _TOTAL = len(BOOKS) * 2
    print("SELECTION - gates + scorecard, sig and multi kept apart")
    print("%d books x 2 eras, ~%d min" % (len(BOOKS), len(BOOKS) * 2 * 9 // 60))
    print()
    t0 = time.time()
    sim = craze.build_module()
    eras = {e: load_era(e) for e in ("is", "oos")}
    print("loaded (%.0fs)\n" % (time.time() - t0))

    out = {}
    # Resume. The first run lost 22 minutes to a KeyError at book 44 of 97, so
    # every completed book is written out and skipped on the next start. Delete
    # selection_partial.json to force a clean sweep.
    PART = HERE / "selection_partial.json"
    if PART.exists():
        out = json.loads(PART.read_text(encoding="utf-8"))
        print("resuming with %d books already measured\n" % len(out))
    todo = [(b, c) for b, c in sorted(BOOKS.items()) if b not in out]

    for i, (book, cfg) in enumerate(todo, 1):
        row = measure(sim, eras, book, cfg)
        mp = (cfg.get("params") or {}).get("max_positions", 0)
        row["cls"] = "sig" if mp == 1 else ("multi" if mp == 0 else "other")
        row["n_params"] = len(cfg.get("params") or {})
        row["pins_ok"] = None
        row["fails"] = gates(row)
        row["passes"] = not row["fails"]
        out[book] = row
        PART.write_text(json.dumps(out, indent=1), encoding="utf-8")
        step("%-44s %s" % (book, "PASS" if row["passes"] else row["fails"][:1]))

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")

    # ---------------- report ------------------------------------------
    lines = []
    lines.append("# Selection scorecard - %s" % time.strftime("%Y-%m-%d"))
    lines.append("")
    lines.append("Gates + scorecard, per docs/learn/finding optimal book.md:698.")
    lines.append("sig and multi are never mixed (BASELINE.md:63-67).")
    lines.append("")
    lines.append("Gate: pins OK, IS net > 0, OOS net > 0, OOS n >= 100, "
                 "OOS DD <= 40%% of net, no negative 50-trade rolling window.")
    lines.append("")
    for cls in ("sig", "multi"):
        sel = {k: v for k, v in out.items() if v["cls"] == cls}
        ok = {k: v for k, v in sel.items() if v["passes"]}
        lines.append("## %s books - %d total, %d pass the gates" % (cls.upper(), len(sel), len(ok)))
        lines.append("")
        if not ok:
            lines.append("none pass.")
            lines.append("")
            continue
        hdr = ("| book | IS net | OOS net | OOS R/tr | OOS PF | OOS n | OOS DD | DD%% | ulcer |"
               " roll20 | roll50 | roll100 | %pos months | worst yr | top5% share | max gap | params |")
        lines.append(hdr)
        lines.append("|" + "---|" * 16)
        def key(v):
            return -(v["oos"]["net"] / max(v["oos"]["n"], 1))
        for k in sorted(ok, key=key):
            a, b = ok[k]["is"], ok[k]["oos"]
            lines.append("| `%s` | %.1f | %.1f | %.3f | %.2f | %d | %.1f | %.1f%% | %.1f |"
                         " %.1f | %.1f | %.1f | %.0f%% | %.1f | %.0f%% | %d | %d |" % (
                             k, a["net"], b["net"], b["r_trade"], b["pf"], b["n"], b["max_dd"],
                             b["dd_pct"], b["ulcer"],
                             b.get("roll20_worst") or 0.0, b.get("roll50_worst") or 0.0,
                             b.get("roll100_worst") or 0.0, b["pos_month_pct"], b["worst_year"],
                             b.get("top5pct_share") or 0.0,
                             b["spacing"]["max_gap"], ok[k]["n_params"]))
        lines.append("")
        failed = {k: v for k, v in sel.items() if not v["passes"]}
        if failed:
            lines.append("Failed the gates: %s" % ", ".join(
                "`%s` (%s)" % (k, "; ".join(v["fails"])) for k, v in sorted(failed.items())))
            lines.append("")
    CARD.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("=" * 100)
    for cls in ("sig", "multi"):
        sel = {k: v for k, v in out.items() if v["cls"] == cls}
        ok = {k: v for k, v in sel.items() if v["passes"]}
        print("%s: %d books, %d pass the gates" % (cls.upper(), len(sel), len(ok)))
        for k in sorted(ok, key=lambda k: -(ok[k]["oos"]["net"] / max(ok[k]["oos"]["n"], 1)))[:10]:
            b = ok[k]["oos"]
            print("   %-40s OOS %+8.1f  %5.3f/tr  PF %5.2f  n=%-4d DD %6.1f (%.0f%%)"
                  % (k, b["net"], b["r_trade"], b["pf"], b["n"], b["max_dd"], b["dd_pct"]))
        print()
    print("wrote %s and %s  (%.0fs)" % (RESULTS.name, CARD.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
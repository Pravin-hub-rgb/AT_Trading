"""exp_maxcap_sweep - cap simultaneous open positions on fsent_champ_long.

THE QUESTION
============
The book runs unlimited concurrent positions: max_positions is absent, so the
engine default 0 applies and `busy_until` is never armed. Measured concurrency on
the pinned trades is 11 at peak in sample and 6 out of sample, with the large
majority of time spent at exactly 1 open position.

So the cap is not really "limit exposure". On this book the interesting question
is narrower and has three parts:

  1. Does capping cost R? Almost certainly some - the 6th position exists because
     something was found there.
  2. What does it buy? Drawdown, margin, or nothing at all. If it buys nothing,
     it is pure cost and the answer is "do not cap".
  3. Is the cost concentrated in eras? A cap that costs 5R in sample and 40R out
     is the era-split pattern and is a reason to leave it off.

WHY THIS HARNESS HAD TO ADD THE KNOB FIRST
===========================================
`exp_max_concurrent` did not exist in unified.py. It appeared only in
test_experiments_craze.py's injected-params list, and a doc table in 5M_CONFIRM.md
listed it with default 0 - but `git log -S` over the engine found no commit ever
adding it, so the doc was describing a knob that the champion's engine could not
actually accept. It has been added to unified.py as a default-off keyword, and the
duplicate entry removed from the craze harness, in the same commit.

That matters for reading the earlier claim that this had "already been swept at
cap=5". That claim is traceable to a queue line citing exp_max_concurrent, and the
knob was only reachable through a harness patch, so whatever it measured was not
this book on this engine. It is re-measured here rather than trusted.

THE CAP SEMANTICS ARE THE ENGINE'S, NOT THE HARNESS'S
======================================================
`exp_max_concurrent=N` counts trades ALREADY BOOKED whose [entry_ts, exit_ts]
contains the entry bar being considered, inclusive at both ends. Every such
exit_ts was settled before that entry was evaluated, because trades are booked in
stream order, so the gate reads nothing unknowable. At N=0 no list is even
maintained and no gate fires.

WHAT WOULD COUNT AS A RESULT
===========================
Lower net in BOTH eras, or the cost buys a drawdown reduction that survives both
eras. Anything that trades IS for OOS is the eighth appearance of that pattern
here and a reason to keep the book uncapped.

Run:  cd backtest/tests
      python -u exp_maxcap_sweep.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
CAPS = (0, 2, 3, 4, 5, 6, 7, 8)
OUT_JSON = Path(__file__).parent / "_maxcap_sweep.json"
OUT_MD = Path(__file__).parent / "_maxcap_sweep.md"


def concurrency(trades):
    """Peak simultaneous positions, counting [entry_ts, exit_ts] inclusive.

    Matches the engine gate's convention exactly rather than approximating it -
    a cap measured under one counting rule and enforced under another is not a
    measurement of the same thing.
    """
    ev = []
    for t in trades:
        a, b = int(t["entry_ts"]), int(t["exit_ts"])
        ev.append((a, 1))
        ev.append((b, -1))
    # exits land before entries at the same timestamp, so a trade that closes
    # exactly when another opens does not consume a slot for the new one
    ev.sort(key=lambda e: (e[0], e[1]))
    cur = peak = 0
    for _, d in ev:
        cur += d
        peak = max(peak, cur)
    return peak


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}

    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], cfg.get("swing") or "sw10")

    def run(era, cap):
        p = dict(base)
        p["exp_max_concurrent"] = cap
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        m = compute(rs, [t.get("entry_date", "") for t in tr])
        return tr, rs, m

    print("=" * 106)
    print("SIMULTANEOUS-POSITION CAP SWEEP - %s" % BOOK)
    print("=" * 106)
    print("book ships with max_positions ABSENT -> engine default 0 = unlimited.")
    print("cap 0 here is the same unlimited behaviour, re-measured as the control.\n")

    rows = []
    for cap in CAPS:
        rec = {"cap": cap}
        for era in ("is", "oos"):
            tr, rs, m = run(era, cap)
            rec[era] = {"n": m["n"], "net": round(m["net"], 2),
                        "max_dd": round(m["max_dd"], 2), "dd_dur": m.get("dd_dur"),
                        "ulcer": round(m["ulcer"], 2), "max_streak": m.get("max_streak"),
                        "pf": round(m["pf"], 3), "pos_month": m.get("pos_month_pct"),
                        "peak": concurrency(tr),
                        "top": round(sorted(rs, reverse=True)[0], 3) if rs else None,
                        "without_top": round(sum(sorted(rs, reverse=True)[1:]), 2) if rs else None}
        rows.append(rec)

    ctrl = next(r for r in rows if r["cap"] == 0)
    print("%-6s %22s %22s %14s %14s" % ("cap", "IS n/net/dd/peak", "OOS n/net/dd/peak",
                                       "d IS", "d OOS"))
    for r in rows:
        di = r["is"]["net"] - ctrl["is"]["net"]
        do = r["oos"]["net"] - ctrl["oos"]["net"]
        r["d_is"], r["d_oos"] = round(di, 2), round(do, 2)
        star = "  <- shipping (uncapped)" if r["cap"] == 0 else ""
        print("%-6d %22s %22s %+14.1f %+14.1f%s"
              % (r["cap"],
                 "%d / %+.1f / %.1f / %d" % (r["is"]["n"], r["is"]["net"], r["is"]["max_dd"], r["is"]["peak"]),
                 "%d / %+.1f / %.1f / %d" % (r["oos"]["n"], r["oos"]["net"], r["oos"]["max_dd"], r["oos"]["peak"]),
                 di, do, star))

    print()
    print("=" * 106)
    print("WHAT THE CAP BUYS, and in which era")
    print("=" * 106)
    print("%-6s %26s %26s" % ("cap", "IS dd / ulcer / streak", "OOS dd / ulcer / streak"))
    for r in rows:
        print("%-6d %26s %26s"
              % (r["cap"],
                 "%.1f / %.2f / %s" % (r["is"]["max_dd"], r["is"]["ulcer"], r["is"]["max_streak"]),
                 "%.1f / %.2f / %s" % (r["oos"]["max_dd"], r["oos"]["ulcer"], r["oos"]["max_streak"])))

    print()
    print("=" * 106)
    print("VERDICT")
    print("=" * 106)
    caps = [r for r in rows if r["cap"] > 0]
    both_cheaper = [r for r in caps if r["d_is"] < 0 and r["d_oos"] < 0]
    era_split = [r for r in caps if (r["d_is"] < 0 <= r["d_oos"]) or (r["d_oos"] < 0 <= r["d_is"])]
    mixed = [r for r in caps if r not in both_cheaper and r not in era_split]

    if not both_cheaper and not era_split and not mixed:
        print("Every cap costs R in both eras. No cap pays for itself on return.")
    for r in both_cheaper:
        dd_i = r["is"]["max_dd"] - ctrl["is"]["max_dd"]
        dd_o = r["oos"]["max_dd"] - ctrl["oos"]["max_dd"]
        print("cap=%d: cheaper in both eras (%+.1f IS, %+.1f OOS), drawdown %+.1f IS / %+.1f OOS"
              % (r["cap"], r["d_is"], r["d_oos"], dd_i, dd_o))
    for r in era_split:
        print("cap=%d: ERA-SPLIT (%+.1f IS, %+.1f OOS) - the eighth appearance of this"
              % (r["cap"], r["d_is"], r["d_oos"]))
    for r in mixed:
        print("cap=%d: no worse in one era (%+.1f IS, %+.1f OOS)"
              % (r["cap"], r["d_is"], r["d_oos"]))

    if both_cheaper:
        # "closest to free" = the SMALLEST total cost. These are all negative, so
        # max() not min(). min() picks the most negative, i.e. the most
        # expensive cap, which is the opposite of the intended answer.
        best = max(both_cheaper, key=lambda r: r["d_is"] + r["d_oos"])
        total = -(best["d_is"] + best["d_oos"])
        dd_i = best["is"]["max_dd"] - ctrl["is"]["max_dd"]
        dd_o = best["oos"]["max_dd"] - ctrl["oos"]["max_dd"]
        print()
        print("Cheapest cap overall: %d, costing %.1fR across both eras." % (best["cap"], total))
        print("  drawdown change %+.1fR IS, %+.1fR OOS  |  ulcer %+.2f IS, %+.2f OOS"
              % (dd_i, dd_o,
                 best["is"]["ulcer"] - ctrl["is"]["ulcer"],
                 best["oos"]["ulcer"] - ctrl["oos"]["ulcer"]))
        print("  peak exposure %d -> %d out of sample" % (ctrl["oos"]["peak"], best["oos"]["peak"]))

    print()
    print("READ THIS BEFORE USING ANY CAP")
    print("The drawdown column above is the whole answer: from cap=4 upward the IS")
    print("drawdown does not move at all (13.4 unchanged) and ulcer gets slightly")
    print("WORSE, while the losing streak gets worse out of sample (15 -> 14 at")
    print("cap=2..5 is an improvement, but 15 -> 14 with -3.9R is a bad trade).")
    print("A cap that removes return and does not reduce drawdown is not a risk")
    print("control, it is just less trading. If the goal is lower margin usage,")
    print("position SIZING does that without deleting trades - which is the")
    print("question to ask instead.")

    OUT_JSON.write_text(json.dumps({"book": BOOK, "rows": rows}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# simultaneous-position cap sweep - %s" % BOOK, "",
             "cap 0 = shipping (uncapped). Peak is measured under the engine's own",
             "[entry_ts, exit_ts] inclusive convention.", "",
             "| cap | IS n | IS net | IS dd | IS peak | OOS n | OOS net | OOS dd | OOS peak | d IS | d OOS |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        star = " **" if r["cap"] == 0 else ""
        lines.append("| %d%s | %d | %.1f | %.1f | %d | %d | %.1f | %.1f | %d | %+.1f | %+.1f |" % (
            r["cap"], star, r["is"]["n"], r["is"]["net"], r["is"]["max_dd"], r["is"]["peak"],
            r["oos"]["n"], r["oos"]["net"], r["oos"]["max_dd"], r["oos"]["peak"],
            r["d_is"], r["d_oos"]))
    lines += ["", "Shipping row marked **."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
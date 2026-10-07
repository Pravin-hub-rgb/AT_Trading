"""exp_persist_drawdown - what did exp_persist actually DO in OOS's worst stretch?

THE OWNER'S HYPOTHESIS
======================
exp_persist costs 66.1R in sample but only 5.0R out of it. Read naively that
says persist was worth little in OOS. The owner proposed a different reading:
OOS covers a bearish / low-liquidity stretch, chop and atr_pct both whipsaw
there, and exp_persist's 7-bar regime hysteresis is exactly the mechanism that
would stop it being fooled. If so, persist should have earned its keep at the one
moment it mattered, and the aggregate hides it.

That is a testable claim and this is the test. Aggregate R is the wrong
measurement for it, because "saved me in the crash" and "was mildly useful
everywhere" produce similar totals. The measurement has to be conditioned on
WHEN.

WHAT THIS MEASURES
==================
The drawdown period, defined from the shipping book's own equity curve rather
than from any outside assumption about which dates were a crash. Then, inside and
outside that window, persist=7 against persist=0:

    net R, trade count, and the specific trades that differ

and whether the differing trades land inside the bad stretch or outside it. A
hypothesis that says "persist saves us in the crash" predicts the differences
CONCENTRATE in the window. If they spread evenly, the hypothesis is wrong and
persist was just mildly useful throughout.

THE CONCENTRATION TEST IS THE ACTUAL ANSWER
===========================================
Not "was OOS net better with persist" - it is, by 5R, and 5R is nothing. It is
whether the differing trades are where the owner thinks they are. That is a
statement about placement, and it can be wrong independently of the total.

Run:  cd backtest/tests
      python -u exp_persist_drawdown.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
OUT_JSON = Path(__file__).parent / "_persist_dd.json"
OUT_MD = Path(__file__).parent / "_persist_dd.md"

# The two books the hypothesis compares. persist=7 is shipping; persist=0 is the
# same book with regime hysteresis switched off, nothing else moved.
ARMS = (("persist=7 (shipping)", 7), ("persist=0", 0))


def curve_and_dd(rs, dates):
    """Equity, peak-to-trough, and the date range of the deepest stretch."""
    eq = 0.0
    peak = 0.0
    eqs, mdd, peak_at, trough_at, cur_start = [], 0.0, None, None, None
    for r, d in zip(rs, dates):
        eq += r
        if eq > peak:
            peak = eq
            if cur_start is None:
                cur_start = d
        dd = peak - eq
        eqs.append((d, eq))
        if dd > mdd:
            mdd = dd
            peak_at, trough_at = cur_start, d
    return eqs, mdd, peak_at, trough_at


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}

    d = load_era("oos")
    sw = get_swings(d, cfg.get("swing") or "sw10")

    def run(persist):
        p = dict(base)
        p["exp_persist"] = persist
        o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
        return tr, [net_r([t]) for t in tr], [t.get("entry_date", "") for t in tr]

    arms = {}
    for name, pv in ARMS:
        tr, rs, ds = run(pv)
        eqs, mdd, pa, ta = curve_and_dd(rs, ds)
        arms[name] = {"pv": pv, "tr": tr, "rs": rs, "ds": ds,
                      "eqs": eqs, "mdd": mdd, "peak_at": pa, "trough_at": ta}
        print("%-22s n=%3d net %+8.2f  max_dd %6.2f  worst stretch %s -> %s"
              % (name, len(rs), sum(rs), mdd, pa, ta))
    print()

    ship = arms["persist=7 (shipping)"]
    off = arms["persist=0"]
    pa, ta = ship["peak_at"], ship["trough_at"]

    print("=" * 104)
    print("THE DRAWdown WINDOW, taken from the shipping book's own curve")
    print("=" * 104)
    print("  peak %s  ->  trough %s   depth %.2fR" % (pa, ta, ship["mdd"]))
    in_win = lambda d: pa <= d <= ta
    n_in = sum(1 for d in ship["ds"] if in_win(d))
    r_in = sum(r for r, d in zip(ship["rs"], ship["ds"]) if in_win(d))
    r_out = sum(ship["rs"]) - r_in
    print("  shipping book: %d of %d trades inside it, %+.2fR inside vs %+.2fR outside"
          % (n_in, len(ship["ds"]), r_in, r_out))
    print()

    # ------------------------------------------------------------------
    # The hypothesis, stated as a prediction before the numbers.
    # ------------------------------------------------------------------
    print("-" * 104)
    print("INSIDE vs OUTSIDE THE WINDOW  (persist=7 shipping vs persist=0)")
    print("-" * 104)
    print("%-26s %10s %10s %10s" % ("window", "persist7", "persist0", "delta"))
    rows = {}
    for label, keep in (("inside worst stretch", in_win),
                        ("outside it", lambda d: not in_win(d))):
        a = [r for r, d in zip(ship["rs"], ship["ds"]) if keep(d)]
        b = [r for r, d in zip(off["rs"], off["ds"]) if keep(d)]
        rows[label] = {"p7": round(sum(a), 2), "p0": round(sum(b), 2),
                       "d": round(sum(a) - sum(b), 2), "n7": len(a), "n0": len(b)}
        print("%-26s %10.2f %10.2f %+10.2f   (n %d vs %d)"
              % (label, sum(a), sum(b), sum(a) - sum(b), len(a), len(b)))

    # ------------------------------------------------------------------
    # THE ACTUAL TEST - are the differing trades inside the window?
    # ------------------------------------------------------------------
    print()
    print("-" * 104)
    print("PLACEMENT - does persist's effect CONCENTRATE in the stretch?")
    print("-" * 104)
    s_by_ts = {int(t["entry_ts"]): net_r([t]) for t in ship["tr"]}
    o_by_ts = {int(t["entry_ts"]): net_r([t]) for t in off["tr"]}
    only7 = sorted(set(s_by_ts) - set(o_by_ts))
    only0 = sorted(set(o_by_ts) - set(s_by_ts))
    d_of = {int(t["entry_ts"]): t.get("entry_date", "") for t in ship["tr"]}
    d_of.update({int(t["entry_ts"]): t.get("entry_date", "") for t in off["tr"]})

    def place(tss):
        inside = len([t for t in tss if in_win(d_of.get(t, ""))])
        return inside, len(tss) - inside, len(tss)

    i, o, n = place(only7)
    print("trades only at persist=7 : %d  (inside window %d, outside %d)  sum %+.2fR"
          % (n, i, o, sum(s_by_ts[t] for t in only7)))
    i, o, n = place(only0)
    print("trades only at persist=0 : %d  (inside window %d, outside %d)  sum %+.2fR"
          % (n, i, o, sum(o_by_ts[t] for t in only0)))
    i7, _, n7 = place(only7)
    i0, _, n0 = place(only0)
    share = (i7 / n7) if n7 else 0.0
    window_share = (n_in / len(ship["ds"])) if ship["ds"] else 0.0
    print()
    print("share of persist-only trades inside the stretch : %.0f%%" % (100 * share))
    print("share of all shipping trades inside the stretch  : %.0f%%" % (100 * window_share))
    if n7 or n0:
        verdict = ("CONCENTRATES - the hypothesis survives"
                   if share > 2 * window_share else
                   "does NOT concentrate - persist was not a crash-specific save")
        print("-> %s" % verdict)

    print()
    print("-" * 104)
    print("THE TEN BIGGEST PERSIST-ONLY TRADES, sorted by R, with placement")
    print("-" * 104)
    big = sorted(only7, key=lambda t: -s_by_ts[t])[:10]
    print("%-22s %9s  %s" % ("entry date", "R", "inside worst stretch?"))
    for t in big:
        print("%-22s %+9.3f  %s" % (d_of.get(t, ""), s_by_ts[t],
                                     "YES" if in_win(d_of.get(t, "")) else "no"))

    OUT_JSON.write_text(json.dumps(
        {"book": BOOK, "window": [pa, ta], "mdd": ship["mdd"],
         "arms": {k: {"n": len(v["rs"]), "net": round(sum(v["rs"]), 2),
                      "mdd": round(v["mdd"], 2)} for k, v in arms.items()},
         "inside_outside": rows,
         "placement": {"only7": len(only7), "only0": len(only0),
                       "only7_inside": i7, "only0_inside": i0},
         "n_inside_window": n_in, "n_total": len(ship["ds"])}, indent=2) + "\n",
        encoding="utf-8")
    print("\nwrote %s" % OUT_JSON.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
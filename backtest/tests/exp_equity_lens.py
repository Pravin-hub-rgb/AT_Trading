"""exp_equity_lens - two questions on one measurement.

Q1  Is dropping ext_stop_r from fsent_champ_long a true no-op?
    C17 showed 3.0 and 0.0 book the same trades. This checks it the way that
    matters for a book: byte-identical trade lists AND an identical equity
    curve, both eras. If any R differs, the answer to Q1 is no.

Q2  fsent_champ_long_nohalt: the halt off costs drawdown and adds trades. What
    does the FULL equity lens say - ulcer, sortino, calmar, share of the curve
    spent underwater, worst drawdown duration, positive-month rate, worst month -
    rather than just total R and max DD? Total R up with DD up is the shape that
    has filled this repo's graveyard, so the curve metrics are the question.

Run:  cd backtest/tests
      python -u exp_equity_lens.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BASE = "fsent_champ_long"
ARMS = ("fsent_champ_long_nohalt",)
YEARS = {"is": 3.67, "oos": 2.0}
LENS = ["net", "max_dd", "max_dd_dur", "uw_pct", "max_uw", "ulcer",
        "sortino", "calmar", "recovery", "max_streak", "pf", "pos_month_pct",
        "worst_month", "pos_year_pct", "worst_year"]
# max_streak is the LONGEST RUN OF CONSECUTIVE LOSSES (exp_equity_quality.py),
# not a win streak - so lower is better there too. Leaving it out of this set
# made the lens call OOS 15 -> 16 an improvement, which is backwards.
LOWER_IS_BETTER = {"max_dd", "max_dd_dur", "uw_pct", "max_uw", "ulcer",
                   "worst_month", "worst_year", "max_streak"}


def trades_of(sim, data, cfg, ext=None):
    from run_experiment import BP
    p = {**BP, **cfg["params"]}
    p.setdefault("exp_partial_r", 0.0)
    if ext is not None:
        p["ext_stop_r"] = ext
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **p)
    return [t for t in out["ltf_trades"] if t.get("outcome") != "open"]


def main() -> int:
    from exp_tf_family import build_family_module
    from exp_multi_metrics import load_era
    from exp_equity_quality import equity_quality
    import experiment_registry as reg

    sim = build_family_module()
    bc = reg.EXPERIMENTS[BASE]
    data = {e: load_era(e) for e in ("is", "oos")}

    # ---------------- Q1: is ext_stop_r a no-op? --------------------------
    print("=" * 84)
    print("Q1  DROP ext_stop_r FROM %s - is it a true no-op?" % BASE)
    print("=" * 84)
    q1 = True
    for era in ("is", "oos"):
        on = trades_of(sim, data[era], bc, ext=3.0)
        off = trades_of(sim, data[era], bc, ext=0.0)
        a = {(t["entry_ts"], t["dir"], t["sl"], t["r_multiple"]) for t in on}
        b = {(t["entry_ts"], t["dir"], t["sl"], t["r_multiple"]) for t in off}
        ea, eb = equity_quality(on, YEARS[era]), equity_quality(off, YEARS[era])
        same_trades = a == b
        same_curve = all(ea[k] == eb[k] for k in LENS)
        print("  %-4s n %d vs %d | trade lists identical: %-5s | equity curve "
              "identical: %-5s | net %+.2f vs %+.2f"
              % (era.upper(), len(on), len(off), same_trades, same_curve,
                 ea["net"], eb["net"]))
        if not (same_trades and same_curve):
            q1 = False
            for k in LENS:
                if ea[k] != eb[k]:
                    print("        %-14s %.4f -> %.4f" % (k, ea[k], eb[k]))
    print()
    print("  VERDICT Q1: %s" % ("YES - remove it, nothing changes"
                                if q1 else "NO - it still does something"))

    # ---------------- Q2: nohalt under the full lens -----------------------
    print()
    print("=" * 84)
    print("Q2  %s vs %s under the full equity lens" % (ARMS[0], BASE))
    print("=" * 84)
    for era in ("is", "oos"):
        b = equity_quality(trades_of(sim, data[era], bc), YEARS[era])
        a = equity_quality(trades_of(sim, data[era], reg.EXPERIMENTS[ARMS[0]]),
                           YEARS[era])
        print("\n  %s   (n %d -> %d)" % (era.upper(), b["n"], a["n"]))
        print("  %-14s %12s %12s %10s  %s"
              % ("metric", BASE.split("_")[-1], "nohalt", "delta", "verdict"))
        for k in LENS:
            lo = k in LOWER_IS_BETTER
            d = a[k] - b[k]
            better = (d < 0) if lo else (d > 0)
            same = abs(d) < 1e-9
            print("  %-14s %12s %12s %+10s  %s"
                  % (k, _f(b[k]), _f(a[k]), _f(d),
                     "same" if same else ("better" if better else "WORSE")))
    print()
    print("  Two profiles, and the difference is which side of ulcer moves.")
    print("  GRAVEYARD: total R up AND max_dd up AND ulcer up - more total bought")
    print("              with a deeper and more persistently painful curve.")
    print("  OPPOSITE : total R up with ulcer DOWN and sortino up - the typical")
    print("              path got smoother, the worst case got deeper. That is the")
    print("              shape more trades naturally produce, and it is a real trade")
    print("              rather than a free lunch: something has to pay for the")
    print("              smoother average. max_dd and max_dd_dur are what pay.")
    return 0


def _f(x):
    if isinstance(x, float):
        return "%.4f" % x
    return str(x)


if __name__ == "__main__":
    raise SystemExit(main())

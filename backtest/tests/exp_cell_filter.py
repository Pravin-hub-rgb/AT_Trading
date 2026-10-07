"""exp_cell_filter - the cell as a PERMISSION, not a restriction.

THE SHAPE OF THE IDEA
=====================
CELL_GATE_NOT_A_BOOK.md gated the cell and got 144 IS / 58 OOS trades - too few
to size a book, and in-sample drawdown got WORSE (25.2R against 13.4R) because
concentrating the good cell removes the trades that were interleaved between its
drawdowns.

The opposite move is the one this harness tries: keep the whole book, and let the
cell switch ON an extra source of trades. The book already trades decisively when
atrp > 0.65 (its own mode). The cell adds decisive windows where atrp is LOW but
chop is HIGH - bars that are quiet but travelling efficiently, which is a trend
the current router cannot see because it only looks at bar size.

So the rule under test is a UNION of two permissions, not a gate:

    take if  (atrp > 0.65)                    <- the shipping book
          or (chop > 58.0 and atrp < 0.65)    <- the measured cell

WHY THIS IS THE RIGHT FIRST MOVE
================================
It cannot be worse by construction in the way the gate was: the shipping arm is
still there, so every trade it took is still taken. Anything the cell adds is
incremental, and the question becomes only whether the additions are worth their
drawdown. That is a much smaller thing to falsify than "is this cell a book".

Note this is the "union" shape of the router's union branch, expressed as a
condition rather than a second interval set, because both arms select the same
decisive interval set - so no new interval machinery is needed.

THE BAR, UNCHANGED
==================
Both eras, and the outlier test. A union that gains by adding one +48R trade is
the ch=50 failure again with extra steps.

Run:  cd backtest/tests
      python -u exp_cell_filter.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
MODE = "atr_high_or_chop_hi_atr_lo"
OUT_JSON = Path(__file__).parent / "_cell_filter.json"
OUT_MD = Path(__file__).parent / "_cell_filter.md"

PERSIST_GRID = (0, 2, 3, 4, 5, 6, 7)


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)
    a_thr, c_thr = base["atr_high_thresh"], base["chop_thresh"]

    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], cfg.get("swing") or "sw10")

    def run(era, mode, persist=None):
        p = dict(base)
        p["mode"] = mode
        if persist is not None:
            p["exp_persist"] = persist
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        m = compute(rs, [t.get("entry_date", "") for t in tr])
        return tr, m, rs

    print("=" * 100)
    print("CELL AS PERMISSION - mode=%r on %s" % (MODE, BOOK))
    print("=" * 100)
    print("union: shipping (atrp>%s)  OR  the measured cell (chop>%s and atrp<%s)"
          % (a_thr, c_thr, a_thr))
    print("thresholds are the book's own. The shipping arm is untouched, so every")
    print("trade it takes is still taken - only the ADDITIONS are in question.\n")

    ship, res = {}, {}
    for era in ("is", "oos"):
        ship[era] = run(era, "atr_high")
        sm = ship[era][1]
        print("-" * 100)
        print("%s  shipping n=%d net %+.1f dd %.1f dd_dur %s ulcer %.2f streak %s"
              % (era.upper(), sm["n"], sm["net"], sm["max_dd"], sm.get("dd_dur"),
                 sm["ulcer"], sm.get("max_streak")))

        print()
        print("   %-22s %6s %9s %7s %7s %7s %8s %8s" %
              ("arm", "n", "net", "dd", "dd_dur", "ulcer", "d IS", "d OOS"))
        rows = []
        for pv in PERSIST_GRID:
            tr, m, rs = run(era, MODE, pv)
            s_tr = {int(t["entry_ts"]) for t in ship[era][0]}
            c_tr = {int(t["entry_ts"]) for t in tr}
            added = [net_r([t]) for t in tr if int(t["entry_ts"]) not in s_tr]
            dropped = [net_r([t]) for t in ship[era][0] if int(t["entry_ts"]) not in c_tr]
            d = m["net"] - sm["net"]
            rows.append({"persist": pv, "n": m["n"], "net": round(m["net"], 2),
                         "dd": round(m["max_dd"], 2), "dd_dur": m.get("dd_dur"),
                         "ulcer": round(m["ulcer"], 2), "streak": m.get("max_streak"),
                         "d": round(d, 2), "n_added": len(added), "n_dropped": len(dropped),
                         "added_sum": round(sum(added), 2), "dropped_sum": round(sum(dropped), 2),
                         "top": round(sorted(rs, reverse=True)[0], 3) if rs else None,
                         "without_top": round(sum(sorted(rs, reverse=True)[1:]), 2) if rs else None})
            print("   %-22s %6d %+9.1f %7.1f %7s %7.2f %8s %8s" %
                  ("%s persist=%d" % (MODE[:14], pv), m["n"], m["net"], m["max_dd"],
                   m.get("dd_dur"), m["ulcer"], "", ""))
        res[era] = rows
        print()

    print("=" * 100)
    print("WHAT THE ADDITIONS ARE WORTH (persist=7, shipping values)")
    print("=" * 100)
    for era in ("is", "oos"):
        r = res[era][-1]
        print("%s: +%d trades / -%d trades vs shipping | added %+.1fR, dropped %+.1fR, net delta %+.1fR"
              % (era.upper(), r["n_added"], r["n_dropped"], r["added_sum"],
                 r["dropped_sum"], r["d"]))

    print()
    print("=" * 100)
    print("OUTLIER BAR - and does the whole thing survive losing its top trade")
    print("=" * 100)
    ok = True
    for era in ("is", "oos"):
        r = res[era][-1]
        pos = r["without_top"] is not None and r["without_top"] > 0
        ok = ok and pos
        print("   %s persist=7  net %+.1f  largest %+.2fR  without it %+.1fR  %s"
              % (era.upper(), r["net"], r["top"], r["without_top"],
                 "OK" if pos else "FAILS"))
    print("   survives: %s" % ("YES" if ok else "NO"))

    print()
    print("=" * 100)
    print("VERDICT")
    print("=" * 100)
    for era in ("is", "oos"):
        r = res[era][-1]
        print("   %s persist=7: n %+d (%d)   net %+.1f (%+.1f)   dd %.1f (%s)   dd_dur %s (%s)   ulcer %.2f"
              % (era.upper(), r["n_added"], r["n"], r["net"], r["d"], r["dd"],
                 ship[era][1]["max_dd"], r["dd_dur"], ship[era][1].get("dd_dur"),
                 r["ulcer"]))
    both = res["is"][-1]["d"] >= 0 and res["oos"][-1]["d"] >= 0
    if both and ok:
        print("   ahead in both eras and passes the outlier bar.")
    else:
        print("   not ahead in both eras, or fails the outlier bar. Not adopted.")
    print("   shipping config untouched; no book registered.")

    OUT_JSON.write_text(json.dumps({"book": BOOK, "mode": MODE, "res": res}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# cell as permission - %r on %s" % (MODE, BOOK), "",
             "Union of the shipping arm and the measured cell.", "",
             "| era | persist | n | net | dd | dd_dur | ulcer | streak | d vs ship |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        for r in res[era]:
            lines.append("| %s | %d | %d | %.1f | %.1f | %s | %.2f | %s | %+.1f |" % (
                era.upper(), r["persist"], r["n"], r["net"], r["dd"], r["dd_dur"],
                r["ulcer"], r["streak"], r["d"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
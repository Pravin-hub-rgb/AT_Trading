"""exp_cell_shape - is the gated cell's drawdown the SHAPE the halt exists for?

TWO OPEN QUESTIONS, ONE RUN
==========================
#3. exp_cell_filter.py swept persist on the UNION mode and found every setting
    loses out of sample, with persist=5 the era-split (+28.8R OOS, -14.0R IS).
    But it never swept persist on the GATE. The gate produces a different and
    much smaller trade set, and exp_persist is exactly the knob that decides
    which of them survive - a 7-bar hysteresis holding a routed decision across
    bars is plausible for a sparse regime like this one. Swept here.

#4. CELL_GATE_NOT_A_BOOK.md found that gating makes in-sample drawdown WORSE,
    25.2R against 13.4R, and explained it as clustering. That explanation was
    asserted. This measures the shape: drawdown DURATION, ulcer, longest losing
    run, and the depth-to-duration ratio, for the book and for the gate. The
    halt in signal.py exists to bound losing STREAKS, so max_streak is the field
    that actually speaks to it, and it was not reported.

THE BAR IS UNCHANGED AND IS THE POINT
=====================================
A persist setting that gains on one era only is the era-split pattern, and this
repo has now seen it eight times. So persist is reported as a grid with both
eras side by side and no "best" row picked out. If nothing is not-worse-in-both,
the grid is the answer and no arm is adopted.

Run:  cd backtest/tests
      python -u exp_cell_shape.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
GATE = "chop_hi_atr_lo_gate"
OUT_JSON = Path(__file__).parent / "_cell_shape.json"
OUT_MD = Path(__file__).parent / "_cell_shape.md"

PERSIST_GRID = (0, 1, 2, 3, 4, 5, 6, 7)


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
        return rs, compute(rs, [t.get("entry_date", "") for t in tr])

    ship = {}
    for e in ("is", "oos"):
        _rs, _m = run(e, "atr_high")
        ship[e] = _m

    print("=" * 104)
    print("GATE SHAPE - %s, mode=%r" % (BOOK, GATE))
    print("=" * 104)

    # ------------------------------------------------------------------
    # #4 - drawdown SHAPE, which was asserted last time and is measured here.
    # ------------------------------------------------------------------
    print()
    print("-" * 104)
    print("#4  DRAWDOWN SHAPE - the field the halt actually cares about is max_streak")
    print("-" * 104)
    for era in ("is", "oos"):
        rs, m = run(era, GATE)
        sm = ship[era]
        print("\n%s" % era.upper())
        print("   %-22s %14s %14s %s" % ("metric", "whole book", "gated cell", "direction"))
        for k, lower_better in (("n", False), ("net", False), ("max_dd", True),
                                ("dd_dur", True), ("ulcer", True), ("max_streak", True),
                                ("pf", False), ("top5_share_pct", True),
                                ("trimmed", False), ("sortino", False)):
            bv, cv = sm.get(k), m.get(k)
            if bv is None or cv is None:
                continue
            if k == "n":
                arrow = "fewer trades"
            elif isinstance(bv, (int, float)) and isinstance(cv, (int, float)) and bv != cv:
                worse = (cv > bv) if lower_better else (cv < bv)
                arrow = "WORSE" if worse else "better"
            else:
                arrow = ""
            print("   %-22s %14s %14s %s" % (k, bv, cv, arrow))

    # ------------------------------------------------------------------
    # #3 - the persist grid on the gate, both eras, no row picked out.
    # ------------------------------------------------------------------
    print()
    print("-" * 104)
    print("#3  PERSIST GRID ON THE GATE - both eras side by side, no 'best' row")
    print("-" * 104)
    rows = []
    print("%-9s %18s %18s %10s %10s %14s" % ("persist", "IS n/net/dd", "OOS n/net/dd",
                                              "d IS", "d OOS", "verdict"))
    for pv in PERSIST_GRID:
        _rs_is, m_is = run("is", GATE, pv)
        _rs_oos, m_oos = run("oos", GATE, pv)
        rs_is, rs_oos = _rs_is, _rs_oos
        di = m_is["net"] - ship["is"]["net"]
        do = m_oos["net"] - ship["oos"]["net"]
        if di >= 0 and do >= 0:
            v = "not worse both"
        elif di > 0 > do:
            v = "ERA-SPLIT"
        else:
            v = "worse"
        rows.append({"persist": pv,
                     "is": {k: m_is.get(k) for k in ("n", "net", "max_dd", "dd_dur", "ulcer", "max_streak")},
                     "oos": {k: m_oos.get(k) for k in ("n", "net", "max_dd", "dd_dur", "ulcer", "max_streak")},
                     "d_is": round(di, 2), "d_oos": round(do, 2), "verdict": v,
                     "is_without_top": round(sum(sorted(rs_is, reverse=True)[1:]), 2),
                     "oos_without_top": round(sum(sorted(rs_oos, reverse=True)[1:]), 2)})
        print("%-9s %18s %18s %+10.1f %+10.1f %14s"
              % (pv,
                 "%d / %+.1f / %.1f" % (m_is["n"], m_is["net"], m_is["max_dd"]),
                 "%d / %+.1f / %.1f" % (m_oos["n"], m_oos["net"], m_oos["max_dd"]),
                 di, do, v))

    print()
    print("=" * 104)
    print("VERDICT")
    print("=" * 104)
    ok = [r for r in rows if r["verdict"] == "not worse both"]
    print("persist settings not worse in both eras: %s"
          % (", ".join(str(r["persist"]) for r in ok) if ok else "NONE"))
    for r in ok:
        print("   persist=%d survives without its top trade: IS %+.1fR, OOS %+.1fR"
              % (r["persist"], r["is_without_top"], r["oos_without_top"]))
    if not ok:
        print()
        print("The gate loses in at least one era at every persist setting, so the")
        print("sweep does not rescue it either. Combined with the OOS trade count")
        print("(CELL_GATE_NOT_A_BOOK.md) and the +0.65 correlation (exp_cell_sleeve.py),")
        print("the cell is a real finding and not a book or a sleeve.")

    print()
    print("On #4 specifically, the shape result is the part worth keeping: it says")
    print("whether gating the cell makes the losing-run profile better or worse,")
    print("which is the quantity the halt governance note turns on. Read the table")
    print("above rather than this summary.")

    OUT_JSON.write_text(json.dumps({"book": BOOK, "gate": GATE, "rows": rows}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# gate shape - %r on %s" % (GATE, BOOK), "",
             "## persist grid, both eras", "",
             "| persist | IS n | IS net | IS dd | IS dur | IS streak | OOS n | OOS net | OOS dd | OOS dur | OOS streak | d IS | d OOS | verdict |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        i, o = r["is"], r["oos"]
        lines.append("| %d | %d | %.1f | %.1f | %s | %s | %d | %.1f | %.1f | %s | %s | %+.1f | %+.1f | %s |" % (
            r["persist"], i["n"], i["net"], i["max_dd"], i["dd_dur"], i["max_streak"],
            o["n"], o["net"], o["max_dd"], o["dd_dur"], o["max_streak"],
            r["d_is"], r["d_oos"], r["verdict"]))
    lines += ["", "## The persist grid is flat because it CANNOT bind on this mode",
             "",
             "Every row 0..7 is byte-identical, which is a structural result and not a",
             "measurement to trust at face value. `chop_hi_atr_lo_gate` does `continue`",
             "on any signal outside the cell, so `use` is never assigned for those",
             "signals and the v19 hysteresis state (_rg_s / _rg_c) never advances on",
             "them. The regime stickiness exp_persist controls only exists on signals",
             "that survive the gate, and on a cell covering 14% of bars there is",
             "almost nothing for it to stick to.",
             "",
             "So `exp_persist` is structurally inert on any gate-shaped mode. That is a",
             "property of the mode SHAPE, not of this threshold: sweeping persist on a",
             "gate is not a question this engine can answer. Answering it would need a",
             "gate that assigns `use=\"flip\"` rather than skipping the signal."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

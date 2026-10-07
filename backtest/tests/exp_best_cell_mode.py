"""exp_best_cell_mode - build a mode for the cell the lens says is real.

THE CHAIN, AND EACH LINK'S EVIDENCE
===================================
1. exp_mode_regime.py measured the joint cells. chop is a Choppiness Efficiency
   Ratio on 1h and reads direction; atr_high is ATR% of price on 15m and does
   not. They disagree on 24.6% of IS bars and 35.5% of OOS bars, in opposite
   directions on exactly the bars that matter.

2. The cell where chop says HIGH and atr_pct says LOW is the book's best cell in
   BOTH eras: +1.76R mean IS and +2.61R mean OOS, against +1.01 and +0.77 for
   the whole book. It is 14% of trades and 24.7% / 45.7% of the net.

3. exp_best_cell_lens.py measured that cell alone under the full lens, and it
   SURVIVES the outlier bar that killed every routing arm in exp_mode_decide.py:
   profitable in both eras with its single largest trade removed (+83.4R IS,
   +83.4R OOS), and still profitable with its top three removed (+41.3 / +45.6).
   Max DD 7.6R IS / 4.7R OOS against 13.4 / 11.9 for the whole book.

So the cell is real and the existing modes cannot express it. `chop_and_atr_low`
looks like it should, but it tests `atrp < atr_low_thresh` (0.35) against
`chop_thresh`, not `atrp < atr_high_thresh` (0.65) - a different and much
tighter population. That is why it measured as a wash.

This adds `mode="chop_hi_atr_lo"`, which tests exactly the measured cell.

WHAT IS DELIBERATELY NOT CLAIMED
================================
This mode is a NEW RULE, not a new threshold. Nothing here tunes a threshold to
fit known trades, which is the failure mode that closed every arm in
exp_mode_decide.py. The thresholds are the ones the book already ships:
chop_thresh=58.0, atr_high_thresh=0.65. The only new thing is which pair of
conditions selects the branch, and that pair was chosen by a cell-level
measurement made BEFORE the mode existed.

The prior is still not good, and it should not be dressed up. If a new mode
made this book, the day-1 cell analysis has to survive it. The harness therefore
does not compare headline nets: it runs the same outlier test that killed the
others, and it reports the era-split pattern if that is what appears.

Run:  cd backtest/tests
      python -u exp_best_cell_mode.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
NEW_MODE = "chop_hi_atr_lo"
OUT_JSON = Path(__file__).parent / "_best_cell_mode.json"
OUT_MD = Path(__file__).parent / "_best_cell_mode.md"

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

    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], cfg.get("swing") or "sw10")

    def run(era, mode, persist):
        p = dict(base)
        p["mode"] = mode
        if persist is not None:
            p["exp_persist"] = persist
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        m = compute(rs, [t.get("entry_date", "") for t in tr])
        return m, rs

    ship_m, ship_rs = {}, {}
    for era in ("is", "oos"):
        ship_m[era], ship_rs[era] = run(era, "atr_high", None)

    print("=" * 104)
    print("BEST-CELL MODE - mode=%r on %s, post-C17" % (NEW_MODE, BOOK))
    print("=" * 104)
    print("thresholds are the book's own, unchanged: chop_thresh=%s atr_high_thresh=%s"
          % (base["chop_thresh"], base["atr_high_thresh"]))
    print("NOTE: this uses atr_high_thresh (0.65), NOT the existing chop_and_atr_low")
    print("      which tests atr_low_thresh (0.35) and measures as a wash.\n")

    # ------------------------------------------------------------------
    # STEP 1 - does the mode actually select the cell it was built for?
    # ------------------------------------------------------------------
    print("-" * 104)
    print("STEP 1 - DOES IT TARGET THE CELL? (every trade the new mode takes must be")
    print("          in chop_HIGH/atr_low, or the mode is not the rule we measured)")
    print("-" * 104)
    import bisect as bs
    from exp_mode_regime import joint_regime
    c_thr, a_thr = base["chop_thresh"], base["atr_high_thresh"]
    cell_ok = True
    for era in ("is", "oos"):
        p = dict(base)
        p["mode"] = NEW_MODE
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        rows, _, _, _ = joint_regime(data[era])
        lut = {r["ts"]: r for r in rows}
        in_cell = 0
        for t in tr:
            r = lut.get(int(t["entry_ts"]) - 900)
            if r and r["ch"] > c_thr and r["atrp"] < a_thr:
                in_cell += 1
        print("   %s: %d trades, %d in the target cell (%.1f%%)"
              % (era.upper(), len(tr), in_cell, 100.0 * in_cell / max(1, len(tr))))
        if in_cell != len(tr):
            cell_ok = False
    print("   -> %s" % ("mode targets exactly the measured cell"
                        if cell_ok else "MISMATCH - mode is not the rule we measured"))

    # ------------------------------------------------------------------
    # STEP 2 - the grid, with the shipping book as the reference line.
    # ------------------------------------------------------------------
    print()
    print("-" * 104)
    print("STEP 2 - GRID vs SHIPPING  (shipping atr_high: IS %d / %+.1f, OOS %d / %+.1f)"
          % (ship_m["is"]["n"], ship_m["is"]["net"], ship_m["oos"]["n"], ship_m["oos"]["net"]))
    print("-" * 104)
    print("%-22s %20s %20s %14s %14s" % ("arm", "IS n/net/dd", "OOS n/net/dd", "d IS", "d OOS"))
    rows = []
    for pv in PERSIST_GRID:
        m, rs = {}, {}
        for era in ("is", "oos"):
            m[era], rs[era] = run(era, NEW_MODE, pv)
        di = m["is"]["net"] - ship_m["is"]["net"]
        do = m["oos"]["net"] - ship_m["oos"]["net"]
        rows.append({"persist": pv, "m": m, "rs": rs, "d_is": round(di, 2), "d_oos": round(do, 2)})
        print("%-22s %20s %20s %+14.1f %+14.1f"
              % ("%s persist=%d" % (NEW_MODE, pv),
                 "%d / %+.1f / %.1f" % (m["is"]["n"], m["is"]["net"], m["is"].get("max_dd", 0)),
                 "%d / %+.1f / %.1f" % (m["oos"]["n"], m["oos"]["net"], m["oos"].get("max_dd", 0)),
                 di, do))

    ahead = [r for r in rows if r["d_is"] >= 0 and r["d_oos"] >= 0]
    print()
    if ahead:
        print("ahead in both eras: %s"
              % ", ".join("persist=%d (%+.1f IS, %+.1f OOS)" % (r["persist"], r["d_is"], r["d_oos"])
                          for r in ahead))
    else:
        print("no grid point is ahead in both eras.")

    # ------------------------------------------------------------------
    # STEP 3 - THE BAR. Same test that closed the other arms.
    # ------------------------------------------------------------------
    print()
    print("=" * 104)
    print("STEP 3 - OUTLIER BAR: net with the single largest trade removed")
    print("=" * 104)
    passed = []
    for r in rows:
        ok, detail = True, []
        for era in ("is", "oos"):
            rs = sorted(r["rs"][era], reverse=True)
            if not rs:
                continue
            rest = sum(rs[1:])
            pos = rest > 0
            ok = ok and pos
            detail.append("%s %+.1f->%+.1fR (top %.1fR) %s"
                          % (era.upper(), sum(rs), rest, rs[0], "OK" if pos else "FAILS"))
        r["survives"] = ok
        print("   persist=%-2d %s" % (r["persist"], "  ".join(detail)))
        if ok and r["persist"] in [a["persist"] for a in ahead]:
            passed.append(r)

    print()
    print("=" * 104)
    print("VERDICT")
    print("=" * 104)
    if not ahead:
        print("The new mode is WORSE than shipping in at least one era at every")
        print("persist setting. It does not become a book. The cell was real; routing")
        print("the whole book into it is not the same as taking the cell.")
        print("This is the finding, and it is a real one: a cell can be the book's best")
        print("cell and still be the wrong thing to trade, because the rest of the")
        print("book is what pays for its drawdowns.")
    else:
        for r in passed:
            print("persist=%d survives the outlier bar in both eras."
                  % r["persist"])
            for era in ("is", "oos"):
                rs = sorted(r["rs"][era], reverse=True)
                print("   %s n=%d net %+.1f mean %+.2f | without top %+.1fR | top3 %+.1fR"
                      % (era.upper(), r["m"][era]["n"], r["m"][era]["net"],
                         r["m"][era]["net"] / max(1, r["m"][era]["n"]),
                         sum(rs[1:]), sum(rs[3:])))
        print("NOTE: still not a book. Before registration this needs both-era")
        print("confirmation against a re-derived pin, and a written causal story.")

    for r in rows:
        r.pop("rs", None)
    OUT_JSON.write_text(json.dumps({"book": BOOK, "mode": NEW_MODE, "rows": rows}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# best-cell mode - %r on %s (post-C17)" % (NEW_MODE, BOOK), "",
             "New rule: decisive ONLY where chop > %s AND atr_pct < %s."
             % (c_thr, a_thr), "",
             "| persist | IS n | IS net | IS dd | OOS n | OOS net | OOS dd | d IS | d OOS |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append("| %d | %d | %.1f | %.1f | %d | %.1f | %.1f | %+.1f | %+.1f |" % (
            r["persist"], r["m"]["is"]["n"], r["m"]["is"]["net"], r["m"]["is"].get("max_dd", 0),
            r["m"]["oos"]["n"], r["m"]["oos"]["net"], r["m"]["oos"].get("max_dd", 0),
            r["d_is"], r["d_oos"]))
    lines += ["", "Shipping: IS %d / %.1f, OOS %d / %.1f."
              % (ship_m["is"]["n"], ship_m["is"]["net"], ship_m["oos"]["n"], ship_m["oos"]["net"])]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
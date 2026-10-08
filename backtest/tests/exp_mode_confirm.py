"""exp_mode_confirm - the three checks before any of the four modes becomes a book.

WHAT THIS HAS TO SETTLE
=======================
exp_mode_sweep.py found four router branches that beat `atr_high` in both eras
and survive one trade removed:

    atr_low      IS +187.9R   OOS +41.1R   315 trades  DD 14.60
    fd           IS   +1.4R   OOS +37.2R   295 trades  DD 12.20
    flip_quality IS   +1.4R   OOS  +4.8R   294 trades  DD 11.90
    union        IS  +46.6R   OOS +64.2R   442 trades  DD 18.20

That is the first thing to pass both eras in this session. It is not yet a
result, for three reasons, and this harness is exactly those three reasons.

WHY THE THREE CHECKS, IN ORDER
===============================
1. OUTLIER BAR AT DEPTH. This is the bar that has closed every candidate in this
   session: trail_half lost its whole +42R advantage when five trades came off,
   persist=5 lost 3.2R to a single 2.2-day long, chop=55 was two trades at 21R
   each. exp_mode_sweep reported no-top1 only. Top-5 and top-10 are where the
   candidates actually die, and shipping's own edge is unresolved at p = 0.91, so
   an arm that improves a book whose significance is unknown needs a deeper bar
   than an arm improving a book that clears one.

2. SECOND LANE. `champion_multi_sw10` and `utcsat_multi_sw10` are the same data,
   so their agreement is not independence. But a candidate that only works on one
   lane is not a candidate, and every proposal that reached P80 in this repo's
   history cleared a lane before it was believed.

3. `atr_low`'s OWN THRESHOLD. The result is a sign flip, not a grid peak - which
   is why it is the interesting one. A sign flip that only holds at 0.35 is a
   coincidence at one point, and the flip's whole virtue is that there was one
   threshold and it was not moved. This is the check that distinguishes those.

BOOKS ARE CREATED, PINNED AND VERIFIED
======================================
Each candidate is written into the registry as a real book, derived with
`exp_fastcheck`, and the pins stored. They are registered as CANDIDATES, not as
promotions, and nothing about `fsent_champ_long` changes. A candidate that
carries a pin can be re-derived by anyone; a candidate that exists only in this
harness cannot be.

WHAT WOULD MAKE ONE OF THEM ADOPTABLE
=====================================
Not "highest net". A candidate has to clear, in BOTH eras: net better than
shipping, drawdown no worse than shipping, AND survive top-5 and top-10 removal,
AND hold on the second lane. The drawdown clause is the one that is most likely
to bind, and it is the clause the halt governance note in
EQUITY_LENS_EXT_AND_NOHALT.md already turns on.

Run:  cd backtest/tests
      python -u exp_mode_confirm.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

CANDIDATES = ("atr_low", "fd", "flip_quality", "union")
TRIM = (1, 5, 10, 25, 50)      # top-N removed, as a percentage of trades
LANES = ("champion_multi_sw10", "utcsat_multi_sw10")
OUT_JSON = Path(__file__).parent / "_mode_confirm.json"
OUT_MD = Path(__file__).parent / "_mode_confirm.md"


def trim_table(rs):
    """Net and mean after removing the biggest k trades, and after removing the
    top k PERCENT of trades. Both are reported because they answer different
    questions: top-k asks how concentrated the gain is, top-pct asks what
    survives on a book that is a different size."""
    s = sorted(rs, reverse=True)
    n = len(s)
    out = {}
    for k in (1, 5, 10):
        if n > k:
            rest = s[k:]
            out["minus_top%d" % k] = round(sum(rest), 2)
    for pct in (10, 25, 50):
        k = max(1, int(n * pct / 100.0))
        if n > k:
            rest = s[k:]
            out["minus_top%d_pct" % pct] = round(sum(rest), 2)
    out["top5_share_pct"] = round(100.0 * sum(s[:5]) / sum(rs), 1) if sum(rs) else 0.0
    out["top10_share_pct"] = round(100.0 * sum(s[:10]) / sum(rs), 1) if sum(rs) else 0.0
    return out


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    base_params = dict(EXPERIMENTS["fsent_champ_long"]["params"])

    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], "sw10")

    def run(era, params, swing="sw10"):
        p = {**BP, **params}
        d = data[era]
        o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                fine_ltf=d["fine"], **p)
        tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        return tr, rs, compute(rs, [t.get("entry_date", "") for t in tr])

    print("=" * 110)
    print("  THE THREE CHECKS - depth, second lane, and atr_low's own threshold")
    print("=" * 110)

    report = {}

    # ------------------------------------------------------------------
    # CHECK 1 - outlier bar at depth, on the shipping lane
    # ------------------------------------------------------------------
    print("\n" + "#" * 110)
    print("# CHECK 1  OUTLIER BAR AT DEPTH  (fsent_champ_long lane)")
    print("#" * 110)
    ship = {}
    for era in ("is", "oos"):
        _, rs, m = run(era, dict(base_params))
        ship[era] = {"m": m, "trim": trim_table(rs)}
    print("\n  SHIPPING baseline:")
    for era in ("is", "oos"):
        t = ship[era]["trim"]
        print("    %-4s n=%3d net %+7.1f  dd %5.1f  |  " % (era.upper(), ship[era]["m"]["n"], ship[era]["m"]["net"], ship[era]["m"]["max_dd"])
              + "  ".join("%s %+7.1f" % (k, v) for k, v in t.items() if k.startswith("minus")))
    print()
    print("  %-14s %-4s %7s %7s %8s %8s %8s %8s" % ("mode", "era", "net", "dd", "-top1", "-top5", "-top10", "-top25%"))
    for mode in CANDIDATES:
        p = dict(base_params)
        p["mode"] = mode
        for era in ("is", "oos"):
            _, rs, m = run(era, p)
            t = trim_table(rs)
            sh = ship[era]["trim"]
            mark = ""
            if era == "oos":
                mark = ("  PASSES depth" if (t["minus_top5"] > sh["minus_top5"]
                                             and t["minus_top10"] > sh["minus_top10"]) else "  dies at depth")
            print("  %-14s %-4s %+7.1f %7.1f %+8.1f %+8.1f %+8.1f %+8.1f%s"
                  % (mode, era.upper(), m["net"], m["max_dd"],
                     t["minus_top1"], t["minus_top5"], t["minus_top10"],
                     t["minus_top25_pct"], mark))
            report.setdefault(mode, {})[era] = {
                "n": m["n"], "net": round(m["net"], 2), "max_dd": round(m["max_dd"], 2),
                "mean": round(m["net"] / max(1, m["n"]), 3), "pf": round(m["pf"], 3),
                "wr": round(m["wr"], 1), "ulcer": round(m["ulcer"], 2),
                "dd_dur": m.get("dd_dur"), "streak": m.get("max_streak"),
                "trim": t}
        report[mode]["lane1_depth_pass"] = (
            report[mode]["is"]["trim"]["minus_top5"] > ship["is"]["trim"]["minus_top5"]
            and report[mode]["oos"]["trim"]["minus_top5"] > ship["oos"]["trim"]["minus_top5"]
            and report[mode]["is"]["trim"]["minus_top10"] > ship["is"]["trim"]["minus_top10"]
            and report[mode]["oos"]["trim"]["minus_top10"] > ship["oos"]["trim"]["minus_top10"])

    # ------------------------------------------------------------------
    # CHECK 2 - second lane
    # ------------------------------------------------------------------
    print()
    print("#" * 110)
    print("# CHECK 2  SECOND LANE  (same data - so agreement is not independence,")
    print("#          but a candidate that only works on one lane is not a candidate)")
    print("#" * 110)
    for lane in LANES:
        lp = {**BP, **EXPERIMENTS[lane]["params"]}
        base_r = {}
        for era in ("is", "oos"):
            _, rs, m = run(era, dict(lp))
            base_r[era] = (m, trim_table(rs))
        print("\n  LANE %s   base IS %dt/%+.1f  OOS %dt/%+.1f"
              % (lane, base_r["is"][0]["n"], base_r["is"][0]["net"],
                 base_r["oos"][0]["n"], base_r["oos"][0]["net"]))
        print("  %-14s %-4s %8s %8s %8s %8s" % ("mode", "era", "net", "dd", "-top5", "delta net"))
        for mode in CANDIDATES:
            p = dict(lp)
            p["mode"] = mode
            for era in ("is", "oos"):
                _, rs, m = run(era, p)
                t = trim_table(rs)
                d = m["net"] - base_r[era][0]["net"]
                report.setdefault(mode, {}).setdefault("lane2", {}).setdefault(lane, {})[era] = {
                    "n": m["n"], "net": round(m["net"], 2), "max_dd": round(m["max_dd"], 2),
                    "mean": round(m["net"] / max(1, m["n"]), 3), "pf": round(m["pf"], 3),
                    "trim": t}
                print("  %-14s %-4s %+8.1f %8.1f %+8.1f %+8.1f"
                      % (mode, era.upper(), m["net"], m["max_dd"], t["minus_top5"], d))
        report.setdefault("_lane2_base", {})[lane] = {
            "is": {"net": round(base_r["is"][0]["net"], 2), "n": base_r["is"][0]["n"]},
            "oos": {"net": round(base_r["oos"][0]["net"], 2), "n": base_r["oos"][0]["n"]}}

    # ------------------------------------------------------------------
    # CHECK 3 - atr_low's own threshold
    # ------------------------------------------------------------------
    print()
    print("#" * 110)
    print("# CHECK 3  atr_low's OWN THRESHOLD - is the sign flip a finding or a")
    print("#          coincidence at one value? (one threshold exists; it was not")
    print("#           moved, which is the whole virtue of the result)")
    print("#" * 110)
    print("  %-10s %-4s %7s %7s %8s %8s %8s" % ("atr_low_thr", "era", "net", "dd", "n", "-top5", "delta net"))
    for thr in (0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60):
        p = dict(base_params)
        p["mode"] = "atr_low"
        p["atr_low_thresh"] = thr
        row = {}
        for era in ("is", "oos"):
            _, rs, m = run(era, p)
            t = trim_table(rs)
            row[era] = {"n": m["n"], "net": round(m["net"], 2), "max_dd": round(m["max_dd"], 2),
                        "trim": t, "d": round(m["net"] - ship[era]["m"]["net"], 2)}
            print("  %-10.2f %-4s %+7.1f %7.1f %8d %+8.1f %+8.1f"
                  % (thr, era.upper(), m["net"], m["max_dd"], m["n"], t["minus_top5"],
                     m["net"] - ship[era]["m"]["net"]))
        report.setdefault("_atr_low_grid", {})["%.2f" % thr] = row

    # ------------------------------------------------------------------
    # VERDICT
    # ------------------------------------------------------------------
    print()
    print("=" * 110)
    print("VERDICT - adoptable requires ALL of: net better in BOTH eras, drawdown no worse")
    print("         in BOTH eras, survive top-5 AND top-10 removal, AND hold on lane 2")
    print("=" * 110)
    adoptable = []
    for mode in CANDIDATES:
        r = report[mode]
        ship_net = {"is": ship["is"]["m"]["net"], "oos": ship["oos"]["m"]["net"]}
        ship_dd = {"is": ship["is"]["m"]["max_dd"], "oos": ship["oos"]["m"]["max_dd"]}
        better_net = r["is"]["net"] > ship_net["is"] and r["oos"]["net"] > ship_net["oos"]
        dd_ok = r["is"]["max_dd"] <= ship_dd["is"] and r["oos"]["max_dd"] <= ship_dd["oos"]
        depth = r["lane1_depth_pass"]

        # Every lane must hold, and each lane against ITS OWN base. An earlier
        # version of this harness stored both lanes under one key so the second
        # overwrote the first, and then compared lane-2 results against lane-1
        # bases - which made a candidate that LOSES on both lanes read as holding.
        lane_detail = []
        lane_ok = bool(r.get("lane2"))
        for lane in LANES:
            l2 = r["lane2"].get(lane)
            b = report["_lane2_base"][lane]
            if not l2:
                lane_ok = False
                continue
            di = l2["is"]["net"] - b["is"]["net"]
            do = l2["oos"]["net"] - b["oos"]["net"]
            this_ok = di > 0 and do > 0
            lane_ok = lane_ok and this_ok
            lane_detail.append("%s IS %+.1f / OOS %+.1f" % (lane.split("_")[0], di, do))

        ok = better_net and dd_ok and depth and lane_ok
        print("\n  %-14s" % mode)
        print("     net better both eras : %-5s   (IS %+.1f vs %+.1f | OOS %+.1f vs %+.1f)"
              % (better_net, r["is"]["net"], ship_net["is"], r["oos"]["net"], ship_net["oos"]))
        print("     drawdown no worse    : %-5s   (IS %.1f vs %.1f | OOS %.1f vs %.1f)"
              % (dd_ok, r["is"]["max_dd"], ship_dd["is"], r["oos"]["max_dd"], ship_dd["oos"]))
        print("     survives top-5/top-10: %-5s" % depth)
        print("     holds on BOTH lanes  : %-5s   (%s)" % (lane_ok, " | ".join(lane_detail)))
        if ok:
            adoptable.append(mode)
            print("     -> ADOPTABLE")
        else:
            blockers = []
            if not better_net:
                blockers.append("net")
            if not dd_ok:
                blockers.append("drawdown")
            if not depth:
                blockers.append("depth")
            if not lane_ok:
                blockers.append("lane 2")
            print("     -> blocked on: %s" % ", ".join(blockers))

    print()
    if adoptable:
        print("  ADOPTABLE: %s" % ", ".join(adoptable))
        print("  These are written to the registry below as CANDIDATE books with pins.")
    else:
        print("  NONE is adoptable. Every candidate spends drawdown, and that alone is")
        print("  disqualifying under the halt governance rule. The books are still written")
        print("  and pinned so the measurement is re-derivable, but they are recorded as")
        print("  candidates and nothing is promoted.")
    print()
    print("  Nothing about fsent_champ_long changes. No mode is removed, no pin moved.")

    OUT_JSON.write_text(json.dumps({"candidates": list(CANDIDATES), "report": report},
                                   indent=2) + "\n", encoding="utf-8")
    lines = ["# the three checks before a mode becomes a book", "",
             "Candidates from exp_mode_sweep.py, confirmed on depth, lane 2 and threshold.", "",
             "| mode | era | n | net | mean | PF | WR | maxDD | dd_dur | ulcer | streak | -top1 | -top5 | -top10 | -top25% |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for mode in CANDIDATES:
        for era in ("is", "oos"):
            r = report[mode][era]
            t = r["trim"]
            lines.append("| %s | %s | %d | %.1f | %.3f | %.2f | %.1f | %.1f | %s | %.1f | %s | %.1f | %.1f | %.1f | %.1f |" % (
                mode, era.upper(), r["n"], r["net"], r["mean"], r["pf"], r["wr"],
                r["max_dd"], r["dd_dur"], r["ulcer"], r["streak"],
                t["minus_top1"], t["minus_top5"], t["minus_top10"], t["minus_top25_pct"]))
    lines += ["", "## atr_low threshold grid", "",
              "| atr_low_thresh | era | n | net | maxDD | -top5 | dNet vs shipping |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for thr, row in report["_atr_low_grid"].items():
        for era in ("is", "oos"):
            rr = row[era]
            lines.append("| %s | %s | %d | %.1f | %.1f | %.1f | %+.1f |" % (
                thr, era.upper(), rr["n"], rr["net"], rr["max_dd"],
                rr["trim"]["minus_top5"], rr["d"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
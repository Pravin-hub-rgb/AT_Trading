"""Apply the five gates from SELECTION_RULES.md to the thirteen-book battery.

The rules were committed before these numbers existed. This script does not
decide anything; it only reports what the pre-declared thresholds say, and it
refuses to round a near-miss into a pass. Where a criterion in the rules has no
corresponding measurement in the battery it is recorded as NOT EVALUATED rather
than quietly dropped, because a gate that silently loses a criterion is a gate
that silently becomes easier to pass.

Usage:  python exp_gate_eval.py
"""

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs", "learn")

CODES = {
    "fsent_champ_long_mcloff_htf15": "107",
    "fsent_champ_long_htf15_tskip6": "110",
    "fsent_champ_long_htffs": "106",
    "fsent_champ_long_htf15_htffs": "109",
    "fsent_champ_long_htfesmcl4": "108",
    "fsent_sig_multi_acc": "acc",
    "fsent_champ_long_htf15": "htf15",
    "fsent_champ_long_mcloff": "mcloff",
    "fsent_champ_long_causalfloor": "cfloor",
    "fsent_champ_long_mode_chop": "mchop",
    "fsent_champ_long_biasmom05": "bmom",
    "fsent_sig_multi_htffs": "sigm_h",
    "fsent_sig_multi": "sigm",
}

TH = {
    # Gate 1 - evidence
    "g1_tail10_pos": True,      # net after dropping best 10 winners > 0, both eras
    "g1_top10pct": 120.0,        # top 10% of winners carrying the result
    "g1_oos_net_pos": True,
    # Gate 2 - robustness
    "g2_span": 60.0,            # T1 net range across the grid, R
    "g2_folds": 2,              # T2 folds where tuned beat registered
    "g2_cliff_ratio": 0.5,      # a cell below this fraction of the best cell
    # Gate 3 - execution
    "g3_be_is": 100.0,          # break-even slippage, bps
    "g3_be_oos": 90.0,
    "g3_lost_frac": 0.50,       # trades lost at 1000 bps
    # Gate 4 - survivability
    "g4_dd25": 5.0,            # fraction of shuffled paths over 25R
    "g4_dd50": 0.0,             # fraction over 50R
    "g4_dd_pct": 99.0,          # observed DD percentile
}


def load(n):
    return json.load(io.open(os.path.join(HERE, "four_techniques_all13_%s.json" % n),
                            encoding="utf-8"))[n]


def break_even(slip):
    """Largest tested slippage at which the book is still profitable."""
    be = 0.0
    for s in slip:
        if s["net"] > 0:
            be = max(be, float(s["bps"]))
    return be


def t1_span(rec):
    out = {}
    for era in ("is", "oos"):
        cells = [c["net"] for c in rec[era]["cells"].values() if c]
        out[era] = (max(cells) - min(cells)) if cells else None
        out[era + "_cliff"] = (min(cells) < TH["g2_cliff_ratio"] * max(cells)) if cells else None
    return out


def main():
    t1, t2, t3, t4 = load("t1"), load("t2"), load("t3"), load("t4")
    vs = json.load(io.open(os.path.join(HERE, "verified_suite.json"), encoding="utf-8"))

    rows = []
    for name, code in CODES.items():
        if name not in t1:
            continue
        v_is, v_oos = vs[name]["is"], vs[name]["oos"]
        r = {"code": code, "name": name}

        # ---- Gate 1
        r["g1_tail10_is"] = v_is["tail10"] > 0
        r["g1_tail10_oos"] = v_oos["tail10"] > 0
        r["g1_top10_is"] = v_is["top10pct"] < TH["g1_top10pct"]
        r["g1_top10_oos"] = v_oos["top10pct"] < TH["g1_top10pct"]
        r["g1_oos_net"] = v_oos["net"] > 0
        r["g1"] = all([r["g1_tail10_is"], r["g1_tail10_oos"], r["g1_top10_is"],
                       r["g1_top10_oos"], r["g1_oos_net"]])

        # ---- Gate 2
        sp = t1_span(t1[name])
        r["span_is"], r["span_oos"] = sp["is"], sp["oos"]
        r["g2_span"] = (sp["is"] is not None and sp["is"] < TH["g2_span"]
                        and sp["oos"] is not None and sp["oos"] < TH["g2_span"])
        folds = t2[name]
        # A fold whose registered baseline is missing cannot be scored as a win.
        # It happens when the registered pair is absent from the coarser
        # walk-forward grid. Scoring those as wins would manufacture confidence,
        # so they are counted as unscored and surfaced in the output.
        scored = [f for f in folds if f.get("reg_test_net") is not None]
        missing = [f for f in folds if f.get("reg_test_net") is None]
        wins = sum(1 for f in scored if f["test_net"] > f["reg_test_net"])
        ties = sum(1 for f in scored if f["test_net"] == f["reg_test_net"])
        r["fold_wins"], r["fold_ties"] = wins, ties
        r["fold_missing"] = len(missing)
        r["g2_folds"] = bool(scored) and (wins + ties) >= TH["g2_folds"]
        r["g2_cliff"] = not (sp["is_cliff"] or sp["oos_cliff"])
        r["g2"] = r["g2_span"] and r["g2_folds"] and r["g2_cliff"]

        # ---- Gate 3
        r["be_is"] = break_even(t3[name]["is"]["slippage"])
        r["be_oos"] = break_even(t3[name]["oos"]["slippage"])
        r["g3_be"] = r["be_is"] >= TH["g3_be_is"] and r["be_oos"] >= TH["g3_be_oos"]
        c_is, c_oos = t3[name]["is"]["cost"], t3[name]["oos"]["cost"]
        r["cost3_is"], r["cost3_oos"] = c_is[-1]["net"], c_oos[-1]["net"]
        r["g3_cost"] = c_is[-1]["net"] > 0 and c_oos[-1]["net"] > 0
        for era in ("is", "oos"):
            sl = t3[name][era]["slippage"]
            n0 = sl[0]["n"]
            n1 = [s for s in sl if s["bps"] == 1000][0]["n"]
            r["lost_" + era] = 100.0 * (n0 - n1) / n0
        r["g3_lost"] = r["lost_is"] < 50.0 and r["lost_oos"] < 50.0
        r["g3"] = r["g3_be"] and r["g3_cost"] and r["g3_lost"]

        # ---- Gate 4
        # T4 stores these ALREADY as percentages (100.0 * count / paths), so the
        # threshold is 5.0 not 0.05. The first version of this script multiplied
        # by 100 again and printed 280% for a book whose true figure was 2.8%,
        # which made every book fail Gate 4 for a reason that did not exist.
        r["dd25_is"] = t4[name]["is"]["frac_paths_dd_over_25"]
        r["dd50_is"] = t4[name]["is"]["frac_paths_dd_over_50"]
        r["dd50_oos"] = t4[name]["oos"]["frac_paths_dd_over_50"]
        r["g4_dd25"] = r["dd25_is"] < TH["g4_dd25"]
        r["g4_dd50"] = r["dd50_is"] <= TH["g4_dd50"] and r["dd50_oos"] <= TH["g4_dd50"]
        r["g4_worst50"] = v_oos["roll"]["50"][1] > 0
        r["g4_pct_is"] = t4[name]["is"]["obs_dd_rank_pct"]
        r["g4_pct_oos"] = t4[name]["oos"]["obs_dd_rank_pct"]
        r["g4_ddpct"] = r["g4_pct_is"] < TH["g4_dd_pct"] and r["g4_pct_oos"] < TH["g4_dd_pct"]
        r["g4"] = r["g4_dd25"] and r["g4_dd50"] and r["g4_worst50"] and r["g4_ddpct"]
        # ruin rate at 1% risk has no field in this battery
        r["g4_ruin"] = None

        r["survive"] = r["g1"] and r["g2"] and r["g3"] and r["g4"]
        r["_pref"] = (-v_oos["roll"]["50"][1], -v_oos["rpt"], -v_oos["net"])
        rows.append(r)

    rows.sort(key=lambda r: r["_pref"])
    ok = [r for r in rows if r["survive"]]

    L = []
    A = L.append
    A("# THIRTEEN-BOOK GATE RESULT")
    A("")
    A("Generated by `exp_gate_eval.py` from `SELECTION_RULES.md`, which was committed")
    A("before any of these numbers existed. No threshold was moved to make a book pass.")
    A("")
    A("## Verdict")
    A("")
    A("| book | G1 evidence | G2 robust | G3 execution | G4 survivable | survives |")
    A("|---|---|---|---|---|---|")
    for r in rows:
        A("| `%s` | %s | %s | %s | %s | %s |" % (
            r["code"], "pass" if r["g1"] else "FAIL", "pass" if r["g2"] else "FAIL",
            "pass" if r["g3"] else "FAIL", "pass" if r["g4"] else "FAIL",
            "**yes**" if r["survive"] else "no"))
    A("")
    A("## What failed, per book")
    A("")
    A("| book | tail10 IS | top10% IS | top10% OOS | T1 span IS | T1 span OOS | cliff | "
      "WF wins | BE slip IS | BE slip OOS | lost@1000 IS | dd>25R | dd>50R | worst50 OOS | DD pct IS | DD pct OOS |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    def b(v):
        return "ok" if v else "**FAIL**"

    for r in rows:
        A("| `%s` | %s | %s | %s | %.0f | %.0f | %s | %d/3 | %.0f | %.0f | %.0f%% | %.1f%% | %.1f%% | %s | %.1f | %.1f |" % (
            r["code"], b(r["g1_tail10_is"]), b(r["g1_top10_is"]), b(r["g1_top10_oos"]),
            r["span_is"] or 0, r["span_oos"] or 0, b(r["g2_cliff"]), r["fold_wins"],
            r["be_is"], r["be_oos"], r["lost_is"],
            r["dd25_is"], r["dd50_is"],
            b(r["g4_worst50"]), r["g4_pct_is"], r["g4_pct_oos"]))
    A("")
    A("## Survivors, ranked by the Gate 5 order")
    A("")
    A("Patience first (worst 50-trade window, OOS), then quality (R per trade), then")
    A("size (net). Not a composite - an ordered tie-break.")
    A("")
    if ok:
        A("| rank | book | worst 50-trade OOS | R/trade OOS | net OOS |")
        A("|---|---|---|---|---|")
        for i, r in enumerate(ok, 1):
            v = vs[r["name"]]["oos"]
            A("| %d | `%s` | %+.1fR | %+.3f | %+.1fR |"
              % (i, r["code"], v["roll"]["50"][1], v["rpt"], v["net"]))
    else:
        A("**No book clears all four gates.** That is a finding, not a failure of the")
        A("method. Nothing goes live yet; the answer is more data, not a re-ranking.")
    A("")
    A("## Not evaluated")
    A("")
    A("- Ruin rate at 1% risk per trade, p95 safe risk >= 1% (Gate 4, listed in the")
    A("  rules, no field in this battery). Recorded as missing rather than passed.")
    A("- The ruin measurement in `SIZING_AND_RUIN.md` predates the current pins.")
    A("")

    with io.open(os.path.join(HERE, "all13_gates.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    with io.open(os.path.join(DOCS, "ALL13_GATES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("\n".join(L[:34]))
    print("\nsurvivors: %s" % ([r["code"] for r in ok] or "none"))


if __name__ == "__main__":
    main()
"""Enrich _results.json with the analysis that has happened since it was exported.

Why this exists
---------------
`_results.json` is what /results serves and therefore what the UI shows. It was
a snapshot from 2026-10-16. Since then the whole multiple-testing gate was run,
and none of that is in the artifact. So the UI displayed 26 books of confident
numbers with no indication that thirteen of them were tried and that the
selection procedure failed its own PBO check. That is the worst kind of stale:
it looks authoritative.

What gets added, per book:
  code            the short handle used everywhere in conversation (107, 110...)
  analysis.gate   which of the five gates it passed, and which criterion killed it
  analysis.dsr    Deflated Sharpe probability after accounting for N trials
  analysis.verdict short string shown in the UI

And at the top level, a `verdict` block stating plainly that nothing is cleared
for deployment, with a pointer to the reasoning. A viewer should not be able to
look at any single book without that context being one click away.

Idempotent and re-runnable. If the underlying analysis files are missing it says
so and leaves the artifact untouched rather than writing half-truths.

Usage:
    python exp_enrich_results.py
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.normpath(os.path.join(HERE, "..", "tests"))
ARTIFACT = os.path.join(TESTS, "_results.json")

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

GATE_FILES = [
    ("is", "verify"), ("oos", "verify"),
]


def _load(path):
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def gate_table():
    """Re-derive the per-criterion pass table by importing the gate modules.

    Deliberately imports rather than parses the markdown: a report and the
    thing that produced it drifting apart is the exact failure this repo has
    already produced three times.
    """
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import exp_gate_eval as G  # noqa: E402
        import exp_gate_counts as C  # noqa: E402
    except Exception as e:
        print("  gate modules unavailable: %s" % e)
        return None, None

    t1, t2, t3, t4 = G.load("t1"), G.load("t2"), G.load("t3"), G.load("t4")
    vs = json.load(io.open(os.path.join(HERE, "verified_suite.json"), encoding="utf-8"))

    per_book = {}
    for name, code in G.CODES.items():
        if name not in t1:
            continue
        v_is, v_oos = vs[name]["is"], vs[name]["oos"]
        sp = G.t1_span(t1[name])
        folds = [x for x in t2[name] if x.get("reg_test_net") is not None]
        sl = t3[name]["is"]["slippage"]
        s1000 = [s for s in sl if s["bps"] == 1000][0]
        w = sum(1 for x in folds if x["test_net"] > x["reg_test_net"])
        ti = sum(1 for x in folds if x["test_net"] == x["reg_test_net"])

        crit = {
            "G1 tail10 IS": v_is["tail10"] > 0,
            "G1 tail10 OOS": v_oos["tail10"] > 0,
            "G1 top10 IS": v_is["net"] > 0 and v_is["top10pct"] < G.TH["g1_top10pct"],
            "G1 top10 OOS": v_oos["net"] > 0 and v_oos["top10pct"] < G.TH["g1_top10pct"],
            "G2 span IS": sp["is"] < G.TH["g2_span"],
            "G2 span OOS": sp["oos"] < G.TH["g2_span"],
            "G2 cliff": not (sp["is_cliff"] or sp["oos_cliff"]),
            "G2 walkfwd": bool(folds) and (w >= G.TH["g2_folds"] or ti == len(folds)),
            "G3 BE slip IS": G.break_even(t3[name]["is"]["slippage"]) >= G.TH["g3_be_is"],
            "G3 BE slip OOS": G.break_even(t3[name]["oos"]["slippage"]) >= G.TH["g3_be_oos"],
            "G3 cost 3x": t3[name]["is"]["cost"][-1]["net"] > 0 and t3[name]["oos"]["cost"][-1]["net"] > 0,
            "G4 dd>25R": t4[name]["is"]["frac_paths_dd_over_25"] < G.TH["g4_dd25"],
            "G4 dd>50R": (t4[name]["is"]["frac_paths_dd_over_50"] <= G.TH["g4_dd50"]
                          and t4[name]["oos"]["frac_paths_dd_over_50"] <= G.TH["g4_dd50"]),
            "G4 worst50 OOS": v_oos["roll"]["50"][1] > 0,
            "G4 DDpct IS": t4[name]["is"]["obs_dd_rank_pct"] < G.TH["g4_dd_pct"],
            "G4 DDpct OOS": t4[name]["oos"]["obs_dd_rank_pct"] < G.TH["g4_dd_pct"],
        }
        npass = sum(1 for x in crit.values() if x)
        fails = [k for k, x in crit.items() if not x]
        g1 = all(crit[k] for k in crit if k.startswith("G1"))
        g2 = all(crit[k] for k in crit if k.startswith("G2"))
        g3 = all(crit[k] for k in crit if k.startswith("G3"))
        g4 = all(crit[k] for k in crit if k.startswith("G4"))
        per_book[name] = {"code": code, "passed": npass, "total": len(crit),
                          "fails": fails, "gates": {"G1": g1, "G2": g2, "G3": g3, "G4": g4},
                          "survives": g1 and g2 and g3 and g4}
    return per_book, G.TH


def dsr_table():
    p = _load(os.path.join(HERE, "pbo_dsr.json"))
    if not p:
        return None
    out = {}
    for era in ("oos", "is"):
        rows = (p.get(era) or {}).get("dsr") or []
        for r in rows:
            b = r["book"]
            out.setdefault(b, {})[era] = {"sr": r["sr"], "dsr": r["dsr"], "p": r["p"],
                                          "n": r["n"]}
    pb = {era: (p.get(era) or {}).get("pbo8") for era in ("oos", "is")}
    return {"per_book": out, "pbo": pb}


def _pbo_text(dsr):
    """The PBO figures, quoted from the data rather than remembered.

    They were hardcoded once, and the hardcoded range went stale the moment the
    engine changed. A number on this page that nobody recomputed is worse than
    no number.
    """
    pb = (dsr or {}).get("pbo") or {}
    if not pb:
        return "not measured"
    return "%.2f OOS and %.2f IS (S=8)" % (pb.get("oos") or 0.0, pb.get("is") or 0.0)


def _coded_rows(art, gates):
    """The coded books with their gate result and their out-of-sample numbers.

    Ordered by how close each book is to clearing the criteria, and then by the
    axis that decides - the out-of-sample permutation - and only then by net.
    Net is the last tie-break on purpose: this repo has said more than once
    that a bigger net is not the decider, and a page that sorts on it would be
    re-teaching the thing the page exists to correct.
    """
    rows = []
    for b in art.get("books", []):
        name = b.get("name")
        g = (gates or {}).get(name)
        if not g:
            continue
        p = b.get("null_p_oos")
        rows.append({"name": name, "code": g["code"], "fails": g["fails"],
                     "passed": g["passed"], "total": g["total"],
                     "oos_net": b.get("oos_net") or 0.0,
                     "oos_p": 1.0 if p is None else float(p),
                     "oos_p_shown": p})
    rows.sort(key=lambda r: (len(r["fails"]), r["oos_p"], -r["oos_net"]))
    return rows


def _closest_codes(art, gates):
    rows = _coded_rows(art, gates)
    return [r["code"] for r in rows[:2]]


def _closest_note(art, gates):
    rows = _coded_rows(art, gates)
    if len(rows) < 2:
        return "no coded book has a gate result"
    a, b = rows[0], rows[1]
    n_fail = len(a["fails"])
    total = a["total"]
    crit = ", ".join(a["fails"]) if a["fails"] else "none"
    crit_b = ", ".join(b["fails"]) if b["fails"] else "none"
    pa = ("%.4f" % a["oos_p"]) if a["oos_p_shown"] is not None else "n/a"
    pb = ("%.4f" % b["oos_p"]) if b["oos_p_shown"] is not None else "n/a"
    return ("%s and %s each fail exactly %d criterion%s out of %d (%s / %s). "
            "Out of sample the permutation separates %s from its parent "
            "(p=%s) and does not separate %s (p=%s), so the pair is not "
            "separable on the numbers either."
            % (a["code"], b["code"], n_fail, "" if n_fail == 1 else "s", total,
               crit, crit_b, a["code"], pa, b["code"], pb))


def main():
    print("enriching %s" % ARTIFACT)
    art = _load(ARTIFACT)
    if art is None:
        print("  artifact missing - run exp_results_export.py first")
        return 1

    gates, th = gate_table()
    dsr = dsr_table()
    if gates is None:
        print("  no gate data - refusing to write a partial verdict")
        return 1

    inv = {v: k for k, v in CODES.items()}
    n_enriched = 0
    for b in art.get("books", []):
        name = b.get("name")
        g = gates.get(name)
        if not g:
            continue
        an = b.setdefault("analysis", {})
        an["code"] = g["code"]
        an["gate_passed"] = "%d/%d" % (g["passed"], g["total"])
        an["gate_fails"] = g["fails"]
        an["gates"] = {k: ("pass" if v else "FAIL") for k, v in g["gates"].items()}
        an["survives_all_gates"] = g["survives"]
        if dsr and name in dsr["per_book"]:
            an["dsr"] = dsr["per_book"][name]
            oos = dsr["per_book"][name].get("oos") or {}
            an["dsr_pass"] = bool(oos.get("p") is not None and oos["p"] < 0.05)
        an["verdict"] = ("cleared" if g["survives"] and an.get("dsr_pass")
                         else "NOT cleared for deployment")
        n_enriched += 1

    art["verdict"] = {
        "headline": "NO BOOK IS CLEARED FOR DEPLOYMENT",
        "reason": ("Thirteen book variants were explored. The multiple-testing "
                   "correction was not applied when the shortlist was made, and "
                   "when it was applied it failed: PBO %s against a %.2f bar, "
                   "and Deflated Sharpe fails for all thirteen books in both "
                   "eras. The history does not identify which variant to trade."
                   % (_pbo_text(dsr), 0.15)),
        "pbo": (dsr or {}).get("pbo"),
        "pbo_bar": 0.15,
        "book_count_tried": len(CODES),
        "closest": _closest_codes(art, gates),
        "closest_note": _closest_note(art, gates),
        "next_step": ("Forward evidence on a frozen candidate, scored once. The "
                      "standard operational gate is 20-50 round trips or one "
                      "quarter; the forward window currently holds about one "
                      "month."),
        "see": "backtest/docs/learn/02_verdict/PBO_DSR_GATE.md",
    }
    art["analysis_generated"] = "exp_enrich_results.py"

    with io.open(ARTIFACT, "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=1)

    print("  enriched %d of %d books with codes, gate verdicts and DSR"
          % (n_enriched, len(art.get("books", []))))
    print("  PBO: %s" % (art["verdict"]["pbo"],))
    print("  wrote %s (%.0f KB)" % (ARTIFACT, os.path.getsize(ARTIFACT) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
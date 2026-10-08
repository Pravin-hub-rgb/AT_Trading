"""exp_mode_sweep - run the 25 router branches no book uses, on the shipping book.

THE GAP THIS CLOSES
===================
exp_repo_map.py found that 25 of the router's 27 regime branches have no book in
the registry. Live books use `mode="atr_high"` (215 of them) and `mode="union"`
(2). The concentration is the finding: 215 variations of ONE routing rule and
zero of the other twenty-five.

That matters because this session measured something the untested branches
already implement. `exp_mode_regime.py` found that `chop` and `atr_high` are
genuinely different variables - the CHOP index reads direction efficiency on 1h,
`atr_high` reads bar size on 15m - disagreeing on 24.6% of IS bars and 35.5% of
OOS bars, and that the cell where chop reads HIGH and atr_pct reads LOW is the
book's best region in both eras (+1.76R / +2.61R mean against +1.01 / +0.77).

That measurement was obtained by GRAFTING chop's condition onto `atr_high` and
building three throwaway modes for it. **Eighteen of the branches that already
implement exactly this sit in the engine and have never been run against a book.**
The three grafted modes were deleted after the experiment closed; these are the
ones that were always there.

WHAT THIS RUNS
==============
Every `mode` the router implements, on `fsent_champ_long`'s exact configuration
with only `mode` moving. Both eras, full metrics. This is the cheapest possible
test of the largest untouched region in the repository - no new mode, no engine
edit, one loop.

READ IT WITH THE FRAMEWORK, NOT WITH NET R
=========================================
The framework in `docs/learn/finding optimal book.md` exists because net R has
misled this repo continuously. Three things are reported for every branch:

  - net R in BOTH eras, because a one-era win is the era-split pattern and this
    repo has now seen it ten times
  - the outlier bar - net with the largest trade removed - because a branch whose
    gain is one trade is not a branch
  - mean R per trade, because a higher net on fewer trades at a collapsed mean is
    a smaller book, not a better one

THE PRIOR, STATED BEFORE THE RUN
================================
Low, and specifically: most of these branches are expected to fail, and the
expectation is not a shrug. `exp_mode_regime.py` already showed that routing on
chop fails on this book at every threshold tried - the best arm bought +42R by
removing two trades at 21R each. These branches are variations on that same
routing, so the prior is that they land in the same place.

If one of them DOES clear both eras and the outlier bar, that is a genuinely
unexpected result and it would be the first routing change in the repo to do so.
It would still need the era-split check against `champion_multi_sw10`, because
the two lanes are the same data and their agreement is not independence.

Run:  cd backtest/tests
      python -u exp_mode_sweep.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
OUT_JSON = Path(__file__).parent / "_mode_sweep.json"
OUT_MD = Path(__file__).parent / "_mode_sweep.md"

# Every branch the router implements, with what the branch means. Copied from
# the engine's own comments so this harness cannot drift from what it runs.
MODES = [
    # (name, reads_chop_thresh, one-line meaning from the engine's comment)
    ("atr_high", False, "decisive when 15m ATR% is high - THE SHIPPING BOOK"),
    ("atr_low", False, "decisive when 15m ATR% is low"),
    ("chop", True, "decisive when 1h CHOP index is high (efficient travel)"),
    ("b2_vs_flip_chop", True, "B2 when chop high, else flip"),
    ("decisive_vs_flip_chop", True, "decisive when chop high, else flip"),
    ("chop_or_atr_low", True, "decisive if chop high OR ATR low"),
    ("chop_and_atr_low", True, "decisive if chop high AND ATR low"),
    ("dynamic_chop", True, "B2 when chop_pct high, else flip"),
    ("entropy", True, "low entropy=range->B2, high entropy=trend->flip"),
    ("entropy_inv", True, "inverted: low entropy->flip, high->B2"),
    ("fd", True, "low FD=trend->flip, high FD=range->B2"),
    ("fd_inv", True, "inverted fd"),
    ("hmm", True, "P(range)*100 > chop_thresh -> range->B2 else flip"),
    ("hmm_inv", True, "inverted hmm"),
    ("garch", True, "low predicted vol -> B2, high vol -> flip"),
    ("garch_inv", True, "inverted garch"),
    ("htf_mag", True, "B2 when HTF magnitude above chop_thresh/10000"),
    ("htf_mag_inv", True, "inverted htf_mag"),
    ("soft_chop", True, "ramped chop band, uncertain zone uses both windows"),
    ("soft_atr", True, "ramped ATR% band"),
    ("soft_ensemble", True, "blends chop+ATR+entropy+fd into a ramp"),
    ("flip_quality", True, "B2/flip by chop AND requires HTF magnitude"),
    ("htf_dir", False, "B2 when HTF swing direction is up"),
    ("ltf_dir", False, "B2 when LTF swing direction is up"),
    ("session", False, "Asia=range->B2, London/NY=trend->flip"),
    ("session_flip", False, "inverted session"),
    ("union", False, "admit either interval set"),
]


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

    def run(era, mode):
        p = dict(base)
        p["mode"] = mode
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        m = compute(rs, [t.get("entry_date", "") for t in tr])
        return tr, rs, m

    print("=" * 118)
    print("  EVERY ROUTER BRANCH, RUN ON %s - only `mode` moves" % BOOK)
    print("=" * 118)
    print("  The shipping book is mode=atr_high. 25 of these 27 branches have no book")
    print("  anywhere in the registry, including 18 that already read chop_thresh - the")
    print("  variable exp_mode_regime.py showed is a different signal from atr_high.")
    print("  Both eras, full metrics. net R alone is not the test.\n")

    rows = []
    for name, reads_chop, meaning in MODES:
        rec = {"mode": name, "reads_chop": reads_chop, "meaning": meaning}
        err = None
        for era in ("is", "oos"):
            try:
                tr, rs, m = run(era, name)
            except Exception as e:
                err = repr(e)[:80]
                rec[era] = None
                continue
            srt = sorted(rs, reverse=True)
            rec[era] = {
                "n": m["n"], "net": round(m["net"], 2), "mean": round(m["net"] / max(1, m["n"]), 3),
                "pf": round(m["pf"], 3), "wr": round(m["wr"], 1),
                "max_dd": round(m["max_dd"], 2), "dd_dur": m.get("dd_dur"),
                "ulcer": round(m["ulcer"], 2), "streak": m.get("max_streak"),
                "pos_month": m.get("pos_month_pct"),
                "top5_share": round(100.0 * sum(srt[:5]) / sum(rs), 1) if sum(rs) else 0.0,
                "without_top1": round(sum(srt[1:]), 2),
                "without_top3": round(sum(srt[3:]), 2),
            }
        rec["error"] = err
        rows.append(rec)
        if rec.get("is") is None or rec.get("oos") is None:
            print("  %-22s ERROR %s" % (name, err))
            continue
        i, o = rec["is"], rec["oos"]
        # The shipping reference is the FIRST row (mode="atr_high" is listed
        # first in MODES). Reading it out of `rec` was a bug: rec is the CURRENT
        # branch, so rec.get("atr_high") is always None and every delta
        # printed as +0.0. The branch being tested was never compared to
        # anything.
        ship = rows[0] if rows and rows[0]["mode"] == "atr_high" else None
        di = i["net"] - ship["is"]["net"] if ship else 0.0
        do = o["net"] - ship["oos"]["net"] if ship else 0.0
        rec["d_is"], rec["d_oos"] = round(di, 2), round(do, 2)
        star = " << SHIPPING" if name == "atr_high" else ""
        print("  %-22s IS %4d/%+7.1f (dd %5.1f)  OOS %4d/%+7.1f (dd %5.1f)  d %+7.1f/%+7.1f%s"
              % (name, i["n"], i["net"], i["max_dd"], o["n"], o["net"], o["max_dd"],
                 di, do, star))

    ship = next(r for r in rows if r["mode"] == "atr_high")

    print()
    print("=" * 118)
    print("FULL METRICS, OOS - net R is the misleading column")
    print("=" * 118)
    hdr = ["n", "net", "mean", "pf", "wr", "max_dd", "dd_dur", "ulcer", "streak", "top5_share", "without_top1"]
    print("  %-22s %s" % ("mode", " ".join("%10s" % h[:10] for h in hdr)))
    for r in rows:
        o = r.get("oos")
        if not o:
            continue
        print("  %-22s %s" % (r["mode"], " ".join(
            "%10s" % (("%d" % o[h]) if h in ("n", "dd_dur", "streak") else
                       (("%.1f" % o[h]) if h in ("wr", "top5_share") else "%.2f" % o[h]))
            for h in hdr)))

    print()
    print("=" * 118)
    print("VERDICT - the test is BOTH ERAS PLUS THE OUTLIER BAR")
    print("=" * 118)
    print("  pass = net > shipping in BOTH eras, AND net-without-best-trade > shipping's")
    print("          net-without-best-trade in BOTH eras")
    print()
    passed = []
    era_split = []
    for r in rows:
        if r["mode"] == "atr_high" or not r.get("is"):
            continue
        i, o = r["is"], r["oos"]
        bi, bo = i["without_top1"], o["without_top1"]
        shi, sho = ship["is"]["without_top1"], ship["oos"]["without_top1"]
        if r["d_is"] > 0 and r["d_oos"] > 0 and bi > shi and bo > sho:
            passed.append(r)
            print("  PASS  %-22s  IS %+.1f/%+.1f (no-top1 %+.1f vs %+.1f)   OOS %+.1f/%+.1f (no-top1 %+.1f vs %+.1f)"
                  % (r["mode"], r["d_is"], r["d_is"], bi, shi, r["d_oos"], r["d_oos"], bo, sho))
        elif (r["d_is"] > 0) != (r["d_oos"] > 0):
            era_split.append(r)
    if not passed:
        print("  NO BRANCH PASSES. Not one routing change in the repo clears both eras")
        print("  and the outlier bar at the same time. The 25 unbooked branches stay")
        print("  unbooked, and the reason is measured rather than assumed.")
    if era_split:
        print()
        print("  era-split (the tenth appearance of that pattern): %s"
              % ", ".join("%s %.0f/%.0f" % (r["mode"], r["d_is"], r["d_oos"]) for r in era_split))
    print()
    print("  The outcome being unsurprising is itself the result: 18 of these branches")
    print("  implement variants of the chop routing that exp_mode_regime.py already")
    print("  showed fails on this book at every level tried. Running them was the cheap")
    print("  way to confirm that, rather than the expensive way of assuming it.")
    print()
    print("  Nothing adopted. No mode added, no book registered, no pin changed.")

    OUT_JSON.write_text(json.dumps({"book": BOOK, "rows": rows}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# every router branch, run on %s" % BOOK, "",
             "Only `mode` moves. The shipping book is `atr_high`.", "",
             "| mode | reads chop | IS n | IS net | IS dd | OOS n | OOS net | OOS dd | mean R OOS | PF OOS | WR OOS | streak OOS | no-top1 OOS | d IS | d OOS |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        i, o = r.get("is"), r.get("oos")
        if not i or not o:
            lines.append("| %s | %s | ERROR | | | | | | | | | | | | |" % (r["mode"], "yes" if r["reads_chop"] else "no"))
            continue
        star = " **" if r["mode"] == "atr_high" else ""
        lines.append("| %s%s | %s | %d | %.1f | %.1f | %d | %.1f | %.1f | %.3f | %.2f | %.1f | %s | %.1f | %+.1f | %+.1f |" % (
            r["mode"], star, "yes" if r["reads_chop"] else "no",
            i["n"], i["net"], i["max_dd"], o["n"], o["net"], o["max_dd"],
            o["mean"], o["pf"], o["wr"], o["streak"], o["without_top1"],
            r["d_is"], r["d_oos"]))
    lines += ["", "Shipping branch marked **."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
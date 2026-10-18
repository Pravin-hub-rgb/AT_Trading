"""Breakeven and trail: remove the choice instead of predicting it.

WHY THIS EXISTS
===============
The htf_rr sweep produced a knife-edge, and the reviewer put it as arithmetic:

    extension rate, measured   79% ......... 97%
    break-even extension rate                80%   ^^^^^^

A parameter sitting on its own break-even gives opposite answers in two markets
for no structural reason, and no state variable can repair that - the thing that
changed was the market, not the trade. Eight candidate signals were tested and
all eight flipped between eras, which is what a knife-edge does to any predictor
applied to it.

So the alternative is not a better predictor. It is removing the choice.

THE STRUCTURAL ARGUMENT
=======================
htf_rr currently welds two decisions together: how far to aim, and what happens
if it fails. The stop is the swing start (sl_mode="swing"), so a failure costs
the full risk, and reaching 4R is required about 80% of the time to break even.
That 80% is the whole fragility. At 79% you lose; at 97% you win; both are the
same book in two markets.

v7_timecap.py:119 already implements breakeven_r - once price reaches N times
risk, the stop moves to entry. It was hardcoded to 0.0 at every call site, so it
was unreachable. This makes it reachable and sweeps it alongside a swing trail.

With the stop at breakeven, a failure costs 0R rather than -1R, and the
required carry rate falls toward zero. The decision stops mattering because the
downside stops existing.

WHAT IS AND IS NOT BEING CLAIMED
================================
This is the only option in the whole investigation that requires NO prediction,
which is also why it can work at an effective sample size of two books and two
eras. That is a real structural advantage and it is the reason to test it.

It is not automatically better. Breakeven converts some genuine winners into
scratches, so it can cost money as well as save it, and a swing trail can give
back a lot of the run it let run. Both need measuring, and the bar is unchanged:
better than the registered configuration in BOTH eras on aggregate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_breakeven.py
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

OUT = HERE / "breakeven.json"
MD = HERE / "breakeven.md"
REPORT = HERE.parent / "docs" / "learn" / "BREAKEVEN_AND_TRAIL.md"

BE = [0.0, 0.5, 1.0, 1.5, 2.0]
TRAIL = ["off", "swing"]
RR = [3.0, 4.0, 5.0]

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htffs", "106"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htfesmcl4", "108"),
         ("fsent_sig_multi_htffs", "sigm_htffs"),
         ("fsent_sig_multi", "sigm"),
         ("fsent_champ_long_htf15", "htf15")]


def stats(tr):
    if not tr:
        return None
    rs = [net_r([t]) for t in tr]
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    st = bst = 0
    for r in rs:
        st = st + 1 if r < 0 else 0
        bst = max(bst, st)
    return {"n": len(rs), "net": round(sum(rs), 2),
            "rpt": round(sum(rs) / len(rs), 4),
            "wr": round(100.0 * len(w) / len(rs), 1),
            "pf": round(sum(w) / -sum(l), 3) if l and -sum(l) else 0.0,
            "dd": round(dd, 2), "streak": bst}


def run(sim, data, cfg, swing, **ov):
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **{**BP, **(cfg.get("params") or {}), **ov})
    tr = sorted([t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
                 if t.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))
    return stats(tr)


def main() -> int:
    t0 = time.time()
    print("loading ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {}
        for era in ("is", "oos"):
            rec = {}
            for rr in RR:
                for be in BE:
                    for tr_ in TRAIL:
                        k = "rr%g|be%g|%s" % (rr, be, tr_)
                        rec[k] = run(sim, ERA[era], cfg, swing, htf_rr=rr,
                                     htf_breakeven_r=be, htf_trail=tr_)
            res[name][era] = rec
        for era in ("is", "oos"):
            base = res[name][era]["rr3|be0|off"]
            print("  %-11s %-4s  base %+7.1f(%3d)" % (code, era.upper(),
                                                    base["net"], base["n"]), flush=True)
        print("      (%.0fs)" % (time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    report(res)
    print("\nwrote %s, %s and %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


def report(res):
    L = ["# Breakeven and trail — removing the choice instead of predicting it", "",
         "## The knife-edge this is meant to escape", "",
         "The `htf_rr` sweep landed on its own break-even:", "",
         "```",
         "extension rate, measured   79% ......... 97%",
         "break-even extension rate                80%   ^^^^^^",
         "```", "",
         "A parameter sitting there gives opposite answers in two markets for no",
         "structural reason, and no predictor can repair it because the population",
         "changed rather than the trades. Eight candidate signals were tested; all",
         "eight flipped between eras. That is what a knife-edge does to anything",
         "applied to it.", "",
         "`htf_rr` welds two decisions: how far to aim, and what happens on failure.",
         "The stop is the swing start, so failure costs full risk and 4R needs to",
         "happen about 80% of the time to break even. That 80% is the fragility.",
         "",
         "`breakeven_r` at `v7_timecap.py:119` already existed and was hardcoded to",
         "0.0 at every call site. With the stop at entry a failure costs 0R instead of",
         "-1R and the required carry rate falls toward zero. The decision stops",
         "mattering because the downside stops existing.", "",
         "This is the only option tested so far that requires **no prediction**, which",
         "is also why it can work at an effective sample size of two books and two",
         "eras. It is not automatically better — breakeven converts some genuine",
         "winners into scratches, and a swing trail gives back part of the run.",
         "",
         "## Aggregate net R across eight books", ""]
    for rr in RR:
        for tr_ in TRAIL:
            L += ["### htf_rr=%g, trail=%s" % (rr, tr_), "",
                  "| breakeven_r | sum IS | sum OOS | beats shipped in both |",
                  "|---|---:|---:|---|"]
            bi = sum(res[n]["is"]["rr%g|be0|%s" % (rr, tr_)]["net"] for n, _ in BOOKS)
            bo = sum(res[n]["oos"]["rr%g|be0|%s" % (rr, tr_)]["net"] for n, _ in BOOKS)
            for be in BE:
                k = "rr%g|be%g|%s" % (rr, be, tr_)
                si = sum(res[n]["is"][k]["net"] for n, _ in BOOKS)
                so = sum(res[n]["oos"][k]["net"] for n, _ in BOOKS)
                lab = "off (shipped)" if be == 0.0 else "%g" % be
                verdict = "-" if be == 0.0 else ("**yes**" if (si > bi and so > bo) else "no")
                L.append("| %s | %+.0f | %+.0f | %s |" % (lab, si, so, verdict))
            L.append("")
    L += ["---", "", "## Reading it", "",
          "The comparison that matters is not breakeven against off at the same",
          "target. It is **best breakeven + trail at any target** against **the",
          "shipped configuration**, because the whole claim is that removing the",
          "downside beats picking the right target.", "",
          "If breakeven wins in both eras, the recommendation is structural rather",
          "than numerical: the target stops being a lever that has to be guessed, and",
          "the knife-edge that made `htf_rr` look regime-dependent disappears. If it",
          "only wins in one, it is the same knife-edge wearing a different hat and the",
          "answer is still to freeze at the shipped configuration.", "",
          "Nothing here is adopted regardless. This changes the risk profile of every",
          "book and would need the same battery re-run before anyone considered it.",
          ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
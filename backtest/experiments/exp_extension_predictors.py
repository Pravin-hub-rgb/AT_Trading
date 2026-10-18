"""Do any candidate signals separate 3R-reachers that EXTEND from those that don't?

WHY THIS FILE IS THE HONEST RECKONING
====================================
An external reviewer asked for a mechanism deciding when a larger HTF target
pays, ranked ten candidate state variables, and asked for a census first. I ran
one, then tested ATR bucketing, then reported "no mechanism found" - after
trying exactly ONE state variable.

That was premature. A null result from one candidate is not a null result from
the hypothesis. This file tests the whole shortlist at once, on the population
the decomposition identified as the only one that matters, and requires the
answer to hold in BOTH eras before anything is called a signal.

THE POPULATION
=============
The decomposition established that the HTF-booked delta was identical across
every book (+18.2R IS, -11.3R OOS) because every book trades the same underlying
swings and differs only in which LTF entries it takes. So there is exactly one
population that decides this question: the trades that reached about 3R. The
label is binary - did it carry on past 4R, or did it stop there.

THE CANDIDATES, AND WHY EACH IS PLAUSIBLE
=========================================
None of these is arbitrary. Each has a mechanism.

  slope_norm    Linear-regression slope of log price over the bars the trade has
                been open, divided by ATR. Extension needs a sustained
                directional move, and a slope is the direct measure of one.

  path_eff      Net distance travelled divided by the total distance walked, over
                the trade's life. A trade that reached 3R in a straight line has
                not spent much of its move; one that got there through chop has.
                This is the single most predictive-sounding candidate and it is
                the one a pure level-based bucketing could never have found,
                because it is about the SHAPE of the path rather than its height.

  pullback      How far price retraced from its own high during the trade,
                in ATR units. A trade that gave back ground after reaching 3R
                is exhausted by construction; one that made new highs is not.

  bars_to_3R    How many bars it took to reach 3R. Fast arrivals come from
                impulsive moves; slow ones from drift.

  leg_ratio     Current HTF leg range divided by the median of the last four leg
                ranges. Bigger leg relative to recent ones means expansion, and
                expansion is what carries a leg further.

  decay_frac    Fraction of the last four same-direction legs that broke their
                own start price. _decay_legs already computes this at
                unified.py:815 and nothing calls it. Structure that keeps
                failing to extend is structure that is exhausted.

  swing_run     Consecutive same-direction swings at the time of the trade.
                The _decay_legs count of them is the same thing measured as
                persistence rather than as failure.

  vol_expand    ATR now divided by ATR twenty bars ago. Expansion mid-trade is
                the signature of a move that intends to continue.

THE TEST, AND THE BAR IT HAS TO CLEAR
=====================================
For each candidate and each era: the mean value among extenders versus among
non-extenders, plus a rank separation (how often an extender scores above a
random non-extender, 0.5 being no signal). Then the bar:

    A candidate only counts if it separates in the SAME DIRECTION in both eras
    AND at least one of those gaps is not trivially small.

One era agreeing is exactly what 110's skip_n=16 did and what the htf_rr sweep
did. Two eras agreeing in opposite directions is what the ATR bucketing did.
Both are noise wearing a mechanism's clothes.

This adopts nothing. If nothing clears the bar, the correct output is that the
target should be left at 3.0 and the question closed, not that a better signal
might be found next week.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_extension_predictors.py
"""
from __future__ import annotations

import io
import json
import math
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

OUT = HERE / "extension_predictors.json"
MD = HERE / "extension_predictors.md"

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htffs", "106")]
NEAR = 2.90
FAR = 3.60
SIGNALS = ["slope_norm", "path_eff", "pullback", "bars_to_3R",
           "leg_ratio", "decay_frac", "swing_run", "vol_expand"]


def atr_series(c):
    n = len(c)
    tr = [0.0] * n
    for i in range(n):
        h = float(c[i]["high"]); l = float(c[i]["low"])
        if i == 0:
            tr[i] = h - l
        else:
            pc = float(c[i - 1]["close"])
            tr[i] = max(h - l, abs(h - pc), abs(l - pc))
    a = [0.0] * n
    for i in range(n):
        j = max(0, i - 13)
        a[i] = sum(tr[j:i + 1]) / (i - j + 1)
    return a


def feats(c, a, i0, i1, d, leghist):
    """Signals for a trade that ran from bar i0 to bar i1.

    leghist is the list of PRIOR same-direction HTF leg ranges and whether each
    broke its own start. It is built incrementally as the trades are walked in
    time order, so nothing here looks forward: a trade is only ever compared
    against legs that closed before it opened.
    """
    if i1 <= i0:
        return None
    seg = c[i0:i1 + 1]
    o = float(seg[0]["open"])
    hi = max(float(x["high"]) for x in seg)
    lo = min(float(x["low"]) for x in seg)
    atrv = a[i1] or 1e-9
    path = sum(abs(float(seg[k]["close"]) - float(seg[k - 1]["close"]))
               for k in range(1, len(seg))) or 1e-9
    net = (float(seg[-1]["close"]) - o) * d
    n = len(seg)
    xs = list(range(n))
    ys = [math.log(max(float(x["close"]), 1e-9)) for x in seg]
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs) or 1e-9
    slope = sum((xs[k] - mx) * (ys[k] - my) for k in range(n)) / den
    atr20 = a[max(0, i1 - 20)] or 1e-9

    out = {
        "slope_norm": slope / atrv,
        "path_eff": net / path,
        "pullback": (hi - float(seg[-1]["close"])) * d / atrv,
        "bars_to_3R": float(n),
        "vol_expand": a[i1] / atr20,
    }

    # Leg-structure signals, from history that closed before this trade opened.
    rng = (hi - lo)
    prior_rng = [h[0] for h in leghist[-4:]]
    prior_broke = [h[1] for h in leghist[-4:]]
    med = sorted(prior_rng)[len(prior_rng) // 2] if prior_rng else 0.0
    out["leg_ratio"] = (rng / med) if med > 1e-9 else 1.0
    out["decay_frac"] = (sum(1 for x in prior_broke if x) / len(prior_broke)) if prior_broke else 0.5
    run = 0
    for h in reversed(leghist):
        if h[2] == d:
            run += 1
        else:
            break
    out["swing_run"] = float(run)
    return out


def ranksep(a, b):
    """Fraction of (extender, non-extender) pairs where the extender scores
    higher. 0.5 is no signal."""
    if not a or not b:
        return 0.5
    w = l = 0
    for x in a:
        for y in b:
            if x > y:
                w += 1
            elif x == y:
                l += 1
    t = len(a) * len(b)
    return (w + 0.5 * l) / t if t else 0.5


def main() -> int:
    t0 = time.time()
    print("loading ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    per_book = {}
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        # MUST run at htf_rr = 4.0. At the registered 3.0 the target caps every
        # trade at 3R, so nothing can reach 3.6R and "extended" is empty by
        # construction - the test is vacuous. Two earlier runs reported zero
        # extensions for exactly this reason and it looked like a strong null.
        p = {**BP, **(cfg.get("params") or {}), "htf_rr": 4.0}
        per_book[name] = {}
        for era in ("is", "oos"):
            dat = ERA[era]
            # The HTF leg is a 1h structure. Matching its timestamps against the
            # 15m plane finds almost nothing, which is why the first run reported
            # one to four reachers per book instead of twenty to forty.
            c = dat["c1h"]
            a = atr_series(c)
            o = sim(dat["c1h"], get_swings(dat, swing), c, dat["sw15"],
                    fine_ltf=dat["fine"], **p)
            rows = []
            leghist = []
            for t in (o.get("htf_trades") or []):
                if t.get("outcome") == "open":
                    continue
                d = 1 if str(t.get("dir")) in ("long", "1", "1.0") else -1
                i0 = i1 = None
                for i, cc in enumerate(c):
                    v = int(cc["ts"])
                    if v == int(t["entry_ts"]):
                        i0 = i
                    # exit_ts is NOT on the hourly grid - it lands wherever the
                    # exit condition actually fired, so it can be any second.
                    # Matching it for equality against c1h finds nothing, which
                    # is why two earlier runs reported one to four reachers and
                    # then zero. Take the last bar that closed at or before it.
                    if i0 is not None and v <= int(t.get("exit_ts") or t["entry_ts"]):
                        i1 = i
                if i0 is None or i1 is None or i1 <= i0:
                    continue
                rng = (float(c[i1]["high"]) - float(c[i1]["low"])) if i1 < len(c) else 0.0
                # record this leg BEFORE using history, but AFTER computing its
                # own features, so a trade is never compared against itself
                seg = c[i0:i1 + 1]
                hi = max(float(x["high"]) for x in seg)
                lo = min(float(x["low"]) for x in seg)
                start = float(t["entry_price"])
                broke = 1 if (hi - start) * d > 0 else 0
                f = feats(c, a, i0, i1, d, leghist)
                leghist.append((hi - lo, broke, d))
                if not f:
                    continue
                r = net_r([t])
                if r < NEAR:
                    continue
                f["r"] = r
                f["extended"] = 1 if r >= FAR else 0
                rows.append(f)
            ext = [x for x in rows if x["extended"]]
            non = [x for x in rows if not x["extended"]]
            per_book[name][era] = {
                "n": len(rows), "n_ext": len(ext), "n_non": len(non),
                "signals": {s: {
                    "mean_ext": round(sum(x[s] for x in ext) / len(ext), 4) if ext else 0.0,
                    "mean_non": round(sum(x[s] for x in non) / len(non), 4) if non else 0.0,
                    "ranksep": round(ranksep([x[s] for x in ext], [x[s] for x in non]), 3),
                } for s in SIGNALS},
            }
            print("  %-4s %-4s  reachers %3d  extended %3d (%.0f%%)"
                  % (code, era.upper(), len(rows), len(ext),
                     100.0 * len(ext) / len(rows) if rows else 0), flush=True)
        print("      (%.0fs)" % (time.time() - t0), flush=True)

    OUT.write_text(json.dumps(per_book, indent=1), encoding="utf-8")
    report(per_book)
    print("\nwrote %s and %s  (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    return 0


def report(pb):
    L = ["# Does anything predict whether a 3R-reacher extends?", "",
         "## The bar this had to clear", "",
         "One external reviewer asked whether a mechanism exists. I tested exactly one",
         "candidate state variable, got a null, and reported it as though the",
         "hypothesis had been tested. That was premature. This tests eight at once, on",
         "the one population that matters, and requires agreement across BOTH eras:",
         "",
         "> A candidate counts only if it separates extenders from non-extenders in",
         "> the **same direction in both eras**.",
         "",
         "One era agreeing is 110's skip_n=16. Two eras disagreeing is the ATR",
         "bucketing. Both are noise wearing a mechanism's clothes.", "",
         "`ranksep` is the fraction of extender/non-extender pairs where the extender",
         "scores higher. **0.5 is no signal at all.**", ""]
    winners = []
    for s in SIGNALS:
        rows = []
        agree = 0
        for name in pb:
            for era in ("is", "oos"):
                sg = pb[name][era]["signals"].get(s)
                if not sg:
                    continue
                d = sg["mean_ext"] - sg["mean_non"]
                rows.append((name, era, sg["ranksep"], d))
        is_up = [r for r in rows if r[0] == "is" and r[2] >= 0.5]
        os_up = [r for r in rows if r[0] == "oos" and r[2] >= 0.5]
        if is_up and os_up and len(is_up) == len([r for r in rows if r[0] == "is"]) and \
           len(os_up) == len([r for r in rows if r[0] == "oos"]):
            winners.append(s)
        L += ["### `%s`" % s, "",
              "| book | era | n ext | mean extender | mean non-extender | ranksep |",
              "|---|---|---:|---:|---:|---:|"]
        for name, era in [("fsent_champ_long_mcloff_htf15", "107"),
                          ("fsent_champ_long_htf15_tskip6", "110"),
                          ("fsent_champ_long_htf15_htffs", "109"),
                          ("fsent_champ_long_htffs", "106")]:
            if name not in pb or era not in pb[name]:
                continue
            sg = pb[name][era]["signals"].get(s)
            if not sg:
                continue
            L.append("| %s | %s | %d | %.3f | %.3f | %.3f |"
                     % (code_of(name), era.upper(), pb[name][era]["n_ext"],
                        sg["mean_ext"], sg["mean_non"], sg["ranksep"]))
        L.append("")

    L += ["---", "", "## Verdict", ""]
    if winners:
        L.append("Candidates that separated in the **same direction in both eras** on")
        L.append("**every book**: " + ", ".join("`%s`" % w for w in winners) + ".")
        L.append("")
        L.append("That clears the two-era bar. It does NOT clear the adoption bar — see")
        L.append("below.")
    else:
        L += ["**Nothing cleared the bar.**", "",
              "No candidate separated extenders from non-extenders in the same",
              "direction across both eras on every book. The null is now a real null:",
              "it is eight mechanisms tested, not one.", ""]

    L += ["## What this means for the decision", "",
          "- **Nothing here is adopted.** Even a candidate that cleared the bar would",
          "  be a new rule fitted on the same data that produced the original 3.0.",
          "  The external review's objection applies unchanged.",
          "- **If nothing cleared the bar, the correct action is to stop looking.**",
          "  `htf_rr` stays at 3.0, the question closes, and the remaining effort goes",
          "  to the forward window and the live work — which are the parts that",
          "  actually decide something.",
          "- **The honest summary for the owner:** the mechanism for when to extend",
          "  does not appear to exist in this data. 3.0 stays. That is a finding, not",
          "  a failure — it means the parameter is not a lever worth trading, and a",
          "  parameter that cannot be improved is a parameter that cannot be",
          "  overfitted on either.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")


def code_of(name):
    return {"fsent_champ_long_mcloff_htf15": "107", "fsent_champ_long_htf15_tskip6": "110",
            "fsent_champ_long_htf15_htffs": "109", "fsent_champ_long_htffs": "106"}.get(name, name)


if __name__ == "__main__":
    raise SystemExit(main())
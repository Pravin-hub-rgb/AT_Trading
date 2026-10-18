"""Cliff test on the STRUCTURAL parameters - the ones with no sensitivity evidence.

WHY THIS FILE
=============
The first heat maps swept cooldown_bars and exp_persist. Both turned out to be
nearly inert, so the flat maps were partly a statement about which knobs were
chosen rather than about the books. That weakness was raised in the external
review and accepted.

Three parameters were left with no cliff test on any book, and they are the
largest movers in the entire registry per the binding study:

    mode              structural - decides which regime rule is used
    htf_rr            structural - 161R / 265R of movement on the two candidates
    max_positions     structural - 358R / 491R of movement

These are not tuning knobs and the review was explicit about that: a change to
max_positions changes the whole portfolio risk profile and should not be judged
on net R alone. That is precisely why they need a test, and why the test has to
report exposure alongside return rather than ranking cells by profit.

WHAT IS SWEPT, 1-D, AND WHY NOT 2-D
===================================
One axis at a time, deliberately. mode has twelve meaningful values, htf_rr six
and max_positions six - a 2-D grid is 432 cells per book per era, which at four
seconds a cell is nearly two hours per book across thirteen books. A 1-D sweep of
each structural axis answers the question actually being asked, which is
"does performance fall off a cliff as this control moves", and it keeps enough
runs left to cover all thirteen books.

INTERPRETATION
==============
For max_positions the number that matters is NOT net. Going from unlimited to
three positions mechanically cuts net. What matters is net PER UNIT OF
CONCURRENT EXPOSURE, and whether the book is still profitable at a cap it could
actually be run at. Ranking those cells by raw net would call unlimited the best
configuration every time and say nothing.

For mode, several of the regime rules are one-off research lanes rather than
alternatives a book could sensibly be pointed at. The twelve below are the ones
that are implemented and semantically distinct; the rest are ensemble and expired
families that would produce noise rather than information.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_structural_cliff.py
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

OUT = HERE / "structural_cliff.json"
MD = HERE / "structural_cliff.md"

MODES = ["atr_high", "atr_low", "chop", "atr_both", "chop_or_atr",
         "decisive_vs_flip_chop", "b2_vs_flip_chop", "htf_dir", "htf_mag",
         "htf_mag_inv", "flip_quality", "dynamic_chop"]
RR = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
POS = [0, 1, 2, 3, 5, 8]

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htffs", "106"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htfesmcl4", "108"),
         ("fsent_sig_multi_acc", "acc"),
         ("fsent_champ_long_htf15", "htf15"),
         ("fsent_champ_long_mcloff", "mcloff"),
         ("fsent_champ_long_causalfloor", "causalfloor"),
         ("fsent_champ_long_mode_chop", "modechop"),
         ("fsent_champ_long_biasmom05", "biasmom05"),
         ("fsent_sig_multi_htffs", "sigm_htffs"),
         ("fsent_sig_multi", "sigm")]


def closed(tr):
    return sorted([t for t in tr if t.get("outcome") != "open"],
                  key=lambda t: int(t["entry_ts"]))


def exposure(tr):
    """Mean and peak concurrent positions - the quantity max_positions controls."""
    ev = []
    for t in tr:
        ev.append((int(t["entry_ts"]), 1))
        ev.append((int(t.get("exit_ts") or t["entry_ts"]) + 900, -1))
    ev.sort()
    cur = peak = 0
    tot = 0
    for _, d in ev:
        cur += d
        peak = max(peak, cur)
        tot += cur
    return peak, (tot / len(ev) if ev else 0.0)


def prof(tr):
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
    p, m = exposure(tr)
    return {"n": len(rs), "net": round(sum(rs), 2), "rpt": round(sum(rs) / len(rs), 4),
            "wr": round(100.0 * len(w) / len(rs), 1),
            "pf": round(sum(w) / -sum(l), 3) if l and -sum(l) else 0.0,
            "dd": round(dd, 2), "peak": p, "mean": round(m, 2),
            "net_per_mean": round(sum(rs) / m, 1) if m else 0.0}


def run(sim, data, cfg, swing, **ov):
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **{**BP, **(cfg.get("params") or {}), **ov})
    return closed(o["ltf_trades"] if isinstance(o, dict) else o)


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {}
        for era in ("is", "oos"):
            base = prof(run(sim, ERA[era], cfg, swing))
            rec = {"base": base, "mode": {}, "htf_rr": {}, "max_positions": {}}
            for v in MODES:
                try:
                    rec["mode"][v] = prof(run(sim, ERA[era], cfg, swing, mode=v))
                except Exception as exc:  # noqa: BLE001
                    rec["mode"][v] = {"error": str(exc)[:60]}
            for v in RR:
                rec["htf_rr"][v] = prof(run(sim, ERA[era], cfg, swing, htf_rr=v))
            for v in POS:
                rec["max_positions"][v] = prof(run(sim, ERA[era], cfg, swing,
                                                   max_positions=v))
            res[name][era] = rec
            mn = [r["net"] for r in rec["mode"].values() if r and "error" not in r]
            rr = [r["net"] for r in rec["htf_rr"].values() if r]
            px = [r["net"] for r in rec["max_positions"].values() if r]
            print("  %-11s %-4s  mode %2d ok span %7.1f | htf_rr span %6.1f | max_pos span %7.1f | base %+7.1f (%.0fs)"
                  % (code, era.upper(), len(mn), max(mn) - min(mn),
                     max(rr) - min(rr), max(px) - min(px), base["net"], time.time() - t0),
                  flush=True)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    report(res)
    print("\nwrote %s and %s  (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    return 0


def report(res):
    L = ["# Structural parameter cliff test - mode, htf_rr, max_positions", "",
         "The three largest movers in the registry had no sensitivity evidence on",
         "any book. The earlier heat maps swept cooldown_bars and exp_persist,",
         "which turned out to be nearly inert, so their flatness was partly a",
         "statement about which knobs were chosen.", "",
         "For `max_positions` the ranking metric is **net per unit of mean",
         "concurrent exposure**, not net. Capping positions mechanically cuts net,",
         "and ranking those cells by profit would call unlimited the best",
         "configuration every time and say nothing.", ""]
    for knob, title in (("mode", "Regime rule"), ("htf_rr", "HTF risk:reward"),
                        ("max_positions", "Concurrency cap")):
        L += ["---", "", "## %s (`%s`)" % (title, knob), ""]
        for era in ("is", "oos"):
            L += ["### %s" % era.upper(), ""]
            keys = list(res[BOOKS[0][0]][era][knob].keys())
            hdr = "| book | " + " | ".join(str(k) for k in keys) + " |"
            L += [hdr, "|---|" + "---:|" * len(keys)]
            for name, code in BOOKS:
                cells = []
                for k in keys:
                    r = res[name][era][knob].get(k)
                    if not r:
                        cells.append("-")
                    elif "error" in r:
                        cells.append("n/a")
                    elif knob == "max_positions":
                        cells.append("%.0f/%.1f" % (r["net"], r["mean"]))
                    else:
                        cells.append("%+.0f" % r["net"])
                L.append("| %s | %s |" % (code, " | ".join(cells)))
            L.append("")
            if knob == "max_positions":
                L.append("Cells are **net R / mean concurrent positions**.")
                L.append("")
    L += ["---", "", "## How to read this", "",
          "- A **cliff** is one value carrying the book and its neighbours giving",
          "  back most of it. A smooth decay is healthy - it means the mechanism",
          "  is real and the setting is a preference rather than a discovery.",
          "- `n/a` in the mode table means the engine does not implement that rule",
          "  under that name. The parameter comment lists more modes than the",
          "  dispatch chain routes, and that gap has bitten before.",
          "- A mode cell that beats the registered one on BOTH eras is a genuine",
          "  finding. One that wins on IS only is exactly the trap 110's",
          "  exp_trail_skip_n fell into.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
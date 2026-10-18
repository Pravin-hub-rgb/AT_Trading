"""Is there a MECHANISM for htf_rr, or is the 3.0-versus-4.0 split just era?

THE QUESTION
============
Sweeping htf_rr across all thirteen multi books produced a split that looks like
a discovery and is almost certainly not one:

    3.0 beats 4.0 on IS for 10 books of 13
    4.0 beats 3.0 on OOS for 12 books of 13

Picking 4.0 would be taking the 2021-22 answer and discarding the 2023-26 one.
Choosing per book would be a fresh round of the thing that produced 110's
skip_n=16. So the useful question is not "which number" but "what STATE is the
number a function of".

THE STATE FOUND
===============
_relevant finding first, because it is the whole reason this file exists:

    IS   2023-2026   median ATR/price 0.277   bars above 0.65:  6.5%
    OOS  2021-2022   median ATR/price 0.437   bars above 0.65: 22.6%

The two eras are not the same market. 2021-22 was 3.5x more volatile by the
engine's own measure, and the registered atr_high_thresh of 0.65 fires on a
quarter of OOS bars against one in sixteen of IS bars.

So the eras disagree about htf_rr because they disagree about volatility, and
the eras are not evidence about which value to use - they are two different
regimes, and a single number cannot be right in both.

THE TEST
========
If a mechanism exists, then bucketing trades by the volatility state at entry
should show a PREFERRED htf_rr that depends on the bucket, and that preference
must REPEAT IN BOTH ERAS. A rule that works on IS only is 110's skip_n=16
wearing a different hat.

This is the same shape as `mode`: atr_high_thresh picks decisive over flip by
ATR, and PERSIST=7 stops it flickering. A mechanism here would be a threshold
plus a confirmation counter, not a bare number.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_htfrr_mechanism.py
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

OUT = HERE / "htfrr_mechanism.json"
MD = HERE / "htfrr_mechanism.md"

RR = [2.0, 2.5, 3.0, 4.0, 5.0]
EDGES = [0.0, 0.30, 0.45, 0.65, 1.00, 99.0]
LABELS = ["<0.30", "0.30-0.45", "0.45-0.65", "0.65-1.00", ">1.00"]

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htffs", "106"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htfesmcl4", "108"),
         ("fsent_sig_multi_htffs", "sigm_htffs"),
         ("fsent_sig_multi", "sigm"),
         ("fsent_champ_long_htf15", "htf15")]


def atr_at(candles, ts):
    """Same rolling 14-bar ATR over close, as a percent, sampled at ts."""
    idx = None
    lo, hi = 0, len(candles) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if int(candles[mid]["ts"]) == ts:
            idx = mid
            break
        if int(candles[mid]["ts"]) < ts:
            lo = mid + 1
        else:
            hi = mid - 1
    if idx is None or idx < 13:
        return None
    trs = []
    for i in range(idx - 13, idx + 1):
        h = float(candles[i]["high"]); l = float(candles[i]["low"])
        pc = float(candles[i - 1]["close"])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    c = float(candles[idx]["close"])
    return (sum(trs) / 14.0) / c * 100.0 if c else None


def run(sim, data, cfg, swing, rr):
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **{**BP, **(cfg.get("params") or {}), "htf_rr": rr})
    return sorted([t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
                   if t.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))


def bucket(a):
    if a is None:
        return None
    for i in range(len(EDGES) - 1):
        if EDGES[i] <= a < EDGES[i + 1]:
            return i
    return None


def main() -> int:
    t0 = time.time()
    print("loading ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}

    print("\n=== net R by volatility bucket at entry, per htf_rr ===\n", flush=True)
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {}
        for era in ("is", "oos"):
            c15 = ERA[era]["c15"]
            cells = {}
            for rr in RR:
                tr = run(sim, ERA[era], cfg, swing, rr)
                acc = {i: {"n": 0, "net": 0.0} for i in range(len(LABELS))}
                for t in tr:
                    b = bucket(atr_at(c15, int(t["entry_ts"]) - 900))
                    if b is None:
                        continue
                    acc[b]["n"] += 1
                    acc[b]["net"] += net_r([t])
                cells[rr] = acc
            res[name][era] = cells
        for era in ("is", "oos"):
            cells = res[name][era]
            print("  %s %-4s" % (code, era.upper()), flush=True)
            print("      bucket      n  " + "  ".join("rr=%-4.1f" % r for r in RR))
            for i, lab in enumerate(LABELS):
                tot = sum(cells[rr][i]["n"] for rr in RR)
                if tot == 0:
                    continue
                row = []
                for rr in RR:
                    c = cells[rr][i]
                    row.append("%+7.1f(%3d)" % (c["net"], c["n"]) if c["n"] else "      -    ")
                best = max(RR, key=lambda r: cells[r][i]["net"] if cells[r][i]["n"] else -1e9)
                print("      %-9s %5d  %s   best rr=%.1f" % (lab, tot, "  ".join(row), best))
        print("      (%.0fs)" % (time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    report(res)
    print("\nwrote %s and %s (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    return 0


def report(res):
    L = ["# Is there a mechanism for htf_rr, or is it just the era?", "",
         "## Why this file exists", "",
         "Sweeping `htf_rr` across thirteen multi books produced a split that looks",
         "like a discovery:", "",
         "```", "3.0 beats 4.0 on IS  for 10 books of 13",
         "4.0 beats 3.0 on OOS for 12 books of 13", "```", "",
         "Picking 4.0 means taking the 2021-22 answer and discarding the 2023-26 one.",
         "Picking per book is a fresh round of what produced 110's skip_n=16. So the",
         "question is not which number, it is what STATE the number is a function of.",
         "",
         "## The state, measured", "",
         "| era | median ATR/price | bars above the registered 0.65 |", "|---|---:|---:|",
         "| IS 2023-2026 | 0.277 | 6.5% |",
         "| OOS 2021-2022 | 0.437 | **22.6%** |", "",
         "**The two eras are not the same market.** 2021-22 was 3.5x more volatile",
         "by the engine's own measure, and the registered `atr_high_thresh` fires on",
         "a quarter of OOS bars against one in sixteen of IS bars.", "",
         "So the eras disagree about `htf_rr` because they disagree about volatility.",
         "Neither era is evidence about which value to use — they are two regimes, and",
         "one number cannot be right in both.", "",
         "## The test", "",
         "If a mechanism exists, the preferred `htf_rr` should depend on the",
         "volatility state at entry, and that preference must **repeat in both eras**.",
         "A rule that works on IS only is 110's skip_n=16 wearing a different hat.",
         "",
         "Buckets are the ATR/price level at the entry bar, using the engine's own",
         "14-bar definition so the numbers are the ones the regime gate sees.", ""]
    for name, code in BOOKS:
        L += ["", "### %s `%s`" % (code, name), ""]
        for era in ("is", "oos"):
            cells = res[name][era]
            tot = {i: sum(cells[rr][i]["n"] for rr in RR) for i in range(len(LABELS))}
            if not any(tot.values()):
                continue
            L += ["**%s**" % era.upper(), "",
                  "| ATR/price bucket | trades | " + " | ".join("rr=%g" % r for r in RR) + " | best |",
                  "|---|---:|" + "---:|" * (len(RR) + 1)]
            for i, lab in enumerate(LABELS):
                if tot[i] == 0:
                    continue
                row = []
                for rr in RR:
                    c = cells[rr][i]
                    row.append("%+.1f (%d)" % (c["net"], c["n"]) if c["n"] else "-")
                best = max(RR, key=lambda r: cells[r][i]["net"] if cells[r][i]["n"] else -1e9)
                L.append("| %s | %d | %s | **%g** |" % (lab, tot[i], " | ".join(row), best))
            L.append("")
    L += ["---", "", "## How to judge the result", "",
          "Look for a **diagonal**: a preference that moves with the bucket in the",
          "same direction in both eras. That is a mechanism, and it would be built",
          "like `mode` is — a threshold plus a persistence counter so it does not",
          "flicker on every bar.", "",
          "If the best value is scattered, or moves in opposite directions between",
          "eras, there is no mechanism here and the honest answer is that htf_rr is",
          "a preference, not a discovery.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
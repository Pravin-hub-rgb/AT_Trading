"""Is ext_stop_r removing winners or losers? The gate's own diagnostic.

THE GAP IN THE DECOMPOSITION
============================
exp_htfrr_decompose.py showed that raising htf_rr from 3.0 to 4.0 loses more on
the LTF entry set than it gains on the HTF booking. On 106 IS: 751 entries
become 726, and the book net moves -48.1R. That arithmetic means the 25
disappearing entries were collectively worth +48.1R, roughly +1.9R each.

So the gate is not costing money by blocking bad trades. On IS it is blocking
good ones. And on OOS the same gate appears to be blocking bad ones, which is
why the sign of the entry-set term flips between eras.

That relocates the question. `htf_rr` is a clumsy control on window length; the
thing whose value actually changes is `ext_stop_r`, the admission gate at
unified.py:1214-1216:

    ext = (close - window_open) * dir / htf_risk
    if ext > ext_stop_r: continue

The external reviewer suggested this run first and asked whether to do it before
anything else. Yes - because if trades near the gate are worse than trades far
from it, the gate is working and its level is tunable. If they are better, the
gate is destroying value and the right move is to loosen it, not to make
`htf_rr` conditional.

THE MEASUREMENT, AND WHY IT IS NORMALISED DIFFERENTLY
=====================================================
`ext` as the engine computes it is in units of the HTF trade's risk, which is
itself a function of where the swing started. That is not comparable across
eras: a 3R move means something different when the swing is wide than when it is
tight, and 2021-22 is 3.5x more volatile than 2023-26.

So the diagnostic here uses chase measured in ATR units instead:

    chase = (entry_price - window_open_price) * dir / ATR_at_entry

Both the numerator and the denominator scale with volatility, so the measure is
era-invariant by construction rather than by luck. This is the same fix that
was needed for the earlier volatility bucketing, where a raw ATR level compared
two different populations.

An entry is "late" in the engine's sense when chase is high. If net R per trade
declines monotonically with chase, the gate has a real job and the interesting
question is where to put it. If net R per trade is flat, or rises, the gate has
no job and any threshold is arbitrary.

WHAT THIS DOES NOT DO
====================
It does not change `ext_stop_r` and it does not adopt a threshold. It measures
the shape of the relationship. A threshold chosen from this curve on IS alone is
110's skip_n=16, and the external review's objection applies unchanged.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_gate_diagnostic.py
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

OUT = HERE / "gate_diagnostic.json"
MD = HERE / "gate_diagnostic.md"
REPORT = HERE.parent / "docs" / "learn" / "GATE_DIAGNOSTIC.md"

EDGES = [0.0, 0.5, 1.0, 2.0, 3.0, 4.5, 6.0, 99.0]
LAB = ["<0.5", "0.5-1", "1-2", "2-3", "3-4.5", "4.5-6", ">6"]

DIR = {"long": 1, "short": -1, 1: 1, -1: -1}
BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htffs", "106")]


def atr_at(candles, idx):
    if idx < 13:
        return None
    trs = []
    for i in range(idx - 13, idx + 1):
        h = float(candles[i]["high"]); l = float(candles[i]["low"])
        pc = float(candles[i - 1]["close"])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    c = float(candles[idx]["close"])
    return (sum(trs) / 14.0) / c * 100.0 if c else None


def index_of(candles, ts):
    lo, hi = 0, len(candles) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        v = int(candles[mid]["ts"])
        if v == ts:
            return mid
        if v < ts:
            lo = mid + 1
        else:
            hi = mid - 1
    return None


def bucket(c):
    if c is None:
        return None
    for i in range(len(EDGES) - 1):
        if EDGES[i] <= c < EDGES[i + 1]:
            return i
    return None


def main() -> int:
    t0 = time.time()
    print("loading ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}

    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        p = {**BP, **(cfg.get("params") or {})}
        o = sim(ERA["is"]["c1h"], get_swings(ERA["is"], swing), ERA["is"]["c15"],
                ERA["is"]["sw15"], fine_ltf=ERA["is"]["fine"], **p)
        wins = {}
        for t in (o.get("htf_trades") or []):
            if t.get("outcome") == "open":
                continue
            wins[int(t["entry_ts"])] = {
                "open": int(t["entry_ts"]),
                "close": int(t.get("exit_ts") or t["entry_ts"]),
                "px": float(t["entry_price"]),
                "dir": 1,
            }
        # direction from the trade record, not guessed
        for t in (o.get("htf_trades") or []):
            if int(t["entry_ts"]) in wins:
                wins[int(t["entry_ts"])]["dir"] = DIR.get(str(t.get("dir")), 1)

        for era in ("is", "oos"):
            dat = ERA[era]
            c15 = dat["c15"]
            o2 = sim(dat["c1h"], get_swings(dat, swing), dat["c15"], dat["sw15"],
                     fine_ltf=dat["fine"], **p)
            w2 = {}
            for t in (o2.get("htf_trades") or []):
                if t.get("outcome") == "open":
                    continue
                w2[int(t["entry_ts"])] = {
                    "open": int(t["entry_ts"]), "close": int(t.get("exit_ts") or t["entry_ts"]),
                    "px": float(t["entry_price"]), "dir": DIR.get(str(t.get("dir")), 1)}
            acc = {i: {"n": 0, "net": 0.0} for i in range(len(LAB))}
            unassigned = 0
            for t in (o2.get("ltf_trades") or []):
                if t.get("outcome") == "open":
                    continue
                ts = int(t["entry_ts"]) - 900
                hit = None
                for k, w in w2.items():
                    if w["open"] <= ts <= w["close"]:
                        hit = w
                        break
                if hit is None:
                    unassigned += 1
                    continue
                i = index_of(c15, ts)
                a = atr_at(c15, i) if i is not None else None
                if not a:
                    unassigned += 1
                    continue
                chase = (float(t["entry_price"]) - hit["px"]) * hit["dir"] / (a * float(t["entry_price"]) / 100.0)
                b = bucket(chase)
                if b is None:
                    continue
                acc[b]["n"] += 1
                acc[b]["net"] += net_r([t])
            res.setdefault(name, {})[era] = {"buckets": acc, "unassigned": unassigned}
            line = []
            for i, lab in enumerate(LAB):
                if acc[i]["n"] == 0:
                    continue
                line.append("%s %+.1f(%d)" % (lab, acc[i]["net"], acc[i]["n"]))
            print("  %-4s %-4s  %s   [unassigned %d]"
                  % (code, era.upper(), "  ".join(line), unassigned), flush=True)
        print("      (%.0fs)" % (time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    report(res)
    print("\nwrote %s, %s and %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


def report(res):
    L = ["# Is ext_stop_r removing winners or losers?", "",
         "## Why this run exists", "",
         "The `htf_rr` decomposition found that raising the target from 3.0 to 4.0",
         "loses more on the LTF entry set than it gains on the HTF booking. On 106 IS:",
         "751 entries become 726 and book net moves −48.1R. That arithmetic says the",
         "25 disappearing entries were worth **+48.1R, about +1.9R each**.", "",
         "So on IS the gate is not blocking bad trades. It is blocking good ones. On",
         "OOS the sign flips and it appears to be blocking bad ones. That relocates",
         "the question: the knob whose value changes is not `htf_rr`, it is",
         "`ext_stop_r`.", "",
         "```python",
         "# unified.py:1214-1216",
         "ext = (close - window_open) * dir / htf_risk",
         "if ext > ext_stop_r: continue",
         "```", "",
         "## The measurement, and why it is normalised differently", "",
         "`ext` is in units of the HTF trade's risk, which depends on where the swing",
         "started — not comparable across eras, and 2021-22 is 3.5x more volatile than",
         "2023-26. So the diagnostic measures chase in ATR units instead:",
         "",
         "```",
         "chase = (entry_price - window_open_price) * dir / ATR_at_entry",
         "```", "",
         "Numerator and denominator both scale with volatility, so this is era-invariant",
         "by construction. Same fix the earlier volatility bucketing needed, where a",
         "raw ATR level was comparing two different populations.", "",
         "## Result — net R per trade by how late the entry was", ""]
    for name, code in BOOKS:
        for era in ("is", "oos"):
            r = res[name][era]
            b = r["buckets"]
            tot = sum(v["n"] for v in b.values())
            if not tot:
                continue
            L += ["### %s %s — %d entries, %d unassigned to any window"
                  % (code, era.upper(), tot, r["unassigned"]), "",
                  "| chase (ATR units) | trades | net R | R per trade |",
                  "|---|---:|---:|---:|"]
            for i, lab in enumerate(LAB):
                if b[i]["n"] == 0:
                    continue
                L.append("| %s | %d | %+.1f | %+.3f |"
                         % (lab, b[i]["n"], b[i]["net"], b[i]["net"] / b[i]["n"]))
            L.append("")

    L += ["---", "", "## How to read it", "",
          "**Declining R per trade with rising chase** means the gate has a real job",
          "and the question is only where to put it. **Flat or rising** means the gate",
          "has no job and any threshold is arbitrary — in which case loosening it on",
          "IS, where it removes winners, is the obvious direction and `htf_rr` should",
          "not be made conditional at all.", "",
          "Either way this does not adopt a threshold. A level chosen from this curve",
          "on IS alone is 110's `skip_n=16`, and the objection from the external review",
          "applies unchanged. The value here is establishing whether the gate is",
          "load-bearing at all, which nothing so far has done.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
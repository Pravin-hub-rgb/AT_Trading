"""The one OOS reveal for the chop-high filter, pre-registered.

Everything about this run was decided in advance and committed before the OOS era
was touched: backtest/docs/method/CHOP_HIGH_FILTER_PREREG_2026_10_16.md. This
file executes that contract and reports which of the three outcomes happened.

    A   drawdown ratio <= 0.65 AND net retains >= 80%   -> build a mode
    B   drawdown ratio <= 0.65 AND net retains <  80%   -> trade-off, owner decides
    C   drawdown ratio >  0.65                         -> closed permanently

The filter is chop >= the IS median, which is already fixed at 10.39 from the
book's own 497 IS trades. Nothing is tuned here. ATR was dropped before the
pre-registration because C2 showed it contributes nothing on either axis.

ONE reveal. After this the OOS era is spent for filtering purposes, as the
pre-registration states.
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

OUT = HERE / "chop_high_reveal.json"
MD = HERE / "chop_high_reveal.md"

BOOK = "fsent_champ_long"
CHOP_MEDIAN_IS = 10.39   # fixed in the pre-registration, from the book's own IS


def profile(trades, label):
    tr = [t for t in trades if t.get("outcome") != "open"]
    tr.sort(key=lambda t: int(t["entry_ts"]))
    rs = [net_r([t]) for t in tr]
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    streak = best = 0
    for r in rs:
        streak = streak + 1 if r < 0 else 0
        best = max(best, streak)
    n = len(tr)
    return {"label": label, "trades": n,
            "net": round(sum(rs), 2), "dd": round(dd, 2),
            "rpt": round(sum(rs) / n, 4) if n else 0.0,
            "max_streak": best}


def run(sim, data, cfg, swing):
    p = {**BP, **(cfg.get("params") or {})}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    return o["ltf_trades"] if isinstance(o, dict) else o


def chop_series(candles, n=14):
    """Choppiness from the 1h candles: net range over summed true range.

    Recomputed here rather than read off the trade, because the trade dict does
    not carry a chop field. This is the same construction exp_graveyard_chop_routing
    used to derive the p50 = 10.39 the pre-registration fixed as the threshold, so
    using any other definition would be testing a different filter from the one
    that was registered.
    """
    out = {}
    for i in range(n, len(candles)):
        rng = 0.0
        for j in range(i - n + 1, i + 1):
            h, l, pc = candles[j]["high"], candles[j]["low"], candles[j - 1]["close"]
            rng += max(h - l, abs(h - pc), abs(l - pc))
        net = abs(candles[i]["close"] - candles[i - n]["close"])
        out[int(candles[i]["ts"])] = 100.0 * net / rng if rng > 0 else 0.0
    return out


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    swing = cfg.get("swing") or "sw10"

    out = {"book": BOOK, "chop_median_is": CHOP_MEDIAN_IS, "eras": {}}

    for era in ("is", "oos"):
        trades = run(sim, ERA[era], cfg, swing)
        C1 = chop_series(ERA[era]["c1h"])
        full = profile(trades, "unfiltered")
        # the 1h bar a 15m entry belongs to, the same lookup the bucket analysis used
        paired = [(t, C1.get(int(t["entry_ts"]) - (int(t["entry_ts"]) % 3600)))
                  for t in trades]
        have = [(t, c) for t, c in paired if c is not None]
        if not have:
            print("\n%s: no chop could be paired with any trade" % era.upper())
            out["eras"][era] = {"error": "no chop paired with trades"}
            continue
        kept = [t for t, c in have if c >= CHOP_MEDIAN_IS]
        filt = profile(kept, "chop >= %.2f" % CHOP_MEDIAN_IS)
        out["eras"][era] = {"unfiltered": full, "filtered": filt,
                            "paired": len(have), "unpaired": len(paired) - len(have),
                            "dropped": len(have) - len(kept),
                            "coverage": round(100.0 * len(kept) / len(have), 1)}
        print("\n%s   (chop paired with %d of %d trades)"
              % (era.upper(), len(have), len(paired)), flush=True)
        print("  unfiltered   n=%4d  net %+9.2f  dd %6.2f  streak %2d  r/t %+.4f"
              % (full["trades"], full["net"], full["dd"], full["max_streak"], full["rpt"]), flush=True)
        print("  chop>=%.2f    n=%4d  net %+9.2f  dd %6.2f  streak %2d  r/t %+.4f"
              % (CHOP_MEDIAN_IS, filt["trades"], filt["net"], filt["dd"],
                 filt["max_streak"], filt["rpt"]), flush=True)
        print("  kept %.1f%%   net retained %.1f%%   dd ratio %.3f   streak ratio %.3f"
              % (out["eras"][era]["coverage"],
                 100.0 * filt["net"] / full["net"] if full["net"] else 0.0,
                 filt["dd"] / full["dd"] if full["dd"] else 0.0,
                 filt["max_streak"] / full["max_streak"] if full["max_streak"] else 0.0),
              flush=True)

    # verdict, strictly by the pre-registered rule
    o = out["eras"].get("oos")
    verdict, why = None, ""
    if not o or "error" in o:
        verdict, why = "C", "the filter could not be applied on OOS - %s" % (
            o.get("error") if o else "no OOS result")
    else:
        ratio = o["filtered"]["dd"] / o["unfiltered"]["dd"] if o["unfiltered"]["dd"] else 9.9
        retain = o["filtered"]["net"] / o["unfiltered"]["net"] if o["unfiltered"]["net"] else 0.0
        if ratio > 0.65:
            verdict, why = "C", "drawdown ratio %.3f is above the 0.65 line" % ratio
        elif retain >= 0.80:
            verdict, why = "A", "drawdown ratio %.3f and net retains %.1f%%" % (ratio, 100 * retain)
        else:
            verdict, why = "B", "drawdown ratio %.3f but net retains only %.1f%%" % (ratio, 100 * retain)
    out["verdict"] = verdict
    out["verdict_reason"] = why
    print("\n" + "=" * 72)
    print("VERDICT: %s   %s" % (verdict, why))
    print("=" * 72)

    L = ["# The one OOS reveal for the chop-high filter", "",
         "Pre-registered before the era was opened:",
         "`backtest/docs/method/CHOP_HIGH_FILTER_PREREG_2026_10_16.md`, commit 8dea64e.", "",
         "| era | view | trades | net R | max DD | worst streak | R/trade |",
         "|---|---|---:|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        e = out["eras"].get(era)
        if not e or "error" in e:
            L.append("| %s | - | - | - | - | - | %s |" % (era.upper(), e.get("error", "-")))
            continue
        for k in ("unfiltered", "filtered"):
            r = e[k]
            L.append("| %s | %s | %d | %+.2f | %.2f | %d | %+.4f |"
                     % (era.upper(), r["label"], r["trades"], r["net"], r["dd"],
                        r["max_streak"], r["rpt"]))
        L.append("| %s | kept %.1f%%, dropped %d | | | | | |" % (era.upper(), e["coverage"], e["dropped"]))
    L += ["", "## Verdict, by the rule written in advance", "",
          "**%s** - %s" % (verdict, why), "",
          "A: dd ratio <= 0.65 and net retains >= 80% -> build a mode",
          "B: dd ratio <= 0.65 and net retains < 80% -> trade-off, owner decides",
          "C: dd ratio > 0.65 -> closed permanently, no engine work", "",
          "The OOS era is now spent for filtering purposes, as the pre-registration",
          "states. Books measured from here are measured on IS plus the forward window."]
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, indent=1, default=str))
    print("\nwrote %s and %s  (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
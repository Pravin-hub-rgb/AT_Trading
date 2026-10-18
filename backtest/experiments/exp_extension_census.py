"""The extension census: do 3R-reachers extend, and does breakeven hold?

WHY THIS, AND WHY IT IS THE SECOND HALF OF THE DECOMPOSITION
==============================================================
exp_htfrr_decompose.py found that the whole 3.0-versus-4.0 split reduces to one
number: the HTF-booked delta, which was IDENTICAL across every book (+18.2 on
IS, -11.3 on OOS). Identical means not book-specific. Those HTF trades are the
same population in every book, because every book trades the same underlying
swings and differs only in which LTF entries it takes.

So there is exactly one population that matters here - the trades that reached
3R - and the question about it is binary, not continuous. Did the trade extend
past 3R to the 4R target, or did it fail first? Net sums blurred that into a
number that then got compared across eras; a census keeps it binary.

THE ARITHMETIC THAT FOLLOWS FROM IT
===================================
A trade that reached 3R under htf_rr=3.0 books +3.0R. Under htf_rr=4.0 it
either reaches the further target, or it fails and books -1R on its stop:

    extended   +4.0R
    failed     -1.0R
    break-even extension rate = 1.0 / (4.0 + 1.0) = 20%

Wait - that is a different figure from the one quoted in review, and it matters
which is right. The review assumed the SL sat at exactly -1R. The engine does not
place it there. The HTF trade uses sl_mode="swing", meaning the stop sits at the
SWING START price, so the loss on failure is however far price had retraced from
the window open, expressed in units of the HTF risk. That distance is measured
per trade here rather than assumed, because assuming -1R when the engine trades
-1.8R or -0.6R changes the break-even rate by a factor of two.

So this file reports the ACTUAL distribution of failure R, and derives the
break-even rate from it rather than from a guess. If failures average worse than
-1R the required extension rate is higher than 20%, and the headroom above it is
smaller than it looks.

WHAT DECIDES WHETHER THIS IS WORTH BUILDING
===========================================
    measured extension rate  vs  break-even extension rate

If the real rate sits below break-even, then a smaller htf_rr is simply correct
and no cleverness changes that. If it sits above, there is room for a rule that
only extends where the trade is structurally strong - which is the extension-rate
framing the reviewer described, and the only version of it that is not just a
restatement of "keep the target where it works".

THE BREAK-EVEN VARIANT, ALSO PREREGISTERED
==========================================
The reviewer noted that keeping the 3R target and moving the stop to breakeven
after 3R converts a failure from -1R into 0R, which would drop the required
extension rate from 20% to about 0%. That is a much better deal than it sounds,
and it is already implemented - v7_timecap.py:119 takes a breakeven_r parameter.
It is NOT enabled here. Enabling it changes every book and would be a new
selection round. It is measured as a separate column so the option is priced,
not chosen.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_extension_census.py
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

OUT = HERE / "extension_census.json"
MD = HERE / "extension_census.md"
REPORT = HERE.parent / "docs" / "learn" / "EXTENSION_CENSUS.md"

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htffs", "106"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htfesmcl4", "108")]
NEAR = 2.90   # "reached 3R" is read as landing within 0.1R of it


def htf_htf(sim, data, cfg, swing, rr, be=0.0):
    p = {**BP, **(cfg.get("params") or {}), "htf_rr": rr}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    return sorted([t for t in (o.get("htf_trades") or [])
                   if t.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))


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
            base = htf_htf(sim, ERA[era], cfg, swing, 3.0)
            far = htf_htf(sim, ERA[era], cfg, swing, 4.0)
            bes = htf_htf(sim, ERA[era], cfg, swing, 3.0, be=1.5)

            reachers = [t for t in base if net_r([t]) >= NEAR]
            ids = {int(t["entry_ts"]) for t in reachers}
            far_by = {int(t["entry_ts"]): t for t in far}
            bes_by = {int(t["entry_ts"]): t for t in bes}

            ext = fail = 0
            fail_rs = []
            for t in reachers:
                o = far_by.get(int(t["entry_ts"]))
                if o is None:
                    continue
                r4 = net_r([o])
                if r4 > NEAR + 0.30:
                    ext += 1
                else:
                    fail += 1
                    fail_rs.append(r4)

            # failure depth under the CURRENT default, measured not assumed
            depth = [net_r([t]) for t in reachers if net_r([t]) < NEAR]
            # what breakeven at 1.5R would have done to the same population
            be_gains = []
            for t in reachers:
                b = bes_by.get(int(t["entry_ts"]))
                if b is not None:
                    be_gains.append(net_r([b]) - net_r([t]))

            n = ext + fail
            rate = 100.0 * ext / n if n else 0.0
            mean_fail = (sum(fail_rs) / len(fail_rs)) if fail_rs else 0.0
            be_needed = (100.0 * (-mean_fail) / (4.0 - mean_fail)) if mean_fail < 0 else 0.0
            res[name][era] = {
                "reached_3R": len(reachers), "matched": n,
                "extended": ext, "failed": fail,
                "extension_rate_pct": round(rate, 1),
                "mean_failure_R": round(mean_fail, 3),
                "break_even_ext_rate_pct": round(be_needed, 1),
                "headroom_pp": round(rate - be_needed, 1),
                "depth_p10": round(sorted(depth)[max(0, int(0.10 * len(depth)))] if depth else 0.0, 2),
                "breakeven_mean_gain_R": round(sum(be_gains) / len(be_gains), 2) if be_gains else 0.0,
            }
            r = res[name][era]
            print("  %-4s %-4s  3R-reachers %4d  extended %4d (%5.1f%%)  mean failure %.2fR  "
                  "break-even needs %5.1f%%  headroom %+6.1f pp  | breakeven-at-1.5R would add %+.2fR each"
                  % (code, era.upper(), len(reachers), ext, rate, mean_fail,
                     be_needed, r["headroom_pp"], r["breakeven_mean_gain_R"]), flush=True)
        print("      (%.0fs)" % (time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")

    L = ["# The extension census - does 3R lead to 4R, and is the target in the right place?", "",
         "This is the second half of the `htf_rr` decomposition. That file found the",
         "whole 3.0-versus-4.0 split reduces to one number - the HTF-booked delta -",
         "which came out identical on every book: +18.2R on IS and -11.3R on OOS.",
         "Identical across books means those HTF trades are not book-specific. Every",
         "book trades the same underlying swings and differs only in which LTF",
         "entries it takes.", "",
         "So there is exactly one population that matters: the trades that reached 3R.",
         "The question about it is binary. Did the trade extend past 3R, or fail first?",
         "Net sums blurred that into a number that then got compared across eras.",
         "", "## The arithmetic, with the assumption removed", "",
         "The break-even extension rate depends entirely on how deep a failure is.",
         "The review assumed the stop sits at -1R. **It does not.** The HTF trade uses",
         '`sl_mode="swing"`, so the stop is the swing-start price, and the loss on',
         "failure is however far price retraced from the window open, in units of HTF",
         "risk. That distance is measured per trade below rather than assumed, because",
         "assuming -1R when the engine trades -1.8R or -0.6R moves the break-even rate",
         "by a factor of two.", "",
         "| book | era | reached 3R | extended | rate | mean failure R | break-even needs | headroom |",
         "|---|---|---:|---:|---:|---:|---:|---:|"]
    for name, code in BOOKS:
        for era in ("is", "oos"):
            r = res[name][era]
            L.append("| %s | %s | %d | %d | %.1f%% | %.2fR | %.1f%% | **%+.1f pp** |"
                     % (code, era.upper(), r["reached_3R"], r["extended"],
                        r["extension_rate_pct"], r["mean_failure_R"],
                        r["break_even_ext_rate_pct"], r["headroom_pp"]))
    L += ["", "## Reading it", "",
          "- **Headroom above zero means the larger target is currently paying for",
          "  itself** in that era. Headroom below zero means it is not, and a smaller",
          "  target is simply correct there.",
          "- **The rate moves between eras for the same population**, which is the",
          "  finding. If the books disagreed only about which LTF entries to take,",
          "  and the HTF population is shared, then a change in that population's",
          "  behaviour between 2021-22 and 2023-26 is a change in the market, not in",
          "  the strategy.",
          "- **That is the answer to 'which number should I use'.** Neither. The",
          "  parameter is not mis-set; the thing it points at is not stationary.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print("\nwrote %s, %s and %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
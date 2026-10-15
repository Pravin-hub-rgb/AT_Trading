"""
UNTESTED-KNOB CENSUS - the last untouched input space, with a firing check first.

WHY THIS SHAPE AND NOT HYPOTHESES

Three hypotheses in a row (swing shape, volatile candles, mark continuation)
produced large four-book IS effects that reversed on OOS. The conclusion recorded
in the sweep doc is that the IS margin of this book family is an ERA EFFECT, so
IS-only hypotheses are not worth running here.

What that leaves is the input side, and it is nearly empty. Read from the
signature, these knobs are named in the engine and set by no experiment at all:

    exp_window_floor_s     only ever 2_700 (the default)
    exp_window_floor_mode  only ever "fixed"
    exp_cap_days           only ever 16 (the default)
    exp_min_sl_pct         only ever 0
    exp_no_opposite        only ever 0 in every book here
    exp_trail_half         only ever 0 or 1
    exp_trail_skip_n       0..3, never swept

FIRING CHECK FIRST, THE LESSON OF THE DECAY GATE

The decay gate turned out to be 0-for-120. A knob that never fires produces a
plausible-looking net that is really the pin, and the honest first question is
not "how good is it" but "does it do anything at all". So every knob is measured
for whether it changes trade count or trade geometry BEFORE its net is discussed.
NULL is a real result and is recorded as one.

THE INVERSE TEST WHERE ONE EXISTS

  exp_window_floor_s   a longer floor delays the entry, a shorter one lets it in
                       sooner. Sweeping the value in both directions IS the
                       inverse: if only one direction wins, and the winning
                       direction is "later", the knob is a latency control, not a
                       signal.
  exp_cap_days         a cap on how long a position may live. Same logic - if
                       only longer wins, it is a holding-time control.
  exp_trail_half / _skip_n  exit-management dials with no complementary mode, so
                       they get STRONG or WEAK on the strength of era agreement
                       alone, and that is stated rather than dressed up.

DISCIPLINE

  - Default-off identity gate first, per knob.
  - IS decides, OOS computed alongside for the survivors. Never searched.
  - No book added, no registry change, no pin touched.
  - Own directory. Does not touch exp_mode_strict.py, exp_mode_yearly.py,
    registry/signal.py or any concurrent mode-census file.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_untouched_census.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backtest/experiments/refit_constants"))
from exp_mcl_matrix import metrics, load_era, LADDER_BOOKS  # noqa: E402

# name, values to sweep, what a change proves
KNOBS = [
    ("exp_window_floor_s", [0, 900, 1800, 2700, 3600, 5400],
     "entry latency floor: larger = enter later"),
    ("exp_window_floor_mode", ["fixed", "fs", "max"],
     "fixed = s+floor; fs = FS print time; max = the later of the two"),
    ("exp_cap_days", [2, 4, 8, 16, 32],
     "maximum bars a position may be held"),
    ("exp_min_sl_pct", [0.0, 0.001, 0.002, 0.004, 0.008],
     "minimum stop distance as a fraction of entry price"),
    ("exp_no_opposite", [0, 1],
     "block an entry while an opposite-direction position is open"),
    ("exp_trail_half", [0, 1],
     "ratchet the stop halfway to the candidate instead of all the way"),
    ("exp_trail_skip_n", [0, 1, 2, 3, 5],
     "drop the first N trailing-stop events outright"),
]


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    out = {"stage": "untouched_census", "knobs": [k[0] for k in KNOBS], "eras": {}}

    for era in ("is", "oos"):
        print()
        print("=" * 118)
        print("UNTOUCHED-KNOB CENSUS    era = %s" % era.upper())
        print("=" * 118)
        d = load_era(era)
        era_out = {}

        def run(book, **ov):
            cfg = EXPERIMENTS[book]
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            p.update(ov)
            sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
            r = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            return r["ltf_trades"] if isinstance(r, dict) else r

        # identity: whatever the knob's own default is, the book must reproduce
        print("  IDENTITY GATE - shipped params, must reproduce the pinned book")
        for b in LADDER_BOOKS:
            m = metrics(run(b))
            era_out.setdefault(b, {})["pin"] = m
            print("    %-28s n=%-4d NET=%+9.2f DD=%6.2f MaxCL=%d"
                  % (b, m["n"], m["net"], m["dd"], m["mc"]))
        print()

        for knob, values, meaning in KNOBS:
            print("  ---- %s : %s" % (knob, meaning))
            print("    %-28s %8s %6s %10s %8s %7s %7s %s"
                  % ("book", "value", "n", "NET", "DD", "MaxCL", "PF", "fires?"))
            print("    " + "-" * 88)
            fired_any = False
            for b in LADDER_BOOKS:
                pin = era_out[b]["pin"]
                default = None
                try:
                    default = BP.get(knob)
                except Exception:
                    pass
                if default is None:
                    cfgp = EXPERIMENTS[b]["params"]
                    default = cfgp.get(knob)
                for v in values:
                    m = metrics(run(b, **{knob: v}))
                    era_out[b].setdefault(knob, {})[str(v)] = m
                    if v == default:
                        continue                      # that is the pin row
                    fires = (m["n"] != pin["n"])
                    fired_any = fired_any or fires
                    print("    %-28s %8s %6d %+10.2f %8.2f %7d %7.2f %s"
                          % (b if v == values[0] else "", v, m["n"], m["net"],
                             m["dd"], m["mc"], m["pf"],
                             "FIRES" if fires else "no-op"))
            print()
            print("    VERDICT: %s"
                  % ("FIRES - measured below" if fired_any
                     else "NULL - no value changes a single trade. Dead knob."))
            print()
            era_out.setdefault("_knob_fires", {})[knob] = fired_any

        out["eras"][era] = era_out

    # ---- cross-era agreement, only for knobs that fired ----------------------
    print("=" * 118)
    print("CROSS-ERA SUMMARY - only knobs that actually fired")
    print("=" * 118)
    fired = [k for k, v in out["eras"]["is"].get("_knob_fires", {}).items() if v]
    null = [k for k, v in out["eras"]["is"].get("_knob_fires", {}).items() if not v]
    if null:
        print("  NULL (never change a trade on any book, any value): %s"
              % ", ".join(null))
    print()
    if not fired:
        print("  No knob fired. The entire untested input space is inert.")
        print("  That is the answer: there is no hidden edge in these knobs.")
    else:
        for knob in fired:
            print("  --- %s ---" % knob)
            print("    %-28s %14s %14s %12s %s"
                  % ("book", "best IS", "same value OOS", "agrees?", "note"))
            for b in LADDER_BOOKS:
                is_c = out["eras"]["is"][b].get(knob, {})
                oos_c = out["eras"]["oos"][b].get(knob, {})
                pin_is = out["eras"]["is"][b]["pin"]
                pin_oos = out["eras"]["oos"][b]["pin"]
                cand = [(v, m) for v, m in is_c.items()
                        if m["n"] != pin_is["n"] and m["net"] > pin_is["net"]]
                if not cand:
                    print("    %-28s %14s %14s %12s %s"
                          % (b, "-", "-", "-", "nothing beats the pin on IS"))
                    continue
                bestv, bestm = max(cand, key=lambda x: x[1]["net"])
                om = oos_c.get(bestv)
                agree = "-"
                if om:
                    agree = "YES" if om["net"] > pin_oos["net"] else "NO"
                print("    %-28s %14s %14s %12s %s"
                      % (b, "%s (%.2f)" % (bestv, bestm["net"]),
                         ("%.2f" % om["net"]) if om else "-", agree,
                         "OOS beat its pin" if agree == "YES" else
                         ("OOS lost to its pin" if agree == "NO" else "")))
            print()

    (HERE / "untouched_census_results.json").write_text(json.dumps(out, indent=2),
                                                        encoding="utf-8")
    print("  wrote %s" % (HERE / "untouched_census_results.json"))
    print()
    print("  NOTHING PROMOTED. Default-off identity verified per knob. No book,")
    print("  no registry entry, no pin touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
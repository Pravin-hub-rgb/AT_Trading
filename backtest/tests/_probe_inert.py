"""Falsification probe: are the four HTF feature lookbacks actually LIVE?

WHY THIS EXISTS
===============
In exp_htf_2h_deep.py the A2 and A3 arms produced BIT-IDENTICAL books in both
eras (+53.9 / +51.6 / +185.6 IS, -46.4 / -50.3 / +11.2 OOS). A2 and A3 differ
ONLY in the chop / garch / ent / detect lookbacks.

That has two very different explanations:
  (1) the features are genuinely inert - the book is decided by the swing
      chain alone, or
  (2) the parameters are silently DROPPED and never reach the engine.
(2) would make the A3 comparison meaningless and would silently invalidate
half this experiment, so it must be ruled out rather than assumed.

THE PROBE
=========
Hold the plane, the swings and every strategy param fixed, and drive the four
feature lookbacks to absurd values. If the book does not move, either they are
inert or they are not wired. To separate those two, the probe ALSO calls the
patched engine's own chop series directly - if `_chop_series_1h` returns a
different series for a different lb, the parameter is demonstrably reaching the
code, and a flat book can only be explained by the feature being non-binding on
trade selection.

Run: $env:PYTHONIOENCODING='utf-8'; python -u _probe_inert.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "backtest/tests/_htf_2h_inert_probe.json"


def main():
    import exp_htf_2h_deep as E
    from exp_sizing_combo import run as sim_fn
    from exp_equity_quality import equity_quality
    from experiment_registry import BP, EXPERIMENTS
    from engine.v18_params import SWING
    from src.btc.btc_routes import _compute_swings

    sim = E.build_deep_module()
    raw = E.load_scope("is")
    sw15 = _compute_swings(raw["f15"], "continuous", min_bars=SWING["min_bars_15m"])
    ltf = {"c15": raw["c15"], "sw15": sw15, "fine": raw["fine"]}
    # plane 2h, swings at min_bars 10/5 -> identical to arm A3 by construction
    htf = E.parent(raw, 7200, 10, 5)
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}

    cases = {
        "A3_baseline": dict(exp31_lb=14, garch_lb=96, ent_lb=96, fd_lb=48),
        "A2_halved": dict(exp31_lb=7, garch_lb=48, ent_lb=48, fd_lb=24),
        "absurd_tiny": dict(exp31_lb=2, garch_lb=3, ent_lb=3, fd_lb=3),
        "absurd_huge": dict(exp31_lb=200, garch_lb=400, ent_lb=400, fd_lb=200),
    }
    res = {}
    for name, fb in cases.items():
        book = sim_fn(sim, {**htf, **ltf}, params, htf_bar_secs=7200, **fb)
        m = equity_quality(book, 3.67)
        res[name] = {"feat": fb, "n": m["n"], "net": round(m["net"], 4),
                     "pf": m["pf"]}
        print(f"  {name:<12} {str(fb):<52} n={m['n']:>3} net={m['net']:>+9.4f}",
              flush=True)

    # Direct proof the chop parameter reaches the code: load the patched module
    # and call its own _chop_series_1h at two different lb values.
    spec = importlib.util.spec_from_file_location(
        "v18_htf2h_deep", str(ROOT / "backtest/tests/_htf2hdeep_tmp.py"))
    m2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m2)
    c = htf["c1h"]
    a = m2._chop_series_1h(c, lb=14)
    b = m2._chop_series_1h(c, lb=2)
    same = (a == b)
    print(f"\n  _chop_series_1h lb=14 vs lb=2 -> identical: {same}", flush=True)

    nets = {k: v["net"] for k, v in res.items()}
    verdict = ("features are LIVE but NON-BINDING on trade selection"
               if not same and len(set(nets.values())) == 1 else
               "features are NOT inert - books move with them")
    payload = {"books": res, "chop_series_differs_by_lb": not same,
               "distinct_nets": sorted(set(nets.values())),
               "verdict": verdict}
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\n  VERDICT: {verdict}")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()

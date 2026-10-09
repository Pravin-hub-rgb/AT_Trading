"""exp_route_parity - prove the new chart routes reproduce the registry pins.

WHY THIS FILE IS A GATE AND NOT A NOTE
======================================
`btc_routes.py` now carries two new version branches so the chart can display
the fsent pair. Until now those books were only reachable from the harness, and
the harness does NOT call the engine the API calls:

  * the harness calls `test_experiments_craze.build_module()`, which patches the
    engine SOURCE TEXT before importing it. `exp_tf_family.build_family_module`
    injects `htf_bar_secs` / `ltf_bar_secs` the same way.
  * the API calls the real `simulate_htf_ltf_streak_halt` from
    `engines/htf_ltf/unified.py`, unpatched.

The difference that matters here: **`exp_mltf` is not a parameter of the real
engine.** inspect.signature returns 38 named parameters and no `**kwargs`, so a
route that passed `exp_mltf=True` would raise TypeError at request time. The
registry books carry `exp_mltf=True` because that is how the harness spells
"allow overlapping positions".

In the real engine the same behaviour is `max_positions=0`, documented as
"0 = unlimited (v19 behaviour), the gate never fires". That is the claim this
file tests rather than trusts: it runs both books through the EXACT parameter set
the route now uses, with no `exp_mltf`, and requires the registry pins to come out
byte-for-byte.

If someone later adds a knob to a registry book and forgets the route branch, or
changes one side only, this fails instead of the chart quietly showing a
different book under a label that quotes a pin.

Run:  cd backtest/tests
      python -u exp_route_parity.py
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

OUT = Path(__file__).parent / "_route_parity.json"

# Mirrors the route branch in btc_routes.py, verbatim, minus the candle
# plumbing. If you change one, change this, and the test will tell you if the
# registry pins stopped reproducing.
ROUTE_PARAMS = {
    "sl_buf_atr": 0.01,
    "ext_stop_r": 0.0,
    "atr_high_thresh": 0.65,
    "atr_low_thresh": 0.35,
    "cooldown_bars": 8,
    "max_consecutive_losses": 3,
    "max_positions": 0,
    "exp_partial_r": 0.0,
    "exp_persist": 7,
    "exp_fs_entry_side": "long",
    "pivot_rule": "leg",
}
BOOKS = {
    "fsent_champ_long": "atr_high",
    "fsent_champ_long_mode_atr_low": "atr_low",
}
# fsent_sig_full is NOT one of the pair above - different params entirely, and
# max_positions=1 rather than 0. It gets its own route-param set and its own
# check, because folding it into the pair's dict would silently assert that the
# signal book's pins reproduce under the multi-book's concurrency setting, which
# they do not and must not.
SIG_FULL_PARAMS = {
    "sl_buf_atr": 0.01,
    "chop_thresh": 58.0,
    "cooldown_bars": 8,
    "max_consecutive_losses": 3,
    "max_positions": 1,          # SERIAL - the busy_until gate is armed
    "mode": "atr_high",
    "atr_high_thresh": 0.65,
    "atr_low_thresh": 0.35,
    "ext_stop_r": 3.0,           # not 0.0 - this is a different book
    "exp_partial_r": 0.0,
    "exp_fs_entry_side": "short",
    "exp_bias_momentum_min": 0.8,
    "exp_trail_skip_n": 2,
    "exp_fs_small_swing": 6.0,
    "exp_skip_weekend": 1,
    "window_end": "exit",
}


def real_engine_signature():
    from src.btc.engines.htf_ltf import unified
    sig = inspect.signature(unified.simulate_htf_ltf_streak_halt)
    return sig


def main():
    from exp_tf_family import build_family_module
    from run_experiment import net_r, get_swings, _net_dd
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS
    from src.btc.btc_routes import _trade_costs, _net_stats
    from src.btc.btc_engine import trade_stats
    from src.btc.engines.htf_ltf import unified as real

    sig = real_engine_signature()
    has_kwargs = any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())
    P = print
    P("=" * 108)
    P("  ROUTE PARITY - the chart branches must reproduce the registry pins")
    P("=" * 108)
    P("  real engine simulate_htf_ltf_streak_halt: %d named params, **kwargs = %s"
      % (len(sig.parameters), has_kwargs))
    P("  'exp_mltf' in real signature: %s   <- if False, passing it would TypeError"
      % ("exp_mltf" in sig.parameters))
    if "exp_mltf" in sig.parameters:
        P("  NOTE: the real engine now accepts exp_mltf. Re-check whether")
        P("  max_positions=0 is still the correct spelling for this route.")
    P("  'max_positions' in real signature: %s" % ("max_positions" in sig.parameters))
    P()

    # The route's own params must all be real-engine params. This is the check
    # that would have caught a TypeError before a user's request hit it.
    for label, pr in (("pair", ROUTE_PARAMS), ("sig_full", SIG_FULL_PARAMS)):
        unknown = sorted(set(pr) - set(sig.parameters))
        if unknown:
            P("  FAIL: %s route passes params the real engine does not accept: %s"
              % (label, unknown))
            return 1
    P("  OK: every param both routes pass is a real engine parameter.")
    P()

    sim = build_family_module()
    payload = {}
    rc = 0

    def metrics(tr):
        """Reproduce the PIN CONVENTION exactly, by calling the same helpers
        exp_fastcheck calls.

        This function existed in its own form in the first version of this file
        and got fsent_sig_full's out-of-sample count wrong by one: it filtered
        `outcome == "open"` before counting, while `exp_fastcheck` does NOT - it
        returns `n = len(tr)` on the raw list, and only `_net_dd` skips open
        trades. So the pin says 152 and a filtered count says 151, with the net
        identical to the cent.

        That is not a rounding detail, it is two different definitions of "how
        many trades did this book make", and it has already produced two false
        mismatches in this repo (trail_skipn4 hit the same thing during the prune).
        Rather than restate the convention a third time and hope, this calls the
        same code the pins were written by. Agreement is then structural.
        """
        _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
        return {"n": len(tr),
                "net": round(_net_stats(trade_stats(tr), tr)["net_total_r"], 2),
                "dd": round(_net_dd(tr), 2)}

    ALL = ([(bk, mode, ROUTE_PARAMS) for bk, mode in BOOKS.items()]
           + [("fsent_sig_full", None, SIG_FULL_PARAMS)])
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, "sw10")
        for book, mode, route_params in ALL:
            cfg = EXPERIMENTS[book]
            pins = cfg["pins"]
            # registry params minus exp_mltf, plus exactly what the route passes.
            pr = {k: v for k, v in cfg["params"].items() if k != "exp_mltf"}
            pr.update(route_params)
            if mode:
                pr["mode"] = mode
            o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **pr)
            m = metrics(o["ltf_trades"])

            if era == "is":
                exp_n, exp_net, exp_dd = pins["n"], pins["net"], pins["dd_net"]
            else:
                exp_n, exp_net, exp_dd = pins["oos_n"], pins["oos_net"], pins["oos_dd_net"]
            ok = (m["n"] == exp_n and abs(m["net"] - exp_net) < 0.05
                  and abs(m["dd"] - exp_dd) < 0.05)
            P("  %-34s %-4s got %4dt / %+8.2fR / dd %5.2fR   want %4dt / %+8.2fR / dd %5.2fR   %s"
              % (book, era.upper(), m["n"], m["net"], m["dd"], exp_n, exp_net, exp_dd,
                 "OK" if ok else "MISMATCH"))
            payload.setdefault(book, {})[era] = {
                "got": [m["n"], m["net"], m["dd"]],
                "want": [exp_n, exp_net, exp_dd], "ok": ok}
            if not ok:
                rc = 1

    P()
    # second, independent check: run the REAL unpatched engine on the same
    # inputs and require identical trades to the patched harness.
    P("  cross-check: real unpatched engine vs the patched harness")
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, "sw10")
        for book, mode, route_params in ALL:
            pr = {k: v for k, v in EXPERIMENTS[book]["params"].items() if k != "exp_mltf"}
            pr.update(route_params)
            if mode:
                pr["mode"] = mode
            out = real.simulate_htf_ltf_streak_halt(
                d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **pr)
            m = metrics(out["ltf_trades"])
            want = payload[book][era]["want"]
            ok = m["n"] == want[0] and abs(m["net"] - want[1]) < 0.05
            P("    %-34s %-4s real engine %4dt / %+8.2fR   %s"
              % (book, era.upper(), m["n"], m["net"], "OK" if ok else "MISMATCH"))
            payload[book][era]["real"] = [m["n"], m["net"], ok]
            if not ok:
                rc = 1

    OUT.write_text(json.dumps({"route_params": ROUTE_PARAMS, "books": payload},
                              indent=2) + "\n", encoding="utf-8")
    P()
    P("  RESULT: %s" % ("PASS - the chart branches and the registry agree."
                        if rc == 0 else "FAIL - the chart would show a different"
                        " book than the label claims."))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
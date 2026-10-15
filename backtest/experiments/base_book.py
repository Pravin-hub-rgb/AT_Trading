"""THE BASE - the bare HTF+LTF book, with nothing added on top.

WHAT "NO FILTER, JUST HTF AND LTF" MEANS HERE
----------------------------------------------
The engine is simulate_htf_ltf_streak_halt in unified.py. Called with its own
signature defaults and nothing else, it does exactly this: the 1h plane emits a
bias window, the 15m plane takes the trade if that window allows it. No regime
routing beyond the engine's own default, no cooldown, no streak halt, no
position cap, no partial exit, no exp_ filter of any kind.

    sl_buf_atr=0.25, ext_stop_r=1.5, chop_thresh=61.8, atr_low_thresh=0.35,
    atr_high_thresh=0.65, mode="chop", soft_width=4.0, cooldown_bars=0,
    max_consecutive_losses=0, htf_rr=3.0, window_end="exit", max_positions=0

WHY THIS FILE EXISTS INSTEAD OF JUST USING A REGISTRY BOOK
---------------------------------------------------------
Two candidates were checked and both are unusable as a base:

  champion_sig_sw10  - BASELINE.md:69-81 publishes this as the base, but it is
      RETIRED (registry/retired.py:82, bar 1, OOS negative) and its pins no
      longer reproduce: pinned IS 395 / +48.63, measured IS 341 / -14.32. Its
      pins predate the current engine. Gating a new thesis on them would have
      failed a correct build.

  champion_multi_sw10 - sets pivot_rule="origin", which kingsweep.py:232 marks
      LOOK-AHEAD. Research only.

So the base is built from the engine signature instead, and measured fresh. It
has no pin because nothing pins a book that has never been run; the guard here
is the mark chain, not a trade count.

THE LOOK-AHEAD TRAP, WHICH IS THE POINT OF exp_causal_sl
----------------------------------------------------------
The engine's own default is exp_causal_sl=0, and unified.py:304-310 says what
that is: sl_pivot = the swing's true ORIGIN, which "is only knowable once the
leg has completed, so using it at the entry bar is lookahead". The default the
engine ships with is therefore a look-ahead book.

This base sets exp_causal_sl=1, which anchors the LTF stop to the running
extreme confirmed at the entry bar. Both are measured below so the size of the
look-ahead is on the record rather than assumed.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

import exp_repin_stale as repin                                  # noqa: E402
from exp_signal_metrics import load_era                          # noqa: E402

SWING = "sw10"

# The engine signature at unified.py:292-347, verbatim, plus max_positions=0.
ENGINE_SIGNATURE_DEFAULTS = {
    "sl_buf_atr": 0.25,
    "ext_stop_r": 1.5,
    "chop_thresh": 61.8,
    "atr_low_thresh": 0.35,
    "atr_high_thresh": 0.65,
    "mode": "chop",
    "soft_width": 4.0,
    "cooldown_bars": 0,
    "max_consecutive_losses": 0,
    "htf_rr": 3.0,
    "window_end": "exit",
    "exp_ltf_no_entry": 0,
    "exp_htf_fs_entry": "",
    "exp_window_floor_s": 2_700,
    "max_positions": 0,
}


def base_cfg(exp_causal_sl: int = 1, **over) -> dict:
    """The bare base. exp_causal_sl defaults to 1 - see the module docstring."""
    p = dict(ENGINE_SIGNATURE_DEFAULTS)
    p["exp_causal_sl"] = exp_causal_sl
    p.update(over)
    return {"params": p, "swing": SWING, "basis": "fine"}


def trades_of(sim, data, c: dict) -> list:
    """Completed trades with costs applied. Open positions are dropped.

    Dropped deliberately: every thesis here reasons about a finished trade's R,
    and a position still open at the era boundary has none yet. This is also why
    the counts below are not comparable to registry pins, which keep opens.
    """
    sw = {"sw10": data["sw10"], "sw20": data["sw20"],
          "sw15": data["sw15"], "htf15": data["htf15"]}[c["swing"]]
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=data["fine"],
             **{**dict(repin.re_.BP), **c["params"]})["ltf_trades"]
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    return [t for t in tr if t.get("outcome") != "open"]


def net_r(t: dict) -> float:
    from exp_equity_quality import net_r as _nr
    return float(_nr([t]))


def summarise(tr: list) -> dict:
    if not tr:
        return {"n": 0, "net": 0.0, "r_trade": 0.0, "wr": 0.0}
    nets = [net_r(t) for t in tr]
    n = len(nets)
    total = sum(nets)
    return {"n": n, "net": round(total, 2),
            "r_trade": round(total / n, 4),
            "wr": round(100.0 * sum(1 for x in nets if x > 0) / n, 1)}


def establish(sim, eras) -> dict:
    """Measure the base. No pin to gate against, so state the guard instead."""
    print("=" * 92)
    print("THE BASE - bare engine, nothing added. Fresh measurement, no pin exists.")
    print("=" * 92)
    out = {}
    for label, sl in (("CAUSAL  exp_causal_sl=1  (the base)", 1),
                      ("LOOK-AHEAD exp_causal_sl=0 (engine default, reference only)", 0)):
        print()
        print(label)
        print("  %-5s %6s %10s %10s %8s" % ("era", "n", "net R", "R/trade", "win %"))
        for era in ("is", "oos"):
            tr = trades_of(sim, eras[era], base_cfg(sl))
            s = summarise(tr)
            out["%s|%s" % (sl, era)] = s
            print("  %-5s %6d %+10.2f %10.4f %7.1f%%"
                  % (era.upper(), s["n"], s["net"], s["r_trade"], s["wr"]))
    a, b = out["1|oos"], out["0|oos"]
    print()
    print("  Look-ahead removed, out of sample: %+.2fR -> %+.2fR  (%.2fR honest)"
          % (b["net"], a["net"], b["net"] - a["net"]))
    print()
    print("  Every thesis below is measured on the CAUSAL row.")
    print("  Open positions are excluded, so these counts sit below registry pins")
    print("  that keep them - compare net, not n, against a pin.")
    return out


def load():
    import test_experiments_craze as craze
    return craze.build_module(), {e: load_era(e) for e in ("is", "oos")}
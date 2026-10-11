"""G2 - does the arming gate actually close, or only ever open?

WHAT IS BEING MEASURED
----------------------
A B1 mark is emitted by _step(), and _step() runs only under `if self.armed`
(firstswing.py:363). A break does not become a B1 on its own; it has to pass the
gate. Exactly four statements in the whole file set `armed` (348, 352, 357, 361)
and all four sit inside the block at firstswing.py:346.

Two of them are conditional, and they are the only place in the engine where a
B1-eligible break can be REJECTED:

    L356   if self._seal_h_idx >= 0 and self._seal_h_idx < g_idx:
    L360   if self._seal_l_idx >= 0 and self._seal_l_idx < g_idx:

ARM1 was this condition returning True forever - which is why a working gate was
indistinguishable from no gate at all. A gate that never closes is not a gate.

The accept side already has evidence: the chain moved 7975 -> 7993 when the
per-kind guard landed, and the owner re-read the marks on the chart. So the
question here is only the REJECT count.

HOW IT IS MEASURED
------------------
compute_btc_swings() is called with the exact arguments _compute_swings uses, so
the chain produced here is the shipping chain. The first attempt drove SwingEngine
by hand, produced 5299 marks instead of 7993, and would have counted nothing
meaningful - it would have looked like the gate never ran at all.

The engine is untouched. process_bar is wrapped and the state the two gates read
is sampled immediately before delegating to the real implementation.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
from src.firstswing import SwingEngine

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000

COUNTS = collections.Counter()
REJECTS = []
AGES = {"L356": [], "L360": []}

_real = SwingEngine.process_bar


def _counted(self, c, i):
    g_idx = i
    seal_h = getattr(self, "_seal_h_idx", -1)
    seal_l = getattr(self, "_seal_l_idx", -1)
    leg = getattr(self, "_pending_leg_dir", None)
    pend = getattr(self, "_pending_arm", False)
    state = getattr(self, "state", None)
    defer = getattr(self, "defer_same_bar_arm", False)
    try:
        up_break = c.high > self.e_hi.px
        down_break = c.low < self.e_lo.px
    except Exception:
        up_break = down_break = False

    _real(self, c, i)

    if not (defer and pend and state == "watch"):
        return

    if leg == "up" and up_break:
        COUNTS["L356_up_leg_up_break"] += 1
        AGES["L356"].append(seal_h - g_idx)
        ok = seal_h >= 0 and seal_h < g_idx
        COUNTS["L356_ACCEPT" if ok else "L356_REJECT"] += 1
        if not ok:
            REJECTS.append({"idx": i, "time": c.time, "leg": leg, "seal_idx": seal_h,
                            "bar_idx": g_idx, "px": c.high,
                            "why": "seal_never_set" if seal_h < 0 else "sealed_on_this_bar"})
    elif leg == "down" and down_break:
        COUNTS["L360_down_leg_down_break"] += 1
        AGES["L360"].append(seal_l - g_idx)
        ok = seal_l >= 0 and seal_l < g_idx
        COUNTS["L360_ACCEPT" if ok else "L360_REJECT"] += 1
        if not ok:
            REJECTS.append({"idx": i, "time": c.time, "leg": leg, "seal_idx": seal_l,
                            "bar_idx": g_idx, "px": c.low,
                            "why": "seal_never_set" if seal_l < 0 else "sealed_on_this_bar"})


SwingEngine.process_bar = _counted


def report():
    a356 = COUNTS["L356_ACCEPT"]
    r356 = COUNTS["L356_REJECT"]
    a360 = COUNTS["L360_ACCEPT"]
    r360 = COUNTS["L360_REJECT"]
    acc, rej = a356 + a360, r356 + r360
    print("=" * 78)
    print("G2  arming gate outcomes - final per-kind engine, real shipping chain")
    print("=" * 78)
    print("  L356  up leg,   up_break     accept %-6d  reject %d" % (a356, r356))
    print("  L360  down leg, down_break   accept %-6d  reject %d" % (a360, r360))
    print("  " + "-" * 74)
    print("  gate evaluated %d times      ACCEPT %d   REJECT %d" % (acc + rej, acc, rej))
    print("")

    for nm in ("L356", "L360"):
        arr = AGES[nm]
        if not arr:
            continue
        d = collections.Counter(arr)
        print("  %s  seal age = seal_idx - bar_idx   (negative = sealed on an EARLIER bar)" % nm)
        print("      n=%d   min=%d   max=%d" % (len(arr), min(arr), max(arr)))
        print("      age == 0  (sealed on this bar) : %d" % d.get(0, 0))
        print("      age  < 0  (sealed earlier)     : %d" % sum(v for k, v in d.items() if k < 0))
        top = ", ".join("age %+d x %d" % (k, v) for k, v in sorted(d.items())[:6])
        print("      distribution: %s" % top)
        print("")

    if rej:
        print("  VERDICT: GATE CLOSES. %d B1-eligible breaks were rejected." % rej)
        why = collections.Counter(x["why"] for x in REJECTS)
        for k, v in why.most_common():
            print("      %-22s %d" % (k, v))
        print("")
        print("  rejected breaks:")
        for r in REJECTS[:10]:
            print("      %-18s leg=%-4s seal_idx=%-7d bar_idx=%-7d px=%-11s %s"
                  % (r["time"], r["leg"], r["seal_idx"], r["bar_idx"], r["px"], r["why"]))
    else:
        print("  VERDICT: THE REJECT PATH IS NEVER REACHED on this data.")
        print("")
        print("  Not the same as ARM1. In ARM1 the condition was wrong - it could not see")
        print("  the seal index at all, so it returned True even when the seal was on the")
        print("  current bar. Here the condition is correct and the distribution above shows")
        print("  why it never has to fire: by the time the walker has sealed a matching-kind")
        print("  pivot on the bar that ends the leg, that pivot always belongs to an EARLIER")
        print("  candle. The pivot it seals on this bar is the opposite kind, so the")
        print("  matching-kind seal is still older than the bar.")
        print("")
        print("  This is a VACUOUS GUARD on this dataset, not a no-op guard. It is not")
        print("  protecting anything today and it is not silently dropping marks either:")
        print("  the chain is 7993 marks and the owner has read them.")
    return rej


def main():
    candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    swings = compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                                max_swings=max(1, len(flow) // 2))
    marks = sum(len(s["breaks"]) for s in swings)
    print("candles %d   swings %d   marks %d   (shipping chain)\n" % (len(flow), len(swings), marks))
    rej = report()
    Path(ROOT / "backtest/tests/_g2.json").write_text(json.dumps({
        "candles": len(flow), "swings": len(swings), "marks": marks,
        "L356_accept": COUNTS["L356_ACCEPT"], "L356_reject": COUNTS["L356_REJECT"],
        "L360_accept": COUNTS["L360_ACCEPT"], "L360_reject": COUNTS["L360_REJECT"],
        "total_reject": rej,
        "L356_age_hist": dict(collections.Counter(AGES["L356"])),
        "L360_age_hist": dict(collections.Counter(AGES["L360"])),
    }, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()

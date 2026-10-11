"""Missing-B1 detector on the owner's rule, walking the chain engine by engine.

THE RULE
--------
Seed candle GREEN  ->  its LOW is the leg's first live level; the pivot that forms on
the high side is the second. Seed RED -> mirrored, its HIGH and the opposite pivot.
Any candle breaking either is a B1. Owner, on 2023-02-10: the swing starts on the
green 21:30, 21:45 takes out the 21:30 low and is a B1, 22:45 is the next B1, 01:00
the FLIP.

WHY THIS FILE EXISTS ALONGSIDE exp_missing_seed_break.py
--------------------------------------------------------
That one read the seed off seg.start_idx. It is not the seed: _lock sets start_idx to
the EXTREME's position at lock time, so for swing 0 the B1 is at idx 1 while
start_idx is 29, and comparing the two produced 1,013 false misses. The seed is the
first bar an engine ever saw - bars_seen == 1 - which btc_swing never writes into the
chain it returns.

So this one instruments the engine class instead and keeps each engine's own seed
along with its own marks. btc_swing builds one engine per swing, so engine -> leg is
one to one, which is the mapping the rule needs.

Reads no marks from the returned chain: candles and engine emissions only.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_missing_leg_seed.py [limit] [show]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_missing_leg_seed.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"
TOL = 2


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    show = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    t0 = time.time()

    from src.firstswing import SwingEngine
    from src.btc.btc_routes import _load_window
    from src.btc.btc_swing import compute_btc_swings

    legs = []                      # one per engine, in build order
    cur = {}

    real_init = SwingEngine.__init__

    def init(self, *a, **kw):
        real_init(self, *a, **kw)
        cur = {}
        legs.append(cur)
        self._leg = cur
    SwingEngine.__init__ = init

    real_step = SwingEngine.process_bar

    def step(self, c, g_idx):
        cur = self._leg
        if cur.get("seed") is None:
            cur["seed"] = g_idx
            cur["seed_candle"] = (c.date, c.open, c.high, c.low, c.close)
        r = real_step(self, c, g_idx)
        if self.break_marks:
            for m in self.break_marks:
                cur.setdefault("marks", []).append(
                    {"idx": m.idx, "time": m.time, "kind": m.kind,
                     "dir": m.dir, "px": m.px})
        self.break_marks = []
        return r
    SwingEngine.process_bar = step

    candles, flow = _load_window(TF, limit, SYMBOL)[0]
    flow = list(flow)
    compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=len(flow) // 2)

    missing, pivot_first, clean, no_break = [], 0, 0, 0
    for L in legs:
        sc = L.get("seed_candle")
        if not sc:
            continue
        seed_i = L["seed"]
        _d, o, h, l, cl = sc
        green = cl >= o
        lvl = l if green else h
        marks = L.get("marks", [])
        b1 = [m for m in marks if m["kind"] == "B1"]

        last = max([m["idx"] for m in marks] + [seed_i])
        hit = None
        for i in range(seed_i + 1, min(last + 1, len(candles))):
            cc = candles[i]
            if (cc["low"] < lvl) if green else (cc["high"] > lvl):
                hit = i
                break
        if hit is None:
            if b1:
                clean += 1
            else:
                no_break += 1
            pivot_first += 1
            continue
        near = [m for m in b1 if abs(m["idx"] - hit) <= TOL]
        if near:
            clean += 1
        else:
            missing.append({
                "seed": candles[seed_i]["date"][:16], "green": green,
                "extreme": lvl, "want": "down" if green else "up",
                "first_break": candles[hit]["date"][:16], "first_break_idx": hit,
                "b1": ", ".join("%s@%d" % (m["dir"], m["idx"]) for m in b1) or "none",
                "earlier_b1": (b1 and b1[0]["idx"] < hit),
            })

    n = len(legs)
    print("\n" + "=" * 78)
    print("MISSING LEG-SEED BREAKS   %s  min_bars=%d  limit=%d" % (TF, MIN_BARS, limit))
    print("=" * 78)
    print("\n  legs built: %d" % n)
    print("    seed extreme never broken in the leg      : %d" % pivot_first)
    print("    seed extreme broken, B1 present            : %d" % clean)
    print("    seed extreme broken, NO B1   <-- MISSING   : %d" % len(missing))
    if missing:
        print("\n--- MISSING (%d) ---" % len(missing))
        for m in missing[:show]:
            print("  seed %s %-5s extreme %-9.1f want %-4s first break %s   b1: %s%s"
                  % (m["seed"], "green" if m["green"] else "red", m["extreme"],
                     m["want"], m["first_break"], m["b1"],
                     "   (a B1 already fired earlier)" if m["earlier_b1"] else ""))
        if len(missing) > show:
            print("  ... and %d more in the JSON" % (len(missing) - show))
    OUT.write_text(json.dumps({"legs": n, "missing": missing},
                              indent=1, default=str) + "\n", encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

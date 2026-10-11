"""Hardest cases for the owner to check: where a remaining bug would show first.

WHY THIS FILE
-------------
Both detectors report zero - exp_b1_pipeline finds no mark broken wrongly, and
exp_missing_leg_seed finds no B1 missing. Two tools agreeing after three earlier
tools produced confident wrong numbers at the owner's hands is not proof. What the
owner needs is a short list of the candles where a remaining defect is MOST likely,
so that checking ten of them is worth more than checking ten random ones.

THE THREE RISK CLASSES
----------------------
RISK 1 - the bar sealed its OWN extreme and also broke an older pivot.
  This is the exact shape the per-kind guard was written for: 2023-02-13 04:30,
  where the walker emitted H@04:00 (older), L@04:15 (older) and H@04:30 (its own
  high) in one batch. The newest code path in the engine, so the least exercised.
  If the H/L split is wrong anywhere, it is here.

RISK 2 - the bar sealed BOTH an H and an L of its own in one batch.
  Two seals, both at g_idx. The guard reads only the matching kind, so the other
  kind's staleness must not leak into the decision. A per-kind bug would hide here
  and nowhere else.

RISK 3 - B1 landed on the leg's own seed extreme, the first-candle case.
  No pivot exists yet, so the only level is the seed's extreme and the arming
  question is at its most degenerate. This is the rule the owner stated most
  explicitly, and the least covered by the earlier cases he checked.

Each class is printed with enough context to settle it on the chart in one look:
the seed, its colour and extreme, every seal the walker emitted on the bar and which
candle each seal's extreme belonged to, and the level the mark is stamped at.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_hard_cases.py [limit] [per_class]
"""
from __future__ import annotations

import json
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_hard_cases.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    t0 = time.time()

    # Instrument: record every seal the walker emits, and every mark, with the seed
    # of the engine that produced it. btc_swing builds one engine per swing.
    p1 = ROOT / "backend" / "src" / "firstswing.py"
    p2 = ROOT / "backend" / "src" / "btc" / "btc_swing.py"
    src = p1.read_text(encoding="utf-8")

    # Seals are recorded inside the walker loop, where p exists. Marks are recorded
    # at the step call, where break_marks has been filled. Two separate anchors:
    # one attempt at a single combined hook referenced p before the loop bound it.
    seal_anchor = "            if not p.sealed:\n                continue\n"
    assert src.count(seal_anchor) == 1
    src = src.replace(seal_anchor, seal_anchor +
                      "            _HS = getattr(self, '_hard', None)\n"
                      "            if _HS is not None:\n"
                      "                _HS.setdefault('seals', {}).setdefault(g_idx, []).append(\n"
                      "                    (p.kind, p.px, p.idx))\n", 1)

    mark_anchor = "        if self.armed:\n            self._step(down_break, up_break)\n"
    assert src.count(mark_anchor) == 1
    src = src.replace(mark_anchor,
                      "        _HM = getattr(self, '_hard', None)\n"
                      "        if _HM is not None and self.break_marks:\n"
                      "            _HM.setdefault('marks', []).extend(\n"
                      "                (k.kind, k.dir, k.px, k.idx, self.bars_seen)\n"
                      "                for k in self.break_marks)\n"
                      "            self.break_marks = []\n" + mark_anchor, 1)

    name = "src.firstswing_hard"
    m = types.ModuleType(name)
    m.__file__ = str(p1)
    m.__package__ = "src"
    m.__dict__["__name__"] = name
    sys.modules[name] = m
    exec(compile(src, str(p1), "exec"), m.__dict__)

    sw = p2.read_text(encoding="utf-8").replace(
        "from src.firstswing import", "from src.firstswing_hard import")
    nm = "src.btc.btc_swing_hard"
    sm = types.ModuleType(nm)
    sm.__file__ = str(p2)
    sm.__package__ = "src.btc"
    sm.__dict__["__name__"] = nm
    sys.modules[nm] = sm
    exec(compile(sw, str(p2), "exec"), sm.__dict__)

    legs = []
    cur = {}
    real_init = sm.SwingEngine.__init__

    def init(self, *a, **kw):
        real_init(self, *a, **kw)
        cur = {}
        cur["_hard"] = self._hard = cur
        legs.append(cur)
    sm.SwingEngine.__init__ = init

    from src.btc.btc_routes import _load_window
    candles, flow = _load_window(TF, limit, SYMBOL)[0]
    flow = list(flow)
    sm.compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                          max_swings=len(flow) // 2)

    risk1, risk2, risk3 = [], [], []
    for L in legs:
        h = L.get("_hard") or {}
        seeds = h.get("seals", {})
        marks = h.get("marks", [])
        if not marks:
            continue
        b1 = [x for x in marks if x[0] == "B1"]
        if not b1:
            continue
        for kind, dirn, px, idx, bseen in b1:
            sl = seeds.get(idx, [])
            own_h = [s for s in sl if s[0] == "H" and s[2] == idx]
            own_l = [s for s in sl if s[0] == "L" and s[2] == idx]
            old_h = [s for s in sl if s[0] == "H" and s[2] < idx]
            old_l = [s for s in sl if s[0] == "L" and s[2] < idx]
            base = {"t": candles[idx]["date"][:16], "kind": kind, "dir": dirn,
                    "px": px, "idx": idx,
                    "seals": [(k, round(v, 1), i) for k, v, i in sl]}
            c = candles[idx]
            if own_h and old_h:
                risk1.append(dict(base, why="sealed its OWN H and broke an older H",
                                  own=own_h[0][1], old=old_h[0][1]))
            if own_h and own_l:
                risk2.append(dict(base, why="sealed BOTH its own H and its own L"))
            if bseen <= 2:
                risk3.append(dict(base, why="B1 on the leg's own first candle",
                                  bars_seen=bseen))

    for nm2, bag in (("RISK 1  bar sealed its OWN high AND broke an older pivot "
                      "(the shape the per-kind guard exists for)", risk1),
                     ("RISK 2  bar sealed BOTH its own H and its own L in one batch", risk2),
                     ("RISK 3  B1 landed on the leg's own first candle "
                      "(no pivot exists yet)", risk3)):
        print("\n" + "=" * 78)
        print("%s" % nm2)
        print("=" * 78)
        print("  %d cases in the window" % len(bag))
        for r in bag[:per]:
            print("\n    %s   B1 %s @ %.1f" % (r["t"], r["dir"], r["px"]))
            print("       %s" % r["why"])
            if "own" in r:
                print("       sealed own H %.1f ; broke older H %.1f" % (r["own"], r["old"]))
            if "bars_seen" in r:
                print("       bar number %d of this leg" % r["bars_seen"])
            if r["seals"]:
                print("       walker sealed on this bar: %s"
                      % ", ".join("%s %.1f@%s" % s for s in r["seals"]))
            w = 2
            for c in candles[r["idx"] - w: r["idx"] + w + 1]:
                tag = "  <<< the B1" if c["date"][:16] == r["t"] else ""
                print("         %s O=%-9.1f H=%-9.1f L=%-9.1f C=%-9.1f%s"
                      % (c["date"][11:16], c["open"], c["high"], c["low"],
                         c["close"], tag))

    OUT.write_text(json.dumps({"risk1": risk1, "risk2": risk2, "risk3": risk3},
                              indent=1, default=str) + "\n", encoding="utf-8")
    print("\ncounts: risk1=%d risk2=%d risk3=%d   wrote %s  (%.0fs)"
          % (len(risk1), len(risk2), len(risk3), OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

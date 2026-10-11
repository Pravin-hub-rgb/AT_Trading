"""Four ways to define B1, measured on the same candles with the same validator.

THE QUESTION
------------
The owner compared unpatched against patched and found the mark is sometimes right
in patched, sometimes right in unpatched. He wants BOTH brought to the same place -
the same pattern as the retro/causal pair, which was reconciled and then the retro
side retired.

Why the two disagree is structural, and it is two separate decisions rather than one:

  1. ARMING  - when a Walker seal arrives, does a same-direction break on that bar
     count? Shipped suppresses it. The patched guard accepts it, but only when the
     pivot it broke was sealed on an EARLIER bar.

  2. WHAT COUNTS AS BROKEN - shipped measures the break against `e_hi_prev` /
     `e_lo_prev`, the running extreme. Owner reads the chart, where the level that
     matters is the sealed PIVOT, the white line. problems.md records the extreme
     rule as the approved semantics, so this was a deliberate choice - but it is
     also why a mark can sit where the owner sees nothing broken.

The arming patch only touches (1). It leaves (2) exactly as shipped, which is why
it could not make the two agree: the owner was checking a pivot and the engine was
still measuring an extreme, on both sides.

THE FOUR VARIANTS
-----------------
  V0  shipped            extreme break, extreme arming   (the chain that ships)
  V1  current patch      extreme break, pivot arming     (what the dropdown serves)
  V2  pivot break        pivot break,   extreme arming   (fix decision 2 only)
  V3  pivot + pivot      pivot break,   pivot arming     (both decisions)

V3 is the candidate that would make unpatched and patched the same engine. Whether
it is worth reaching for is the owner's call from the chart; this only prices it.

Every variant is generated the same way patched_swings does it - string substitution
on firstswing.py and btc_swing.py, never an edit to the source - so the shipping
engine is untouched throughout and every run is reproducible from the anchor count.

CAUSALITY
---------
Substitutions only ever read state that already exists at that point in process_bar.
Nothing here adds a future bar. This is a semantics experiment, not a lookahead test;
the look-ahead check remains the truncation test in the checklist.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_b1_definitions.py [limit]
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exp_phantom_marks as PM            # noqa: E402  (shared mark classifier)

OUT = ROOT / "backtest/tests/_b1_definitions.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"

_FS = ROOT / "backend" / "src" / "firstswing.py"
_SW = ROOT / "backend" / "src" / "btc" / "btc_swing.py"

# --- the two substitution sites -------------------------------------------------

# (1) arming guard. Shipped suppresses the same-direction break on the seal bar.
ARM_ANCHOR = '''            elif self._pending_leg_dir == "up" and down_break:
                self.armed = True
                self._pending_arm = False
                up_break = False
'''
ARM_PIVOT = ARM_ANCHOR + '''            elif self._pending_leg_dir == "up" and up_break:
                if self.e_hi_pivot.idx < g_idx:
                    self.armed = True
                    self._pending_arm = False
            elif self._pending_leg_dir == "down" and down_break:
                if self.e_lo_pivot.idx < g_idx:
                    self.armed = True
                    self._pending_arm = False
'''

# (2) what counts as broken. Shipped measures against the running extreme.
BRK_ANCHOR = '''        up_break = c.high > self.e_hi_prev.px
        down_break = c.low < self.e_lo_prev.px
'''
BRK_PIVOT = '''        up_break = c.high > (self.e_hi_pivot.px if self.e_hi_pivot is not None
                             else self.e_hi_prev.px)
        down_break = c.low < (self.e_lo_pivot.px if self.e_lo_pivot is not None
                              else self.e_lo_prev.px)
'''

VARIANTS = {
    "V0_shipped":        [],
    "V1_patch":          [(ARM_ANCHOR, ARM_PIVOT)],
    "V2_pivotbreak":     [(BRK_ANCHOR, BRK_PIVOT)],
    "V3_pivot_pivot":    [(BRK_ANCHOR, BRK_PIVOT), (ARM_ANCHOR, ARM_PIVOT)],
}


def build(name: str, subs) -> tuple:
    """Materialise one variant as two real modules, return compute_btc_swings."""
    fs_src = _FS.read_text(encoding="utf-8")
    for old, new in subs:
        n = fs_src.count(old)
        if n != 1:
            raise RuntimeError("%s: anchor matched %d times" % (name, n))
        fs_src = fs_src.replace(old, new)

    fs_name = "src.firstswing__" + name
    sw_name = "src.btc.btc_swing__" + name

    def mk(mod_name, src, path):
        m = types.ModuleType(mod_name)
        m.__file__ = str(path)
        m.__package__ = mod_name.rsplit(".", 1)[0]
        m.__dict__["__name__"] = mod_name
        sys.modules[mod_name] = m
        exec(compile(src, str(path), "exec"), m.__dict__)
        return m

    fsmod = mk(fs_name, fs_src, _FS)
    sw_src = _SW.read_text(encoding="utf-8")
    sw_src = sw_src.replace("from src.firstswing import",
                            "from src.firstswing__%s import" % name)
    swmod = mk(sw_name, sw_src, _SW)
    return swmod.compute_btc_swings, fsmod.SwingEngine


def run(name: str, subs, flow) -> list:
    fn, engine_cls = build(name, subs)
    PM._RECORDS = []
    PM._install(engine_cls)
    fn(list(flow), opts={"minBars": MIN_BARS}, max_swings=len(flow) // 2)
    return list(PM._RECORDS)


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    t0 = time.time()
    from src.btc.btc_routes import _load_window
    _, flow = _load_window(TF, limit, SYMBOL)[0]
    print("loaded %d %s candles\n" % (len(flow), TF), flush=True)

    res = {}
    for name, subs in VARIANTS.items():
        print("running %s ..." % name, flush=True)
        res[name] = run(name, subs, flow)

    from collections import Counter
    print("\n=== %s min_bars=%d limit=%d ===" % (TF, MIN_BARS, limit))
    print("  %-16s %8s %8s %8s   %s" % ("variant", "marks", "B1", "flagged", "of which B1"))
    for name, recs in res.items():
        tot = Counter(r["kind"] for r in recs)
        flg = Counter(r["kind"] for r in recs if not r["genuine"])
        b1 = tot["B1"] + flg["B1"]
        print("  %-16s %8d %8d %8d" % (name, len(recs), b1, len(recs) - len(
            [r for r in recs if r["genuine"]])))

    base = {(r["time"], r["kind"], r["dir"]) for r in res["V0_shipped"]}
    print("\n=== difference vs V0_shipped (marks) ===")
    for name, recs in res.items():
        s = {(r["time"], r["kind"], r["dir"]) for r in recs}
        gen = len([r for r in recs if r["genuine"]])
        print("  %-16s added %-6d removed %-6d genuine %d/%d"
              % (name, len(s - base), len(base - s), gen, len(recs)))

    OWNER = ("2023-02-05 07:00", "2023-02-13 04:30", "2023-03-11 08:00",
             "2023-01-14 06:45", "2026-08-14 22:45")
    print("\n=== the candles the owner checked by eye ===")
    for key in OWNER:
        print("  %s" % key)
        for name, recs in res.items():
            hit = [r for r in recs if r["time"].startswith(key)]
            got = ", ".join("%s %s%s" % (r["kind"], r["dir"],
                                        "" if r["genuine"] else "!")
                            for r in hit) or "none"
            print("     %-16s %s" % (name, got))

    OUT.write_text(json.dumps({k: v for k, v in res.items()},
                              indent=1, default=str) + "\n", encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

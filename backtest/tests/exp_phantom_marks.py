"""Count every swing mark that does NOT break a sealed pivot, on both chains.

THE QUESTION THIS ANSWERS
-------------------------
The owner reads the chart and sees marks that "are not breaking anything". Three of
his own, by eye:

    2023-02-05 07:00  B1 up    "the 7:00 candle has not broken the low of this 6:30 candle"
    2023-02-13 04:30  B1 up    "in this case B1 is correctly marked on patched"
    2023-03-11 08:00  B1 down  "B1 here is not breaking anything, any pivot at all"

Three candles is not a measurement. This counts all of them, on the shipped chain and
the patched chain, so the patch can be judged on a number instead of on a sample.

WHY THE OWNER SEES "NOTHING BROKEN" AND THE ENGINE DISAGREES
-------------------------------------------------------------
It is not the patch. It is that B1 has two possible meanings in this codebase and
they are not the same thing:

  - EXTREME semantics (what the engine does): B1 fires when the bar exceeds
    `e_hi_prev` / `e_lo_prev` - the running extreme of the session so far.
    problems.md records this as the APPROVED semantics: "B1 keeps the approved
    extreme-break semantics".

  - PIVOT semantics (what a chart reader sees): B1 fires when the bar breaks a
    SEALED PIVOT - the white line the walker printed.

Where the running extreme and the sealed pivot are the same level, the two agree and
nobody notices. Where they differ - a young engine, or a bar that sealed a fresh
pivot of its own - the engine marks a break and the owner sees nothing broken.

So the validator reports BOTH readings per mark. That is the whole disagreement,
counted. It does not assume which one is right - that is the owner's call from the
chart, and the numbers here are only there to make that call quick.

HOW IT CLASSIFIES
-----------------
State is read INSIDE the engine at the instant the mark is emitted, so everything is
causal by construction - no future bar is reachable. A mark is flagged when any of:

  same-bar      the pivot it sits on was sealed on this very bar (piv.idx == g_idx)
  extreme-only  the bar cleared the running extreme but NOT the sealed pivot
  immature      bars_seen < min_bars - too young to have real structure at all
                (owner's 2023-03-11 case: "swing calculation starts from 7:15, there
                is no wide pivot line here at all")

A mark flagged by none of these broke a pivot sealed on an earlier bar: GENUINE.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_phantom_marks.py [limit]
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

OUT = ROOT / "backtest/tests/_phantom_marks.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"


def _probe_hook(state, kind, dir_):
    """Called inside the engine at mark time. Appends one classified record."""
    up = dir_ == "up"
    # The pivot that was ACTUALLY standing when this bar was processed, i.e.
    # before this bar's own seal refreshed e_hi_pivot/e_lo_pivot further up in
    # process_bar. Reading e_hi_pivot here reports the pivot this bar just
    # sealed, so every mark looks like piv_idx == g_idx and every one of them
    # looks like a phantom. That is what made 2023-02-04 15:45 - which the owner
    # confirmed correct, the 12:30 pivot broken on a later bar - come out wrong.
    piv = state.e_hi_pivot_prev if up else state.e_lo_pivot_prev
    bar_hi, bar_lo = state.hi, state.lo
    piv_px = piv.px if piv is not None else None
    piv_idx = piv.idx if piv is not None else -1
    crossed_pivot = ((bar_hi > piv_px) if up else (bar_lo < piv_px)) if piv_px is not None else False
    reasons = []
    if piv_idx < 0:
        reasons.append("no-pivot")
    elif piv_idx == state.g_idx:
        reasons.append("same-bar")
    if not crossed_pivot:
        reasons.append("extreme-only")
    # The LEVEL that was actually broken, and where that level was set. The
    # owner reads the chart, so he needs both: a level can be legitimate either
    # because it is a sealed pivot, or because it is the extreme of the FIRST
    # candle of the leg, where the white flow line has not started yet and no
    # pivot can exist ("the pivot is at 8:30 but the extreme is 7:15's high").
    lvl_idx = state.e_hi_prev.idx if up else state.e_lo_prev.idx
    _RECORDS.append({
        "kind": kind, "dir": dir_, "idx": state.g_idx, "time": state.t,
        "piv_px": piv_px, "piv_idx": piv_idx, "bars_seen": state.bars_seen,
        "bar_hi": bar_hi, "bar_lo": bar_lo,
        "lvl_idx": lvl_idx, "seed_idx": state.seed_idx,
        "genuine": not reasons, "reasons": reasons,
    })


_RECORDS: list = []


def _install(engine_cls):
    """Wrap the three marking methods so each mark is classified as it happens.

    Idempotent: both sides now run the same class, and wrapping twice would make
    the second run record every mark a second time.
    """
    if getattr(engine_cls, "_phantom_probe_installed", False):
        return
    setattr(engine_cls, "_phantom_probe_installed", True)
    for meth, kind in (("_lock", "B1"), ("_confirm_direction", "B2"), ("_flip", "FLIP")):
        orig = getattr(engine_cls, meth)

        def make(orig=orig, kind=kind):
            def wrapper(self, *a, **kw):
                # _lock(dir), _flip(dir, as_b2=False), _confirm_direction()
                # _confirm_direction takes no direction and uses self.dir.
                d = a[0] if a else self.dir
                # _flip(dir, as_b2=True) emits a B2 mark, not a FLIP mark
                # (firstswing.py _step: "this break IS that legs B2, not a new
                # flip"). Labelling it FLIP put ~1000 marks on the wrong side of
                # the diff against the served chain.
                k = kind
                if kind == "FLIP" and kw.get("as_b2"):
                    k = "B2"
                _probe_hook(self, k, d)
                return orig(self, *a, **kw)
            return wrapper
        setattr(engine_cls, meth, make())


def run(patched: bool) -> list:
    """Walk one chain, recording every mark as the engine emits it.

    `patched=True` used to load the generated firstswing_b1patch module. That
    module is gone: the guard now lives in firstswing.py itself, so patched_swings
    hands back the shipped chain and there is nothing separate to load. The side
    is kept as a parameter so the two columns in the output stay comparable and
    so the equality can be re-checked later rather than assumed.
    """
    global _RECORDS
    from src.btc.btc_swing import compute_btc_swings
    from src.firstswing import SwingEngine
    _RECORDS = []
    _install(SwingEngine)
    from src.btc.btc_routes import _load_window
    _, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    flow = list(flow)
    if patched:
        from src.btc.patched_swings import compute_ships
        fn = lambda: compute_ships(flow, "continuous", MIN_BARS)
    else:
        fn = lambda: compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                                       max_swings=len(flow) // 2)
    fn()
    return list(_RECORDS)


LIMIT = 200000


def summarise(name, recs) -> dict:
    from collections import Counter
    by_kind = Counter()
    flagged = Counter()
    for r in recs:
        by_kind[r["kind"]] += 1
        if not r["genuine"]:
            flagged[r["kind"]] += 1
    return {"name": name, "total": by_kind, "flagged": flagged, "n": len(recs)}


def main() -> int:
    t0 = time.time()
    ship = run(False)
    patch = run(True)
    print("\n=== phantom counts  (fsent_champ_long, %s min_bars=%d, limit=%d) ==="
          % (TF, MIN_BARS, LIMIT))
    print("  %-6s %8s %8s" % ("kind", "shipped", "patched"))
    from collections import Counter
    st = Counter(r["kind"] for r in ship)
    pt = Counter(r["kind"] for r in patch)
    sf = Counter(r["kind"] for r in ship if not r["genuine"])
    pf = Counter(r["kind"] for r in patch if not r["genuine"])
    for k in ("B1", "B2", "FLIP"):
        print("  %-6s %4d/%-4d %4d/%-4d   flagged" % (k, sf[k], st[k], pf[k], pt[k]))
    print("\n  read as flagged/total")
    print("\n=== flagged marks by reason (patched) ===")
    rc = Counter(tuple(r["reasons"]) for r in patch if not r["genuine"])
    for k, n in rc.most_common():
        print("  %-40s %d" % (",".join(k), n))
    print("\n=== worst 12 flagged B1s (patched) - chart spot-check ===")
    b1 = [r for r in patch if r["kind"] == "B1" and not r["genuine"]]
    b1.sort(key=lambda r: r["idx"])
    for r in b1[:12]:
        print("  %s  B1 %-4s piv_idx=%-7d g_idx=%-7d %s"
              % (r["time"], r["dir"], r["piv_idx"], r["idx"],
                 ",".join(r["reasons"])))

    # The three candles the owner found by eye. Same minute may appear in both
    # chains, so print whatever is there rather than assuming one side.
    OWNER = ("2023-02-05 07:00", "2023-02-13 04:30", "2023-03-11 08:00",
             "2023-01-14 06:45", "2026-08-14 22:45")
    print("\n=== the candles the owner checked by eye ===")
    for key in OWNER:
        print("  %s" % key)
        for nm, recs in (("shipped", ship), ("patched", patch)):
            hit = [r for r in recs if r["time"].startswith(key)]
            if not hit:
                print("     %-8s  (no mark)" % nm)
            for r in hit:
                print("     %-8s B1 %-4s piv_idx=%-6d g_idx=%-6d piv_px=%-9s "
                      "bar_hi=%-9s bar_lo=%-9s %s"
                      % (nm, r["dir"], r["piv_idx"], r["idx"], r["piv_px"],
                         r["bar_hi"], r["bar_lo"],
                         "GENUINE" if r["genuine"] else "PHANTOM:" + ",".join(r["reasons"])))
    OUT.write_text(json.dumps({"tf": TF, "min_bars": MIN_BARS, "limit": LIMIT,
                               "shipped": ship, "patched": patch},
                              indent=1, default=str) + "\n", encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""HTF BIAS CONTAINMENT - no LTF entry may exist outside a causally-known HTF window.

This is the machine-checkable form of the whole thesis. The strategy is a 1h
bias that opens a window, and a 15m execution that may only trade inside that
window and only in the window's direction. If any trade can be found outside it,
the engine is reading something it could not have known at that bar - which is
the C12/C14/C15 lookahead class, and the same class as B2 being acted on before
its candle closes.

The engine enforces this itself at unified.py:642-647:

    idx  = bisect_right(starts, bar_ts) - 1
    if not (s + 2700 < bar_ts <= e + 2700): continue

That gate is NOT what this check calls. It re-derives the covering window from
the intervals the engine returns, which are the HTF windows themselves, and
verifies every booked trade against them from the outside. A bug in the gate
therefore cannot hide a violation from this check - the intervals do not depend
on the gate.

Causality, stated once. `s` is the opening timestamp of the 1h window. That 1h
candle closes at s+3600. The 15m bar at bar_ts closes at bar_ts+900. Requiring

    bar_ts + 900 > s + 3600      <=>      bar_ts > s + 2700

is exactly "the execution bar closes after the bias candle closes". Anything
weaker lets the trade act on an unfinished 1h candle.

Run:  cd backtest/checks && python exp_htf_bias_containment.py
"""
import bisect
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(ROOT / "backend"))

HTF_CANDLE = 3600
LTF_CANDLE = 900
# A 15m execution bar must close strictly after the 1h bias candle closes.
MIN_LEAD = HTF_CANDLE - LTF_CANDLE          # 2700s


def _windows(intervals):
    """-> sorted [(start, end, dir)] from the engine's interval tuples."""
    out = []
    for iv in intervals:
        out.append((int(iv[0]), int(iv[1]), int(iv[2])))
    out.sort()
    return out


def audit(trades, intervals):
    """-> (violations, stats). A violation is a trade no window can justify."""
    wins = _windows(intervals)
    starts = [w[0] for w in wins]
    violations = []
    checked = 0
    for t in trades:
        ets = int(t["entry_ts"])
        tdir = 1 if t.get("dir") == "long" else -1
        # Walk every window that could cover this bar. Usually one; the loop is
        # deliberate so an overlapping-window bug shows up instead of hiding
        # behind a bisect that picks only the latest start.
        idx = bisect.bisect_right(starts, ets)
        covering = []
        lo = max(0, idx - 3)
        hi = min(len(wins), idx + 1)
        # Causality is part of the predicate, not a separate assertion. A trade
        # at s+1800 sits inside the window's clock range but the governing 1h
        # candle has not closed yet, so the bias was not knowable. Testing only
        # s <= ets would wave that through - the exact C14 shape of bug, and it
        # was in this check's first draft.
        for j in range(lo, hi):
            s, e, d = wins[j]
            if s + MIN_LEAD < ets <= e + MIN_LEAD and d == tdir:
                covering.append((s, e, d))
        checked += 1
        if not covering:
            # Distinguish "outside every window" from "inside but wrong way".
            j = bisect.bisect_right(starts, ets) - 1
            if j >= 0:
                s, e, d = wins[j]
                if s + MIN_LEAD < ets <= e + MIN_LEAD:
                    kind = "WRONG_DIRECTION (window active, trade against it)"
                elif ets < s + MIN_LEAD:
                    kind = "TOO_EARLY (before the 1h bias candle closes)"
                else:
                    kind = "OUTSIDE_WINDOW"
            else:
                kind = "BEFORE_FIRST_WINDOW"
            violations.append({"entry_ts": ets, "dir": t.get("dir"),
                               "kind": kind, "r": t.get("r_multiple")})
    stats = {"windows": len(wins), "trades": checked,
             "violations": len(violations)}
    return violations, stats


def _load():
    import run_experiment as re_
    data = re_.get_data()
    sim = re_.build_module()
    cfg = re_.EXPERIMENTS["champion_multi_sw10_leg"]
    params = {**dict(re_.BP), **cfg["params"]}
    sw = re_.get_swings(data, cfg["swing"])
    res = sim(data["c1h"], sw, data["c15"], data["sw15"],
              fine_ltf=data["fine"], **params)
    return res["ltf_trades"], res["intervals"]


def main():
    trades, intervals = _load()
    violations, stats = audit(trades, intervals)

    print("=" * 64)
    print("HTF BIAS CONTAINMENT")
    print("=" * 64)
    print("HTF windows          : %d" % stats["windows"])
    print("LTF trades booked    : %d" % stats["trades"])
    print("violations           : %d" % stats["violations"])
    print("rule: every trade needs a window w with")
    print("      w.start + %d < entry_ts <= w.end + %d  and  w.dir == trade.dir"
          % (MIN_LEAD, MIN_LEAD))
    print()

    if violations:
        by_kind = {}
        for v in violations:
            by_kind[v["kind"]] = by_kind.get(v["kind"], 0) + 1
        print("breakdown:")
        for k, c in sorted(by_kind.items(), key=lambda x: -x[1]):
            print("   %-52s %d" % (k, c))
        print()
        print("first 10 violations:")
        for v in violations[:10]:
            print("   entry_ts=%d  dir=%-4s  R=%-7s  %s"
                  % (v["entry_ts"], v["dir"], v["r"], v["kind"]))
        print()
        print("RESULT: FAIL - %d trade(s) outside a causally-known HTF bias"
              % len(violations))
        return 1

    print("RESULT: PASS - every trade sat inside a causally-known HTF window,")
    print("        in that window's direction, closing after the 1h candle closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
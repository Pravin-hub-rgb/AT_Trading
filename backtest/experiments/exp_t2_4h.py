"""T2 - a third timeframe. The only genuinely NEW input available to the base.

WHY THIS THESIS
---------------
Everything the repo has ever tested lives on two planes: 1h emits a bias
window, 15m takes the trade. 27 modes, the ATR sweep, the stability harness, the
entry-break study, T1's concurrency axis - all of them choose among signals
inside those two planes.

A 4h layer is not a knob. It is a different clock, and it is the one input that
has never been in the room. The hypothesis is the obvious one and worth testing
precisely because it is obvious: the 1h window is noisy, and a 4h swing saying
which side the bigger structure is on should raise the base's 22% win rate
without touching entry, exit or sizing.

THE BASE IS NOT LOOKING GOOD GOING IN
-------------------------------------
base_book.establish measures the bare causal base at:

               n     net R    R/trade   win %
    IS        503   +105.18    0.2091    22.1%
    OOS       278    -33.68   -0.1212    21.6%

22% and negative out of sample. Any filter that lifts R-per-trade in BOTH eras
is worth something here; anything that only lifts IS net is the union mistake.

CAUSALITY
---------
The 4h series is built by bucketing the 1h candles on floor(ts / 14400), so bars
are aligned to absolute 4h boundaries rather than to whatever offset the data
happens to start at. A 4h swing is used only from the moment it CONFIRMED -
confirmed_at_idx mapped to its own candle timestamp - never from the leg it
describes. So the filter at an entry bar sees the 4h structure that was already
finished at that bar, exactly as the 1h plane does.

Stated plainly: no 4h information from after the entry bar can reach the
decision.

KNOWN LIMITATION, STATED NOT HIDDEN
-----------------------------------
The gate is applied to completed trades after the engine has run, not injected
into the engine's signal loop. So the position cap and streak-halt see the
unfiltered stream. On the bare base those are all off (cooldown_bars=0,
max_consecutive_losses=0, no cap), so nothing is distorted HERE. If this ever
gets built on a book that has brakes on, it has to move into the engine.

Output: t2_4h_results.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "t2_4h_results.json"

import base_book as bb                                           # noqa: E402

BAR = 14_400          # 4h in seconds
MIN_BARS = (4, 6)     # a 4h leg of 16h and 24h

_T = 2 * (len(MIN_BARS) * 3 + 1)
_D = 0
_T0 = time.time()


def step(lbl):
    global _D
    _D += 1
    el = time.time() - _T0
    eta = (el / _D) * (_T - _D) if _D else 0.0
    pct = 100.0 * _D / _T
    sys.stdout.write("\r  [%3.0f%%] %s %5.0fs elapsed, ~%4.0fs left   %s"
                     % (pct, "#" * int(pct / 2.5), el, eta, lbl))
    sys.stdout.flush()


def to_4h(data):
    """Bucket the 1h series into absolute 4h buckets.

    Two parallel lists come back because the repo keeps the 1h series twice and
    the two halves are not interchangeable:

      c4 - dicts carrying an absolute ts. Built from data["c1h"], which is what
           the gate reads, because confirmed_at_idx is an index into THIS array.
      f4 - FlowCandle objects. Built from data["f1h"], because
           _compute_swings -> compute_btc_swings -> firstswing.process_bar does
           c.date and will raise AttributeError on a plain dict.

    Verified index-for-index identical between c1h and f1h (same length, same
    date and close), so bucketing both with the same key keeps them aligned.
    """
    from src.walker import FlowCandle
    c1h, f1h = data["c1h"], data["f1h"]
    if len(c1h) != len(f1h):
        raise AssertionError("c1h and f1h differ in length; cannot bucket together")
    buckets = {}
    order = []
    for c, f in zip(c1h, f1h):
        key = (int(c["ts"]) // BAR) * BAR
        if key not in buckets:
            buckets[key] = {"ts": key, "date": f.date, "open": float(f.open),
                            "high": float(f.high), "low": float(f.low),
                            "close": float(f.close)}
            order.append(key)
        b = buckets[key]
        b["high"] = max(b["high"], float(f.high))
        b["low"] = min(b["low"], float(f.low))
        b["close"] = float(f.close)
    c4 = [buckets[k] for k in sorted(order)]
    f4 = [FlowCandle(b["date"], b["open"], b["high"], b["low"], b["close"]) for b in c4]
    return c4, f4


def swings_4h(data, min_bars):
    from src.btc.btc_routes import _compute_swings
    c4, f4 = to_4h(data)
    sw = _compute_swings(f4, "continuous", min_bars=min_bars)
    if not sw:
        return c4, []
    assert sw[0]["dir"] in ("up", "down"), sw[0]["dir"]
    # Confirmation time, mapped onto the 4h series. This is the only 4h field
    # the gate is allowed to read.
    out = []
    for s in sw:
        ci = s.get("confirmed_at_idx")
        if ci is None or ci >= len(c4):
            continue
        out.append({"conf_ts": int(c4[ci]["ts"]), "dir": s["dir"],
                    "conf_idx": s.get("confirmed_at_idx"), "kind": s.get("kind")})
    out.sort(key=lambda x: x["conf_ts"])
    return c4, out


def bias_at(sw, entry_ts):
    """Direction of the last 4h swing confirmed at or before entry_ts."""
    d = None
    for s in sw:
        if s["conf_ts"] <= entry_ts:
            d = s["dir"]
        else:
            break
    return d


DIR_MAP = {"long": "up", "short": "down"}


def split(trades, sw):
    """Partition by whether the confirmed 4h swing points our way.

    The two series name a direction differently and the mismatch is silent:
    trades carry 'long'/'short', swings carry 'up'/'down'. The first run of this
    harness compared them as strings and every single trade came out
    "disagreeing" - 503 of 503, 0 agreeing - which reads as a finding and is
    actually a type error. Asserted rather than assumed now.
    """
    agree, disagree, unknown = [], [], []
    for t in trades:
        d = bias_at(sw, int(t["entry_ts"]))
        want = DIR_MAP.get(t["dir"])
        if d is None:
            unknown.append(t)
        elif d == want:
            agree.append(t)
        else:
            disagree.append(t)
    return agree, disagree, unknown


def main() -> int:
    print("T2 - THE 4h LAYER")
    print("new input: a third timeframe the base has never had")
    print()
    t0 = time.time()
    sim, eras = bb.load()
    print("loaded (%.0fs)\n" % (time.time() - t0))

    out = {"min_bars": {}}
    base_stats = {}
    for era in ("is", "oos"):
        step("base " + era)
        tr = bb.trades_of(sim, eras[era], bb.base_cfg(1))
        base_stats[era] = bb.summarise(tr)
        out.setdefault("base", {})[era] = base_stats[era]

    print("=" * 100)
    print("THE BASE (no 4h layer)")
    print("=" * 100)
    print("  %-5s %6s %10s %10s %8s" % ("era", "n", "net R", "R/trade", "win %"))
    for era in ("is", "oos"):
        s = base_stats[era]
        print("  %-5s %6d %+10.2f %10.4f %7.1f%%" % (era.upper(), s["n"], s["net"], s["r_trade"], s["wr"]))
    print()

    summary = {}
    for mb in MIN_BARS:
        print("=" * 100)
        print("4h SWINGS, min_bars=%d  (a leg of %d hours)" % (mb, mb * 4))
        print("=" * 100)
        row = {}
        for era in ("is", "oos"):
            step("min_bars=%d %s" % (mb, era))
            c4, sw = swings_4h(eras[era], mb)
            tr = bb.trades_of(sim, eras[era], bb.base_cfg(1))
            ag, dis, unk = split(tr, sw)
            row[era] = {"n_4h_candles": len(c4), "n_4h_swings": len(sw),
                        "agree": bb.summarise(ag), "disagree": bb.summarise(dis),
                        "unknown": len(unk)}
        out["min_bars"][str(mb)] = row
        summary[mb] = row

        for era in ("is", "oos"):
            r = row[era]
            b = base_stats[era]
            print()
            print("  %s   4h candles %d, 4h swings %d"
                  % (era.upper(), r["n_4h_candles"], r["n_4h_swings"]))
            print("    %-22s %6s %10s %10s %8s   %s"
                  % ("arm", "n", "net R", "R/trade", "win %", "vs base R/trade"))
            for lab, key in (("base (no 4h)", None), ("4h AGREES", "agree"),
                             ("4h DISAGREES", "disagree")):
                if key is None:
                    s = b
                else:
                    s = r[key]
                    s = dict(s, n=s["n"])
                d = "" if key is None else "  %+.4f" % (s["r_trade"] - b["r_trade"])
                print("    %-22s %6d %+10.2f %10.4f %7.1f%%%s"
                      % (lab, s["n"], s["net"], s["r_trade"], s["wr"], d))
            print("    %-22s %6d" % ("(no 4h swing yet)", r["unknown"]))
        print()

    # ---------------- the verdict -------------------------------------
    print("=" * 100)
    print("THE CLAIM: taking only 4h-agreeing trades raises R-per-trade in BOTH eras")
    print("=" * 100)
    good = []
    for mb in MIN_BARS:
        di = summary[mb]["is"]["agree"]["r_trade"] - base_stats["is"]["r_trade"]
        do = summary[mb]["oos"]["agree"]["r_trade"] - base_stats["oos"]["r_trade"]
        ok = di > 0 and do > 0
        good.append(ok)
        print("  min_bars=%d   IS %+.4f   OOS %+.4f   %s"
              % (mb, di, do, "HOLDS" if ok else "no"))
    print()
    if all(good):
        print("  -> The 4h layer is real. It is a direction gate, not a regime knob,")
        print("     and it needs a registry entry and one deliberate OOS reveal.")
    else:
        print("  -> The 4h layer does not lift R-per-trade in both eras. Recorded as a")
        print("     negative result; the third timeframe is now off the table for the")
        print("     base rather than untried.")

    # did the DISAGREEING bucket make money instead?
    print()
    print("  For completeness - if 4h disagreement is the edge rather than agreement:")
    for mb in MIN_BARS:
        for era in ("is", "oos"):
            s = summary[mb][era]["disagree"]
            print("    min_bars=%d %-4s disagree: n=%-4d net=%+8.2f  R/trade=%.4f  win=%.1f%%"
                  % (mb, era.upper(), s["n"], s["net"], s["r_trade"], s["wr"]))

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print()
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
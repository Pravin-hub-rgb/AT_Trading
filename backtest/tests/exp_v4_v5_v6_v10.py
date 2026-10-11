"""V4, V5, V6, V10 - read the engine, count what is there, claim nothing.

None of these needs the owner's FS rule. They are questions about what the code
does and what the chain contains, answered by reading and counting. Every number
below is printed with the evidence for it, and nothing is called wrong here - the
owner decides that.

  V4   fs_at vs confirmed_at disagree on 481 of 2952 swings, by 1..10 bars.
       Characterise them: which swings, how big, does the mark set shift with it.

  V5   swing.source is 'chop' on 2952 of 2952. The 'sustain' confirmation path has
       never run. Is it reachable at all, or is it dead?

  V6   Outside bars: both up_break and down_break true on the same bar. ARM20 says
       the V-reversal branch is reached first so the arming branches are
       unreachable there. Count them and see what the engine actually does.

  V10  bars_seen resets per swing so min_bars is never reached inside a leg. Prove
       it rather than assert it.
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
from src.firstswing import SwingEngine

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000
OUT = HERE / "_v45610.json"


def chain(flow):
    return compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                              max_swings=max(1, len(flow) // 2))


def v4(swings, out):
    print("=" * 76)
    print("V4   fs_at vs confirmed_at")
    print("=" * 76)
    gap = collections.Counter()
    rows = []
    for s in swings:
        fa, ca = s.get("fs_at_idx"), s.get("confirmed_at_idx")
        if fa is None or ca is None:
            continue
        d = ca - fa
        gap[d] += 1
        if d != 0:
            rows.append({"swing": s["swing_index"], "fs_at": s.get("fs_at_time"),
                         "confirmed_at": s.get("confirmed_at_time"), "gap": d,
                         "dir": s.get("dir"), "n_breaks": len(s["breaks"])})
    tot = sum(gap.values())
    print("  swings with both stamps : %d" % tot)
    print("  same bar                : %d  (%.1f%%)" % (gap[0], 100.0 * gap[0] / tot))
    print("  differ                  : %d  (%.1f%%)"
          % (tot - gap[0], 100.0 * (tot - gap[0]) / tot))
    print()
    print("  gap distribution (bars):", dict(sorted(gap.items())))
    big = sorted([r for r in rows if r["gap"] >= 5], key=lambda r: -r["gap"])
    print("  gap >= 5 bars           : %d" % len(big))
    for r in big[:8]:
        print("     swing %-5d fs_at %-6s confirmed %-6s gap %-3d dir=%-4s breaks=%d"
              % (r["swing"], r["fs_at"], r["confirmed_at"], r["gap"], r["dir"], r["n_breaks"]))
    print()
    print("  Does the gap predict anything?")
    bydir = collections.Counter(r["dir"] for r in rows)
    print("     differ, by direction :", dict(bydir))
    withb = collections.Counter(min(r["n_breaks"], 4) for r in rows)
    print("     differ, by #breaks   :", dict(sorted(withb.items())))
    allb = collections.Counter(min(len(s["breaks"]), 4) for s in swings)
    print("     all swings by #breaks:", dict(sorted(allb.items())))
    out["v4"] = {"total": tot, "same": gap[0], "differ": tot - gap[0],
                 "gap_hist": dict(gap), "rows": rows[:400]}


def v5(swings, out):
    print("=" * 76)
    print("V5   swing.source - is the 'sustain' path reachable?")
    print("=" * 76)
    src = collections.Counter(s.get("source") for s in swings)
    print("  source across %d swings : %s" % (len(swings), dict(src)))
    print("  kind   across %d swings : %s"
          % (len(swings), dict(collections.Counter(s.get("kind") for s in swings))))
    print()
    seen = collections.Counter()
    real = SwingEngine.process_bar
    import src.firstswing as fs
    text = pathlib_text(fs.__file__)
    for tok in ("sustain", "confirm_source", "SUS", "_check_sustain"):
        print("  %-16s appears %d time(s) in firstswing.py"
              % (tok, text.count(tok)))
    print()
    print("  Where confirm_source is assigned:")
    for i, l in enumerate(text.splitlines(), 1):
        if "confirm_source" in l and "=" in l and "==" not in l:
            print("     L%-5d %s" % (i, l.strip()[:88]))
    print()
    print("  Where the walker's seal branch picks sustain vs chop:")
    for i, l in enumerate(text.splitlines(), 1):
        s = l.strip()
        if s.startswith("if ") and "confirm" in s.lower():
            print("     L%-5d %s" % (i, s[:88]))
    out["v5"] = {"sources": dict(src)}


def v6(swings, flow, out):
    print("=" * 76)
    print("V6   outside bars - both breaks true on the same bar")
    print("=" * 76)
    outside = []
    eng_holder = {}
    real = SwingEngine.process_bar

    def spy(self, c, i):
        try:
            up = c.high > self.e_hi.px
            dn = c.low < self.e_lo.px
        except Exception:
            up = dn = False
        r = real(self, c, i)
        if up and dn:
            outside.append({"idx": i, "time": getattr(c, "date", None),
                            "up_px": c.high, "dn_px": c.low})
        return r

    SwingEngine.process_bar = spy
    try:
        chain(list(flow))
    finally:
        SwingEngine.process_bar = real
    print("  bars where up_break AND down_break both true : %d of %d candles"
          % (len(outside), len(flow)))
    if outside:
        by_time = {}
        for s in swings:
            for b in s["breaks"]:
                by_time[b["time"]] = b
        marked = [o for o in outside if o["time"] in by_time]
        print("  of those, %d carry a mark" % len(marked))
        print("  mark kinds on outside bars :",
              dict(collections.Counter(by_time[o["time"]]["kind"] for o in marked)))
        print()
        print("  sample outside bars:")
        for o in outside[:8]:
            m = by_time.get(o["time"])
            print("     %-20s h=%-10s l=%-10s  mark=%s"
                  % (o["time"], o["up_px"], o["dn_px"],
                     "%s %s @%s" % (m["kind"], m["dir"], m["px"]) if m else "none"))
    out["v6"] = {"outside_bars": len(outside), "candles": len(flow),
                 "marked": len([o for o in outside if o.get("time") in {}]) or None,
                 "sample": outside[:40]}


def v10(flow, out):
    print("=" * 76)
    print("V10  bars_seen / min_bars - does the warmup ever apply?")
    print("=" * 76)
    rows = []
    real = SwingEngine.__init__

    def init(self, *a, **kw):
        real(self, *a, **kw)
        self._init_bars = getattr(self, "bars_seen", None)
        rows.append({"minBars": getattr(self, "min_bars", None),
                     "bars_seen_at_init": self._init_bars})

    SwingEngine.__init__ = init
    try:
        chain(list(flow))
    finally:
        SwingEngine.__init__ = real
    seen = collections.Counter(str(r["bars_seen_at_init"]) for r in rows)
    mb = collections.Counter(str(r["minBars"]) for r in rows)
    print("  engines created          : %d" % len(rows))
    print("  bars_seen at construction: %s" % dict(seen.most_common(6)))
    print("  minBars configured       : %s" % dict(mb.most_common(6)))
    print()
    print("  If bars_seen restarts at 1 for every leg, min_bars=%d is never reached"
          % MIN_BARS)
    print("  inside a leg and the engine is never 'warming up' - it is only ever")
    print("  compared against min_bars at the point a leg starts.")
    print("  First engine constructed at bar %d or later?" % len(flow))
    out["v10"] = {"engines": len(rows), "bars_seen_hist": dict(seen.most_common(10)),
                  "minBars_hist": dict(mb.most_common(5))}


def pathlib_text(p):
    return Path(p).read_text(encoding="utf-8")


def main():
    _c, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    flow = list(flow)
    swings = chain(flow)
    print("chain: %d candles, %d swings, %d marks"
          % (len(flow), len(swings), sum(len(s["breaks"]) for s in swings)))
    print()
    out = {}
    v4(swings, out)
    v5(swings, out)
    v6(swings, flow, out)
    v10(flow, out)
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print()
    print("wrote %s" % OUT.name)


if __name__ == "__main__":
    main()

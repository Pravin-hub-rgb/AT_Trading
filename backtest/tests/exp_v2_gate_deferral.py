"""What exp_v2_b2_flip.py CANNOT see: bars that broke the extreme but did not
get a mark because a gate held them back.

WHY THE MAIN DETECTOR IS BLIND HERE
    It checks "no earlier bar crossed the same target". That is vacuous. When
    bar k sets a new running extreme, self.e_hi becomes bar k's high. So when
    the mark finally fires at a later bar m, target(m) >= high(k) already, and
    bar k cannot cross it. A late mark therefore looks exactly like a correct
    one. Check 3 always reads 0 - it proved nothing.

WHAT THIS SCRIPT COUNTS
    For every B2/FLIP mark, walk back over the leg and list the bars that set a
    NEW RUNNING EXTREME on that mark's side. Every one of those is a genuine
    break of the standing extreme - the same event that fires a mark when no
    gate intervenes. The mark fires on the last one; the ones before it were
    suppressed by defer_same_bar_arm / b2_gap_bars / arming / dir_confirmed.

    suppressed = break candidates before the mark's own bar.
    0 across the chain would mean the detector has no blind spot at all.

READ-ONLY. Engine untouched. Reports dated cases; changes nothing.
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (str(HERE), str(HERE.parent), str(ROOT / "backend")):
    sys.path.insert(0, p)

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
from src.firstswing import SwingEngine

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000
OUT = HERE / "_v2_gate_deferral.json"
NOW_BARS = 8          # window on each side of a suppressed bar to show
MAX_GAP = 40          # only report suppresses within this many bars


def main():
    candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    candles, flow = list(candles), list(flow)
    HIGH = [float(x["high"]) for x in candles]
    LOW = [float(x["low"]) for x in candles]
    TS = [x["date"][:16] for x in candles]

    o_init, o_pb = SwingEngine.__init__, SwingEngine.process_bar
    DECL = []

    def init(self, *a, **k):
        o_init(self, *a, **k)
        self._first = None

    def pb(self, *a, **k):
        before = getattr(self, "declared", False)
        r = o_pb(self, *a, **k)
        if getattr(self, "_first", None) is None:
            self._first = self.g_idx
        if self.declared and not before:
            DECL.append(self._first)
        return r

    SwingEngine.__init__, SwingEngine.process_bar = init, pb
    sw = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=len(candles) // 2)
    SwingEngine.__init__, SwingEngine.process_bar = o_init, o_pb

    print("=" * 94)
    print("V2  GATE DEFERRAL - the blind spot in exp_v2_b2_flip.py")
    print("=" * 94)
    print("  swings %d" % len(sw))

    rows = []
    for i, s in enumerate(sw):
        brk = sorted(s["breaks"], key=lambda b: b["idx"])
        if not brk:
            continue
        leg = DECL[i] if i < len(DECL) else 0
        prev = leg
        for b in brk:
            if b["kind"] not in ("B2", "FLIP"):
                prev = max(prev, b["idx"])
                continue
            up = (b["dir"] == "up")
            # running extreme spans the WHOLE leg up to each bar, not just from
            # the previous mark - seeding at HIGH[prev] under-counts and invents
            # candidates that never broke anything.
            hi_run, lo_run = {}, {}
            mh, ml = float("-inf"), float("inf")
            for k in range(leg, b["idx"] + 1):
                mh = max(mh, HIGH[k])
                ml = min(ml, LOW[k])
                hi_run[k], lo_run[k] = mh, ml
            # bars in (prev, mark] that set a NEW running extreme on this side
            cands = []
            for k in range(prev + 1, b["idx"] + 1):
                base = (hi_run[k - 1] if k > prev else
                        hi_run[prev] if prev >= leg else float("-inf"))
                if up and HIGH[k] > base:
                    cands.append(k)
                elif (not up):
                    base_l = (lo_run[k - 1] if k > prev else
                              lo_run[prev] if prev >= leg else float("inf"))
                    if LOW[k] < base_l:
                        cands.append(k)
            supp = cands[:-1] if cands else []
            rows.append({
                "swing": s["swing_index"], "kind": b["kind"], "dir": b["dir"],
                "mark_idx": b["idx"], "mark_time": TS[b["idx"]],
                "prev_idx": prev, "candidates": len(cands),
                "suppressed": len(supp),
                "suppressed_at": [TS[k] for k in supp[:MAX_GAP]],
                "suppressed_gap": (b["idx"] - supp[-1]) if supp else 0,
            })
            prev = b["idx"]

    tot = collections.Counter()
    for r in rows:
        tot[r["kind"] + "_marks"] += 1
        if r["suppressed"]:
            tot[r["kind"] + "_with_suppression"] += 1
        tot[r["kind"] + "_suppressed_bars"] += r["suppressed"]

    print()
    print("BREAK CANDIDATES THE MAIN DETECTOR DISCARDS")
    print("-" * 94)
    for k in ("B2", "FLIP"):
        print("  %-4s  marks %5d   with suppressed candidates %5d   bars suppressed %6d"
              % (k, tot[k + "_marks"], tot[k + "_with_suppression"],
                 tot[k + "_suppressed_bars"]))
    clean = [r for r in rows if r["suppressed"] == 0]
    print()
    print("  marks the main detector can actually vouch for (no suppression):")
    for k in ("B2", "FLIP"):
        n = sum(1 for r in clean if r["kind"] == k)
        print("    %-4s %5d of %5d" % (k, n, tot[k + "_marks"]))
    print()
    print("  The suppressed bars are the gate doing its job OR misfiring. Nothing")
    print("  in exp_v2_b2_flip.py can tell those two apart. They are the list to review.")

    # worst offenders, nearest suppressions first
    worst = sorted([r for r in rows if r["suppressed"]],
                   key=lambda r: (r["suppressed_gap"], -r["suppressed"]))
    print()
    print("NEAREST SUPPRESSIONS - a mark landing one bar after an unbroken break")
    print("-" * 94)
    for r in worst[:6]:
        print()
        print("  swing %d  %s %s @ %s   %d candidate(s), last %d bar(s) before the mark"
              % (r["swing"], r["kind"], r["dir"], r["mark_time"],
                 r["candidates"], r["suppressed_gap"]))
        for t in r["suppressed_at"]:
            print("      suppressed break at %s" % t)
        print("      mark                at %s" % r["mark_time"])
        lo = max(0, r["mark_idx"] - NOW_BARS)
        for k in range(lo, min(len(candles), r["mark_idx"] + 3)):
            tag = ""
            if TS[k] in r["suppressed_at"]:
                tag = "   <- broke the extreme, NO MARK"
            if k == r["mark_idx"]:
                tag = "   <- MARK"
            print("        %s  H%10.1f  L%10.1f%s" % (TS[k], HIGH[k], LOW[k], tag))

    OUT.write_text(json.dumps({
        "swings": len(sw), "totals": dict(tot),
        "rows": rows,
    }, indent=1, default=str), encoding="utf-8")
    print()
    print("wrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
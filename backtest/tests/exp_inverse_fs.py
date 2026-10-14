"""
C1 - THE INVERSE CONDITION: the swings that produce NOTHING.

The earlier coverage decomposition answered one direction. Every swing that gets
an FS also gets a B2 or a FLIP - IS 2840/2840, OOS 1571/1571, zero FS-without-a-
mark. That rules out one gap: FS is never dangling.

It says nothing about the other direction. A swing can complete its leg, confirm,
never fire an FS, and simply end with no mark at all. Those are the ones that
produce no trade, no stop, no target - the engine has decided the swing did not
resolve. Are those decisions right?

THE QUESTION

If a no-mark swing was correctly abandoned, the price should have gone against the
leg soon after it died. If the leg carried on favourably, we are discarding
resolvable swings and every book is leaving marks - and therefore trades - on the
table.

So this measures forward behaviour after the swing ends, and compares the no-mark
population against the marked one. If the no-mark population went on to move in
the leg direction significantly more often than the marked population did, the
filter is too strict and that is a real cost.

WHAT IS DELIBERATELY NOT DONE

No proposal. No threshold, no gate, no engine change. This characterises a
population so the owner can decide whether it deserves a follow-up. A result
that looks interesting here earns its own experiment with IS-then-OOS discipline,
not an edit based on one read of this table.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\backend\\venv\\Scripts\\python.exe -u exp_inverse_fs.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent

# how far past the swing's end to look, in 15m bars
FWD = [8, 24, 48]


def main() -> int:
    from run_experiment import get_data
    from engine.v18_params import SWING
    from src.btc.btc_swing import compute_btc_swings

    d = get_data()
    c15 = d["c15"]
    sw = compute_btc_swings(
        d["f15"], opts={"minBars": SWING["min_bars_15m"], "b2GapBars": 1},
        max_swings=len(d["f15"]))
    close = [float(c["close"]) for c in c15]
    n = len(close)

    # identity gate - this must be the chain everything else was measured on
    rows = []
    for s in sw:
        for b in s["breaks"]:
            rows.append("%s|%s|%s|%d|%d" % (b["time"][:16], b["kind"], b["dir"],
                                            round(float(b["px"]), 1), s["swing_index"]))
        if s.get("fs_at_idx") is not None:
            rows.append("FS|%s|%s" % (s["fs_at_time"][:16], s["dir"]))
    rows.sort()
    fp = hashlib.sha256(chr(10).join(rows).encode()).hexdigest()[:16]
    print("=" * 92)
    print("C1 - THE INVERSE CONDITION: swings that produce no mark at all")
    print("=" * 92)
    print("  chain fingerprint %s  swings=%d marks=%d" % (fp, len(sw), len(rows) - sum(
        1 for s in sw if s.get("fs_at_idx") is not None)))
    if fp != "83a3af3f6ebf0ffa":
        print("  ABORT: chain %s != A1 freeze. Nothing below is comparable." % fp)
        return 2
    print("  == A1 freeze. Chain matches every other result in this sweep.")
    print()

    # ---- classify -----------------------------------------------------------
    def kind_of(s):
        # B1 is present on essentially every swing and says nothing here. The
        # question is whether the RUNNING EXTREME was ever broken (a B2) and
        # whether the leg resolved into a FLIP instead.
        ks = {b["kind"] for b in s["breaks"] if b["kind"] in ("B2", "FLIP")}
        has_fs = s.get("fs_at_idx") is not None
        if not has_fs and not ks:
            return "none"
        if ks == {"B2"}:
            return "b2_only"
        if ks == {"FLIP"}:
            return "flip_only"
        if not ks:
            return "fs_only"
        return "both"

    BUCKETS = ("both", "b2_only", "flip_only", "fs_only", "none")
    buckets = {}
    for s in sw:
        buckets.setdefault(kind_of(s), []).append(s)
    print("  SWING CENSUS")
    print("    %-12s %6s %8s" % ("bucket", "n", "share"))
    for k in BUCKETS:
        v = buckets.get(k, [])
        print("    %-12s %6d %7.1f%%" % (k, len(v), 100.0 * len(v) / len(sw)))
    print()
    print("    The C1 population is everything WITHOUT a B2 - the extreme that was")
    print("    never broken. b2_only/both had their extreme broken; flip_only,")
    print("    fs_only and none did not.")
    print()

    # ---- forward behaviour --------------------------------------------------
    def fwd_move(s, k):
        """Signed move in the LEG direction, k bars past the swing's final event.

        The swing is over once its last event has printed - the final break, the
        confirmation, or the leg start, whichever is latest. Measuring from there
        avoids scoring a swing against a break it already printed."""
        end = s["leg_start_idx"]
        for b in s["breaks"]:
            end = max(end, b["idx"])
        if s.get("confirmed_at_idx") is not None:
            end = max(end, s["confirmed_at_idx"])
        j = min(end + k, n - 1)
        if j <= end:
            return None
        m = close[j] - close[end]
        return m if s["dir"] == "up" else -m

    print("  FORWARD MOVE in the leg direction, bars past the swing's end.")
    print("  Positive = the leg carried on. This is what a missed mark would have")
    print("  been worth. Negative = the swing was correctly abandoned.")
    print()
    hdr = "    %-12s %6s %s" % ("bucket", "n", "".join("%18s" % ("+%d bars" % k) for k in FWD))
    print(hdr)
    print("    " + "-" * (len(hdr) - 4))
    stats = {}
    for k in BUCKETS:
        v = buckets.get(k, [])
        if not v:
            continue
        cells = []
        for kk in FWD:
            mv = sorted(fwd_move(s, kk) for s in v)
            mv = [x for x in mv if x is not None]
            if not mv:
                cells.append((0, 0.0, 0.0, 0.0, 0.0))
                continue
            up = sum(1 for x in mv if x > 0)
            mean = sum(mv) / len(mv)
            med = mv[len(mv) // 2]
            p25 = mv[len(mv) // 4]
            p75 = mv[(3 * len(mv)) // 4]
            cells.append((len(mv), mean, 100.0 * up / len(mv), med, p75 - p25))
        stats[k] = cells
        print("    %-12s %6d %s" % (k, len(v), "".join(
            "%8.1f/%8.1f" % (c[1], c[3]) for c in cells)))
    print("    (MEAN / MEDIAN move $ at +8 / +24 / +48 bars)")
    print()
    print("    Mean and median are printed together on purpose. Where they")
    print("    diverge sharply the distribution has a fat tail and the MEAN is an")
    print("    artefact of a handful of large moves, not a typical outcome.")
    print()

    # ---- the decisive comparison -------------------------------------------
    print("  THE COMPARISON THAT MATTERS - extreme BROKEN (has B2) vs NEVER BROKEN")
    broken = buckets.get("both", []) + buckets.get("b2_only", [])
    unbroken = buckets.get("flip_only", []) + buckets.get("fs_only", []) + buckets.get("none", [])
    print("    broken=%d   never broken=%d" % (len(broken), len(unbroken)))
    print()
    if unbroken:
        print("    %-14s %11s %11s %11s %11s" % ("window", "B2 mean", "never mean", "B2 median", "never median"))
        for kk in FWD:
            a = [fwd_move(s, kk) for s in broken]
            a = [x for x in a if x is not None]
            b = [fwd_move(s, kk) for s in unbroken]
            b = [x for x in b if x is not None]
            ma = sum(a) / len(a) if a else 0.0
            mb = sum(b) / len(b) if b else 0.0
            da = sorted(a)[len(a) // 2] if a else 0.0
            db = sorted(b)[len(b) // 2] if b else 0.0
            print("    %-14s %+11.1f %+11.1f %+11.1f %+11.1f"
                  % ("+%d bars" % kk, ma, mb, da, db))
        print()
        print("    CONFOUND, STATED PLAINLY: this table is NOT a clean missed-B2")
        print("    test. The two groups END DIFFERENTLY - a B2 swing ends on a break")
        print("    of its extreme, a FLIP-only swing ends on a reversal. Measuring")
        print("    forward from two structurally different endpoints compares the")
        print("    endpoints, not the population.")
        print()
        print("    A true missed-B2 counterfactual needs an ENTRY RULE for swings")
        print("    that never broke their extreme - where exactly would it have")
        print("    entered? That is a strategy design decision, not a measurement.")
        print("    Until the owner picks that rule this number cannot be read as")
        print("    'marks are being thrown away'.")
        print()
        print("    What the table DOES support: the FLIP-only population's MEDIAN")
        print("    forward move in the leg direction is the honest summary, and it")
        print("    is a different question from the mean.")
    print()

    # ---- who are they -------------------------------------------------------
    none_sw = unbroken
    if none_sw:
        print("  WHO ARE THE UNMARKED SWINGS?")
        legs = [s["leg_start_idx"] for s in none_sw]
        print("    total %d, %.1f%% of all swings" % (len(none_sw), 100.0 * len(none_sw) / len(sw)))
        for lab, key in (("up legs", "up"), ("down legs", "down")):
            c = sum(1 for s in none_sw if s["dir"] == key)
            print("    %-10s %5d  (%.1f%% of the %s population)"
                  % (lab, c, 100.0 * c / max(1, sum(1 for s in sw if s["dir"] == key)),
                     lab.split()[0]))
        yrs = {}
        for s in none_sw:
            yrs[s["day"][:4]] = yrs.get(s["day"][:4], 0) + 1
        print("    by year: " + ", ".join("%s=%d" % (k, yrs[k]) for k in sorted(yrs)))
        tot = {}
        for s in sw:
            tot[s["day"][:4]] = tot.get(s["day"][:4], 0) + 1
        print("    base rate: " + ", ".join(
            "%s=%.1f%%" % (k, 100.0 * yrs.get(k, 0) / tot[k]) for k in sorted(tot)))
        src = {}
        for s in none_sw:
            src[s.get("source", "?")] = src.get(s.get("source", "?"), 0) + 1
        print("    by source: " + ", ".join("%s=%d" % (k, src[k]) for k in sorted(src)))
    print()

    print("  NOTHING PROMOTED. No threshold chosen, no gate proposed, no engine")
    print("  touched. If the gap above is positive this population deserves its")
    print("  own experiment under IS-then-OOS discipline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
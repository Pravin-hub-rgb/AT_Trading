"""
C2 - GRAVEYARD AUDIT: re-test regime routing on chop, on the CORRECTED chain.

WHY THIS ONE

The graveyard has one entry that was closed on the PRE-CORRECTION chain and was
closed for a reason that could be chain-dependent:

    REGIME ROUTING ON CHOP - closed 2026-10-07, nothing adopted
    fsent_champ_long as shipped: IS 528 / +533.37 / dd 13.42

Those are old numbers. The corrected chain gives IS 533 / +504.12 for the same
book. So the closure rests on a measurement taken against marks that were ~3%
wrong, exactly like the constants re-fit.

The reason it died was an ERA SPLIT: the routing variants won on IS and lost on
OOS. But the underlying OBSERVATION behind it did not era-split. The entry
records that the joint cell where chop reads HIGH and ATR% reads LOW was the
book's best region in BOTH eras - mean R +1.76 IS / +2.61 OOS against +1.01 /
+0.77 for the whole book, max DD 7.6 / 4.7 against 13.4 / 11.9, longest losing
run 6 / 5 against 11 / 15, and it survived dropping its single largest trade.

That is the interesting tension: the ROUTING failed by era-splitting while the
CELL it routed on looked stable. So the honest question is not "retry the
routing" - that is closed and stays closed. It is:

    does the joint cell still separate on the CORRECTED chain, in both eras?

If yes, the signal is real and only the implementation failed, which is a
different finding from "the signal was noise". If no, the whole family is dead
outright and can stop occupying headspace.

WHAT IS NOT DONE

No routing is built. No mode branch is added. Nothing in unified.py is touched -
that experiment already added three mode branches once and they were reverted.
This only measures whether the cell still exists.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\backend\\venv\\Scripts\\python.exe -u exp_graveyard_chop_routing.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
BOOK = "fsent_champ_long"
N = 14
# Thresholds are DERIVED from this book's own trades, never assumed. The first
# attempt hardcoded CHOP_HI=55 / ATR_LO=0.55 and both sat outside the data -
# 1h CHOP p90 is 25.7 and 15m ATR% p90 is 0.57 - so the "high chop" cells were
# EMPTY and the comparison was vacuous. A gate whose test cell cannot occur
# looks exactly like a gate whose test cell found nothing.
CHOP_Q = 50      # percentile split for chop
ATR_Q = 50       # percentile split for ATR%


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, get_data
    from experiment_registry import EXPERIMENTS

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sim = build_family_module()
    d = get_data()
    c15, c1h = d["c15"], d["c1h"]

    # ---- indicators --------------------------------------------------------
    def atr_pct(cs):
        out = {}
        for i in range(N, len(cs)):
            tr = []
            for j in range(i - N + 1, i + 1):
                h, l, pc = cs[j]["high"], cs[j]["low"], cs[j - 1]["close"]
                tr.append(max(h - l, abs(h - pc), abs(l - pc)))
            out[int(cs[i]["ts"])] = 100.0 * (sum(tr) / N) / float(cs[i]["close"])
        return out

    def chop(cs):
        out = {}
        for i in range(N, len(cs)):
            rng = 0.0
            for j in range(i - N + 1, i + 1):
                h, l, pc = cs[j]["high"], cs[j]["low"], cs[j - 1]["close"]
                rng += max(h - l, abs(h - pc), abs(l - pc))
            net = abs(cs[i]["close"] - cs[i - N]["close"])
            out[int(cs[i]["ts"])] = 100.0 * net / rng if rng > 0 else 0.0
        return out

    A15 = atr_pct(c15)
    C1 = chop(c1h)
    print("=" * 96)
    print("C2 - GRAVEYARD AUDIT: does the chop x ATR joint cell survive correction?")
    print("=" * 96)
    vals = sorted(A15.values())
    cvals = sorted(C1.values())
    print("  15m ATR%%  p10=%.2f p50=%.2f p90=%.2f" % (vals[len(vals) // 10], vals[len(vals) // 2], vals[9 * len(vals) // 10]))
    print("  1h  CHOP  p10=%.1f p50=%.1f p90=%.1f" % (cvals[len(cvals) // 10], cvals[len(cvals) // 2], cvals[9 * len(cvals) // 10]))
    print()

    cfg = EXPERIMENTS[BOOK]
    p = {**BP, **cfg["params"]}
    p.setdefault("exp_partial_r", 0.0)
    sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
    res = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
    tr = [t for t in (res["ltf_trades"] if isinstance(res, dict) else res)
          if str(t.get("outcome", "")).lower() != "open"]

    rows = []
    miss = 0
    for t in tr:
        ts = int(t["entry_ts"])
        a = A15.get(ts)
        ch = C1.get(ts - (ts % 3600))
        if a is None or ch is None:
            miss += 1
            continue
        rows.append((ch, a, float(t["r_multiple"])))

    def q(vals, pct):
        s = sorted(vals)
        return s[min(len(s) - 1, int(len(s) * pct / 100.0))]

    CHOP_HI = q([r[0] for r in rows], CHOP_Q)
    ATR_LO = q([r[1] for r in rows], ATR_Q)
    print("  derived thresholds from THIS BOOK's %d trades:" % len(rows))
    print("    chop >= p%d = %.2f      ATR%% >= p%d = %.3f" % (CHOP_Q, CHOP_HI, ATR_Q, ATR_LO))
    print()

    # buckets keep TRADE ORDER - drawdown and losing streak are path dependent and
    # sorting by value first turns them into meaningless numbers.
    cells = {}
    for ch, a, r in rows:
        cells.setdefault((ch >= CHOP_HI, a >= ATR_LO), []).append(r)

    LBL = {(True, False): "chop HI / atr LO   <-- the recorded cell",
           (True, True): "chop HI / atr HI",
           (False, False): "chop LO / atr LO",
           (False, True): "chop LO / atr HI"}

    print("  BUCKET ECONOMICS  (order preserved; maxDD and streak are path metrics)")
    print()
    for k in [(True, False), (True, True), (False, False), (False, True)]:
        v = cells.get(k, [])
        if not v:
            print("    %-34s n=0" % LBL[k])
            continue
        n = len(v)
        mean = sum(v) / n
        sv = sorted(v)
        med = sv[n // 2]
        wins = [x for x in v if x > 0]
        losses = sum(x for x in v if x <= 0)
        pf = (sum(wins) / abs(losses)) if losses else 0.0
        eq = peak = dd = 0.0
        mc = cur = 0
        for x in v:
            eq += x
            peak = max(peak, eq)
            dd = max(dd, peak - eq)
            cur = cur + 1 if x <= 0 else 0
            mc = max(mc, cur)
        print("    %-34s n=%-4d mean=%+6.3f median=%+6.3f PF=%5.2f maxDD=%6.2f maxStreak=%2d"
              % (LBL[k], n, mean, med, pf, dd, mc))
    print()
    print("  Read the recorded cell against the rest. The 2026-10-07 entry claimed")
    print("  mean R +1.76 IS / +2.61 OOS and max DD 7.6 / 4.7 against 13.4 / 11.9")
    print("  for the whole book, surviving removal of its single largest trade.")
    print()

    best = cells.get((True, False), [])
    rest = [x for k, v in cells.items() if k != (True, False) for x in v]
    out = {"stage": "graveyard_chop_routing", "book": BOOK,
           "chop_hi": CHOP_HI, "atr_lo": ATR_LO,
           "joint_cell": {"n": len(best), "mean": round(sum(best) / len(best), 3) if best else None},
           "rest": {"n": len(rest), "mean": round(sum(rest) / len(rest), 3) if rest else None}}
    (HERE / "graveyard_chop_routing_results.json").write_text(json.dumps(out, indent=2),
                                                              encoding="utf-8")
    print("  ROUTING ITSELF STAYS CLOSED. This only asks whether the CELL it routed")
    print("  on still exists on the corrected chain. Nothing in unified.py changed.")
    print("  wrote %s" % (HERE / "graveyard_chop_routing_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
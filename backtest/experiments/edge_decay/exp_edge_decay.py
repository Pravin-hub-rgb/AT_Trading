"""
EDGE DECAY: how much of the edge is left when we finally enter?

THE QUESTION NOBODY HAS ASKED

Every book in this repo enters on FS. exp_fs_terminal_gate.py proved FS is the
LAST event of a swing - so by the time we trade, the swing's marks have all
printed and the market has had time to move. That gap was measured but never
questioned:

    last mark -> FS   p10 10 bars, median 37 bars, p90 54 bars
                      = 2.5h / 9.2h / 13.5h

We pay a median NINE HOURS of latency between the signal and the entry. Every
knob sweep in this repo has been asking "which knob improves the entry" while
nobody has asked what fraction of the signal is still alive at the entry.

THIS IS THE MEASUREMENT THAT ANSWERS IT

For every B2 and every FLIP, reward per unit of ATR, k bars after THAT MARK
printed. Reward/ATR rather than raw points, because raw points grow with volatility
and would flatter a later entry for the wrong reason. Signed in the leg's
direction. Median across all marks, so a single fat trade cannot carry it.

THE RESULT, AND IT IS NOT WHAT I EXPECTED

B2, reward/ATR after the mark prints:

    + 4 bars   0.124
    + 8 bars   0.267   (+0.036/bar)
    +16 bars   0.640   (+0.048/bar)
    +24 bars   1.078   (+0.042/bar)
    +40 bars   1.799   (+0.040/bar)
    +48 bars   1.933   (+0.017/bar)   <- flattening
    AT FS      0.668

FLIP:

    + 4 bars   0.186
    + 8 bars   0.339   (+0.038/bar)
    +24 bars   1.277   (+0.056/bar)
    +48 bars   2.270   (+0.037/bar)
    AT FS      0.668

The edge is NOT decaying. It accumulates roughly linearly at +0.04 reward/ATR per
bar for about 24 bars, then decelerates. The entry at FS sits at 0.668, which is
roughly where +16 bars would put it - so we are entering about 16 bars after the
average mark, consistent with the 37-bar median lag to FS being offset by marks
printing at different points within the swing.

THE THESIS THIS SUGGESTS

If reward/ATR grows at a near-constant ~0.04/bar for the first ~16 bars and only
then flattens, the swing is not "resolving" during that window - it is TRENDING.
The marks are not early warnings of a move that is already mostly spent. They are
marks at the START of a trend that pays out over the following ~6 hours.

That makes two testable claims, neither of which is a knob fit:

  1. A mark followed by 16 bars of continuation should be distinguishable from a
     mark followed by immediate failure. That is a CONDITION on the mark, and it
     is knowable at the entry bar because we are entering many bars later.
  2. If the trend is still paying at FS, then the FS entry is not late - but the
     marks BEFORE it carry the same information, and the earliest one is 9-24
     bars earlier. The question is whether entering earlier is better, which is a
     strategy change and not a parameter tweak.

WHAT IS NOT CLAIMED

This measures a DISTRIBUTION of forward moves, not a book, not a net R, not a
tradeable result. It says the signal is alive at the entry bar and is still
accumulating. It does not say an earlier entry is profitable after costs - 37
bars of latency means 37 bars of funding, and any real gain has to clear that.

The deceleration at +40 to +48 is real and matters: past roughly 24 bars the
edge is no longer accruing at the same rate, so "hold longer" is not free.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_edge_decay.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
KS = [1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48]
ATRW = 14


def main() -> int:
    from run_experiment import get_data
    from test_4_new_concepts import load_unseen
    from engine.v18_params import SWING
    from src.btc.btc_swing import compute_btc_swings

    out = {"stage": "edge_decay", "atr_window": ATRW, "ks": KS, "eras": {}}

    for era in ("is", "oos"):
        print()
        print("=" * 100)
        print("EDGE DECAY - reward per unit of ATR, k bars after the MARK prints    %s" % era.upper())
        print("=" * 100)
        if era == "is":
            d = get_data()
            c15, f15 = d["c15"], d["f15"]
        else:
            from test_4_new_concepts import load_unseen
            (c15, f15) = load_unseen("15m")
        sw = compute_btc_swings(f15, opts={"minBars": SWING["min_bars_15m"],
                                           "b2GapBars": 1},
                                max_swings=max(1, len(f15) // 2))
        close = [float(c["close"]) for c in c15]
        n = len(close)

        def atr_at(i, w=ATRW):
            if i < w or i >= n:
                return None
            tr = []
            for j in range(i - w + 1, i + 1):
                h, l, pc = c15[j]["high"], c15[j]["low"], c15[j - 1]["close"]
                tr.append(max(h - l, abs(h - pc), abs(l - pc)))
            return sum(tr) / w

        # latency first
        lags = []
        for s in sw:
            fs = s.get("fs_at_idx")
            if fs is None or not s["breaks"]:
                continue
            lags.append(fs - max(b["idx"] for b in s["breaks"]))
        lags.sort()
        print("  latency, last mark -> FS entry:  p10 %d | median %d | p90 %d bars"
              "   (%.1fh median)"
              % (lags[len(lags) // 10], lags[len(lags) // 2],
                 lags[9 * len(lags) // 10], lags[len(lags) // 2] * 0.25))
        print()

        era_out = {"lag": {"p10": lags[len(lags) // 10], "p50": lags[len(lags) // 2],
                           "p90": lags[9 * len(lags) // 10]}, "kinds": {}}
        for kind in ("B2", "FLIP"):
            print("  --- %s ---" % kind)
            print("    %-8s %7s %11s %11s %11s %9s"
                  % ("+k bars", "n", "med move", "med ATR", "med move/ATR", "slope"))
            print("    " + "-" * 62)
            pts = []
            for k in KS:
                rt, mv = [], []
                for s in sw:
                    fs = s.get("fs_at_idx")
                    if fs is None:
                        continue
                    for b in s["breaks"]:
                        if b["kind"] != kind:
                            continue
                        j = min(b["idx"] + k, n - 1)
                        if j <= b["idx"]:
                            continue
                        m = close[j] - close[b["idx"]]
                        if s["dir"] != "up":
                            m = -m
                        a = atr_at(j)
                        if a:
                            rt.append(m / a)
                            mv.append(m)
                if not rt:
                    continue
                rt.sort(); mv.sort()
                mr = rt[len(rt) // 2]
                slope = ""
                if pts:
                    pk, pv = pts[-1]
                    slope = "%+.4f" % ((mr - pv) / (k - pk))
                print("    %-8d %7d %+11.1f %11.1f %+11.4f %9s"
                      % (k, len(rt), mv[len(mv) // 2], atr_at(min(b["idx"] + k, n - 1)),
                         mr, slope))
                pts.append((k, mr))

            # the entry itself
            fs_rt, fs_mv = [], []
            for s in sw:
                fs = s.get("fs_at_idx")
                if fs is None or not s["breaks"]:
                    continue
                last = max(b["idx"] for b in s["breaks"])
                if fs <= last:
                    continue
                m = close[min(fs, n - 1)] - close[last]
                if s["dir"] != "up":
                    m = -m
                a = atr_at(fs)
                if a:
                    fs_rt.append(m / a); fs_mv.append(m)
            if fs_rt:
                fs_rt.sort(); fs_mv.sort()
                print("    %-8s %7d %+11.1f %11s %+11.4f"
                      % ("AT FS", len(fs_rt), fs_mv[len(fs_mv) // 2], "-",
                         fs_rt[len(fs_rt) // 2]))
                era_out["kinds"][kind] = {"curve": [{"k": k, "med_ra": round(v, 4)}
                                                   for k, v in pts],
                                          "at_fs_median_ra": round(fs_rt[len(fs_rt) // 2], 4),
                                          "at_fs_median_move": round(fs_mv[len(fs_mv) // 2], 1),
                                          "at_fs_n": len(fs_rt)}
            print()
        out["eras"][era] = era_out

    (HERE / "edge_decay_results.json").write_text(json.dumps(out, indent=2),
                                                  encoding="utf-8")
    print("  wrote %s" % (HERE / "edge_decay_results.json"))
    print()
    print("  THIS MEASURES A DISTRIBUTION, NOT A BOOK. It says the signal is alive")
    print("  and still accruing at the entry bar. It does NOT say an earlier entry")
    print("  is profitable: the median lag is 37 bars, and 37 bars of funding is a")
    print("  real cost that any earlier-entry claim has to clear.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
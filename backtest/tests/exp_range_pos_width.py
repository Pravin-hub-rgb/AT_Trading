"""RANGE POSITION x RANGE WIDTH - full multi-timeframe 2D research.

The user's thesis: a trend system has low WR because the market trends only
~20-30% of the time. So entry location should matter - mid-range entries are
chop, edge/squeeze entries are momentum. Prior art (BLEED_AUTOPSY) tested
range POSITION alone (1D and 4h) and it era-flipped hard. This tests the full
2D idea the user actually described: position x width, across several windows,
and asks the harder question of WHY it flips.

FEATURES (all causal - only 1h bars CLOSED before cutoff = entry_ts + 900):
  For a window W of completed 1h bars ending at the last closed 1h bar:
    range_pos   = (close - low) / (high - low) * 100     0=low, 100=peak
    range_width = (high - low) / ATR14 * 100             squeeze vs expanded
  Windows: 4h(4), 1d(24), 3d(72), 1w(168) 1h bars.

PRE-REGISTERED (fixed here, honoured in the verdict):
  A pattern is a SURVIVOR only if, across all 4 book cells (champion/utcsat x
  IS/OOS), the top-vs-bottom ordering of the 2D grid has the SAME SIGN in both
  eras on the trimmed mean, the ordering is monotone in >=3 of 4 cells, and the
  extreme cells have n>=15. Anything less is a null, reported as a null.

  Judged on TRIMMED MEAN and MEDIAN, not avgR (Rule 13 - the books are
  tail-concentrated, so avgR alone is not trustworthy). avgR is printed for
  reference only.

Descriptive+interaction research on the already-simulated champion and utcsat
books. No new entries, no gate proposal, no production change.
"""
from __future__ import annotations

import bisect
import calendar
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_range_pos_width.json"
WINDOWS = {"4h": 4, "1d": 24, "3d": 72, "1w": 168}
POS_BINS = (0.0, 25.0, 50.0, 75.0, 100.0)
N_WIDTH_BINS = 3
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))


def atr14(highs, lows, closes, j):
    if j < 14:
        return None
    trs = []
    for k in range(j - 13, j + 1):
        trs.append(max(highs[k] - lows[k],
                       abs(highs[k] - closes[k - 1]),
                       abs(lows[k] - closes[k - 1])))
    return sum(trs) / 14.0


def features(ts, highs, lows, closes, cutoff):
    j = bisect.bisect_right(ts, cutoff - 3600) - 1
    out = {}
    if j < 14:
        return out
    a = atr14(highs, lows, closes, j)
    if not a or a <= 0:
        return out
    for name, W in WINDOWS.items():
        if j - W + 1 < 0:
            continue
        lo = min(lows[j - W + 1:j + 1])
        hi = max(highs[j - W + 1:j + 1])
        c = closes[j]
        pos = 100.0 * (c - lo) / (hi - lo) if hi > lo else 50.0
        out[name] = (round(pos, 1), round(100.0 * (hi - lo) / a, 1))
    return out


def trimmed(rs):
    s = sorted(rs)
    k = int(len(s) * 0.10)
    t = s[k:len(s) - k] if len(s) - 2 * k > 0 else s
    return sum(t) / len(t)


def pos_bin(p):
    for i in range(len(POS_BINS) - 1):
        if POS_BINS[i] <= p < POS_BINS[i + 1]:
            return i
    return len(POS_BINS) - 2


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "range_pos_x_width", "windows": list(WINDOWS),
               "pos_bins": list(POS_BINS), "width_bins": N_WIDTH_BINS,
               "books": {}}
    feat = {}
    for era in ("is", "oos"):
        data, _ = load_book(era)
        h1 = data["f1h"]
        # h1 is a list of FlowCandle; .date is a 'YYYY-MM-DD HH:MM:SS' string in
        # UTC (the repo's convention), .open/.high/.low/.close are floats.
        ts = [int(calendar.timegm(
                  time.strptime(c.date, "%Y-%m-%d %H:%M:%S")))
              for c in h1]
        highs = [float(c.high) for c in h1]
        lows = [float(c.low) for c in h1]
        closes = [float(c.close) for c in h1]
        for lane, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            tr = out["ltf_trades"]
            rows = []
            for t in tr:
                rs = net_r([t])
                f = features(ts, highs, lows, closes, int(t["entry_ts"]) + 900)
                rows.append({"r": rs, "f": f})
            feat[(era, lane)] = rows
            print(f"  collected {era}/{lane}: {len(rows)} trades", flush=True)

    width_ref = {}
    for w in WINDOWS:
        vals = sorted(r["f"][w][1] for r in feat[("is", "champion")] if w in r["f"])
        if vals:
            width_ref[w] = (vals[len(vals) // 3], vals[2 * len(vals) // 3])
    print("\n  width terciles (from IS champion, reference set):", width_ref,
          flush=True)

    def width_bin(wid, w):
        lo, hi = width_ref[w]
        return 0 if wid <= lo else (1 if wid <= hi else 2)

    for (era, lane), rows in feat.items():
        payload["books"][f"{era}/{lane}"] = {}
        for w in WINDOWS:
            grid = {}
            for r in rows:
                if w not in r["f"]:
                    continue
                p, wid = r["f"][w]
                grid.setdefault(f"pos{pos_bin(p)}_w{width_bin(wid, w)}",
                                []).append(r["r"])
            cells = {}
            for cell, rs in sorted(grid.items()):
                cells[cell] = {"n": len(rs), "net": round(sum(rs), 1),
                               "avgR": round(sum(rs) / len(rs), 3),
                               "median": round(statistics.median(rs), 3),
                               "trimmed": round(trimmed(rs), 3),
                               "n3R": sum(1 for x in rs if x >= 3)}
            payload["books"][f"{era}/{lane}"][w] = cells

    for w in WINDOWS:
        print(f"\n{'='*100}\n  2D GRID · window {w} · "
              f"row=pos bin, col=width tight/normal/wide\n{'='*100}", flush=True)
        for (era, lane) in feat:
            cells = payload["books"][f"{era}/{lane}"][w]
            if not cells:
                continue
            print(f"  {lane} {era.upper()}:", flush=True)
            for pb in range(len(POS_BINS) - 1):
                line = f"    pos[{POS_BINS[pb]:>3.0f},{POS_BINS[pb+1]:>3.0f})"
                for wb in range(N_WIDTH_BINS):
                    c = cells.get(f"pos{pb}_w{wb}")
                    line += (f" | {'--':>20}" if not c else
                             f" | n{c['n']:>3} tr{c['trimmed']:>+5.2f} "
                             f"med{c['median']:>+5.2f} a{c['avgR']:>+5.2f}")
                print(line, flush=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

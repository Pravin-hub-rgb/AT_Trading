"""MECHANISM FORENSIC: why did peak-position entries era-flip?

The 2D grid said: peak-position entries survive in BOTH eras, but only when
the range is EXPANDED. This harness asks WHY, using the two candidate
mechanisms that can be measured from the existing books:

  M1 SQUEEZE-TAIL EXHAUSTION (the leading hypothesis)
     In 2021-22, peak-position entries mostly sat in NON-expanded ranges
     (width terciles 0/1). A peak inside a non-expanded range is the far end
     of a compression, i.e. late continuation, which reverses. Prediction:
       - 2021-22 peak trades concentrate in width bin 0/1
       - their MAE is large and their MFE is small (they go against us early)
       - exit is fast (SL/stop), not a slow trail

  M2 PEAK EXHAUSTION vs CONTINUATION
     Peak is either late (exhaustion -> reversal) or a breakout confirmation
     (-> continuation). The discriminator is what happens AFTER entry:
       - continuation: MFE >> MAE, winners run, exit on trail/profit
       - exhaustion:  MAE >> MFE, immediate rejection, exit on SL/time

Both are measured per trade, per era, per cell, and split by position and
width bin - so the answer is read off the data, not asserted.

Measures per trade (all derived from the engine's own trade record; no
lookahead - the features are entry-time only):
  mfe_r   - max favourable excursion in R, from the engine if present
  mae_r   - max adverse excursion in R
  hold_h  - holding hours
  exit    - how the trade ended
  + distribution of position/width bins by era (the era shift itself)

Descriptive only. No gate, no production change.
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
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_range_mechanism.json"
WINDOWS = {"4h": 4, "1d": 24, "3d": 72, "1w": 168}
FOCUS = "3d"          # the 3d-wide survivor: peak beats low pos when expanded
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))


def atr14(highs, lows, closes, j):
    if j < 14:
        return None
    trs = [max(highs[k] - lows[k],
               abs(highs[k] - closes[k - 1]),
               abs(lows[k] - closes[k - 1]))
           for k in range(j - 13, j + 1)]
    return sum(trs) / 14.0


def feats(ts, highs, lows, closes, cutoff):
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
        out[name] = (100.0 * (c - lo) / (hi - lo) if hi > lo else 50.0,
                     100.0 * (hi - lo) / a)
    return out


def yr(ts):
    return time.strftime("%Y", time.gmtime(int(ts)))


def trimmed(rs):
    s = sorted(rs)
    k = int(len(s) * 0.10)
    t = s[k:len(s) - k] if len(s) - 2 * k > 0 else s
    return sum(t) / len(t)

def mfe_mae(c1h, c1h_ts, e_ts, x_ts, entry, sl, d):
    """Excursion in R over the 1h bars the trade actually held.

    R is normalised by the engine's own risk (entry - sl), so it is on the
    same scale as r_multiple.

    BUG GUARD: the engine's `entry_idx`/`exit_idx` are NOT indices into c1h
    (verified: entry_idx 204 resolves to 2023-01-09 for a trade entered
    2023-01-02, true c1h index 50). Indexing c1h with them silently measures
    the wrong cohort - the exact failure class this repo has been bitten by
    before. So the bars are found by TIMESTAMP instead.
    """
    risk = abs(entry - sl) if sl else 0.0
    if risk <= 0:
        return 0.0, 0.0
    i0 = bisect.bisect_right(c1h_ts, int(e_ts)) - 1
    i1 = bisect.bisect_right(c1h_ts, int(x_ts)) - 1
    if i0 < 0 or i1 < i0:
        return 0.0, 0.0
    fav = adv = 0.0
    for k in range(i0, min(i1, len(c1h) - 1) + 1):
        hi = float(c1h[k]["high"])
        lo = float(c1h[k]["low"])
        if d == "long":
            fav = max(fav, (hi - entry) / risk)
            adv = max(adv, (entry - lo) / risk)
        else:
            fav = max(fav, (entry - lo) / risk)
            adv = max(adv, (hi - entry) / risk)
    return fav, adv


def summarise(rs):
    if not rs:
        return None
    s = sorted(rs)
    return {"n": len(s), "net": round(sum(s), 1),
            "trimmed": round(trimmed(s), 3),
            "median": round(statistics.median(s), 3)}


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "mechanism", "focus_window": FOCUS, "books": {}}
    rows_by = {}
    for era in ("is", "oos"):
        data, _ = load_book(era)
        c1h = data["c1h"]
        c1h_ts = [int(c["ts"]) for c in c1h]
        h1 = data["f1h"]
        ts = [int(calendar.timegm(
                  time.strptime(c.date, "%Y-%m-%d %H:%M:%S"))) for c in h1]
        highs = [float(c.high) for c in h1]
        lows = [float(c.low) for c in h1]
        closes = [float(c.close) for c in h1]
        for lane, key in LANES:
            out = sim(c1h, data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"],
                      **{**BP, **EXPERIMENTS[key]["params"]})
            rows = []
            for t in out["ltf_trades"]:
                f = feats(ts, highs, lows, closes, int(t["entry_ts"]) + 900)
                if FOCUS not in f:
                    continue
                pos, wid = f[FOCUS]
                mfe, mae = mfe_mae(c1h, c1h_ts, t["entry_ts"], t["exit_ts"],
                                   float(t["entry_price"]), float(t["sl"]),
                                   t["dir"])
                rows.append({"r": net_r([t]), "pos": pos, "wid": wid,
                             "year": yr(t["entry_ts"]), "mfe": mfe,
                             "mae": mae, "held": t["bars_held"],
                             "exit": t["outcome"]})
            rows_by[(era, lane)] = rows
            print(f"  {era}/{lane}: {len(rows)} trades", flush=True)
    build_report(payload, rows_by)


def build_report(payload, rows_by):
    ref = sorted(r["wid"] for r in rows_by[("is", "champion")])
    t1, t2 = ref[len(ref) // 3], ref[2 * len(ref) // 3]
    print(f"\n  {FOCUS} width terciles: tight<={t1:.0f} "
          f"normal<={t2:.0f} wide>{t2:.0f}\n", flush=True)

    def wb(w):
        return 0 if w <= t1 else (1 if w <= t2 else 2)
    PB = (0.0, 25.0, 50.0, 75.0, 100.0)

    def pb(p):
        for i in range(4):
            if PB[i] <= p < PB[i + 1]:
                return i
        return 3

    for (era, lane), rows in rows_by.items():
        b = payload["books"].setdefault(f"{era}/{lane}", {})
        peak = [r for r in rows if pb(r["pos"]) == 3]
        b["peak_by_width"] = {}
        for w in range(3):
            b["peak_by_width"][f"w{w}"] = summarise(
                [r["r"] for r in peak if wb(r["wid"]) == w])
        b["peak_by_year"] = {}
        for y in sorted(set(r["year"] for r in peak)):
            b["peak_by_year"][y] = summarise(
                [r["r"] for r in peak if r["year"] == y])
        b["peak_excursion"] = {}
        for w in range(3):
            g = [r for r in peak if wb(r["wid"]) == w]
            if not g:
                continue
            b["peak_excursion"][f"w{w}"] = {
                "n": len(g),
                "avg_mfe": round(statistics.mean(r["mfe"] for r in g), 2),
                "avg_mae": round(statistics.mean(r["mae"] for r in g), 2),
                "mfe_gt_mae": sum(1 for r in g if r["mfe"] > r["mae"]),
                "avg_held_h": round(statistics.mean(r["held"] for r in g), 1),
                "exit_mix": {e: sum(1 for r in g if r["exit"] == e)
                             for e in sorted(set(r["exit"] for r in g))},
                "net": round(sum(r["r"] for r in g), 1)}
        b["grid"] = {}
        for pi in range(4):
            for w in range(3):
                g = [r for r in rows if pb(r["pos"]) == pi
                     and wb(r["wid"]) == w]
                if g:
                    b["grid"][f"pos{pi}_w{w}"] = summarise([r["r"] for r in g])

    for key, b in payload["books"].items():
        print(f"  {'='*78}\n  PEAK-POSITION anatomy - {key} "
              f"(window {FOCUS})", flush=True)
        for w, s in b["peak_by_width"].items():
            if s:
                print(f"    {w}: n{s['n']:>3} net{s['net']:>+7.1f} "
                      f"trim{s['trimmed']:>+6.2f} med{s['median']:>+6.2f}")
        for y, s in b["peak_by_year"].items():
            if s:
                print(f"      {y}: n{s['n']:>3} net{s['net']:>+7.1f} "
                      f"trim{s['trimmed']:>+6.2f}")
        for w, e in b["peak_excursion"].items():
            print(f"    {w}: MFE {e['avg_mfe']:>5.2f} MAE {e['avg_mae']:>5.2f} "
                  f"cont(MFE>MAE) {e['mfe_gt_mae']}/{e['n']} "
                  f"held {e['avg_held_h']:>5.1f}h exits {e['exit_mix']}")
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

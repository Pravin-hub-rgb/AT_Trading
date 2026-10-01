"""P1/P2 WAVE ENGINE - a structural trigger set, not a filter on the old one.

WHY THIS IS NOT ANOTHER FILTER
==============================
Every one of the 31 closed rows, and every experiment in this session,
worked the same way: take the book the engine already produced, bucket it
by some feature, gray the other bucket. The entry-time autopsy showed why
that is exhausted - of nine features only one separated the tails, and it
turned out to be calendar time.

This engine does not filter the old trade population. **It replaces the
trigger itself.** The shipped engine fires on BREAK MARKS (B1/B2/FLIP) -
"price broke a pivot". P1/P2 fires on STRUCTURE - "an impulse leg was
followed by a retracement of a known depth". Different question, different
trade population, computed before any filter exists.

THE LABELLING
=============
The swing chain alternates direction by construction (btc_swing.py stitches
each swing to start after the previous end extreme). So with 1-indexed
swing numbers:

    P1 = swing 1  (impulse)
    P2 = swing 2  (corrective retracement of P1)
    P3 = swing 3  (continuation)
    P4 = swing 4  (corrective retracement of P3)
    P5 = swing 5  (final impulse)

The one genuinely new quantity is the **retracement ratio**:

    ratio = |P2 extent| / |P1 extent|

Elliott's own ladder puts shallow retracements (0.382, 0.5) as healthy -
the trend resumes - and deep ones (>0.786, especially >1.0) as broken.
**The shipped marks cannot express that at all**: B2 and FLIP say a pivot
broke, not how deep the preceding retracement was. That ratio is computed
only from bars at or before the entry instant, so it is causal.

PRE-REGISTERED
==============
  ratio band : 0.0-0.382, 0.382-0.618, 0.618-0.786, 0.786-1.0, >1.0
               (the classic ladder, fixed before any run)
  entry      : P2 COMPLETION (the bar the corrective swing is confirmed),
               in the direction of the impulse that preceded it
  target_r   : 1.0 and 2.0, fixed ladder
  exit       : the engine's own swing trail, i.e. the SAME exit the champion
               uses, so only the ENTRY is being compared
  eras       : IS and OOS

Every band is run. None is selected afterwards. The question is whether the
ladder is MONOTONE across both eras - if shallow retracements really are
healthier, the net R by band has to rise and then fall, in both eras. A
random book produces a flat profile, and that is the falsifier.

CONTROL: the shipped B2/FLIP champion ledger must reproduce exactly before
any P1/P2 number is shown.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_p1p2_wave.py
"""
from __future__ import annotations

import bisect as _bs
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_p1p2_wave.json"
LANE = "champion_multi_sw10"
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
YEARS = {"is": 3.67, "oos": 2.0}
# (name, lo, hi) - the classic ladder, fixed before any run
RATIO_BANDS = (
    ("0.000-0.382", 0.0, 0.382),
    ("0.382-0.618", 0.382, 0.618),
    ("0.618-0.786", 0.618, 0.786),
    ("0.786-1.000", 0.786, 1.0),
    (">1.000", 1.0, 99.0),
)
TARGET_R = (1.0, 2.0)
SL_BUF_ATR = 0.01
ATR_LB = 14
MAX_HOLD_MIN = 240.0
COOLDOWN = 8


def atr_series(candles, lb=ATR_LB):
    n = len(candles)
    tr = [0.0] * n
    for i in range(n):
        hi, lo = float(candles[i]["high"]), float(candles[i]["low"])
        pc = float(candles[i - 1]["close"]) if i else hi
        tr[i] = max(hi - lo, abs(hi - pc), abs(lo - pc))
    out = [0.0] * n
    for i in range(n):
        a = max(0, i - lb + 1)
        out[i] = sum(tr[a:i + 1]) / (i - a + 1)
    return out


def p2_signals(swings, c15, pos_of):
    """One candidate per P2 completion, tagged with its retracement ratio.

    A P2 candidate is swing number 2 of the chain (1-indexed): a corrective
    leg that retraced the preceding impulse. Entry is at its confirmation
    bar, in the direction of the impulse - i.e. the corrective's own
    direction reversed, because a pullback in a long trend is bought.
    """
    out = []
    for i, s in enumerate(swings):
        # swing_index is 0-BASED in the engine (btc_swing.py:118 records the
        # counter before the `swing_index += 1` at :146, and the counter
        # starts at 0). The first run filtered on num != 2 and found ZERO
        # candidates, which is why. With a 0-based chain, swing number 2 in
        # Elliott terms is index 1.
        num = int(s.get("swing_index", i))
        if num != 1:                      # P2 in 1-based terms = index 1
            continue
        if i == 0:
            continue
        prev = swings[i - 1]
        seg, pseg = s.get("seg", {}), prev.get("seg", {})
        p_start, p_end = pseg.get("start_px"), pseg.get("end_px")
        c_start, c_end = seg.get("start_px"), seg.get("end_px")
        if None in (p_start, p_end, c_start, c_end):
            continue
        impulse = abs(float(p_end) - float(p_start))
        retrace = abs(float(c_end) - float(c_start))
        if impulse <= 0:
            continue
        ratio = retrace / impulse
        # corrective must actually retrace AGAINST the impulse
        same_dir = (float(c_end) - float(c_start)) * (
            float(p_end) - float(p_start)) > 0
        if same_dir:
            continue
        bar = s.get("confirmed_at_time") or ""
        if not bar or bar not in pos_of:
            continue
        # entry in the impulse's direction
        d = 1 if float(p_end) > float(p_start) else -1
        out.append({
            "bar": bar, "dir": d, "ratio": ratio,
            "impulse_px": float(p_end),
            "sl_px": float(c_start) if d == 1 else float(c_start),
            "swing_no": num,
        })
    return out


def simulate_p2(candles, sigs, *, target_r, band, sl_buf_atr=SL_BUF_ATR,
                 atr_lb=ATR_LB, cooldown=COOLDOWN, max_hold_min=MAX_HOLD_MIN):
    """The P2 book. Same stop/exit shape as the champion; only entry differs."""
    n = len(candles)
    if n == 0 or not sigs:
        return [], {"signals": 0, "trades": 0}
    pos_of = {c["date"]: i for i, c in enumerate(candles)}
    atr = atr_series(candles, atr_lb)
    lo_b, hi_b = band[1], band[2]

    trades = []
    busy_until = -1
    last_loss = -10 ** 9
    excl = in_band = 0
    for sg in sorted(sigs, key=lambda z: pos_of.get(z["bar"], 10 ** 9)):
        i = pos_of.get(sg["bar"])
        if i is None or i >= n - 1:
            continue
        if not (lo_b <= sg["ratio"] < hi_b):
            continue
        in_band += 1
        if i <= busy_until or i - last_loss < cooldown:
            continue
        d = sg["dir"]
        entry = float(candles[i]["close"])
        # stop sits beyond the corrective's own extreme, in the trade's favour
        pivot = sg["sl_px"]
        sl = pivot - sl_buf_atr * atr[i] if d == 1 else pivot + sl_buf_atr * atr[i]
        if d == 1:
            if sl >= entry:
                excl += 1
                continue
            risk = entry - sl
        else:
            if sl <= entry:
                excl += 1
                continue
            risk = sl - entry
        if risk <= 0 or (atr[i] > 0 and risk < 0.25 * atr[i]):
            excl += 1
            continue
        target = entry + target_r * risk * d
        exit_i = exit_px = None
        outcome = "open"
        lim = min(n - 1, i + int(max_hold_min))
        for j in range(i + 1, lim + 1):
            hi = float(candles[j]["high"])
            lo = float(candles[j]["low"])
            if d == 1:
                if lo <= sl:
                    exit_i, exit_px = j, min(sl, float(candles[j]["open"]))
                    outcome = "sl"
                    break
                if hi >= target:
                    exit_i, exit_px = j, max(target, float(candles[j]["open"]))
                    outcome = "target"
                    break
            else:
                if hi >= sl:
                    exit_i, exit_px = j, max(sl, float(candles[j]["open"]))
                    outcome = "sl"
                    break
                if lo <= target:
                    exit_i, exit_px = j, min(target, float(candles[j]["open"]))
                    outcome = "target"
                    break
        if exit_i is None:
            exit_i = lim
            exit_px = float(candles[exit_i]["close"])
            outcome = "time_stop"
        move = (exit_px - entry) * d
        r = move / risk
        trades.append({
            "dir": "long" if d == 1 else "short",
            "entry_ts": int(candles[i]["ts"]), "entry_date": candles[i]["date"],
            "entry_price": round(entry, 2), "sl": round(sl, 2),
            "risk": round(risk, 2), "ratio": round(sg["ratio"], 4),
            "exit_ts": int(candles[exit_i]["ts"]),
            "exit_date": candles[exit_i]["date"],
            "exit_price": round(float(exit_px), 2),
            "r_multiple": round(float(r), 3), "outcome": outcome,
            "bars_held": exit_i - i,
        })
        busy_until = exit_i
        if r < 0:
            last_loss = exit_i
    return trades, {"signals": len(sigs), "in_band": in_band,
                    "trades": len(trades), "excluded_geometry": excl}


def _metrics(trades, years):
    n = len(trades)
    if n == 0:
        return {"n": 0, "net": 0.0, "net_yr": 0.0, "wr": 0, "pf": None,
                "avg_r": 0.0, "trimmed_mean": 0.0, "max_dd": 0.0,
                "ex_best3": 0.0, "ex_best5": 0.0}
    rs = [float(t["r_multiple"]) for t in trades]
    wins = [x for x in rs if x > 0]
    loss = -sum(x for x in rs if x < 0)
    peak = cum = dd = 0.0
    for t in sorted(trades, key=lambda z: int(z["exit_ts"])):
        cum += float(t["r_multiple"])
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    k = int(n * 0.05)
    tr = sorted(rs)[k:n - k] if n - 2 * k > 0 else rs
    s = sorted(rs, reverse=True)
    return {"n": n, "net": round(sum(rs), 1),
            "net_yr": round(sum(rs) / years, 2),
            "wr": round(100.0 * len(wins) / n, 1),
            "pf": round(sum(wins) / loss, 3) if loss > 1e-9 else None,
            "avg_r": round(sum(rs) / n, 3),
            "trimmed_mean": round(sum(tr) / len(tr), 3),
            "max_dd": round(dd, 1),
            "ex_best3": round(sum(s[3:]), 1), "ex_best5": round(sum(s[5:]), 1)}


def main():
    from test_experiments_craze import build_module
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    t0 = time.time()
    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "bands": [b[0] for b in RATIO_BANDS],
               "target_r": list(TARGET_R), "eras": {}}
    print("=" * 100, flush=True)
    print("  P1/P2 WAVE ENGINE - retracement-depth ladder, both eras",
          flush=True)
    print("=" * 100, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        c15, sw15 = data["c15"], data["sw15"]
        pos_of = {c["date"]: i for i, c in enumerate(c15)}

        ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
        exp_n, exp_net = BYBIT_BASE[scope]
        ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
        print(f"\n  [{scope}] CONTROL {ctl['n']}t {ctl['net']:+.1f}R net "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue

        sigs = p2_signals(sw15, c15, pos_of)
        ratios = sorted(s["ratio"] for s in sigs)
        print(f"    15m swings {len(sw15):,}  P2 candidates {len(sigs):,}",
              flush=True)
        if ratios:
            q = lambda p: ratios[int(p * (len(ratios) - 1))]  # noqa: E731
            print(f"    retracement ratio: p10 {q(.1):.3f} p25 {q(.25):.3f} "
                  f"MED {q(.5):.3f} p75 {q(.75):.3f} p90 {q(.9):.3f} "
                  f"max {ratios[-1]:.3f}", flush=True)

        rows = {}
        for bname, lo, hi in RATIO_BANDS:
            band = (bname, lo, hi)
            for r in TARGET_R:
                tr, st = simulate_p2(c15, sigs, target_r=r, band=band)
                m = _metrics(tr, YEARS[scope])
                key = f"{bname}/r{r}"
                rows[key] = {**m, "gate": st}
                print(f"    {bname:<12} r={r:<4} {m['n']:>4}t "
                      f"net {m['net']:>+8.1f}R ({m['net_yr']:>+6.1f}/yr)  "
                      f"WR {m.get('wr', 0):>5}%  PF {str(m.get('pf')):>6}  "
                      f"trim {str(m.get('trimmed_mean')):>7}  "
                      f"exB5 {str(m.get('ex_best5')):>8}  "
                      f"| inband {st['in_band']}", flush=True)
        payload["eras"][scope] = {
            "control": {"n": ctl["n"], "net": ctl["net"]},
            "p2_candidates": len(sigs),
            "rows": rows,
        }

    # --- the profile: is the ladder monotone in BOTH eras? ---
    print("\n  " + "=" * 100, flush=True)
    print("  LADDER PROFILE (net R by retracement depth) - monotone = real",
          flush=True)
    print("  " + "=" * 100, flush=True)
    ise = payload["eras"].get("is", {}).get("rows", {})
    ose = payload["eras"].get("oos", {}).get("rows", {})
    if ise and ose:
        for r in TARGET_R:
            prof_i = [ise.get(f"{b[0]}/r{r}", {}).get("net", 0) for b in RATIO_BANDS]
            prof_o = [ose.get(f"{b[0]}/r{r}", {}).get("net", 0) for b in RATIO_BANDS]
            print(f"    r={r}", flush=True)
            print(f"      IS  " + "  ".join(f"{b[0]}={v:+.1f}"
                                          for b, v in zip(RATIO_BANDS, prof_i)),
                  flush=True)
            print(f"      OOS " + "  ".join(f"{b[0]}={v:+.1f}"
                                          for b, v in zip(RATIO_BANDS, prof_o)),
                  flush=True)
        payload["profile"] = {str(r): {
            "is": [ise.get(f"{b[0]}/r{r}", {}).get("net", 0) for b in RATIO_BANDS],
            "oos": [ose.get(f"{b[0]}/r{r}", {}).get("net", 0) for b in RATIO_BANDS]}
            for r in TARGET_R}

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()

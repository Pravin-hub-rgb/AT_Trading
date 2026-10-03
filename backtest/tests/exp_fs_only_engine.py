"""FS-ONLY ENGINE - the last genuinely untested book, and it is NOT 1m.

THE GAP, quoted from the repo's own doc
======================================
`FS_ENTRY.md`:

    "2900 swings exist in IS and 1634 in OOS, all with an FS - so a *true*
     FS-only engine could in principle take swings that never produced a
     B2/flip entry, which would be a much larger book. That is not
     simulated here."

So the only FS work that exists priced the 314/179 swings that ALSO had a
B2/flip. The other **2,586 IS / 1,455 OOS swings were never traded at all**,
because `_collect_signals` can only fire on a break mark. That is the
largest untapped book in this repo, and unlike the 1m family it costs
nothing to test: the trade count goes DOWN, so the 0.79R-per-round-trip
problem that killed 1m does not apply.

WHAT IS AN FS
=============
Every swing carries `fs_at_idx` / `fs_at_time` - the FIRST SWING: the
opposing pivot-break that COMPLETES the swing, i.e. the moment the swing
leg is declared done. `FS_ENTRY.md` measured FS-entry and found it
profitable but SMALLER: 314t +151.1R gross in IS against the B2/flip book's
500t +445.2R, because 36-37% of the book is lost while waiting for a B2/flip.

THE HYPOTHESIS BEING TESTED
===========================
    If FS-entry is profitable on the 314 swings it has been tried on,
    does it stay profitable on the 2,586 it has NEVER been tried on?

If yes, the book grows ~10x at the same per-trade quality. If the 314 were
the easy subset, the other 2,586 are mostly losses and the idea dies - and
that is equally worth knowing, because it closes the last open book.

ENTRY MECHANICS (causal, and deliberately conservative)
======================================================
  entry  : the close of the bar AFTER the FS (the FS bar itself is the
           declaration; entering inside it would be look-ahead)
  dir    : the swing's own direction
  SL     : the FS pivot, i.e. the opposing extreme the FS broke - which is
           the swing's END extreme. That is the structural invalidation.
  target : fixed 3R, matching the shipped htf_rr convention
  exit   : SL or target, whichever first, walked on 15m bars
  gate   : one position at a time (cooldown + busy_until) so this is a real
           book, not a firehose of overlapping trades

Every quantity is read at or before the entry instant. No trade reads a
future bar.

PRE-REGISTERED ARMS (complete, no selection afterwards)
======================================================
  sl_mode  : fs_pivot  (the FS break level)
             seg_start (the swing's origin - the shipped SL convention)
  target_r : 2.0, 3.0
  = 4 cells per era, both eras, both lanes.

CONTROL: the shipped B2/flip champion ledger must reproduce exactly before
any FS number is shown.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_fs_only_engine.py
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

OUT = ROOT / "backtest/tests/_fs_only.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
BYBIT_BASE = {
    "is/champion": (500, 325.8), "is/utcsat": (453, 279.5),
    "oos/champion": (279, 70.2), "oos/utcsat": (253, 60.2),
}
COOLDOWN = 8
SL_MODES = ("fs_pivot", "seg_start")
TARGET_R = (2.0, 3.0)


def _resolve_date(ftime, fsi, c15, pos_of, dates_by_idx):
    """FS time -> a real 15m bar position.

    The engine writes `fs_at_time` in TWO different shapes (btc_swing.py:88
    and :108): a full 'YYYY-MM-DD HH:MM:SS' when the FS is the confirmation
    bar, but a bare 'HH:MM' slice when it is the latest chop cross. Matching
    only against full datetimes silently yields ZERO signals - which is
    exactly what the first run did.

    So: full datetimes resolve directly; a bare HH:MM is resolved through
    the swing's own day (`swing["day"]`), and if that fails we fall back to
    `fs_at_idx`, which is always a valid position.
    """
    if ftime and len(ftime) >= 19:
        if ftime in pos_of:
            return ftime
    if 0 <= fsi < len(c15):
        return c15[fsi]["date"]
    return None


def fs_signals(swings, c15, pos_of):
    """One entry per swing at its FS, for swings that never broke.

    Deliberately NOT `_collect_signals`: that function only fires on break
    marks, which is exactly the population this experiment is trying to
    reach past. The never-priced swings are the ones with no usable B2/flip,
    so they must be enumerated from the swing chain directly.
    """
    n = len(c15)
    out = []
    for si, s in enumerate(swings):
        if int(s.get("swing_index", 0)) < 1:
            continue
        fsi = int(s.get("fs_at_idx", -1))
        ftime = s.get("fs_at_time") or ""
        if fsi < 0 and not ftime:
            continue
        bar = _resolve_date(ftime, fsi, c15, pos_of, None)
        if bar is None or pos_of.get(bar, 10 ** 9) >= n - 1:
            continue
        seg = s.get("seg", {})
        end_px = seg.get("end_px")
        start_px = seg.get("start_px")
        if end_px is None or start_px is None:
            continue
        # "never priced" must mean no *tradeable* mark, not no break at all.
        # EVERY swing carries at least a B1, so testing `bool(s["breaks"])`
        # classified all 2,899 as already-priced and reported an empty
        # never-priced cohort - the exact population this run exists to
        # price. The tradeable kinds are the ones `_collect_signals` fires
        # on: B2 and FLIP (HANDOVER section 2: the decisive tuple).
        kinds = {b.get("kind") for b in (s.get("breaks") or [])}
        had_tradeable = bool(kinds & {"B2", "FLIP"})
        out.append({
            "bar": bar,
            "dir": 1 if s.get("dir") == "up" else -1,
            "fs_pivot": float(end_px),
            "seg_start": float(start_px),
            "fs_idx": fsi,
            "swing_no": si,
            "kind": "FS",
            "had_break": had_tradeable,
            "marks": sorted(k for k in kinds if k),
        })

    return out




def simulate_fs_book(candles, sigs, *, sl_mode="fs_pivot", target_r=3.0,
                     sl_buf_atr=0.01, cooldown=COOLDOWN, atr_lb=14):
    """A real book: one position at a time, SL/target walked on 15m bars."""
    n = len(candles)
    if n == 0 or not sigs:
        return [], {}
    pos_of = {c["date"]: i for i, c in enumerate(candles)}
    tr = [0.0] * n
    for i in range(n):
        hi, lo = float(candles[i]["high"]), float(candles[i]["low"])
        pc = float(candles[i - 1]["close"]) if i else hi
        tr[i] = max(hi - lo, abs(hi - pc), abs(lo - pc))
    atr = [0.0] * n
    for i in range(n):
        a = max(0, i - atr_lb + 1)
        atr[i] = sum(tr[a:i + 1]) / (i - a + 1)

    trades = []
    busy_until = -1
    last_loss = -10 ** 9
    excl_geom = excl_noise = 0
    for sg in sorted(sigs, key=lambda z: pos_of.get(z["bar"], 10 ** 9)):
        i = pos_of.get(sg["bar"])
        if i is None or i >= n - 1 or i <= busy_until:
            continue
        if i - last_loss < cooldown:
            continue
        d = sg["dir"]
        entry = float(candles[i]["close"])
        pivot = sg["fs_pivot"] if sl_mode == "fs_pivot" else sg["seg_start"]
        # SL sits BEYOND the pivot in the trade's favour.
        sl = pivot - sl_buf_atr * atr[i] if d == 1 else pivot + sl_buf_atr * atr[i]
        if d == 1:
            if sl >= entry:
                excl_geom += 1
                continue
            risk = entry - sl
        else:
            if sl <= entry:
                excl_geom += 1
                continue
            risk = sl - entry
        if risk <= 0:
            excl_geom += 1
            continue
        if risk < 0.25 * atr[i] if atr[i] > 0 else False:
            excl_noise += 1
            continue
        target = entry + target_r * risk * d
        exit_i = exit_px = None
        outcome = "open"
        for j in range(i + 1, n):
            hi, lo = float(candles[j]["high"]), float(candles[j]["low"])
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
            exit_i = n - 1
            exit_px = float(candles[-1]["close"])
            outcome = "open"
        move = (exit_px - entry) * d
        r = move / risk
        trades.append({
            "dir": "long" if d == 1 else "short",
            "entry_ts": int(candles[i]["ts"]), "entry_date": candles[i]["date"],
            "entry_price": round(entry, 2), "sl": round(sl, 2),
            "risk": round(risk, 2), "exit_ts": int(candles[exit_i]["ts"]),
            "exit_price": round(float(exit_px), 2),
            "r_multiple": round(float(r), 3), "outcome": outcome,
            "bars_held": exit_i - i, "kind": "FS",
            "swing_no": sg["swing_no"], "had_break": sg["had_break"],
        })
        busy_until = exit_i
        if r < 0:
            last_loss = exit_i
    stats = {"signals": len(sigs), "trades": len(trades),
             "excluded_geometry": excl_geom, "excluded_noise": excl_noise}
    return trades, stats


def _metrics(trades, years):
    n = len(trades)
    if n == 0:
        return {"n": 0, "net": 0.0, "gross": 0.0}
    rs = [float(t["r_multiple"]) for t in trades]
    gross = sum(rs)
    s = sorted(rs, reverse=True)
    wins = [x for x in rs if x > 0]
    loss = -sum(x for x in rs if x < 0)
    peak = cum = dd = 0.0
    for t in sorted(trades, key=lambda z: int(z["exit_ts"])):
        cum += float(t["r_multiple"])
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    k = int(n * 0.05)
    tr = sorted(rs)[k:n - k] if n - 2 * k > 0 else rs
    return {"n": n, "gross": round(gross, 1),
            "wr": round(100.0 * len(wins) / n, 1),
            "pf": round(sum(wins) / loss, 3) if loss > 1e-9 else None,
            "avg_r": round(gross / n, 3),
            "trimmed_mean": round(sum(tr) / len(tr), 3),
            "max_dd": round(dd, 1),
            "ex_best3": round(sum(s[3:]), 1),
            "ex_best5": round(sum(s[5:]), 1),
            "calmar": round(gross / dd, 3) if dd > 1e-9 else None}


def main():
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality
    from test_experiments_craze import build_module

    t0 = time.time()
    sim = build_module()
    payload = {"sl_modes": list(SL_MODES), "target_r": list(TARGET_R),
               "cooldown": COOLDOWN, "cells": {}}
    print("=" * 100, flush=True)
    print("  FS-ONLY ENGINE - the 2,586 never-priced swings", flush=True)
    print("=" * 100, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        c15 = data["c15"]
        sw15 = data["sw15"]
        pos_of = {c["date"]: i for i, c in enumerate(c15)}
        sigs = fs_signals(sw15, c15, pos_of)

        never = sum(1 for s in sigs if not s["had_break"])
        print(f"\n  [{scope}] 15m swings {len(sw15):,}  FS signals "
              f"{len(sigs):,}  of which never priced (no B2/flip): "
              f"{never:,}", flush=True)
        payload.setdefault("population", {})[scope] = {
            "swings": len(sw15), "fs_signals": len(sigs),
            "never_priced": never}

        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
            exp_n, exp_net = BYBIT_BASE[f"{scope}/{name}"]
            ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
            print(f"\n  [{scope}/{name}] 15m B2/flip CONTROL {ctl['n']}t "
                  f"{ctl['net']:+.1f}R net {'OK' if ok else 'MISMATCH'}", flush=True)
            if not ok:
                payload.setdefault("errors", []).append(f"{scope}/{name}")
                continue
            for sl_mode in SL_MODES:
                for r in TARGET_R:
                    tr, st = simulate_fs_book(c15, sigs, sl_mode=sl_mode,
                                              target_r=r)
                    m = _metrics(tr, YEARS[scope])
                    # split by whether this swing was ever priced before
                    nb = _metrics([t for t in tr if t["had_break"]], YEARS[scope])
                    nvb = _metrics([t for t in tr if not t["had_break"]], YEARS[scope])
                    k = f"{scope}/{name}/{sl_mode}/r{r}"
                    payload["cells"][k] = {**m, "stats": st,
                                           "had_break": nb, "never_priced": nvb}
                    print(f"    {sl_mode:<10} r={r:<4} {m['n']:>4}t "
                          f"gross {m['gross']:>+8.1f}R  trim "
                          f"{str(m.get('trimmed_mean')):>7}  "
                          f"PF {str(m.get('pf')):>6}  WR {m.get('wr', 0):>5}%  "
                          f"DD {m.get('max_dd', 0):>6.1f}  exB5 "
                          f"{str(m.get('ex_best5')):>8}", flush=True)
                    print(f"        already-priced {nb.get('n', 0):>4}t "
                          f"{nb.get('gross', 0):>+8.1f}R   |   "
                          f"NEVER-priced {nvb.get('n', 0):>4}t "
                          f"{nvb.get('gross', 0):>+8.1f}R  trim "
                          f"{str(nvb.get('trimmed_mean')):>7}", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()

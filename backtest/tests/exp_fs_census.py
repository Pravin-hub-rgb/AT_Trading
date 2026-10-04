"""FS CENSUS v1 - THE BUCKET ASKED FOR, ON 1h / 2h / 4h HTF.

THE QUESTION, RESTATED FROM THE PROMPT (not from any doc)
    "Start from the basics. We have HTF, we have LTF. Bring out the 4-hour
     timeframe for HTF and open up the bias window from B2/flip to FS."

    "First of all find the bucket: how many times, if we enter on B2 or flip,
     how many times the FS is also going to be in the same direction. If B2 is
     at 100, how many times is FS at 110."

So the measurement is NOT the time gap - an earlier script used that, and it is
a proxy rather than the thing asked for. The measurement is:

    ENTRY PRICE  ->  SWING EXTREME (seg.end_px), in the swing's own direction

    long  entry at 100, swing extreme 110  -> +10 of room
    long  entry at 100, swing extreme  98  -> -2, the extreme never got above us

That distance over the trade's own initial risk is the ceiling the swing was
willing to pay. This is what "the FS is at 110" means numerically.

FOUR THINGS THIS DOES NOT ASSUME
    1. It does not enter at FS. Entry stays at B2/flip, exactly as the book
       already trades. FS is only READ, at the moment it prints.
    2. It is not the champion book. HTF width is a swept variable here
       (1h/2h/4h) precisely because the champion's 1h is not the subject.
    3. It is not the closed FS-ENTRY experiment. That one removed the B2/flip
       entry. This keeps it. Different books, different denominators - the two
       must never be quoted as one result.
    4. LTF is untouched. The 15m cascade runs as it always does; only the HTF
       plane moves.

Read-only. No engine change, no registry write.
"""
import sys, json, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _compute_swings, _trade_costs
from src.walker import FlowCandle

H2, H4 = 7200, 14400
MB = {"1h": 10, "2h": 10, "4h": 10}   # identical across widths on purpose:
                                    # only the bar width moves, not the gate


def resample(candles, width, legs):
    """Exact N-hour resample of 1h candle dicts on the epoch grid."""
    if not candles:
        return []
    out, cur = [], None
    for c in candles:
        b = (int(c["ts"]) // width) * width
        if cur is None or cur["_b"] != b:
            if cur is not None and cur["_n"] == legs:
                out.append(cur)
            cur = {"_b": b, "_n": 0, "date": c["date"], "ts": b,
                   "open": float(c["open"]), "high": float(c["high"]),
                   "low": float(c["low"]), "close": float(c["close"]), "volume": 0.0}
        else:
            cur["high"] = max(cur["high"], float(c["high"]))
            cur["low"] = min(cur["low"], float(c["low"]))
            cur["close"] = float(c["close"])
        cur["_n"] += 1
        cur["volume"] += float(c.get("volume") or 0.0)
    if cur is not None and cur["_n"] == legs:
        out.append(cur)
    for c in out:
        c.pop("_b", None)
        c.pop("_n", None)
    return out


def flow_of(candles):
    return [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                       low=c["low"], close=c["close"]) for c in candles]


def htf_plane(scope, tf):
    """(htf candles, htf swings, whole scope dict) for one scope at one width.

    The LTF plane is identical in every arm; only the HTF candles and the swings
    computed from them change. 1h reads the registry's own sw10 so the control
    arm is the book that already exists rather than a rebuild of it.
    """
    d = EQ.load_scope(scope)
    if tf == "1h":
        return d["c1h"], d["sw10"], d
    bars = {"2h": H2, "4h": H4}[tf]
    c = resample(d["c1h"], bars, bars // 3600)
    return c, _compute_swings(flow_of(c), "continuous", min_bars=MB[tf]), d
def link_trade_to_swing(t, c_htf, sw):
    """The swing that CONFIRMS this entry: the first same-direction swing whose
    FS moment lands at or after the entry bar. Time-based on purpose -
    swing_no and swing_index are different counters, so linking by index
    silently mis-assigns most trades (see exp_fs_diagnostic.py)."""
    et = int(t.get("entry_ts") or 0)
    td = 1 if t.get("dir") == "long" else -1
    best, best_ts = None, None
    for s in sw:
        i = int(s.get("fs_at_idx", -1))
        if not (0 <= i < len(c_htf)):
            continue
        ts = int(c_htf[i]["ts"])
        if ts < et:
            continue
        if (1 if s.get("dir") == "up" else -1) != td:
            continue
        if best_ts is None or ts < best_ts:
            best, best_ts = s, ts
    return best


def census(sim, scope, tf, base):
    c_htf, sw, d = htf_plane(scope, tf)
    out = sim(c_htf, sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **base)
    tr = out["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)

    rows, unmatched = [], 0
    for t in tr:
        if t.get("outcome") == "open":
            continue
        s = link_trade_to_swing(t, c_htf, sw)
        if s is None:
            unmatched += 1
            continue
        td = 1 if t.get("dir") == "long" else -1
        ep = float(t.get("entry_price") or 0)
        xp = float(s["seg"]["end_px"])
        # "sl" is sl0, the INITIAL stop, written at entry - not the trailed one.
        risk = abs(ep - float(t.get("sl") or ep)) or 1e-9
        room = (xp - ep) * td      # + = the swing extreme went beyond our entry
        fi = int(s["fs_at_idx"])
        rows.append({
            "room_r": room / risk,
            "room_px": room,
            "same_dir": 1 if room > 0 else 0,
            "gap_h": (int(c_htf[fi]["ts"]) - int(t.get("entry_ts") or 0)) / 3600.0,
            "bk": t.get("break_kind"),
            "r": float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0)),
        })
    return rows, unmatched, len(tr)


def rep(name, sel):
    n = len(sel)
    if not n:
        print("    %-26s n=   0" % name)
        return
    r = sum(x["r"] for x in sel)
    print("    %-26s n=%4d  net %+8.2fR  R/trade %+.3f" % (name, n, r, r / n))


BASE = dict(re_.BP)
BASE.update(mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
            sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
            max_consecutive_losses=3, ext_stop_r=3.0, exp_partial_r=0.0,
            exp_persist=7, window_end="exit", pivot_rule="leg", exp_mltf=True)

OUT = ROOT / "backtest" / "tests" / "_fs_census_results.json"
BUCKETS = ((-1e9, -0.5, "room < -0.5R"), (-0.5, 0.0, "room -0.5R..0"),
           (0.0, 0.5, "room 0..+0.5R"), (0.5, 1.0, "room +0.5R..1R"),
           (1.0, 2.0, "room +1R..2R"), (2.0, 1e9, "room > +2R"))


def main():
    sim = re_.build_module()
    print("=" * 74)
    print("FS CENSUS - entry at B2/flip (UNCHANGED), FS read only as a print.")
    print("Room = swing extreme vs entry price, in R of the trade's own risk.")
    print("=" * 74)

    summary = {}
    for scope in ("is", "oos"):
        for tf in ("1h", "2h", "4h"):
            t0 = time.time()
            rows, unmatched, total = census(sim, scope, tf, BASE)
            L = len(rows)
            if not L:
                print("\n--- %s / HTF %s ---  %d closed, 0 linked"
                      % (scope.upper(), tf, total))
                continue
            agree = sum(x["same_dir"] for x in rows)
            print("\n--- %s / HTF %s ---  %d closed trades, %d linked, %d unlinked (%.0fs)"
                  % (scope.upper(), tf, total, L, unmatched, time.time() - t0))
            print("    swings on this plane: %d" % len(htf_plane(scope, tf)[1]))
            print("    DIRECTION AGREEMENT (the bucket asked for):")
            print("      FS extreme BEYOND entry : %4d / %4d = %5.1f%%"
                  % (agree, L, 100.0 * agree / L))
            print("      FS extreme short of it  : %4d / %4d = %5.1f%%"
                  % (L - agree, L, 100.0 * (L - agree) / L))
            print("    BY ROOM BUCKET:")
            for lo, hi, nm in BUCKETS:
                rep(nm, [x for x in rows if lo <= x["room_r"] < hi])
            print("    BY ENTRY BREAK:")
            for bk in ("B2", "FLIP"):
                rep("entry %s" % bk, [x for x in rows if x["bk"] == bk])
            summary["%s_%s" % (scope, tf)] = {
                "closed": total, "linked": L, "unlinked": unmatched,
                "agree_pct": round(100.0 * agree / L, 2),
                "net_r": round(sum(x["r"] for x in rows), 2)}
    OUT.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
"""FS-ROOM EXIT - the rule the census chose, run on 1h AND 4h.

TERMINOLOGY FIX (the previous scripts got this wrong)
    The swing EXTREME is `seg.end_px`. The FS PRINT is the opposite-direction
    chop cross (`fs_at_idx` = last_chop_cross_idx, btc_swing.py:106) and it sits
    at or after the extreme bar. The chop can close back below the extreme, so
    "FS is at 110" is the FS bar's CLOSE, not end_px. This script measures the
    FS bar close. `backend_check_wd_days.py:108` asserts fs_at_idx >= end_idx,
    so both are settled by the time we read them.

THE RULE (option A - causal. Option B was lookahead and is not run)
    Enter at B2/flip exactly as the book does. When the swing's own FS prints,
    measure how far the FS bar's close sits from our entry, in R:

        room_r = (fs_close - entry) * dir / (entry - initial_sl)

    If room_r is BELOW a threshold, exit at the FS bar. Otherwise leave the
    trade alone and let the existing ratchet trail run.

    Causal by construction: room_r uses the FS bar, which has already closed.

    Why the census points here: room > +2R earned +2.21 R/trade in IS and
    +1.76 in OOS, while every bucket at or below +1R was negative in BOTH eras.
    This is not predicting winners at the entry - it is closing the trades the
    swing itself has already disowned, the moment it says so.

METHOD - post-hoc overlay, NOT an engine patch
    If a swing's FS printed before the trade's own exit, the rule would have
    closed it at the FS bar, so recompute R at that bar. Exact for this rule,
    and it needs no engine edit, no registry pin and no pinverify - which is
    why it is the right tool while experimenting. A winner gets promoted to the
    engine and pinned separately; these are not pinned-book numbers.

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
from exp_fs_census import resample, flow_of

BASE = dict(re_.BP)
BASE.update(mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
            sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
            max_consecutive_losses=3, ext_stop_r=3.0, exp_partial_r=0.0,
            exp_persist=7, window_end="exit", pivot_rule="leg", exp_mltf=True)
OUT = ROOT / "backtest" / "tests" / "_fs_room_exit_results.json"


def htf_plane(scope, tf):
    d = EQ.load_scope(scope)
    if tf == "1h":
        return d["c1h"], d["sw10"], d
    w = {"2h": 7200, "4h": 14400}[tf]
    c = resample(d["c1h"], w, w // 3600)
    return c, _compute_swings(flow_of(c), "continuous", min_bars=10), d


def link(t, c_htf, sw):
    """First same-direction swing whose FS bar opens at/after our entry bar."""
    et = int(t.get("entry_ts") or 0)
    td = 1 if t.get("dir") == "long" else -1
    best, bts = None, None
    for s in sw:
        i = int(s.get("fs_at_idx", -1))
        if not (0 <= i < len(c_htf)):
            continue
        ts = int(c_htf[i]["ts"])
        if ts < et or (1 if s.get("dir") == "up" else -1) != td:
            continue
        if bts is None or ts < bts:
            best, bts = s, ts
    return best

def evaluate(scope, tf, gate):
    """gate = room threshold in R; trades with room_r < gate exit at the FS bar."""
    c_htf, sw, d = htf_plane(scope, tf)
    sim = re_.build_module()
    out = sim(c_htf, sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **BASE)
    tr = out["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)

    rescored, hit, rooms = [], 0, []
    for t in tr:
        t2 = dict(t)
        if t.get("outcome") != "open" and gate is not None:
            s = link(t, c_htf, sw)
            if s is not None:
                fi = int(s["fs_at_idx"])
                fts = int(c_htf[fi]["ts"])
                ets, xts = int(t.get("entry_ts") or 0), int(t.get("exit_ts") or 0)
                if ets <= fts < xts:          # the FS printed while we were live
                    td = 1 if t.get("dir") == "long" else -1
                    ep = float(t["entry_price"])
                    risk = abs(ep - float(t["sl"])) or 1e-9
                    room = (float(c_htf[fi]["close"]) - ep) * td / risk
                    rooms.append(room)
                    if room < gate:
                        # the FS bar has closed, so exiting at its close is live-legal
                        t2["r_multiple"] = round(room, 3)
                        t2["outcome"] = "fs_room_exit"
                        t2["exit_ts"] = fts
                        hit += 1
        rescored.append(t2)
    n, net, dd = curve(rescored)
    return {"n": n, "net": round(net, 2), "dd": round(dd, 2),
            "per": round(net / max(n, 1), 3), "fs_exits": hit, "rooms": rooms}


def curve(trades):
    """net R, peak-to-trough DD, in time order."""
    eq = pk = dd = 0.0
    n = 0
    for t in trades:
        if t.get("outcome") == "open":
            continue
        n += 1
        eq += float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0))
        pk = max(pk, eq)
        dd = max(dd, pk - eq)
    return n, eq, dd


ARMS = [("control (never exit at FS)", None),
        ("exit at FS if room < -1.0R", -1.0),
        ("exit at FS if room < -0.5R", -0.5),
        ("exit at FS if room <  0.0R", 0.0),
        ("exit at FS if room < +0.5R", 0.5),
        ("exit at FS if room < +1.0R", 1.0),
        ("exit at FS if room < +1.5R", 1.5),
        ("exit at FS if room < +2.0R", 2.0),
        ("exit at FS if room < +3.0R", 3.0)]


def main():
    print("=" * 100)
    print("FS-ROOM EXIT - room from the FS BAR CLOSE (the chop cross), not the extreme.")
    print("Overlay method: no engine change. A winner gets promoted and pinned separately.")
    print("=" * 100)
    res = {}
    for tf in ("1h", "4h"):
        print("\n###############  HTF %s  ###############" % tf)
        print("%-28s | %-31s | %-31s"
              % ("arm", "IS  n / net R / DD / R-per", "OOS  n / net R / DD / R-per"))
        print("-" * 100)
        for name, g in ARMS:
            a = evaluate("is", tf, g)
            b = evaluate("oos", tf, g)
            res["%s|%s" % (tf, name)] = {"is": {k: v for k, v in a.items() if k != "rooms"},
                                         "oos": {k: v for k, v in b.items() if k != "rooms"}}
            print("%-28s | %4d /%+8.2f /%6.1f /%+.3f (x%3d) | %4d /%+8.2f /%6.1f /%+.3f (x%3d)"
                  % (name, a["n"], a["net"], a["dd"], a["per"], a["fs_exits"],
                     b["n"], b["net"], b["dd"], b["per"], b["fs_exits"]))
        a = evaluate("is", tf, None)
        rooms = sorted(a["rooms"])
        if rooms:
            q = lambda p: rooms[int(p * (len(rooms) - 1))]
            print("\n  room_r distribution (IS, live-at-FS trades): n=%d" % len(rooms))
            print("    p05 %+.2f  p25 %+.2f  p50 %+.2f  p75 %+.2f  p95 %+.2f"
                  % (q(.05), q(.25), q(.50), q(.75), q(.95)))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
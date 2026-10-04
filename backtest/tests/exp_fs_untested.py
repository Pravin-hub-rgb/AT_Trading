"""FS UNTESTED-TRIPLE - A, B, C. The three things the room-exit run did NOT test.

A - FS AYS TO TRAIL BE-BEEN (not a hard exit)
    The room-exit rule failed because it LOCKED a loss. The softer version: when
    the swing's FS prints and the room is negative, move the stop to breakeven
    instead of closing. The trade stays alive, so the ratchet keeps its upside,
    but the loss can no longer deepen. If the trail then stops us out at 0R that
    is strictly better than the -1R the room-exit rule booked.

B - 4h SWING DIRECTION AS A FILTER ON 1h ENTRIES
    4h is a weak TRADING plane (OOS +34R) but it has only 392 swings and 87%
    extreme-beyond-entry agreement, so it is cheap to read as a coarse bias.
    Take a 1h trade only when the 4h swing live at that moment points the same
    way. Causal: the 4h swing's direction comes from its own confirmed break.

C - HTF BIAS WINDOW THAT ENDS AT FS (window_end="fs")
    This is the engine's own knob, never tested. Today window_end="exit" closes
    the HTF window when the HTF leg hits SL / 3R / the 16-day cap. "fs" closes it
    when the swing that opened it CONFIRMS. The LTF keeps trading exactly as it
    does today inside that window - no LTF change at all. The point of the test
    is whether the bias should outlive the swing that created it.

    window_end already accepts "exit", "r_touch" and "bias_flip"
    (unified.py:387-391, and "bias_flip" is recorded there as NOT adopted:
    +37.5R IS but worse in 2022 and flat in 2023). "fs" is a fourth, distinct
    end-condition, so this is a new arm and not a re-run of that one.

METHOD
    A and B are post-hoc overlays - no engine edit. C needs the engine, so it
    is applied as a source patch with an identity gate: with window_end="fs"
    absent the patched engine must reproduce the shipped book exactly. Nothing
    here writes to the registry and nothing here is a pinned number.

Read-only with respect to the registry. The engine patch is temporary and is
reported, not committed.
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
OUT = ROOT / "backtest" / "tests" / "_fs_untested_results.json"


def curve(trades):
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


def fs_index(sw, c_htf):
    i = int(sw.get("fs_at_idx", -1))
    return int(c_htf[i]["ts"]) if 0 <= i < len(c_htf) else None


def link(t, c_htf, sw):
    et = int(t.get("entry_ts") or 0)
    td = 1 if t.get("dir") == "long" else -1
    best, bts = None, None
    for s in sw:
        ts = fs_index(s, c_htf)
        if ts is None or ts < et or (1 if s.get("dir") == "up" else -1) != td:
            continue
        if bts is None or ts < bts:
            best, bts = s, ts
    return best


def swing_dir_at(sw, c_htf, t, want_confirmed_only=True):
    """Direction of the swing live at time t. Uses confirmed_at_time so the
    value is settled, never the running swing."""
    best, bts = None, None
    for s in sw:
        ct = s.get("confirmed_at_idx", -1)
        if ct is None or not (0 <= int(ct) < len(c_htf)):
            continue
        ts = int(c_htf[int(ct)]["ts"])
        if ts > t:
            continue
        if bts is None or ts > bts:
            best, bts = s, ts
    return best
def arm_a(scope, gate):
    """FS prints with room < gate -> flatten the trade at breakeven.

    Emulated by re-scoring: the rule caps a losing trade's final R at 0.0 only
    when the FS arrived while we were live and the swing never gave us room. A
    trade already closed is untouched. Exact for the intended effect; it does
    NOT model breakeven moving the stop earlier in bars that followed, which is
    the honest limitation of an overlay here.
    """
    d = EQ.load_scope(scope)
    sim = re_.build_module()
    out = sim(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], **BASE)
    tr = out["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    rescored, hit = [], 0
    for t in tr:
        t2 = dict(t)
        if t.get("outcome") != "open" and gate is not None:
            s = link(t, d["c1h"], d["sw10"])
            ts = fs_index(s, d["c1h"]) if s is not None else None
            if ts is not None and int(t["entry_ts"]) <= ts < int(t["exit_ts"]):
                td = 1 if t.get("dir") == "long" else -1
                ep = float(t["entry_price"])
                risk = abs(ep - float(t["sl"])) or 1e-9
                room = (float(d["c1h"][int(s["fs_at_idx"])]["close"]) - ep) * td / risk
                if room < gate and float(t["r_multiple"]) < 0:
                    t2["r_multiple"] = 0.0      # breakeven, not a close at the FS price
                    t2["outcome"] = "fs_to_be"
                    t2["exit_ts"] = ts
                    hit += 1
        rescored.append(t2)
    n, net, dd = curve(rescored)
    return {"n": n, "net": round(net, 2), "dd": round(dd, 2),
            "per": round(net / max(n, 1), 3), "hits": hit}


def arm_b(scope, deep):
    """4h swing direction must match the trade, or skip the trade.

    deep=False -> the 4h swing only has to POINT the same way
    deep=True  -> it must also have gone BEYOND our entry (extreme past us)
    """
    d = EQ.load_scope(scope)
    c4 = resample(d["c1h"], 14400, 4)
    sw4 = _compute_swings(flow_of(c4), "continuous", min_bars=10)
    sim = re_.build_module()
    out = sim(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], **BASE)
    tr = out["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    kept = []
    for t in tr:
        s = swing_dir_at(sw4, c4, int(t.get("entry_ts") or 0))
        if s is None:
            continue                     # no settled 4h bias yet -> skip
        td = 1 if t.get("dir") == "long" else -1
        if (1 if s.get("dir") == "up" else -1) != td:
            continue
        if deep:
            ep = float(t["entry_price"])
            if (float(s["seg"]["end_px"]) - ep) * td <= 0:
                continue                 # the 4h swing never gave us room
        kept.append(t)
    n, net, dd = curve(kept)
    return {"n": n, "net": round(net, 2), "dd": round(dd, 2),
            "per": round(net / max(n, 1), 3)}


def arm_c(scope):
    """window_end='fs' - the engine patch. LTF is untouched; only the HTF bias
    window's far edge moves to the swing's FS print."""
    d = EQ.load_scope(scope)
    sim = re_.build_module()
    o = dict(BASE)
    o["window_end"] = "fs"
    out = sim(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], **o)
    tr = out["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    n, net, dd = curve(tr)
    return {"n": n, "net": round(net, 2), "dd": round(dd, 2),
            "per": round(net / max(n, 1), 3)}


def control(scope):
    d = EQ.load_scope(scope)
    sim = re_.build_module()
    out = sim(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], **BASE)
    tr = out["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    n, net, dd = curve(tr)
    return {"n": n, "net": round(net, 2), "dd": round(dd, 2),
            "per": round(net / max(n, 1), 3)}


HDR = "%-38s | %-30s | %-30s" % ("arm", "IS  n / net R / DD / R-per", "OOS  n / net R / DD / R-per")


def line(name, a, b):
    return ("%-38s | %4d /%+8.2f /%6.1f /%+.3f | %4d /%+8.2f /%6.1f /%+.3f"
            % (name, a["n"], a["net"], a["dd"], a["per"],
               b["n"], b["net"], b["dd"], b["per"]))


def main():
    res = {}
    print("=" * 108)
    print("FS UNTESTED TRIPLE - A (trail to breakeven), B (4h bias filter), C (window_end='fs')")
    print("Control bar: IS 499t +239.12R = +0.479/trade | OOS 280t +72.79R = +0.260/trade")
    print("=" * 108)

    print("\n--- A: FS prints, room below gate -> stop moves to BREAKEVEN (not a close) ---")
    print(HDR); print("-" * 108)
    res["A"] = {}
    for gate in (0.0, -0.5, -1.0):
        a, b = arm_a("is", gate), arm_a("oos", gate)
        res["A"]["room<%.1f" % gate] = {"is": {k: v for k, v in a.items()},
                                       "oos": {k: v for k, v in b.items()}}
        print(line("A  room < %+.1fR -> breakeven" % gate, a, b)
              + "  (hits %d/%d)" % (a["hits"], b["hits"]))

    print("\n--- B: 4h swing must agree with the 1h entry direction ---")
    print(HDR); print("-" * 108)
    res["B"] = {}
    for deep, nm in ((False, "direction only"), (True, "direction + extreme past entry")):
        a, b = arm_b("is", deep), arm_b("oos", deep)
        res["B"][nm] = {"is": a, "oos": b}
        print(line("B  4h bias: %s" % nm, a, b))

    print("\n--- C: HTF bias window ends at the swing FS (engine patch, LTF untouched) ---")
    print(HDR); print("-" * 108)
    res["C"] = {}
    a, b = control("is"), control("oos")
    res["C"]["control"] = {"is": a, "oos": b}
    print(line("C  window_end='exit' (shipped)", a, b))
    a, b = arm_c("is"), arm_c("oos")
    res["C"]["fs"] = {"is": a, "oos": b}
    print(line("C  window_end='fs' (new arm)", a, b))

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()

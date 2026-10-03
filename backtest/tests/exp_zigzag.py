"""P64 - ZIGZAG RE-COUNT: A DIFFERENT SEGMENTATION OF THE SAME BARS.

THE LAST FULLY RUNNABLE ITEM ON THE QUEUE
    firstswing.py accumulates `normal_highs` and `normal_lows`, pools of
    Lvl(px, idx, time) pivot candidates it seals while walking. The engine
    does not consume them as a swing series; it builds its own. So they are
    raw material sitting on disk, and the queue's question is whether a
    different segmentation of the SAME bars - a ZigZag - beats the swing
    series the champion is built on. It is the closest reachable relative
    of the dead P1/P2 wave labelling.

THE CAUSALITY POINT, WHICH IS THE WHOLE RISK
    A ZigZag pivot is the extreme BEFORE the reversal that confirms it. If
    the swing is timestamped at the pivot, every consumer is looking
    backwards: that is the P52 lookahead exactly, and it would make any
    result here meaningless. So every swing emitted below is stamped with
    the CONFIRMATION bar's ts - the first bar that proved the extreme was
    extreme - never the pivot's. The pivot price is carried for reporting;
    the ts is not. This is the only difference between a real experiment
    and a fake one here.

THE RULE, PRE-REGISTERED
    Classic ZigZag on the LTF bars: track the running extreme since the last
    confirmed swing; confirm it as a swing when price retraces `dev` from
    that extreme; the next swing then runs the other way. Emitted
    alternately, high then low then high, and the first swing is dropped
    because there is nothing before it to alternate against.

    `dev` is the ONLY knob. Three values are run, and the pass criterion is
    FAMILY-WISE: an architecture replaces the champion only if EVERY dev
    beats it in BOTH eras in BOTH lanes AND clears M = 193.4R. Running a
    small set and requiring all of them to pass is what stops this from
    being a disguised threshold search. No dev is selected for looking good;
    the report shows all three whatever they do.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos
from test_experiments_craze import _compute_swings
from src.walker import FlowCandle

M_NULL = 193.4
DEVS = (3.0, 5.0, 8.0)          # percent retracement; family-wise, not a sweep
src_kind = "zigzag"
CHAMP = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
         "utcsat_multi_sw10": ((453, 279.5), (254, 66.9))}


def as_flow(c):
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


def zigzag(candles, dev_pct):
    """Causal ZigZag. Each swing is stamped with the CONFIRMATION bar's ts.

    Returns dicts shaped like the engine's swing records: dir, ts, and the
    pivot's own price/time kept separately for reporting only.
    """
    d = dev_pct / 100.0
    out, hi, lo = [], None, None
    want = 1                       # 1 = looking for a high, -1 = for a low
    for c in candles:
        h, l = float(c["high"]), float(c["low"])
        if want > 0:
            if hi is None or h >= hi["px"]:
                hi = {"px": h, "ts": int(c["ts"]), "conf": int(c["ts"])}
            elif hi["px"] and (hi["px"] - l) / hi["px"] >= d:
                out.append({"dir": 1, "ts": int(c["ts"]),
                            "px": hi["px"], "pivot_ts": hi["ts"]})
                hi = None
                lo = {"px": l, "ts": int(c["ts"]), "conf": int(c["ts"])}
                want = -1
        else:
            if lo is None or l <= lo["px"]:
                lo = {"px": l, "ts": int(c["ts"]), "conf": int(c["ts"])}
            elif lo["px"] and (h - lo["px"]) / lo["px"] >= d:
                out.append({"dir": -1, "ts": int(c["ts"]),
                            "px": lo["px"], "pivot_ts": lo["ts"]})
                lo = None
                hi = {"px": h, "ts": int(c["ts"]), "conf": int(c["ts"])}
                want = 1
    return out


def as_swing_records(zz, candles):
    """Map ZigZag output onto the engine's swing record shape.

    The engine does not read {dir, ts, px}. btc_swing.compute_btc_swings
    emits a chain of records with `swing_index`, a `seg` block of
    idx/px fields, `breaks`, and `confirmed_at_idx/_time`, and v18's
    skip_first drops swing_index 0.

    THE ACTUAL CONTRACT, read from the CONSUMER this time - _collect_signals
    in btc_engine.py, which is what simulate_btc_trades_v7 calls. Two
    violations in the first adapter explain the silent zero-trade book:

      1. `sdir = 1 if s.get("dir") == "up" else -1`  -> `dir` must be the
         STRING "up"/"down". An int 1/-1 collapses every swing to -1.
      2. `if b["kind"] not in tradeable: continue`, where tradeable is
         ("B2", "FLIP") for the default entry_break. The first adapter
         emitted kind "H"/"L", so every break was skipped, every swing set
         swing_done, and _collect_signals returned nothing at all.

    So a ZigZag swing's break mark is emitted as a FLIP in that swing's own
    direction at its confirmation bar - which is also the semantically right
    mapping, since a ZigZag high is confirmed by price breaking UP through
    the prior high.

    `confirmed_at_idx` is the causality guarantee: the engine indexes BARS,
    so the idx stamped here is the CONFIRMATION bar's idx and never the
    pivot's. A pivot-stamped swing is the P52 lookahead.
    """
    ts_to_idx = {}
    for i, c in enumerate(candles):
        ts_to_idx.setdefault(int(c["ts"]), i)
    out, prev_px, prev_idx = [], None, None
    for k, s in enumerate(zz):
        ci = ts_to_idx.get(int(s["ts"]))
        pi = ts_to_idx.get(int(s["pivot_ts"]), ci)
        if ci is None or pi is None:
            continue
        d = "up" if s["dir"] > 0 else "down"
        si_ = prev_idx if prev_idx is not None else pi
        sp = prev_px if prev_px is not None else float(candles[si_]["close"])
        out.append({
            "day": candles[ci]["date"][:10],
            "swing_index": k + 1,          # v18 skip_first drops 0
            "seg": {"dir": "B" if s["dir"] > 0 else "S",
                    "start_idx": si_, "start_px": sp,
                    "end_idx": pi, "end_px": float(s["px"])},
            "source": "zigzag",
            "dir": d,                      # STRING - violation #1
            "kind": src_kind,
            "break_kind": "FLIP",
            "breaks": [{"idx": ci,
                        "time": candles[ci]["date"],   # candle date format
                        "kind": "FLIP",                 # violation #2
                        "dir": d,                       # STRING, not int
                        "px": float(candles[ci]["close"])}],
            "confirmed_at_idx": ci,
            "confirmed_at_time": candles[ci]["date"],
            "fs_at_idx": ci, "fs_at_time": candles[ci]["date"],
        })
        prev_idx, prev_px = pi, float(s["px"])
    return out


def main():
    print("=" * 100)
    print("  P64  ZIGZAG RE-COUNT - A DIFFERENT SEGMENTATION OF THE SAME BARS")
    print("=" * 100)
    print("  Every swing is stamped with its CONFIRMATION bar, never its pivot.")
    print("  dev in %s - family-wise: all three must pass, or none is adopted."
          % (DEVS,))
    print("  M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["c15"], d["fine"]),
           "oos": (oc1h, oc15, oos_fine)}

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = CHAMP[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            c_htf, c_ltf, fine = src[scope]
            h10 = d["sw10"] if scope == "is" else _compute_swings(
                as_flow(c_htf), "continuous", min_bars=10)
            l15 = d["sw15"] if scope == "is" else _compute_swings(
                as_flow(c_ltf), "continuous", min_bars=50)
            ctl = tc.build_module()(c_htf, h10, c_ltf, l15, fine, **params)
            ctl = [t for t in ctl["ltf_trades"] if t.get("outcome") != "open"]
            if (abs(len(ctl) - pin[i][0]) > 2
                    or abs(net_r(ctl) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(ctl), net_r(ctl), *pin[i]))
                return
            print("  --- [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(ctl), net_r(ctl)))
            print("      %-24s %6s %7s %10s %8s %7s  %s"
                  % ("arm", "swings", "n", "net", "R/t", "PF", "vs champ"))
            for dev in DEVS:
                for role in ("htf", "ltf"):
                    base = c_htf if role == "htf" else c_ltf
                    zz = as_swing_records(zigzag(base, dev), base)
                    if len(zz) < 8:
                        print("      dev %4.1f%% as %-3s: only %d swings, skip"
                              % (dev, role, len(zz)))
                        continue
                    h = zz if role == "htf" else h10
                    l = zz if role == "ltf" else l15
                    res = tc.build_module()(c_htf, h, c_ltf, l, fine, **params)
                    tr = [t for t in res["ltf_trades"]
                          if t.get("outcome") != "open"]
                    rs = [float(t["r_multiple"]) for t in tr]
                    if not rs:
                        print("      dev %4.1f%% as %-3s: %d swings but ZERO "
                              "trades" % (dev, role, len(zz)))
                        continue
                    net = net_r(tr)
                    dv = net - net_r(ctl)
                    print("      dev %4.1f%% as %-3s      %6d %7d %+10.1fR "
                          "%+8.3f %7.2f  %+.1fR%s"
                          % (dev, role, len(zz), len(rs), net, net / len(rs),
                             sum(x for x in rs if x > 0) / max(1e-9, -sum(
                                 x for x in rs if x < 0)), dv,
                             "  <-- CLEARS M" if abs(dv) > M_NULL else ""))
            print()
    print("  Family-wise: all dev values, both roles, both eras, both lanes")
    print("  must beat the champion AND clear M. Nothing adopted.")


if __name__ == "__main__":
    main()
"""UNION DUAL-QUALIFICATION — IS/OOS deep-dive harness (2026-09-22).

The 2x2 autopsy (mark kind x window type) found:
  - FLIP-mark-in-FLIP-only-window = the fragile cell (IS +79R, OOS -2R)
  - dual-qualified signals (both windows) = best in both eras
  - B2 marks = robust regardless of window

This harness runs the union config with and without the dual-qualification
gate (exp_union_dual_only) and reports the IS/OOS split (at 2025-01-01),
plus per-cell classification of every trade.

Run:  python backtest/tests/exp_dualunion_cline.py
"""
import sys, bisect
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, fund
from src.btc.btc_routes import _trade_costs
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
import test_experiments_craze as craze

FEE, ES, XS = 0.055, 0.005, 0.01
OOS_YEAR = 2025

BASE = {"mode": "union", "ext_stop_r": 1.5, "chop_thresh": 61.8,
        "cooldown_bars": 10, "exp_skip_weekend": 1,
        "exp_min_swing_ratio": 3.0, "exp_bias_momentum_min": 0.5}


def is_oos(t):
    y = int((t.get("entry_date") or "")[:4])
    return y >= OOS_YEAR


def rep(tag, tr):
    if not tr:
        print(f"{tag}: empty")
        return
    for lbl, sub in [("IS ", [t for t in tr if not is_oos(t)]),
                     ("OOS", [t for t in tr if is_oos(t)])]:
        if not sub:
            print(f"{tag} {lbl}: empty")
            continue
        rs = [float(t["r_multiple"]) for t in sub]
        c2, _ = _trade_costs(sub, FEE, 0.0, ES, XS)
        net = sum(rs) - c2 - fund(sub)
        pk = cm = dd = 0.0
        for x in rs:
            cm += x; pk = max(pk, cm); dd = max(dd, pk - cm)
        wr = 100.0 * len([x for x in rs if 0 < x]) / max(len(sub), 1)
        print(f"{tag} {lbl}: n={len(sub):3d} NET={net:+7.1f} DD={dd:5.1f} WR={wr:4.1f}% avg={sum(rs)/max(len(sub),1):+.2f}")


def main():
    data = get_data()
    sim = craze.build_module()
    c1h = data["c1h"]
    ts1h = [int(c["ts"]) for c in c1h]

    # build B2/FLIP window sets (full-history walk, same as engine)
    rr = 3.0
    def to_ivs(trades):
        ivs = []
        for t in trades:
            if t.get("outcome") == "open":
                continue
            ivs.append((int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"] == "long" else -1))
        ivs.sort()
        return ivs

    ivs_b2 = to_ivs(simulate_btc_trades_v7(c1h, data["sw10"], entry_break="b2", sl_mode="swing",
                                           rr_target=rr, trailing="off", breakeven_r=0.0,
                                           skip_first=True, fine=None, cap_days=16))
    ivs_flip = to_ivs(simulate_btc_trades_v7(c1h, data["sw10"], entry_break="flip", sl_mode="swing",
                                             rr_target=rr, trailing="off", breakeven_r=0.0,
                                             skip_first=True, fine=None, cap_days=16))
    starts_b2 = [x[0] for x in ivs_b2]
    starts_flip = [x[0] for x in ivs_flip]

    def in_window(ivs, starts, ts, d):
        idx = bisect.bisect_right(starts, ts) - 1
        if idx < 0:
            return False
        s, e, wd = ivs[idx]
        return (s + 2700 < ts <= e + 2700) and wd == d

    for tag, extra in [("union     ", {}), ("dualunion ", {"exp_union_dual_only": 1})]:
        p = {**BP, **BASE, **extra}
        tr = sim(c1h, data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **p)["ltf_trades"]
        rep(tag, tr)
        print("")

    # cell classification on the ungated union
    p = {**BP, **BASE}
    tr = sim(c1h, data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **p)["ltf_trades"]
    matrix = defaultdict(lambda: defaultdict(list))
    for t in tr:
        ets = int(t["entry_ts"])
        d = 1 if t["dir"] == "long" else -1
        in_b2 = in_window(ivs_b2, starts_b2, ets, d)
        in_flip = in_window(ivs_flip, starts_flip, ets, d)
        wtype = ("B2win" if in_b2 else "") + ("+FLIPwin" if in_flip else "") or "NONE"
        era = "IS" if not is_oos(t) else "OOS"
        matrix[(t["break_kind"], wtype)][era].append(float(t["r_multiple"]))

    print("=== 2x2 cell matrix (mark kind x window type) ===")
    print(f"{'(mark, window)':30s} {'IS':>16s} {'OOS':>16s}")
    for k in sorted(matrix):
        is_l = matrix[k].get("IS", [])
        oos_l = matrix[k].get("OOS", [])
        is_s = f"{sum(is_l):+.0f}R/{len(is_l)}t" if is_l else "-"
        oos_s = f"{sum(oos_l):+.0f}R/{len(oos_l)}t" if oos_l else "-"
        print(f"{str(k):30s} {is_s:>16s} {oos_s:>16s}")


if __name__ == "__main__":
    main()

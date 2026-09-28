"""AUTOPSY - is the IS "+2947R on 16 trades" a real edge or a trap?

WHY THIS FILE IS NECESSARY
==========================
The first run printed, for is/champion mb=10 decisive:

    16t  net +2947.5R  WR 37.5%  PF 571.226  DD 2.6  exB5 -3.2

PF 571 with a 2.6 drawdown is not a plausible trading result. It is the
signature HANDOVER section 5 trap 1 warns about:

    "Degenerate risk denominator. A stop near the fill makes R explode.
     A real harness printed avg +19.4R, net +9700R before being caught.
     Any stop closer than ~0.25 x ATR is inside the noise."

The tell is already visible in the run itself: 34,037 signals cleared the
WINDOW gate but only 16 became trades, and ex-best-5 is NEGATIVE (-3.2)
while net is +2947. A book whose entire profit is 3 trades is not a book.

This script proves which it is, by measuring the two things that separate
a real edge from a degenerate denominator:

  1. risk_in_atr  = |entry - sl| / atr1m     (the repo's own yardstick)
  2. the R histogram, and net with the top-N trades removed

If risk_in_atr is far below 0.25, the R multiples are arithmetic, not skill.
The fix is then NOT to discard the idea but to re-run it under a
denominator floor - which is what `min_risk_atr` does.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u scalp_1m_autopsy.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_1m_scalp_autopsy.json"

# The repo's stated floor: "any stop closer than ~0.25 x ATR is noise"
RISK_FLOOR_ATR = 0.25
MIN_BARS = 10


def _flow(candles):
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=float(c["open"]),
                       high=float(c["high"]), low=float(c["low"]),
                       close=float(c["close"])) for c in candles]


def diagnose(trades, atr_by_ts, label):
    """risk_in_atr distribution + where the R actually comes from."""
    n = len(trades)
    if n == 0:
        return {"n": 0}
    rs = [float(t["r_multiple"]) for t in trades]
    ratios = []
    for t in trades:
        a = atr_by_ts.get(int(t["entry_ts"]), 0.0)
        rk = abs(float(t["entry_price"]) - float(t["sl"]))
        ratios.append(rk / a if a > 0 else float("nan"))
    good = [x for x in ratios if x == x]
    srt = sorted(rs, reverse=True)
    out = {
        "n": n,
        "net": round(sum(rs), 1),
        "median_r": round(sorted(rs)[n // 2], 3),
        "max_r": round(max(rs), 1),
        "risk_in_atr_median": round(sorted(good)[len(good) // 2], 4) if good else None,
        "risk_in_atr_min": round(min(good), 4) if good else None,
        "risk_in_atr_max": round(max(good), 3) if good else None,
        "below_floor_0.25atr": sum(1 for x in good if x < RISK_FLOOR_ATR),
        "pct_below_floor": (round(100.0 * sum(1 for x in good if x < RISK_FLOOR_ATR)
                                   / len(good), 1) if good else None),
        "net_ex_best1": round(sum(srt[1:]), 1),
        "net_ex_best3": round(sum(srt[3:]), 1),
        "net_ex_best5": round(sum(srt[5:]), 1),
    }
    print(f"\n  {label}")
    print(f"    n={n}  net={out['net']:+.1f}R  median_r={out['median_r']}  "
          f"max_r={out['max_r']}")
    print(f"    risk/ATR: median {out['risk_in_atr_median']}  "
          f"min {out['risk_in_atr_min']}  max {out['risk_in_atr_max']}")
    print(f"    below the {RISK_FLOOR_ATR}x ATR floor: {out['below_floor_0.25atr']}"
          f"/{len(good)} ({out['pct_below_floor']}%)")
    print(f"    net ex-best1 {out['net_ex_best1']:+.1f}  "
          f"ex-best3 {out['net_ex_best3']:+.1f}  "
          f"ex-best5 {out['net_ex_best5']:+.1f}")
    return out


def main():
    import scalp_1m_engine as E
    E.install_b1_key()
    from src.btc.btc_routes import _compute_swings
    from exp_5m_confirm import load_book

    report = {"risk_floor_atr": RISK_FLOOR_ATR, "min_bars": MIN_BARS,
              "diagnosis": {}}

    for scope in ("is", "oos"):
        print(f"\n{'=' * 78}\n{scope.upper()}\n{'=' * 78}", flush=True)
        data, _ = load_book(scope)
        c1m = data["fine"]
        sw = _compute_swings(_flow(c1m), "continuous", min_bars=MIN_BARS)
        wins = E.htf_windows(data["c1h"], data["sw10"], fine_ltf=data["fine"])
        atr = E.atr_series(c1m, 14)
        atr_by_ts = {int(c["ts"]): a for c, a in zip(c1m, atr)}

        for kind in ("decisive", "flip"):
            st = {}
            tr = E.simulate_1m_scalp(c1m, sw, wins, entry_break=kind,
                                    target_r=2.0, sl_buf_atr=0.01,
                                    max_concurrent=1, stats=st)
            d = diagnose(tr, atr_by_ts, f"{scope} / {kind}")
            d["gate"] = st
            report["diagnosis"][f"{scope}/{kind}"] = d

    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

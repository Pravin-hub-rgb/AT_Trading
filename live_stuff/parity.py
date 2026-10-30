"""Parity oracle for the live bot vs backtest.

Compares the trade list produced by two runs of the vendored batch sim
(`simulate_htf_ltf_streak_halt`) and reports the first divergence. Used to
gate the incremental (O(1)) refactor: the incremental sim must reproduce
the batch sim's trade list byte-for-byte.

Usage (offline):
    from parity import run_parity, trade_list_diff
    diff = run_parity(candles_1h_a, swings_1h_a, candles_15m_a, swings_15m_a,
                      candles_1h_b, swings_1h_b, candles_15m_b, swings_15m_b,
                      v18_params)
    print(diff["summary"])
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _vendored.unified import simulate_htf_ltf_streak_halt


def _trade_key(t):
    return (int(t.get("entry_ts", 0)), str(t.get("dir", "")))


def trade_list_diff(trades_a, trades_b):
    """Return a dict describing the first divergence between two trade lists.

    Trades are matched by (entry_ts, dir). Compares count, then per-trade
    outcome/r_multiple/exit_ts/exit_price. Returns {"equal": bool, ...}.
    """
    a = {_trade_key(t): t for t in trades_a}
    b = {_trade_key(t): t for t in trades_b}

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    if only_a or only_b:
        return {
            "equal": False,
            "reason": "trade set mismatch",
            "only_in_a": only_a[:10],
            "only_in_b": only_b[:10],
            "count_a": len(trades_a),
            "count_b": len(trades_b),
        }

    fields = ("outcome", "r_multiple", "exit_ts", "exit_price", "entry_price", "sl", "target")
    diffs = []
    for k in sorted(a):
        ta, tb = a[k], b[k]
        for f in fields:
            va, vb = ta.get(f), tb.get(f)
            if va != vb:
                diffs.append((k, f, va, vb))
                if len(diffs) >= 20:
                    break
        if len(diffs) >= 20:
            break

    if diffs:
        return {
            "equal": False,
            "reason": "trade field mismatch",
            "diffs": diffs,
            "count_a": len(trades_a),
            "count_b": len(trades_b),
        }
    return {
        "equal": True,
        "reason": "identical",
        "count": len(trades_a),
    }


def run_parity(c1h_a, sw1h_a, c15_a, sw15_a,
               c1h_b, sw1h_b, c15_b, sw15_b,
               v18_params=None, fine_ltf=None):
    """Run batch sim on both input sets and return the trade-list diff."""
    params = dict(v18_params or {})
    if fine_ltf is None:
        fine_ltf = []
    try:
        ra = simulate_htf_ltf_streak_halt(c1h_a, sw1h_a, c15_a, sw15_a,
                                          fine_ltf=fine_ltf, **params)
        rb = simulate_htf_ltf_streak_halt(c1h_b, sw1h_b, c15_b, sw15_b,
                                          fine_ltf=fine_ltf, **params)
    except Exception as e:
        return {"equal": False, "reason": f"sim error: {e}",
                "count_a": 0, "count_b": 0}
    diff = trade_list_diff(ra.get("ltf_trades", []), rb.get("ltf_trades", []))
    diff["summary"] = ("PARITY OK: %d trades identical" % diff.get("count", 0)
                       if diff["equal"] else "PARITY FAIL: %s" % diff["reason"])
    return diff


if __name__ == "__main__":
    print("parity module loaded; run_parity() ready")
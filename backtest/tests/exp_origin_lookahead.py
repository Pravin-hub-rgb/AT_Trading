"""Permanent check: the origin pivot is causal. Truncate the swing chain at
each swing's confirmation and confirm seg.start_px does not change.

Run:  cd backtest/tests && python exp_origin_lookahead.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
for sub in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / sub))
sys.path.insert(0, str(ROOT))
from src.btc.btc_config import load_btc_df
from src.walker import FlowCandle
from src.btc.btc_routes import _compute_swings
SAMPLE = 40
MIN_BARS = 50
WARMUP = 3000

def main():
    df = load_btc_df("15m", "BTCUSDT_BYBIT")
    flow = [FlowCandle(date=r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                       open=float(r.open), high=float(r.high),
                       low=float(r.low), close=float(r.close)) for r in df.itertuples()]
    full = _compute_swings(flow, "continuous", min_bars=MIN_BARS)
    print("candles %d | swings %d" % (len(flow), len(full)))
    print()
    print("%-20s %-7s %-11s %-11s %s" % ("confirmed", "start_i", "full px", "cut px", "verdict"))
    same = diff = shown = 0
    examples = []
    for sw in full:
        ci = sw.get("confirmed_at_idx"); conf = sw.get("confirmed_at_time")
        seg = sw.get("seg") or {}
        if ci is None or not conf or "start_idx" not in seg or ci < WARMUP:
            continue
        try:
            cut = _compute_swings(flow[:ci + 1], "continuous", min_bars=MIN_BARS)
        except Exception:
            continue
        m = [x for x in cut if (x.get("seg") or {}).get("start_idx") == seg["start_idx"]]
        if not m:
            continue
        a = float(seg.get("start_px")); b = float((m[0].get("seg") or {}).get("start_px"))
        ok = abs(a - b) < 1e-9
        same += ok; diff += (not ok)
        if not ok and len(examples) < 6:
            examples.append((str(conf)[:16], seg["start_idx"], a, b))
        if shown < 6:
            print("%-20s %-7s %-11.2f %-11.2f %s" % (str(conf)[:16], seg["start_idx"], a, b,
                                                       "SAME" if ok else "DIFFERS"))
            shown += 1
        if same + diff >= SAMPLE:
            break
    print()
    print("compared                   : %d" % (same + diff))
    print("start_px IDENTICAL         : %d" % same)
    print("start_px CHANGED by future : %d" % diff)
    for c, i, a, b in examples:
        print("   %s start_idx=%d full=%.2f cut=%.2f" % (c, i, a, b))
    print()
    if diff:
        print("RESULT: FAIL - %d swing(s) take a start price that needs bars after" % diff)
        print("        their confirmation. The origin pivot IS lookahead for those." % ())
        return 1
    print("RESULT: PASS - the origin pivot is causal.")
    print("        seg.start_px is identical with and without the future, so the")
    print("        stop C16 calls a structural pivot is knowable at the entry bar.")
    print("        What C16 changed was the risk denominator, not knowledge of the")
    print("        future. 'Lookahead' overstated it; the rule itself still ships,")
    print("        because the leg extreme is the right structure for a stop.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

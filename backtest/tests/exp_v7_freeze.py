"""V7 - freeze the chain so a future engine edit cannot move a mark silently.

THE PROBLEM THIS EXISTS FOR
---------------------------
The per-kind B1 guard was wrong from day one and stayed wrong for the entire life of
the repo. Nothing caught it. Not because the engine was hard to check but because
there was no tripwire: no test asserted a single mark, so an engine edit could move
marks, change every book's P&L, and every harness would happily report the new
numbers as if they were findings.

The B1 bug was only found by hand, on the chart, by one person. That is not a
process.

TWO LEVELS, ON PURPOSE
----------------------
1. A small committed fixture. The existing backtest/tests/fixtures/candles.json
   (961 candles) with the exact marks the engine produces on it, asserted mark by
   mark - index, time, kind, direction and price. Fast, runs anywhere, and catches a
   whole class of arming and arming-order bugs.

2. A fingerprint of the FULL 129,715-candle chain: a sha256 over every one of the
   7993 marks. 64 bytes instead of a megabyte of JSON, and it catches drift
   anywhere in the history, not just in the first 961 candles.

Level 2 is deliberately opaque - it will not tell you WHICH mark moved. It exists to
make the question "did anything at all change?" answerable in one comparison. When
it fails, regenerate with --write and read the diff, which is the real signal.

USAGE
    python exp_v7_freeze.py --write     # (re)write both files
    python exp_v7_freeze.py             # verify only, exit 1 on any drift
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000
FIX = HERE / "fixtures"
CANDLES = FIX / "candles.json"
FROZEN = FIX / "frozen_marks.json"
CHAIN = FIX / "chain_fingerprint.json"

FIELDS = ("idx", "time", "kind", "dir", "px")


def marks_of(swings):
    return [{k: b[k] for k in FIELDS} for s in swings for b in s["breaks"]]


def fingerprint(marks):
    h = hashlib.sha256()
    for m in marks:
        h.update(("%s|%s|%s|%s|%s\n" % (m["idx"], m["time"], m["kind"],
                                         m["dir"], m["px"])).encode("utf-8"))
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="rewrite the fixtures")
    args = ap.parse_args()

    # ---- level 1: the small committed candle fixture -----------------------
    # candles.json is a dict of metadata plus a parallel-array "rows"
    blob = json.loads(CANDLES.read_text(encoding="utf-8"))
    candles = _rows(blob)
    flow = _to_flow(candles)
    sw_small = compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                                  max_swings=max(1, len(flow) // 2))
    small = marks_of(sw_small)

    # ---- level 2: the whole chain ------------------------------------------
    _c, flow_full = _load_window(TF, LIMIT, SYMBOL)[0]
    flow_full = list(flow_full)
    sw_full = compute_btc_swings(flow_full, opts={"minBars": MIN_BARS},
                                 max_swings=max(1, len(flow_full) // 2))
    full = marks_of(sw_full)
    fp = fingerprint(full)

    if args.write:
        FROZEN.write_text(json.dumps(
            {"candles": len(candles), "swings": len(sw_small), "marks": small},
            indent=1), encoding="utf-8")
        CHAIN.write_text(json.dumps(
            {"tf": TF, "symbol": SYMBOL, "min_bars": MIN_BARS,
             "candles": len(flow_full), "swings": len(sw_full),
             "marks": len(full), "sha256": fp}, indent=1), encoding="utf-8")
        print("wrote %s  (%d candles, %d marks)" % (FROZEN.name, len(candles), len(small)))
        print("wrote %s  (%d candles, %d marks, sha %s)"
              % (CHAIN.name, len(flow_full), len(full), fp[:16]))
        return 0

    # ---- verify ------------------------------------------------------------
    bad = 0
    if not FROZEN.exists() or not CHAIN.exists():
        print("MISSING fixtures - run with --write")
        return 1

    fz = json.loads(FROZEN.read_text(encoding="utf-8"))
    ch = json.loads(CHAIN.read_text(encoding="utf-8"))

    print("=" * 74)
    print("V7  frozen chain - has anything moved?")
    print("=" * 74)

    if fz["candles"] != len(candles):
        print("  FIXTURE candles %d != engine input %d" % (fz["candles"], len(candles)))
        bad += 1
    want, got = fz["marks"], small
    if want == got:
        print("  small fixture   %d marks on %d candles   IDENTICAL"
              % (len(got), len(candles)))
    else:
        print("  small fixture   %d marks expected, %d produced" % (len(want), len(got)))
        n = 0
        for i in range(max(len(want), len(got))):
            a = want[i] if i < len(want) else None
            b = got[i] if i < len(got) else None
            if a != b:
                print("     mark %d\n       was %s\n       now %s" % (i, a, b))
                n += 1
                if n >= 12:
                    print("     ... and more")
                    break
        bad += 1

    if ch["sha256"] == fp and ch["marks"] == len(full):
        print("  full chain      %d candles, %d marks   IDENTICAL  (sha %s)"
              % (len(flow_full), len(full), fp[:16]))
    else:
        print("  full chain      DRIFTED")
        print("     expected %d marks sha %s" % (ch["marks"], ch["sha256"][:16]))
        print("     produced %d marks sha %s" % (len(full), fp[:16]))
        bad += 1

    print()
    print("  VERDICT: %s" % ("no drift" if not bad else
                            "%d mismatch(es) - an engine edit moved marks" % bad))
    return 1 if bad else 0


def _rows(blob):
    """candles.json is metadata + parallel arrays; other shapes are plain lists."""
    if isinstance(blob, list):
        return blob
    for key in ("rows", "candles", "ohlc"):
        v = blob.get(key)
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return v
    if isinstance(blob.get("rows"), list):
        r = blob["rows"]
        if r and isinstance(r[0], list):
            return [dict(zip(("date", "open", "high", "low", "close"), x)) for x in r]
    raise SystemExit("candles.json: cannot find the candle rows")


def _to_flow(candles):
    from src.firstswing import FlowCandle
    out = []
    for c in candles:
        if isinstance(c, FlowCandle):
            out.append(c)
            continue
        d = c.get("date") or c.get("ts") or c.get("t")
        out.append(FlowCandle(date=d, open=float(c["open"]), high=float(c["high"]),
                              low=float(c["low"]), close=float(c["close"])))
    return out


if __name__ == "__main__":
    sys.exit(main())

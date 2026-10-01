"""Live-vs-backtest swing parity. Proves a claim instead of assuming it.

live_loop builds its swings with PersistentSwingEngine (src/live/persistent_swing.py),
which is fed bar by bar and persists state across restarts. The pin test builds
them with _compute_swings -> compute_btc_swings (src/btc/btc_routes.py), which is
fed a whole window at once.

PersistentSwingEngine's own docstring says "Parity with compute_btc_swings". That
was a claim. It passes timeCap="00:00" and stitches completed swings the way the
batch path does, which is the right shape, but nothing asserted that the two emit
the same swings.

Both are fed minBars 50 on 15m and 20 on 1h, which is what live_loop.py:94-95 and
engine/v18_params.py SWING both use. If the two disagree, the v18 pin of 352
trades / +146.55R is measuring a swing set that production does not produce, and
the live expectation is wrong.

Run: python -u exp_live_swing_parity.py     (about 2 min)
"""
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/Pravin/Desktop/main/AT_Trading")
for p in ("backend", "backtest", "backtest/sweeps", "backtest/engine"):
    sys.path.insert(0, str(ROOT / p))
# Append, never insert. backend/src contains a token.py, and putting that
# directory first shadows the stdlib "token" module that tokenize imports. Every
# harness in this repo appends it for exactly this reason.
sys.path.append(str(ROOT / "backend" / "src"))

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
from src.firstswing import SwingEngine
from engine.v18_params import SWING
from src.live.persistent_swing import PersistentSwingEngine

SYMBOL = "BTCUSDT_BYBIT"
# Fields worth comparing: structural identity of the swing, not exit bookkeeping.
KEYS = ("dir", "sdir", "seg_start", "start", "end", "start_time", "end_time",
        "seg_start_px", "end_px")


def live_swings(flow, min_bars):
    """Feed the whole window through the persistent engine, bar by bar."""
    eng = PersistentSwingEngine("probe", db=None, opts={"minBars": min_bars})
    out = []
    for i, c in enumerate(flow):
        s = eng.process_bar(c, i)
        if s:
            out.append(s)
    res = eng._build_result()
    return out, res


def compare(tf, min_bars):
    win, err = _load_window(tf, None, SYMBOL)
    candles, flow = win
    batch = compute_btc_swings(flow, opts={"minBars": min_bars},
                               max_swings=max(1, len(flow) // 2))
    streamed, built = live_swings(flow, min_bars)
    live = built.get("swings", built) if isinstance(built, dict) else built

    lines = [f"  {tf:4s} minBars={min_bars:<3d} batch={len(batch):<5d} "
             f"streamed={len(streamed):<5d} built={len(live) if live is not None else '?'}"]
    if len(batch) != len(streamed):
        lines.append(f"      COUNT MISMATCH  batch {len(batch)} vs streamed {len(streamed)}")
        return False, lines
    diff = 0
    for i, (a, b) in enumerate(zip(batch, streamed)):
        for k in KEYS:
            if k in a and k in b and a[k] != b[k]:
                diff += 1
                if diff <= 5:
                    lines.append(f"      swing {i} field {k}: batch={a[k]!r} streamed={b[k]!r}")
                break
    lines.append(f"      field diffs: {diff} across {len(batch)} swings")
    return diff == 0, lines


ok_all = True
for tf, mb in (("15m", SWING["min_bars_15m"]), ("1h", SWING["min_bars_1h"])):
    ok, lines = compare(tf, mb)
    ok_all &= ok
    for ln in lines:
        print(ln)
print()
print("PARITY: " + ("identical on both timeframes" if ok_all else "MISMATCH - do not trust the pin"))
sys.exit(0 if ok_all else 1)
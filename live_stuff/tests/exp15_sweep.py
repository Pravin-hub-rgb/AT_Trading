"""Exp 15 Phase 1 — sweep-and-reclaim entry qualifier metrics (read-only).

Hypothesis: a stop-hunt fingerprint BEFORE entry (a bar whose wick breaks the
recent low but closes back above it — swept and reclaimed) precedes real moves.
Long entries preceded by a sweep should outperform; mirror for shorts.

Definitions (causal — bars up to the entry bar only):
- prior_low(b)  = min(low[b-5:b])   (5-bar low BEFORE bar b)
- prior_high(b) = max(high[b-5:b])
- sweep bar (long):  low[b] < prior_low(b)  AND close[b] > prior_low(b)
- sweep bar (short): high[b] > prior_high(b) AND close[b] < prior_high(b)
- present at entry = a sweep bar exists within the last W bars before entry
Variants: W in {3, 6, 10}; also "recent+holding" variant (entry close still
above the swept level).

Outcome profile per bucket: n / lossR / winR / WR, plus half-splits and the
rough net delta of a veto (skip no-sweep entries).
"""
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt

_p = dict(get_v18_params(INSTRUMENT)); _p.update(V18_ENGINE)
BASE = {k: _p[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                           "atr_low_thresh", "atr_high_thresh", "mode",
                           "cooldown_bars", "max_consecutive_losses",
                           "htf_rr", "window_end"] if k in _p}
(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
trades = r["ltf_trades"] if isinstance(r, dict) else r
close = [float(c["close"]) for c in c15]
lo15 = [float(c["low"]) for c in c15]
hi15 = [float(c["high"]) for c in c15]
LB = 5  # lookback for the prior low/high

rows = []
for t in trades:
    i = int(t["entry_idx"])
    d = 1 if t["dir"] == "long" else -1
    # sweep bars in the last 12 bars before/at entry
    sweeps = []
    for b in range(max(LB, i - 11), i + 1):
        if d == 1:
            pl = min(lo15[b - LB:b])
            if lo15[b] < pl and close[b] > pl:
                sweeps.append(b)
        else:
            ph = max(hi15[b - LB:b])
            if hi15[b] > ph and close[b] < ph:
                sweeps.append(b)
    rows.append(dict(i=i, d=d, sweeps=sweeps, r=float(t["r_multiple"]),
                     yr=(t.get("entry_date") or "")[:4],
                     close=close[i], sl=float(t["sl"])))


def has_sweep(x, W):
    return any(b >= x["i"] - W + 1 for b in x["sweeps"])


def bucket(name, pred):
    sel = [x for x in rows if pred(x)]
    if not sel:
        print("  %-28s n=%4d" % (name, 0)); return (0, 0.0)
    losses = [x for x in sel if x["r"] < 0]
    wins = [x for x in sel if x["r"] > 0]
    lr = sum(x["r"] for x in losses); wr_ = sum(x["r"] for x in wins)
    wr = 100.0 * len(wins) / len(sel)
    h1 = sum(x["r"] for x in sel if x["yr"] in ("2023", "2024"))
    h2 = sum(x["r"] for x in sel if x["yr"] in ("2025", "2026"))
    print("  %-28s n=%4d  R=%+8.1f  WR=%4.1f%%  lossR=%+7.1f winR=%+7.1f  H1=%+7.1f H2=%+7.1f"
          % (name, len(sel), lr + wr_, wr, lr, wr_, h1, h2))
    return len(sel), lr + wr_


print("=== EXP 15 Phase 1: sweep-and-reclaim at entry (coarse) ===")
print("total trades: %d" % len(rows))
for W in (3, 6, 10):
    print("\n-- sweep within last %d bars --" % W)
    n_y, r_y = bucket("sweep=YES (W=%d)" % W, lambda x, W=W: has_sweep(x, W))
    n_n, r_n = bucket("sweep=NO", lambda x, W=W: not has_sweep(x, W))
    if n_n:
        print("  -> veto NO-sweep effect: %+.1fR removed" % r_n)

print("\n-- strict: sweep within 6 bars AND entry still holds the reclaim (long: close> swept level) --")
def holds(x):
    if not has_sweep(x, 6): return False
    if x["d"] == 1:
        b = max(x["sweeps"])
        pl = min(lo15[b - LB:b])
        return x["close"] > pl
    else:
        b = max(x["sweeps"])
        ph = max(hi15[b - LB:b])
        return x["close"] < ph
n_y, r_y = bucket("sweep+hold=YES", holds)
n_n, r_n = bucket("sweep+hold=NO", lambda x: not holds(x))
if n_n:
    print("  -> veto effect: %+.1fR removed" % r_n)

print("\n-- SL-loss book: how many losses had a sweep at entry --")
sl_losses = [x for x in rows if x["r"] <= -0.95 and x["r"] < 0]
for W in (6,):
    ny = sum(1 for x in sl_losses if has_sweep(x, W))
    print("  SL-direct losses with sweep(W=%d): %d/%d" % (W, ny, len(sl_losses)))
print("(exp15 done)")

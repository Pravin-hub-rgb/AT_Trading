"""Test v20 idea: HTF 'first come first claim' across sets (cross-set busy).

User's question (Jan 11 2023): B2 break came first on that swing, flip came later.
Chop said flip -> engine traded the flip window. User proposes: first break type
claims the HTF -- later opposite-kind break should be ignored while first is live.

Testable version: cross-set busy -- while ANY HTF trade (flip or b2) is open,
breaks of the OTHER kind may not open a window. Within-set busy already exists
in v7 (busy_until). This adds the cross-set rule, iterated to a fixed point.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
import src.btc.engines.v7_timecap as v7mod
import src.btc.engines.htf_ltf.v18_streak_halt as v18mod
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

ORIG = v7mod.simulate_btc_trades_v7

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)

KW = dict(sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0,
          skip_first=True, fine=fine, cap_days=16)

def busy_of(trades):
    return [(t["entry_idx"], t["exit_idx"]) for t in trades]

def run_gated(kind, other_busy):
    def gate(i):
        return not any(s <= i <= e for s, e in other_busy)
    return ORIG(c1h, sw1h, entry_break=kind, entry_gate=gate, **KW)

def stats(trades):
    tot = sum(float(t.get("r_multiple", t.get("r", 0))) for t in trades)
    years = {}
    for t in trades:
        y = t["entry_date"][:4]
        years[y] = years.get(y, 0.0) + float(t.get("r_multiple", t.get("r", 0)))
    dd = cur = 0.0
    for t in trades:
        cur += float(t.get("r_multiple", t.get("r", 0)))
        dd = min(dd, cur)
    return tot, dd, years

print("=== BASELINE: v18 as-is ===")
base = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)["ltf_trades"]
tot, dd, years = stats(base)
print(f"trades={len(base)}  netR={tot:+.1f}  maxDD={dd:.1f}")
for y in sorted(years): print(f"  {y}: {years[y]:+.1f}R")
jan11 = [t for t in base if t["entry_date"].startswith("2023-01-11")]
print(f"Jan 11 trades: {[(t['entry_date'], t['dir']) for t in jan11]}")

print()
print("=== VARIANT: cross-set busy (first come claims the HTF) ===")
# iterate to fixed point: flip blocked by b2 busy, b2 blocked by flip busy
flip_busy, b2_busy = [], []
for it in range(8):
    new_flip = run_gated("flip", b2_busy)
    new_b2 = run_gated("b2", busy_of(new_flip))
    nf, nb = busy_of(new_flip), busy_of(new_b2)
    if nf == flip_busy and nb == b2_busy:
        break
    flip_busy, b2_busy = nf, nb
print(f"converged after {it+1} iterations: flip windows={len(new_flip)}  b2 windows={len(new_b2)}  (baseline flip/b2 before halt: unfiltered)")

# Check Jan 11 specifically
print("Flip windows Jan 10-13:", [(t['entry_date'], t['exit_date'], t['dir']) for t in new_flip if "2023-01-10" <= t["entry_date"][:10] <= "2023-01-13"])
print("B2 windows Jan 10-13:", [(t['entry_date'], t['exit_date'], t['dir']) for t in new_b2 if "2023-01-10" <= t["entry_date"][:10] <= "2023-01-13"])

# patch v7 inside v18's import path and run full v18
def patched(candles, swings, **kw):
    kind = kw.get("entry_break", "flip")
    if kind == "flip":
        return new_flip
    if kind == "b2":
        return new_b2
    return ORIG(candles, swings, **kw)

v7mod.simulate_btc_trades_v7 = patched
try:
    var = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
        cooldown_bars=20, max_consecutive_losses=5)["ltf_trades"]
finally:
    v7mod.simulate_btc_trades_v7 = ORIG

tot2, dd2, years2 = stats(var)
print(f"trades={len(var)}  netR={tot2:+.1f}  maxDD={dd2:.1f}")
for y in sorted(years2): print(f"  {y}: {years2[y]:+.1f}R")
jan11v = [t for t in var if t["entry_date"].startswith("2023-01-11")]
print(f"Jan 11 trades: {[(t['entry_date'], t['dir']) for t in jan11v]}")

print()
print("=== DELTA ===")
print(f"baseline: {len(base)}t {tot:+.1f}R DD {dd:.1f}")
print(f"variant : {len(var)}t {tot2:+.1f}R DD {dd2:.1f}   delta={tot2-tot:+.1f}R")
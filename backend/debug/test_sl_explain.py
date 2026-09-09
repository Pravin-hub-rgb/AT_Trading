"""Explain trade #1's SL system: the two lines the user sees on the chart.

Expected facts to verify:
- entry = short @ 15m close of Jan 6 16:30 B2-down bar (16749.05)
- sl_pivot = swing-8 start extreme = 16991.87 (Jan 5 00:30 high)
- initial SL = sl_pivot + 0.25*ATR14  (~16996.6-16997.5)
- outcome "trail": MB50 swing-pivot trail ratcheted SL below initial before hit
- exit 16991.87 -> -0.981R
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle


def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low),
                        "close": float(row.close)})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)
res = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)
t = res["ltf_trades"][0]

print("=== TRADE #1 full dict ===")
for k, v in t.items():
    print(f"  {k}: {v}")

ed = str(t.get("entry_date") or t.get("entry_ts"))
idx = next((i for i, c in enumerate(c15) if c["date"].startswith(ed[:16])), None)
print(f"\nentry bar: {c15[idx]['date']}  close/entry={c15[idx]['close']}")

# ATR(14) at entry bar (same rolling mean as engine)
trl = []
for i, c in enumerate(c15):
    pc = float(c15[i - 1]["close"]) if i > 0 else None
    trr = float(c["high"]) - float(c["low"])
    if pc is not None:
        trr = max(trr, abs(float(c["high"]) - pc), abs(float(c["low"]) - pc))
    trl.append(trr)
lo = max(0, idx - 13)
atr = sum(trl[lo:idx + 1]) / (idx - lo + 1)
print(f"ATR(14) at entry = {atr:.2f}   ->   0.25*ATR = {0.25*atr:.2f}")
print(f"initial SL (trade dict 'sl') = {t['sl']:.4f}")
print(f"implied sl_pivot = {t['sl'] - 0.25*atr:.2f}   (swing-8 start extreme = 16991.87)")
print(f"risk = {abs(t['entry_price'] - t['sl']):.2f}")
print(f"exit = {t['exit_price']}   r_multiple = {t['r_multiple']:.4f}")
print(f"loss in $ = {t['exit_price'] - t['entry_price']:.2f}  (short: exit above entry)")

# Trail events (MB50 swing-start pivots, same-direction) that could ratchet SL
from src.btc.btc_engine import _trail_events
events = _trail_events(sw15, -1)  # short
print("\n=== MB50 trail events (down-swing start highs) at/after entry ===")
for ci, px in events:
    if ci >= idx - 1 and ci <= idx + 200:
        print(f"  confirmed@ {c15[min(ci+1, len(c15)-1)]['date']}  pivot {px:.2f}"
              f"  {'<-- ratchets SL down' if px < t['sl'] else ''}")

# exit: 1m-precise (exit_date carries 1m timestamp) — find the 1m bar
xd = str(t.get("exit_date") or t.get("exit_ts"))
fbar = next((c for c in fine if str(c.get("date", "")) == xd or str(c.get("ts")) == xd), None)
if fbar is None:
    xts = int(t["exit_ts"])
    fbar = next((c for c in fine if int(c["ts"]) == xts), None)
if fbar is not None:
    print(f"\nexit 1m bar: ts={fbar['ts']}  O={fbar['open']} H={fbar['high']} L={fbar['low']} C={fbar['close']}")
    print(f"fill rule (short): exit = max(sl_cur, 1m open) -> sl_cur was {t['exit_price']:.2f}")
else:
    print(f"\nexit 1m bar not found for {xd} (fine window may not cover it)")


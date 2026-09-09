"""Explain Jan 14-15 2023: why the 22:45 flip long entered but the Jan 15
19:00 flip (and the 14:00 sell flip, and the B2 before it) did not.

Dumps for Jan 14 00:00 -> Jan 16 23:59:
1. every LTF decisive signal (kind, dir, swing_no) with chop and the filter
   verdict (which HTF interval set, inside window?, direction match, ext stop)
2. the HTF flip/b2 intervals covering the window
3. the actual LTF trades taken with busy/cooldown/halt state
"""
import sys
import bisect as bs
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.btc.btc_engine import _collect_signals
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
fine = _load_fine_1m(t0, t1) if False else None
res = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=None,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)

T0, T1 = "2023-01-14", "2023-01-17"

print("=== HTF 1h intervals (flip set) overlapping Jan 14-17 ===")
for s, e, d, pe, psl in res["intervals"]:
    sd = {1: "long", -1: "short"}[d]
    import datetime
    se = datetime.datetime.utcfromtimestamp(s).strftime("%Y-%m-%d %H:%M")
    ee = datetime.datetime.utcfromtimestamp(e).strftime("%Y-%m-%d %H:%M")
    if ee >= T0 and se <= T1:
        print(f"  {se} -> {ee}  {sd}  entry={pe:.2f} sl={psl:.2f}")

print("\n=== LTF trades taken in Jan 14-17 ===")
for t in res["ltf_trades"]:
    if T0 <= str(t["entry_date"])[:10] < T1:
        print(f"  #{t['trade_no']} {t['dir']:<5} {t['break_kind']:<4} entry {t['entry_date']} @ {t['entry_price']:.2f}"
              f"  exit {t['exit_date']} @ {t['exit_price']:.2f}  {t['outcome']}  {t['r_multiple']:+.3f}R")

# --- replicate the filter pipeline with reasons ---
from src.btc.engines.htf_ltf.v18_streak_halt import _chop_series_1h, _atr_pct_15m
chop = _chop_series_1h(c1h, lb=14)
atr_pct = _atr_pct_15m(c15)
ts15 = [int(c["ts"]) for c in c15]
ts1h = [int(c["ts"]) for c in c1h]
chop_per_ltf = [50.0] * len(c15)
for i, ts in enumerate(ts15):
    j = bs.bisect_right(ts1h, ts) - 1
    if j >= 0 and j < len(chop):
        chop_per_ltf[i] = chop[max(0, j)]

iv_flip = res["intervals"]
# rebuild the b2 HTF interval set exactly as v18 does internally
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
htf_b2 = simulate_btc_trades_v7(c1h, sw1h, entry_break="b2", sl_mode="swing",
    rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=None, cap_days=16)
iv_b2 = [(int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"] == "long" else -1,
          float(t["entry_price"]), float(t["sl"])) for t in htf_b2 if t["outcome"] != "open"]
iv_b2.sort(key=lambda x: x[0])
starts_flip = [s for s, _, _, _, _ in iv_flip]
starts_b2 = [s for s, _, _, _, _ in iv_b2]

sigs = _collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)

# Raw 15m swing marks around Jan 15 (before _collect_signals filtering)
print("\n=== RAW 15m swings & break marks Jan 14 12:00 -> Jan 16 12:00 ===")
for s in sw15:
    si = s["seg"]["start_idx"]
    ei = s["seg"]["end_idx"]
    if si >= len(c15) or ei >= len(c15):
        continue
    sd = c15[si]["date"]
    ed = c15[ei]["date"]
    if not (ed >= "2023-01-14 12:00" and sd <= "2023-01-16 12:00"):
        continue
    print(f"  sw{s['swing_index']} dir={s['dir']} declared={s.get('declared', s.get('is_declared','?'))} "
          f"seg {sd}({s['seg']['start_px']:.2f}) -> {ed}({s['seg']['end_px']:.2f}) conf@{s.get('confirmed_at_time','?')}")
    for b in s["breaks"]:
        bi = b["idx"]
        bd = c15[bi]["date"] if bi < len(c15) else "?"
        print(f"     {b['kind']:<4} {b['dir']:<4} @ {bd}  px={b['px']:.2f}")

print("\n=== ALL LTF signals Jan 14-17 with filter verdict (walk-state aware) ===")
# replicate walk state chronologically
busy_until = -1
last_loss_bar = -999999
consec = 0
halted = False
trades_taken = []
real_by_entry = {str(t["entry_date"]): t for t in res["ltf_trades"]}
for sig in sigs:
    bar = sig["bar"]
    d = str(c15[bar]["date"])
    if not (T0 <= d[:10] < T1):
        continue
    ch = chop_per_ltf[bar]
    atrp = atr_pct[bar]
    use = "b2" if ch > 61.8 else "flip"
    iv, starts = (iv_b2, starts_b2) if use == "b2" else (iv_flip, starts_flip)
    sdir = 1 if sig["dir"] == "up" else -1
    reasons = []
    idx = bs.bisect_right(starts, ts15[bar]) - 1
    if idx < 0:
        reasons.append("no HTF window yet")
    else:
        s, e, dd, pe, psl = iv[idx]
        sd = {1: "long", -1: "short"}[dd]
        if not (s < ts15[bar] <= e):
            wsd = datetime.datetime.utcfromtimestamp(s).strftime("%m-%d %H:%M")
            wed = datetime.datetime.utcfromtimestamp(e).strftime("%m-%d %H:%M")
            reasons.append(f"outside {sd} window ({wsd}->{wed})")
        elif sdir != dd:
            reasons.append(f"dir mismatch (signal {sig['dir']}, window {sd})")
        else:
            hrisk = abs(pe - psl)
            if hrisk > 0:
                ext = (float(c15[bar]["close"]) - pe) * sdir / hrisk
                if ext > 1.5:
                    reasons.append(f"ext stop: {ext:.2f}R > 1.5")
    # walk state
    if bar <= busy_until:
        reasons.append(f"busy (trade open until bar {busy_until})")
    elif bar - last_loss_bar < 20:
        reasons.append(f"cooldown ({bar - last_loss_bar}/20 bars after loss)")
    elif halted:
        reasons.append("halted")
    if not reasons:
        rt = real_by_entry.get(d)
        if rt is not None:
            reasons_out = f"TRADE  -> engine #{rt['trade_no']} {rt['dir']} {rt['break_kind']} exit {rt['exit_date']} {rt['outcome']} {rt['r_multiple']:+.3f}R"
            busy_until = int(rt["exit_idx"])
            if rt["r_multiple"] < 0:
                last_loss_bar = int(rt["exit_idx"])
            if rt["r_multiple"] <= 0:
                consec += 1
                if consec >= 5:
                    halted = True
            else:
                consec = 0
                halted = False
        else:
            reasons_out = "TRADE (candidate — but engine has no trade here!)"
        trades_taken.append((d, sig["kind"], sig["dir"]))
        print(f"  {d}  {sig['kind']:<4} {sig['dir']:<5} sw{sig.get('swing_no','?'):>3}  chop={ch:.1f}  use={use:<4}  {reasons_out}")
    else:
        print(f"  {d}  {sig['kind']:<4} {sig['dir']:<5} sw{sig.get('swing_no','?'):>3}  chop={ch:.1f}  use={use:<4}  skip: {'; '.join(reasons)}")

print("\n(real engine trades in window: #3 FLIP long Jan 14 22:45 -> SL Jan 15 08:45 -1R;"
      " #4 B2 long Jan 16 07:45 -> trail Jan 16 20:30 -0.952R)")


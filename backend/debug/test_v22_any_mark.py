"""v22 experiment: ANY tradeable mark can be a signal (remove one-swing-one-trade).

Q1 answered here too: cooldown blocks signals that FIRE during it; swings whose
first tradeable mark fires after cooldown ends are still fully tradable.

A/B vs baseline v18 (330t +331.1R). Same engine, same SL/trail/cooldown/halt;
only the signal stream changes: every B2/FLIP mark is a candidate (still gated
by HTF window, direction, ext-stop 1.5R, busy, cooldown, halt).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf import v18_streak_halt as v18mod
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

ARGS = dict(fine_ltf=fine, sl_buf_atr=0.25, ext_stop_r=1.5,
            mode="b2_vs_flip_chop", cooldown_bars=20, max_consecutive_losses=5)


def collect_all_marks(swings, entry_break="decisive", skip_first=True,
                      selection="stream", candles=None):
    """Copy of _collect_signals WITHOUT the one-swing-one-trade early break."""
    tradeable = ("B2", "FLIP")
    out = []
    seen = set()
    for si, s in enumerate(swings):
        if skip_first and int(s.get("swing_index", 0)) < 1:
            continue
        brks = s.get("breaks") or []
        if not brks:
            continue
        sdir = 1 if s.get("dir") == "up" else -1
        seg_start = float(s["seg"]["start_px"])
        prev_end = float(swings[si - 1]["seg"]["end_px"]) if si > 0 else None
        start_idx = int(s["seg"]["start_idx"])
        prev_end_idx = int(swings[si - 1]["seg"]["end_idx"]) if si > 0 else -1
        for b in brks:
            if b["kind"] not in tradeable:
                continue
            bdir = 1 if b["dir"] == "up" else -1
            bidx = int(b["idx"])
            if bdir == sdir:
                if bidx < start_idx:
                    if candles is None or si == 0 or prev_end_idx < 0:
                        continue
                    lo_seg = [float(c["low"]) for c in candles[prev_end_idx + 1: bidx + 1]]
                    hi_seg = [float(c["high"]) for c in candles[prev_end_idx + 1: bidx + 1]]
                    if not lo_seg or not hi_seg:
                        continue
                    entry_px = float(candles[bidx]["close"])
                    if bdir == 1:
                        sl = min(lo_seg)
                        if sl >= entry_px:
                            continue
                    else:
                        sl = max(hi_seg)
                        if sl <= entry_px:
                            continue
                else:
                    sl = seg_start
            else:
                if prev_end is None or bidx < prev_end_idx:
                    continue
                sl = prev_end
                if candles is not None and prev_end_idx >= 0:
                    try:
                        entry_px_chk = float(candles[bidx]["close"])
                        lo_seg = [float(c["low"]) for c in candles[prev_end_idx + 1: bidx + 1]]
                        hi_seg = [float(c["high"]) for c in candles[prev_end_idx + 1: bidx + 1]]
                        if lo_seg and hi_seg:
                            if bdir == 1:
                                cand = min(lo_seg)
                                if cand < entry_px_chk:
                                    sl = cand
                            else:
                                cand = max(hi_seg)
                                if cand > entry_px_chk:
                                    sl = cand
                    except Exception:
                        pass
            key = (bidx, b["kind"], b["dir"], round(float(b["px"]), 6))
            if key in seen:
                continue
            seen.add(key)
            out.append({"bar": int(b["idx"]), "dir": bdir, "swing_start_px": sl,
                        "swing_no": int(s.get("swing_index", si)), "kind": b["kind"]})
    out.sort(key=lambda x: x["bar"])
    return out


def stats(trades, label):
    rs = [t["r_multiple"] for t in trades]
    net = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    yearly = {}
    for t in trades:
        y = str(t["entry_date"])[:4]
        yearly[y] = yearly.get(y, 0.0) + t["r_multiple"]
    ys = "  ".join(f"{y}:{v:+.1f}" for y, v in sorted(yearly.items()))
    print(f"{label}: {len(trades)}t  net {net:+.1f}R  PF {pf:.2f}  maxDD {dd:.1f}R  "
          f"winrate {100*len(wins)/len(rs):.1f}%")
    print(f"    yearly: {ys}")
    return net, len(trades)


print("=== BASELINE v18 (one-swing-one-trade) ===")
base = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, **ARGS)
b_net, b_n = stats(base["ltf_trades"], "baseline")

print("\n=== VARIANT v22 (any mark can trade) ===")
from src.btc import btc_engine as _be
orig = _be._collect_signals
_be._collect_signals = collect_all_marks
try:
    var = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, **ARGS)
finally:
    v18mod._collect_signals = orig
v_net, v_n = stats(var["ltf_trades"], "variant")

print(f"\nDelta: {v_n - b_n:+d} trades, {v_net - b_net:+.1f}R")

print("\nVariant trades Jan 12-18 (to trace the Jan 14-16 cascade):")
for t in var["ltf_trades"]:
    if "2023-01-12" <= str(t["entry_date"])[:10] <= "2023-01-18":
        print(f"  #{t['trade_no']} {t['dir']:<5} {t['break_kind']:<4} sw{t['swing_no']:>3} entry {t['entry_date']} "
              f"@ {t['entry_price']:.2f}  exit {t['exit_date']} @ {t['exit_price']:.2f}  "
              f"{t['outcome']}  {t['r_multiple']:+.3f}R")
print("\nfirst 5 variant trades overall:")
for t in var["ltf_trades"][:5]:
    print(f"  #{t['trade_no']} {t['dir']:<5} {t['break_kind']:<4} entry {t['entry_date']}  r={t['r_multiple']:+.3f}")

# halt verification: variant trades #1-#4 outcomes + which signals vanished
print("\nvariant trade #1-#6 r_multiples:",
      [t["r_multiple"] for t in var["ltf_trades"][:6]])

# which baseline signals vanished in variant (halt/blocking cascade)
b_ents = {str(t["entry_date"]) for t in base["ltf_trades"]}
v_ents = {str(t["entry_date"]) for t in var["ltf_trades"]}
gone = sorted(b_ents - v_ents)
new = sorted(v_ents - b_ents)
print(f"\nbaseline entries missing in variant: {len(gone)}  (first 6: {gone[:6]})")
print(f"new entries only in variant: {len(new)}")
extra_rs = [t["r_multiple"] for t in var["ltf_trades"] if str(t["entry_date"]) in set(new)]
if extra_rs:
    import statistics as st
    m = sum(extra_rs) / len(extra_rs)
    sd = st.pstdev(extra_rs) or 1e-9
    t_stat = m / (sd / (len(extra_rs) ** 0.5))
    print(f"new-only trades: {len(extra_rs)}  avg {m:+.3f}R  t={t_stat:.2f}")





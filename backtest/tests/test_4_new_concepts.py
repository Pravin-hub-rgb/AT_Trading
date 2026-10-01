"""4 NEW CONCEPTS — implemented as standalone tests on top of wage10+wknd baseline.
Each concept is independent. Tests IS + OOS."""
import sys, time, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd
from test_experiments_craze import build_module, _compute_swings
from engine.v18_params import SWING
from replay_harness import INSTRUMENT
from src.walker import FlowCandle
from run_experiment import get_data

IST_OFFSET_SEC = 5 * 3600 + 30 * 60
UNSEEN_DIR = ROOT / "data" / "unseen" / "bybit"

BASELINE = {"mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
            "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 0,
            "max_consecutive_losses": 3, "ext_stop_r": 3.0,
            "exp_partial_r": 0.0, "exp_wage_h": 10, "exp_skip_weekend": 1,
            "window_end": "exit"}


def load_unseen(tf):
    path = UNSEEN_DIR / f"BTCUSDT_{tf}.csv"
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": float(getattr(row, "volume", 0.0) or 0.0)})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def load_fine_1m(ts_start, ts_end):
    path = UNSEEN_DIR / "BTCUSDT_1m.csv"
    if not path.exists(): return []
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    df = df[(df["ts"] >= ts_start) & (df["ts"] <= ts_end)]
    return [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
             "open": float(r.open), "high": float(r.high),
             "low": float(r.low), "close": float(r.close)} for r in df.itertuples()]


def analyze(trades, label=""):
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs); net = sum(rs)
    wins = sum(1 for r in rs if r > 0); wr = wins / max(n, 1) * 100
    peak = 0.0; cum = 0.0; dd = 0.0
    for r in rs: cum += r; peak = max(peak, cum); dd = max(dd, peak - cum)
    ndd = abs(net / dd) if dd > 0 else 0
    yearly = defaultdict(float)
    for t in trades:
        y = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        yearly[y] += float(t["r_multiple"])
    monthly = defaultdict(float)
    for t in trades:
        m = (t.get("exit_date") or t.get("entry_date") or "")[:7]
        monthly[m] += float(t["r_multiple"])
    green = sum(1 for v in monthly.values() if v >= 0)
    return {"n": n, "net": net, "wr": wr, "dd": dd, "ndd": ndd,
            "yearly": dict(yearly), "green": green, "months": len(monthly)}


def run_baseline(sim, c1h, sw10, c15, sw15, fine):
    r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **BASELINE)
    return r["ltf_trades"] if isinstance(r, dict) else r


def main():
    print("=" * 100)
    print("  4 NEW CONCEPTS — IS + OOS")
    print("=" * 100)

    is_data = get_data()
    sim = build_module()

    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    fine_oos = load_fine_1m(c1ho[0]["ts"], c1ho[-1]["ts"])
    sw10_oos = _compute_swings(f1ho, "continuous", min_bars=10)
    sw15_oos = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])

    # =========================================================================
    # CONCEPT 3: ROOM FILTER (simplest, from autopsy)
    # room < X => skip. Room = distance to 24h opposing extreme in risk units.
    # We'll add this as exp_room_min parameter to the patcher.
    # =========================================================================
    print(f"\n{'='*100}")
    print(f"  CONCEPT 3: ROOM FILTER — skip entries with no room to 24h opposing extreme")
    print(f"{'='*100}")

    # Room is computed from 15m candles: max(high[i-96:i]) for LONG, min(low[i-96:i]) for SHORT
    # We can't modify the engine directly here, so we'll post-filter:
    # Run baseline, get trades with entry bar index, then compute room for each
    # and filter out room < threshold

    def compute_room_for_trades(trades, c15):
        """Recompute room for each trade using 15m candles."""
        # Build price arrays
        hi15 = [float(c["high"]) for c in c15]
        lo15 = [float(c["low"]) for c in c15]
        ts15 = [int(c["ts"]) for c in c15]

        enriched = []
        for t in trades:
            entry_date = t.get("entry_date", "")[:19]
            entry = float(t["entry_price"])
            sl = float(t["sl"])
            risk = abs(entry - sl)
            d = 1 if t["dir"] == "long" else -1

            # Find entry bar index in c15
            bar_idx = -1
            for j, c in enumerate(c15):
                if c["date"][:19] == entry_date:
                    bar_idx = j
                    break

            if bar_idx < 0 or risk <= 0:
                enriched.append({**t, "room": 0.0, "chase": 0, "slw": 0.0})
                continue

            # Room: 24h opposing extreme (96 bars of 15m)
            if d == 1:
                ext = max(hi15[max(0, bar_idx - 96):bar_idx + 1])
                room = (ext - entry) / risk
            else:
                ext = min(lo15[max(0, bar_idx - 96):bar_idx + 1])
                room = (entry - ext) / risk

            # Chase: consecutive same-dir bars leading into entry
            chase = 0
            o15 = [float(c["open"]) for c in c15]
            c15c = [float(c["close"]) for c in c15]
            for j in range(bar_idx, 0, -1):
                if d == 1 and c15c[j] > o15[j]: chase += 1
                elif d == -1 and c15c[j] < o15[j]: chase += 1
                else: break

            # SL width
            atr_val = max(hi15[max(0, bar_idx-13):bar_idx+1]) - min(lo15[max(0, bar_idx-13):bar_idx+1])
            slw = risk / atr_val if atr_val > 0 else 0.0

            enriched.append({**t, "room": room, "chase": chase, "slw": slw})
        return enriched

    # Run baseline IS
    trades_is = run_baseline(sim, is_data["c1h"], is_data["sw10"], is_data["c15"], is_data["sw15"], is_data["fine"])
    enriched_is = compute_room_for_trades(trades_is, is_data["c15"])

    # Run baseline OOS
    trades_oos = run_baseline(sim, c1ho, sw10_oos, c15o, sw15_oos, fine_oos)
    enriched_oos = compute_room_for_trades(trades_oos, c15o)

    base_is = analyze(trades_is)
    base_oos = analyze(trades_oos)

    print(f"\n  Baseline (wage10+wknd):  IS {base_is['n']}t {base_is['net']:+.1f}R  OOS {base_oos['n']}t {base_oos['net']:+.1f}R")

    # Room thresholds
    for thresh in [0.5, 1.0, 1.5, 2.0]:
        filtered_is = [t for t in enriched_is if t["room"] >= thresh]
        filtered_oos = [t for t in enriched_oos if t["room"] >= thresh]
        ais = analyze(filtered_is)
        aoos = analyze(filtered_oos)
        dnet_is = ais["net"] - base_is["net"]
        dnet_oos = aoos["net"] - base_oos["net"]
        print(f"  room>={thresh:.1f}: IS {ais['n']:>3}t {ais['net']:>+7.1f}R (d{dnet_is:>+.1f})  OOS {aoos['n']:>3}t {aoos['net']:>+7.1f}R (d{dnet_oos:>+.1f})  21={aoos['yearly'].get('2021',0):>+5.1f} 22={aoos['yearly'].get('2022',0):>+5.1f}")

    # Chase thresholds
    print(f"\n  Chase filter:")
    for thresh in [3, 4, 5]:
        filtered_is = [t for t in enriched_is if t["chase"] < thresh]
        filtered_oos = [t for t in enriched_oos if t["chase"] < thresh]
        ais = analyze(filtered_is)
        aoos = analyze(filtered_oos)
        dnet_oos = aoos["net"] - base_oos["net"]
        print(f"  chase<{thresh}: IS {ais['n']:>3}t {ais['net']:>+7.1f}R  OOS {aoos['n']:>3}t {aoos['net']:>+7.1f}R (d{dnet_oos:>+.1f})  21={aoos['yearly'].get('2021',0):>+5.1f} 22={aoos['yearly'].get('2022',0):>+5.1f}")

    # Combined: room + chase
    print(f"\n  Combined room + chase:")
    for rm, ch in [(1.0, 3), (1.5, 3), (1.0, 4), (1.5, 4), (2.0, 3)]:
        filtered_is = [t for t in enriched_is if t["room"] >= rm and t["chase"] < ch]
        filtered_oos = [t for t in enriched_oos if t["room"] >= rm and t["chase"] < ch]
        ais = analyze(filtered_is)
        aoos = analyze(filtered_oos)
        dnet_oos = aoos["net"] - base_oos["net"]
        print(f"  room>={rm} & chase<{ch}: IS {ais['n']:>3}t {ais['net']:>+7.1f}R  OOS {aoos['n']:>3}t {aoos['net']:>+7.1f}R (d{dnet_oos:>+.1f})  21={aoos['yearly'].get('2021',0):>+5.1f} 22={aoos['yearly'].get('2022',0):>+5.1f}")

    # Room distribution for wins vs losses
    print(f"\n  Room distribution (wins vs losses):")
    wins = [t for t in enriched_oos if float(t["r_multiple"]) > 0]
    losses = [t for t in enriched_oos if float(t["r_multiple"]) <= 0]
    if wins:
        avg_room_w = sum(t["room"] for t in wins) / len(wins)
        print(f"    Wins:  avg room = {avg_room_w:.2f}")
    if losses:
        avg_room_l = sum(t["room"] for t in losses) / len(losses)
        print(f"    Losses: avg room = {avg_room_l:.2f}")

    # =========================================================================
    # CONCEPT 1: LEG QUALITY SCORE
    # Uses swing metadata: magnitude relative to ATR, break density
    # =========================================================================
    print(f"\n{'='*100}")
    print(f"  CONCEPT 1: LEG QUALITY SCORE — swing magnitude, break density")
    print(f"{'='*100}")

    def compute_leg_quality(trades, c15, sw15):
        """Score leg quality from swing metadata."""
        atr15 = [0.0] * len(c15)
        for i in range(len(c15)):
            start = max(0, i - 13)
            h = max(float(c15[j]["high"]) for j in range(start, i + 1))
            l = min(float(c15[j]["low"]) for j in range(start, i + 1))
            atr15[i] = h - l

        enriched = []
        for t in trades:
            entry_date = t.get("entry_date", "")[:19]
            bar_idx = -1
            for j, c in enumerate(c15):
                if c["date"][:19] == entry_date:
                    bar_idx = j
                    break

            if bar_idx < 0:
                enriched.append({**t, "leg_quality": 0.5})
                continue

            # Find which swing this trade belongs to
            d = 1 if t["dir"] == "long" else -1
            swing_mag = 0
            swing_bars = 1
            n_breaks = 0
            for sw in reversed(sw15):
                seg = sw.get("seg", {})
                si = int(seg.get("start_idx", -1))
                ei = int(seg.get("end_idx", -1))
                if si <= bar_idx <= ei and ei > si:
                    spx = float(seg.get("start_px", 0))
                    epx = float(seg.get("end_px", 0))
                    swing_mag = abs(epx - spx)
                    swing_bars = ei - si
                    n_breaks = len(sw.get("breaks", []))
                    break

            # Quality components
            atr_at_entry = atr15[bar_idx] if bar_idx < len(atrp15 := [0.0]) else 1.0
            # Simple ATR recalc
            start = max(0, bar_idx - 13)
            h = max(float(c15[j]["high"]) for j in range(start, bar_idx + 1))
            l = min(float(c15[j]["low"]) for j in range(start, bar_idx + 1))
            atr_now = h - l if h > l else 1.0

            mag_ratio = swing_mag / atr_now if atr_now > 0 else 0  # swing size in ATR units
            speed = swing_bars  # lower = faster = stronger
            break_density = n_breaks / max(swing_bars, 1)  # breaks per bar

            # Score: higher mag, fewer bars, more breaks = higher quality
            quality = 0.0
            if mag_ratio > 3: quality += 0.4
            elif mag_ratio > 2: quality += 0.3
            elif mag_ratio > 1: quality += 0.2
            else: quality += 0.1

            if speed < 20: quality += 0.3
            elif speed < 40: quality += 0.2
            elif speed < 80: quality += 0.1

            if break_density > 0.1: quality += 0.3
            elif break_density > 0.05: quality += 0.2
            elif break_density > 0.02: quality += 0.1

            enriched.append({**t, "leg_quality": quality, "mag_ratio": mag_ratio,
                            "speed": speed, "break_density": break_density})
        return enriched

    eq_is = compute_leg_quality(trades_is, is_data["c15"], is_data["sw15"])
    eq_oos = compute_leg_quality(trades_oos, c15o, sw15_oos)

    for qmin in [0.0, 0.3, 0.4, 0.5, 0.6, 0.7]:
        filtered_is = [t for t in eq_is if t["leg_quality"] >= qmin]
        filtered_oos = [t for t in eq_oos if t["leg_quality"] >= qmin]
        ais = analyze(filtered_is)
        aoos = analyze(filtered_oos)
        dnet_oos = aoos["net"] - base_oos["net"]
        print(f"  quality>={qmin:.1f}: IS {ais['n']:>3}t {ais['net']:>+7.1f}R  OOS {aoos['n']:>3}t {aoos['net']:>+7.1f}R (d{dnet_oos:>+.1f})  21={aoos['yearly'].get('2021',0):>+5.1f} 22={aoos['yearly'].get('2022',0):>+5.1f}")

    # Quality distribution for wins vs losses
    print(f"\n  Leg quality distribution (OOS wins vs losses):")
    oos_wins = [t for t in eq_oos if float(t["r_multiple"]) > 0]
    oos_losses = [t for t in eq_oos if float(t["r_multiple"]) <= 0]
    if oos_wins:
        avg_q_w = sum(t["leg_quality"] for t in oos_wins) / len(oos_wins)
        avg_mag_w = sum(t["mag_ratio"] for t in oos_wins) / len(oos_wins)
        avg_spd_w = sum(t["speed"] for t in oos_wins) / len(oos_wins)
        print(f"    Wins:  avg quality={avg_q_w:.2f}  avg mag={avg_mag_w:.1f}  avg speed={avg_spd_w:.0f} bars")
    if oos_losses:
        avg_q_l = sum(t["leg_quality"] for t in oos_losses) / len(oos_losses)
        avg_mag_l = sum(t["mag_ratio"] for t in oos_losses) / len(oos_losses)
        avg_spd_l = sum(t["speed"] for t in oos_losses) / len(oos_losses)
        print(f"    Losses: avg quality={avg_q_l:.2f}  avg mag={avg_mag_l:.1f}  avg speed={avg_spd_l:.0f} bars")

    # =========================================================================
    # CONCEPT 2: STRUCTURE EVOLUTION
    # Track swing frequency and magnitude trend, adapt entry mode
    # =========================================================================
    print(f"\n{'='*100}")
    print(f"  CONCEPT 2: STRUCTURE EVOLUTION — swing frequency/magnitude trend")
    print(f"{'='*100}")

    def compute_structure_metrics(sw15, window=50):
        """Compute rolling structure metrics from swing chain."""
        n = len(sw15)
        freq = [0.0] * n  # swings per window
        mag_trend = [0.0] * n  # avg magnitude trend

        for i in range(n):
            # Count swings in last window
            start_sw = max(0, i - window)
            segs = []
            for j in range(start_sw, i + 1):
                seg = sw15[j].get("seg", {})
                spx = float(seg.get("start_px", 0))
                epx = float(seg.get("end_px", 0))
                mag = abs(epx - spx)
                segs.append(mag)

            freq[i] = len(segs) / window
            if len(segs) >= 2:
                first_half = sum(segs[:len(segs)//2]) / max(len(segs)//2, 1)
                second_half = sum(segs[len(segs)//2:]) / max(len(segs) - len(segs)//2, 1)
                mag_trend[i] = second_half / first_half if first_half > 0 else 1.0

        return freq, mag_trend

    # Run baseline IS and get structure metrics
    # Structure evolution works on 15m swings
    freq_is, magtrend_is = compute_structure_metrics(is_data["sw15"])

    print(f"  IS structure metrics computed: freq range [{min(freq_is):.3f}, {max(freq_is):.3f}]")
    print(f"  IS mag_trend range [{min(magtrend_is):.2f}, {max(magtrend_is):.2f}]")

    # For OOS
    freq_oos, magtrend_oos = compute_structure_metrics(sw15_oos)
    print(f"  OOS structure metrics computed: freq range [{min(freq_oos):.3f}, {max(freq_oos):.3f}]")
    print(f"  OOS mag_trend range [{min(magtrend_oos):.2f}, {max(magtrend_oos):.2f}]")

    # This is a more complex concept that requires engine-level changes
    # For now, just show the metrics distribution
    print(f"\n  (Structure evolution requires engine-level changes — storing for later)")
    print(f"  Key insight: swing frequency and magnitude trend are COMPUTABLE from existing data")
    print(f"  but require dynamic entry-mode switching inside the engine loop")

    # =========================================================================
    # CONCEPT 4: MTF REGIME
    # Check 1h alignment at entry time
    # =========================================================================
    print(f"\n{'='*100}")
    print(f"  CONCEPT 4: MTF REGIME — multi-timeframe alignment")
    print(f"{'='*100}")

    def compute_mtf_regime(trades, c15, sw15, sw10):
        """Check 1h swing direction at entry time."""
        # sw10 = 1h swings with min_bars=10
        # sw15 = 15m swings
        # At entry, check: what is the current 1h swing direction?
        # And what was the PREVIOUS 1h swing direction?
        # If they agree: trending. If they disagree: ranging.

        ts15 = [int(c["ts"]) for c in c15]

        enriched = []
        for t in trades:
            entry_date = t.get("entry_date", "")[:19]
            bar_idx = -1
            for j, c in enumerate(c15):
                if c["date"][:19] == entry_date:
                    bar_idx = j
                    break

            if bar_idx < 0:
                enriched.append({**t, "mtf_aligned": True, "htf_dir": 0})
                continue

            entry_ts = ts15[bar_idx]

            # Find current and previous 1h swing directions
            htf_dirs = []
            for sw in sw10:
                seg = sw.get("seg", {})
                si = int(seg.get("start_idx", -1))
                ei = int(seg.get("end_idx", -1))
                spx = float(seg.get("start_px", 0))
                epx = float(seg.get("end_px", 0))
                # Get timestamps for these indices (from 1h data)
                if epx > spx:
                    htf_dirs.append(1)  # up swing
                else:
                    htf_dirs.append(-1)  # down swing

            # Find which 1h swing we're in at entry_ts
            # Simple approach: find the last completed 1h swing before entry
            current_dir = 0
            prev_dir = 0
            for i, sw in enumerate(sw10):
                seg = sw.get("seg", {})
                spx = float(seg.get("start_px", 0))
                epx = float(seg.get("end_px", 0))
                d = 1 if epx > spx else -1
                if i < len(htf_dirs) - 1:
                    prev_dir = current_dir
                current_dir = d

            aligned = (current_dir != 0 and prev_dir != 0 and current_dir == prev_dir)
            trade_dir = 1 if t["dir"] == "long" else -1
            aligned_with_trade = aligned and (current_dir == trade_dir)

            enriched.append({**t, "mtf_aligned": aligned, "htf_dir": current_dir,
                           "aligned_with_trade": aligned_with_trade})
        return enriched

    mtf_is = compute_mtf_regime(trades_is, is_data["c15"], is_data["sw15"], is_data["sw10"])
    mtf_oos = compute_mtf_regime(trades_oos, c15o, sw15_oos, sw10_oos)

    # Aligned vs not aligned
    aligned_is = [t for t in mtf_is if t["mtf_aligned"]]
    not_aligned_is = [t for t in mtf_is if not t["mtf_aligned"]]
    aligned_oos = [t for t in mtf_oos if t["mtf_aligned"]]
    not_aligned_oos = [t for t in mtf_oos if not t["mtf_aligned"]]

    ais_a = analyze(aligned_is)
    ais_na = analyze(not_aligned_is)
    aoos_a = analyze(aligned_oos)
    aoos_na = analyze(not_aligned_oos)

    print(f"\n  HTF-aligned trades:  IS {ais_a['n']:>3}t {ais_a['net']:>+7.1f}R  OOS {aoos_a['n']:>3}t {aoos_a['net']:>+7.1f}R  21={aoos_a['yearly'].get('2021',0):>+5.1f} 22={aoos_a['yearly'].get('2022',0):>+5.1f}")
    print(f"  HTF-not-aligned:     IS {ais_na['n']:>3}t {ais_na['net']:>+7.1f}R  OOS {aoos_na['n']:>3}t {aoos_na['net']:>+7.1f}R  21={aoos_na['yearly'].get('2021',0):>+5.1f} 22={aoos_na['yearly'].get('2022',0):>+5.1f}")

    # Filter out not-aligned
    filtered_is = aligned_is
    filtered_oos = aligned_oos
    ais_f = analyze(filtered_is)
    aoos_f = analyze(filtered_oos)
    dnet_oos = aoos_f["net"] - base_oos["net"]
    print(f"\n  Filter (aligned only): IS {ais_f['n']:>3}t {ais_f['net']:>+7.1f}R  OOS {aoos_f['n']:>3}t {aoos_f['net']:>+7.1f}R (d{dnet_oos:>+.1f})  21={aoos_f['yearly'].get('2021',0):>+5.1f} 22={aoos_f['yearly'].get('2022',0):>+5.1f}")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print(f"\n{'='*100}")
    print(f"  SUMMARY: ALL 4 CONCEPTS vs BASELINE")
    print(f"{'='*100}")
    print(f"\n  Baseline (wage10+wknd):  IS {base_is['n']}t {base_is['net']:+.1f}R  OOS {base_oos['n']}t {base_oos['net']:+.1f}R  OOS N/D={base_oos['ndd']:.2f}")
    print(f"\n  Concept 3 (room>=1.0):")
    filt = [t for t in enriched_oos if t["room"] >= 1.0]
    af = analyze(filt)
    print(f"    OOS: {af['n']}t {af['net']:+.1f}R  N/D={af['ndd']:.2f}  21={af['yearly'].get('2021',0):+.1f} 22={af['yearly'].get('2022',0):+.1f}")
    print(f"\n  Concept 3 (chase<3):")
    filt = [t for t in enriched_oos if t["chase"] < 3]
    af = analyze(filt)
    print(f"    OOS: {af['n']}t {af['net']:+.1f}R  N/D={af['ndd']:.2f}  21={af['yearly'].get('2021',0):+.1f} 22={af['yearly'].get('2022',0):+.1f}")
    print(f"\n  Concept 3 (room>=1.0 & chase<3):")
    filt = [t for t in enriched_oos if t["room"] >= 1.0 and t["chase"] < 3]
    af = analyze(filt)
    print(f"    OOS: {af['n']}t {af['net']:+.1f}R  N/D={af['ndd']:.2f}  21={af['yearly'].get('2021',0):+.1f} 22={af['yearly'].get('2022',0):+.1f}")
    print(f"\n  Concept 1 (quality>=0.5):")
    filt = [t for t in eq_oos if t["leg_quality"] >= 0.5]
    af = analyze(filt)
    print(f"    OOS: {af['n']}t {af['net']:+.1f}R  N/D={af['ndd']:.2f}  21={af['yearly'].get('2021',0):+.1f} 22={af['yearly'].get('2022',0):+.1f}")
    print(f"\n  Concept 4 (HTF aligned only):")
    af = analyze(aligned_oos)
    print(f"    OOS: {af['n']}t {af['net']:+.1f}R  N/D={af['ndd']:.2f}  21={af['yearly'].get('2021',0):+.1f} 22={af['yearly'].get('2022',0):+.1f}")


if __name__ == "__main__":
    main()

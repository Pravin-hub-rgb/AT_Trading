"""Replay harness — run all backtest trades through the LIVE window pipeline.

The parked-item tripwire (M6/M7/M8): instead of waiting months for live
trades to exercise window-edge/boundary/cooldown conditions, replay every
historical backtest trade through the exact live decision path:

  For each backtest trade at entry time E:
    1. Build the window live would have had at E (15m [E-30d, E], 1h
       [E-20d, E], swings rebuilt fresh over a warmup fetch — same as
       parity_report / live seeding)
    2. Run the EXACT live sim call (fine_ltf=[], same v18 params)
    3. Check the trade reproduces (same dir, entry_ts within 1 bar)

  A miss means the 30d live window construction loses that signal — the
  exact failure mode M6 guards against. Misses are classified:
    boundary-bar (1h boundary entry), post-loss (within cooldown of the
    previous closed trade), window-edge (entry near the window start).

  This is also the permanent regression harness: any future engine/live
  change re-replays 3.8 years in minutes.

Usage:
    python replay_harness.py                 # full 261-trade replay
    python replay_harness.py --sample 30     # quick subset
    python replay_harness.py --out replay.txt
"""

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "backend"))

from persistence.database import Database
from persistence.trade_store import open_htf_window  # noqa: F401 (swing-state db)
from src.walker import FlowCandle
from src.live.persistent_swing import PersistentSwingEngine
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from engine.v18_params import SWING, get_v18_params
from live_loop import LiveLoop

# C9: the validated 261-trade config is the BYBIT perp instrument — same
# dataset AND params the live loop must bind (main.py v18_instrument).
INSTRUMENT = "BTCUSDT_BYBIT"

DAY = 86400
BAR = 900  # 15m
COOLDOWN_BARS = None  # filled from v18 params


def load_candles():
    """Load 15m/1h CSVs into candle dicts (same convention as live)."""
    out = {}
    for tf in ("15m", "1h"):
        df = load_btc_df(tf, INSTRUMENT)
        candles, flow = [], []
        for row in df.itertuples():
            date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            candles.append({
                "date": date,
                "ts": int(row.ts),
                "open": float(row.open), "high": float(row.high),
                "low": float(row.low), "close": float(row.close),
            })
            flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                                   low=float(row.low), close=float(row.close)))
        out[tf] = (candles, flow)
    return out["15m"], out["1h"]


def build_swings(candles, tf, min_bars, time_cap=None):
    """Fresh PersistentSwingEngine over a candle list (throwaway state DB).

    time_cap=None keeps CURRENT live behavior (timeCap default 09:29 — Nifty
    session-gate leftover, C11). Pass "00:00" to test the backtest's 24/7
    behavior.
    """
    state_db = Database(os.path.join(tempfile.mkdtemp(prefix="replay_sw_"), "s.db"))
    state_db.connect()
    state_db.create_tables()
    opts = {"minBars": min_bars}
    if time_cap:
        opts["timeCap"] = time_cap
    pse = PersistentSwingEngine(tf, state_db, opts)
    swings = []
    for g_idx, c in enumerate(candles):
        r = pse.process_bar(FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                                       low=c["low"], close=c["close"]), g_idx)
        if r:
            swings.append(r)
    return swings


def run_sim(c15, sw15, c1h, sw1h, v18):
    return simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15,
        fine_ltf=[],
        sl_buf_atr=v18["sl_buf_atr"],
        ext_stop_r=v18["ext_stop_r"],
        mode=v18["mode"],
        chop_thresh=v18["chop_thresh"],
        cooldown_bars=v18["cooldown_bars"],
        max_consecutive_losses=v18["max_consecutive_losses"],
    )["ltf_trades"]

def main():
    global COOLDOWN_BARS
    ap = argparse.ArgumentParser(description="Live-window replay harness")
    ap.add_argument("--sample", type=int, default=0, help="replay only first N trades")
    ap.add_argument("--timecap", default=None, help="C11 test: '00:00' = backtest 24/7 behavior; default = live's 09:29 leftover")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    lines = []

    def out(s=""):
        lines.append(s)
        print(s, flush=True)

    v18 = get_v18_params(INSTRUMENT)
    COOLDOWN_BARS = v18["cooldown_bars"]

    out("=" * 78)
    out(f"REPLAY HARNESS — all backtest trades through the live window pipeline")
    out(f"  instrument: {INSTRUMENT}  (C9: same params live must bind)")
    out(f"  timeCap: {args.timecap or '09:29 (live default, C11)'}")
    out(f"  start: {time.strftime('%Y-%m-%d %H:%M:%S')}  sample={args.sample or 'ALL'}")
    out("=" * 78)

    out("\n[1] loading CSVs ...")
    (c15_all, f15_all), (c1h_all, f1h_all) = load_candles()
    data_start = c15_all[0]["ts"]
    out(f"    15m={len(c15_all)}  1h={len(c1h_all)}  "
        f"range {c15_all[0]['date']} -> {c15_all[-1]['date']}")

    out("[2] baseline sim (full history, continuous swings, fine_ltf=[]) ...")
    t0 = time.time()
    sw15_all = _compute_swings(f15_all, "continuous", min_bars=SWING["min_bars_15m"])
    sw1h_all = _compute_swings(f1h_all, "continuous", min_bars=SWING["min_bars_1h"])
    baseline = run_sim(c15_all, sw15_all, c1h_all, sw1h_all, v18)
    out(f"    baseline: {len(baseline)} trades ({time.time() - t0:.0f}s) "
        f"— expect 261 (fine fills don't change entries)")

    # Trades inside the first warmup span of the dataset cannot get a proper
    # live-style window (no older data to fetch) — reported, not counted.
    data_start_n = sum(1 for t in baseline if int(t["entry_ts"]) - data_start < 35 * DAY)
    ref = [t for t in baseline
           if not args.sample or args.sample >= (baseline.index(t) + 1)][:args.sample or None]
    ref = [t for t in ref if int(t["entry_ts"]) - data_start >= 35 * DAY]

    out(f"\n[3] replaying {len(ref)} entries through live-style windows "
        f"({data_start_n} near dataset start excluded) ...")
    reproduced = 0
    misses = []
    t0 = time.time()
    for i, t in enumerate(ref):
        E = int(t["entry_ts"])
        d = t["dir"]
        # live-style fetch: 5d warmup before the window start
        f15 = [c for c in c15_all if E - 35 * DAY <= c["ts"] <= E]
        f1h = [c for c in c1h_all if E - 25 * DAY <= c["ts"] <= E]
        if not f15 or not f1h:
            misses.append((E, d, "no-data"))
            continue
        sw15 = build_swings(f15, "15m", SWING["min_bars_15m"], time_cap=args.timecap)
        sw1h = build_swings(f1h, "1h", SWING["min_bars_1h"], time_cap=args.timecap)
        c15 = [c for c in f15 if c["ts"] >= E - 30 * DAY]
        c1h = [c for c in f1h if c["ts"] >= E - 20 * DAY]
        sim_trades = run_sim(c15, sw15, c1h, sw1h, v18)
        hit = any(x["dir"] == d and abs(int(x["entry_ts"]) - E) <= BAR
                  for x in sim_trades)
        if hit:
            reproduced += 1
        else:
            misses.append((E, d, classify(E, baseline, c15, f15)))
        if (i + 1) % 20 == 0:
            out(f"    ... {i + 1}/{len(ref)} replayed ({reproduced} reproduced, "
                f"{len(misses)} missed)  {time.time() - t0:.0f}s")

    out(f"\n[4] RESULT: {reproduced}/{len(ref)} reproduced through live windows "
        f"({time.time() - t0:.0f}s)")
    if misses:
        out(f"\n  !! MISSES ({len(misses)}) — signals the live window loses:")
        for E, d, why in misses:
            out(f"     {time.strftime('%Y-%m-%d %H:%M', time.gmtime(E))} {d}  [{why}]")
        counts = {}
        for _, _, why in misses:
            counts[why] = counts.get(why, 0) + 1
        out("\n  miss classification: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    else:
        out("  zero misses — every historical trade survives the live window pipeline")

    verdict = "PASS" if not misses else ("WARN" if reproduced / len(ref) >= 0.95 else "FAIL")
    out(f"\nVERDICT: {verdict}  ({reproduced}/{len(ref)} reproduced)")
    if args.out:
        Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nwritten: {args.out}")
    sys.exit(0 if not misses else 1)

def classify(E, baseline, c15, f15):
    """Why the live window lost this signal?"""
    why = []
    # window edge: entry near the START of the trimmed window
    ws = c15[0]["ts"] if c15 else 0
    if ws and (E - ws) < 2 * DAY:
        why.append("window-edge")
    # boundary bar: entry within the last hour-bar of a 1h close
    if E % 3600 >= 3600 - BAR:
        why.append("boundary-bar")
    # post-loss: previous closed trade ended within cooldown of E
    prev = [t for t in baseline
            if t.get("outcome") not in ("open",) and int(t.get("exit_ts", 0)) <= E]
    if prev:
        last = max(prev, key=lambda t: int(t["exit_ts"]))
        gap_bars = (E - int(last["exit_ts"])) // BAR
        if gap_bars < (COOLDOWN_BARS or 0) + 4:
            why.append(f"post-loss(gap={gap_bars}b)")
    # warmup: entry near the very start of the fetched data
    if f15 and (E - f15[0]["ts"]) < 2 * DAY:
        why.append("warmup-edge")
    return "+".join(why) if why else "unexplained"


if __name__ == "__main__":
    main()



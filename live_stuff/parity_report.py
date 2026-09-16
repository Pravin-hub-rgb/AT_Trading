"""Parity report — live DB trades vs a fresh v18 sim over the same window.

The go/no-go tool for paper mode. For a lookback window it:
  1. Reads the live DB ltf_trades
  2. Refetches the same 15m/1h candles live saw (Bybit REST, the same fetcher
     live's seeding uses) and rebuilds swings with the same engines (fresh
     PersistentSwingEngine on a throwaway DB — live swing state untouched)
  3. Runs the EXACT same simulate_htf_ltf_streak_halt call as
     LiveLoop._run_v18_simulation (fine_ltf=[], same v18 params)
  4. Diffs the result trade-by-trade against the DB

Usage (from live_stuff/):
    python parity_report.py                     # last 7 days
    python parity_report.py --days 14
    python parity_report.py --days 7 --out parity.txt
    python parity_report.py --mainnet           # mainnet REST instead of demo

Verdict:
  PASS  every sim trade has a matching DB row, exit reasons match, deltas small
  WARN  matched but entry/R deltas beyond soft tolerance (slippage drift)
  FAIL  missing/extra trades, open-state or exit-reason mismatches
Exit code: 0 on PASS/WARN, 1 on FAIL (cron-friendly).

Known by-design caveats:
  - Live sims run continuously on rolling windows; this is a single-shot run
    over the current window. Trades near window edges can legitimately differ.
  - Guard-skipped DB rows (stale_skip/halted_skip/order_failed) are not real
    trades — reported separately, never counted as mismatches.
  - Real fills differ from sim close prices (slippage) — entry deltas within
    tolerance are expected.
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

import config
from persistence.database import Database
from persistence.trade_store import get_ltf_trades
from bybit_streamer import backfill_klines_bybit
from src.walker import FlowCandle
from src.live.persistent_swing import PersistentSwingEngine
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from engine.v18_params import SWING, get_v18_params
# LiveLoop only for _normalize_candles — the method never touches self, so we
# call it unbound to guarantee byte-for-byte the same normalization as live.
from live_loop import LiveLoop

GUARD_REASONS = ("stale_skip", "halted_skip", "order_failed", "order_error")
ENTRY_TOL_PCT = 0.15   # soft: real fill vs sim close
ENTRY_FAIL_PCT = 0.50  # hard: too far to be slippage
R_TOL = 0.30           # soft: R delta


def fetch_candles(symbol: str, interval: str, start_ms: int, demo: bool) -> list:
    """Fetch all closed candles from start_ms to now via live's fetcher."""
    step_ms = {"1": 60_000, "5": 300_000, "15": 900_000, "60": 3_600_000}.get(interval, 900_000)
    now_ms = int(time.time() * 1000)
    need = int((now_ms - start_ms) / step_ms) + 10
    raw = backfill_klines_bybit(symbol, interval, limit=need, demo=demo, start_ms=start_ms)
    raw = [c for c in raw if c.get("close_time", c.get("open_time", 0)) <= now_ms]
    return LiveLoop._normalize_candles(None, raw)


def build_swings(candles: list, tf: str, min_bars: int) -> list:
    """Replicate the live seed path over a candle list (throwaway state DB)."""
    state_db = Database(os.path.join(tempfile.mkdtemp(prefix="parity_swing_"), "state.db"))
    state_db.connect()
    state_db.create_tables()
    pse = PersistentSwingEngine(tf, state_db, {"minBars": min_bars})
    swings = []
    for g_idx, c in enumerate(candles):
        fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                        low=c["low"], close=c["close"])
        r = pse.process_bar(fc, g_idx)
        if r:
            swings.append(r)
    return swings


def main():
    ap = argparse.ArgumentParser(description="Live-vs-backtest parity report")
    ap.add_argument("--days", type=float, default=7.0, help="report window (days)")
    ap.add_argument("--db", default="backbencher.db", help="live DB path")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--mainnet", action="store_true", help="use mainnet REST (default: demo)")
    ap.add_argument("--out", default=None, help="also write the report to this file")
    args = ap.parse_args()
    demo = not args.mainnet

    now = int(time.time())
    report_start = now - int(args.days * 86400)
    lines = []

    def out(s=""):
        lines.append(s)
        print(s)

    out("=" * 78)
    out(f"PARITY REPORT  symbol={args.symbol}  window=last {args.days:g}d  "
        f"{'MAINNET' if not demo else 'demo'}")
    out(f"  generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now))} UTC")
    out("=" * 78)

    # --- 1. live DB trades --------------------------------------------------
    db = Database(args.db)
    db.connect()
    all_db = get_ltf_trades(db)
    db_win = [t for t in all_db if int(t["entry_ts"]) >= report_start]
    real = [t for t in db_win if (t.get("exit_reason") or "") not in GUARD_REASONS]
    guards = [t for t in db_win if (t.get("exit_reason") or "") in GUARD_REASONS]
    out(f"\n[1] live DB: {len(db_win)} rows in window -> {len(real)} real trades, "
        f"{len(guards)} guard-skips (C3/C5/order-fail — expected)")

    # --- 2. candles + swings (mirror live seeding exactly) -------------------
    lookback15 = config.WINDOW_DAYS_15M + 5
    lookback1h = config.WINDOW_DAYS_1H + 5
    out(f"\n[2] fetching candles (15m +{lookback15}d warmup, 1h +{lookback1h}d) ...")
    candles15 = fetch_candles(args.symbol, "15", (report_start - lookback15 * 86400) * 1000, demo)
    candles1h = fetch_candles(args.symbol, "60", (report_start - lookback1h * 86400) * 1000, demo)
    if not candles15 or not candles1h:
        out("FATAL: no candles fetched — check network / symbol / interval")
        sys.exit(2)
    out(f"    fetched: 15m={len(candles15)}  1h={len(candles1h)}")
    sw15 = build_swings(candles15, "15m", SWING["min_bars_15m"])
    sw1h = build_swings(candles1h, "1h", SWING["min_bars_1h"])
    # window trim mirrors live's current rolling window exactly
    c15 = [c for c in candles15 if c["ts"] >= now - config.WINDOW_DAYS_15M * 86400] or candles15
    c1h = [c for c in candles1h if c["ts"] >= now - config.WINDOW_DAYS_1H * 86400] or candles1h
    out(f"    windows: 15m={len(c15)} 1h={len(c1h)} | swings: 15m={len(sw15)} 1h={len(sw1h)}")

    # --- 3. the EXACT live sim call ------------------------------------------
    v18 = get_v18_params(args.symbol)
    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15,
        fine_ltf=[],
        sl_buf_atr=v18["sl_buf_atr"],
        ext_stop_r=v18["ext_stop_r"],
        mode=v18["mode"],
        chop_thresh=v18["chop_thresh"],
        cooldown_bars=v18["cooldown_bars"],
        max_consecutive_losses=v18["max_consecutive_losses"],
    )
    sim_trades = [t for t in result["ltf_trades"] if int(t["entry_ts"]) >= report_start]
    out(f"\n[3] sim: {len(sim_trades)} trades in window (live call, fine_ltf=[], same params)")

    # --- 4. diff --------------------------------------------------------------
    sim_map = {(int(t["entry_ts"]), t["dir"]): t for t in sim_trades}
    db_map = {(int(t["entry_ts"]), t["direction"]): t for t in real}
    missing = sorted(set(sim_map) - set(db_map))   # strategy took, live has no real row
    extra = sorted(set(db_map) - set(sim_map))     # live real row, sim did not take
    matched = sorted(set(sim_map) & set(db_map))

    out(f"\n[4] diff: matched={len(matched)}  missing_in_db={len(missing)}  extra_in_db={len(extra)}")

    def fmt_ts(ts):
        return time.strftime("%m-%d %H:%M", time.gmtime(int(ts)))

    hard = 0
    soft = 0

    if missing:
        hard += len(missing)
        out("\n  !! MISSING IN DB (sim took, live has no real row):")
        for k in missing:
            t = sim_map[k]
            out(f"     {fmt_ts(k[0])} {k[1]}  entry={float(t['entry_price']):.2f}  "
                f"sim_outcome={t['outcome']}")

    if extra:
        hard += len(extra)
        out("\n  !! EXTRA IN DB (live real row exists, sim did not take):")
        for k in extra:
            t = db_map[k]
            out(f"     {fmt_ts(k[0])} {k[1]}  entry={float(t['entry_price']):.2f}  "
                f"exit_reason={t.get('exit_reason')}")

    if matched:
        out("\n  matched (ts dir | entry sim/db | reason sim/db | R sim/db):")
    for k in matched:
        s, d = sim_map[k], db_map[k]
        s_open = s["outcome"] == "open"
        d_open = d["status"] == "open"
        e_sim, e_db = float(s["entry_price"]), float(d["entry_price"])
        epct = abs(e_sim - e_db) / max(abs(e_sim), 1e-9) * 100
        if s_open and d_open:
            if epct > ENTRY_TOL_PCT:
                soft += 1
                out(f"   ~ {fmt_ts(k[0])} {k[1]}  OPEN both  entry {e_sim:.2f}/{e_db:.2f} "
                    f"({epct:.2f}%)  << soft-delta")
            else:
                out(f"   ~ {fmt_ts(k[0])} {k[1]}  OPEN both  entry {e_sim:.2f}/{e_db:.2f} ({epct:.2f}%)")
            continue
        if s_open != d_open:
            hard += 1
            out(f"   !! {fmt_ts(k[0])} {k[1]}  OPEN-STATE MISMATCH sim={s['outcome']} "
                f"db={d['status']}/{d.get('exit_reason')}")
            continue
        r_sim, r_db = float(s["r_multiple"]), float(d["r_multiple"])
        rdelta = r_db - r_sim
        if s["outcome"] != d["exit_reason"]:
            hard += 1
            out(f"   !! {fmt_ts(k[0])} {k[1]}  REASON MISMATCH {s['outcome']}/{d['exit_reason']}  "
                f"R {r_sim:+.2f}/{r_db:+.2f}")
            continue
        tag = ""
        if epct > ENTRY_TOL_PCT or abs(rdelta) > R_TOL:
            soft += 1
            tag = "  << soft-delta"
        out(f"    {fmt_ts(k[0])} {k[1]}  {e_sim:.2f}/{e_db:.2f} ({epct:.2f}%)  "
            f"{s['outcome']}/{d['exit_reason']}  R {r_sim:+.2f}/{r_db:+.2f} ({rdelta:+.2f}){tag}")

    out("\n" + "-" * 78)
    out(f"guard-skips in window: {len(guards)} (stale_skip/halted_skip/order_failed — C3/C5/C7, expected)")
    verdict = "FAIL" if hard else ("WARN" if soft else "PASS")
    out(f"VERDICT: {verdict}  (hard issues={hard}, soft deltas={soft})")
    if args.out:
        Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nwritten: {args.out}")
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()



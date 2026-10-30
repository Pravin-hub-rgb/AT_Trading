# Old initial live engine (superseded by live_stuff/) — check contents

"""Backbencher — LIVE marks logger (run this).

Prints, in real time:
  [15m CLOSE] date | O H L C
  [ 1h CLOSE] date | O H L C
  [MARK] 15m B2   up   sw123 @ px   (bar ...)
  [MARK]  1h FLIP down sw45  @ px   (bar ...)

Every closed candle is also journaled to data/live/marks_YYYYMMDD.jsonl (L1)
for the future daily compare.

Uses REST API polling (more reliable than websockets for live trading).

Usage:
    python backend/src/live/main.py            # runs forever
    python backend/src/live/main.py 120        # runs 120 s then exits (test)
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/

from src.btc.btc_swing import compute_btc_swings
from src.live.aggregator import to_ist_wall
from src.live.boot_data import fetch_klines
from src.live.mark_engine import MarkEngine
from src.walker import FlowCandle

SYMBOL = "BTCUSDT"
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "live"
SEP = "-" * 78
POLL_SECONDS = 60  # poll every 60s for new closed candles


def log(msg: str):
    print(msg, flush=True)


def journal(rec: dict):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        day = rec.get("date", "")[:10].replace("-", "")
        with open(DATA_DIR / f"marks_{day}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:  # journaling must never kill the runner
        log(f"[journal error] {e}")


def _load_csv_candles(tf: str) -> list[dict]:
    """Load full history from the Bybit CSV (same source as the backtest).

    The walker is path-dependent: a rolling window produces a DIFFERENT
    swing chain than full history, so marks fall on the wrong bars.
    Seeding from the full CSV fixes this — the live chain now matches the
    backtest chain exactly.
    """
    import pandas as pd
    from src.btc.btc_config import BTC_BYBIT_DATA_DIR
    csv_path = Path(BTC_BYBIT_DATA_DIR) / f"BTCUSDT_{tf}.csv"
    df = pd.read_csv(csv_path)
    candles = []
    for _, r in df.iterrows():
        ts = int(pd.Timestamp(r["timestamp"]).timestamp()) - 19800  # IST wall-clock → UTC epoch
        candles.append({
            "date": r["timestamp"],
            "ts": ts,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
        })
    return candles


def _print_csv_marks(tf: str, eng: MarkEngine, label: str):
    """Print marks for the CSV's latest candles so the user sees current state."""
    # Compute chain ONCE for the full window, then filter to last 200 candles
    flow = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                       low=c["low"], close=c["close"]) for c in eng.candles]
    swings = compute_btc_swings(flow, opts={"minBars": eng.min_bars}, max_swings=len(flow) // 2)
    cutoff_idx = max(0, len(eng.candles) - 200)
    seen = set()
    for s in swings:
        for b in s.get("breaks", []):
            idx = int(b.get("idx", -1))
            if idx >= cutoff_idx:
                candle = eng.candles[idx]
                key = (candle["date"], b["kind"], b["dir"])
                if key not in seen:
                    seen.add(key)
                    log(f"[{label}] {candle['date']} | {b['kind']:<4} {b['dir']:<4} sw{s['swing_index']} @ {b['px']:.2f}")


def make_engines():
    log(SEP)
    log("Backbencher | boot: loading full history from CSV (path-independent chain)...")
    c15 = _load_csv_candles("15m")
    c1h = _load_csv_candles("1h")
    eng15 = MarkEngine("15m", min_bars=50, window_bars=len(c15) + 100)
    eng1h = MarkEngine("1h", min_bars=15, window_bars=len(c1h) + 100)
    eng15.seed(c15)
    eng1h.seed(c1h)
    log(f"seeded 15m: {len(c15)} candles ({c15[0]['date']} -> {c15[-1]['date']})")
    log(f"seeded  1h: {len(c1h)} candles ({c1h[0]['date']} -> {c1h[-1]['date']})")
    # Print marks for the latest CSV candles so the user sees current state
    log("latest marks in CSV:")
    _print_csv_marks("15m", eng15, "15m")
    _print_csv_marks("1h", eng1h, " 1h")
    log("watching: every 15m and 1h CLOSE -> OHLC + B1/B2/FLIP marks")
    log(SEP)
    return eng15, eng1h


def handle_close(tf: str, eng: MarkEngine, k) -> None:
    # Handle both websocket kline format and REST candle dict format
    if isinstance(k, dict) and "date" in k:
        candle = k  # Already a candle dict from REST polling
    else:
        candle = {"date": to_ist_wall(int(k["t"]) // 1000), "ts": int(k["t"]) // 1000,
                  "open": float(k["o"]), "high": float(k["h"]),
                  "low": float(k["l"]), "close": float(k["c"])}
    label = "15m" if tf == "15m" else " 1h"
    log(f"[{label} CLOSE] {candle['date']} | "
        f"O {candle['open']:.2f}  H {candle['high']:.2f}  "
        f"L {candle['low']:.2f}  C {candle['close']:.2f}")
    journal({"type": "close", "tf": tf, **candle})
    marks, n_swings = eng.on_close(candle)
    for m in marks:
        pad = "15m" if tf == "15m" else " 1h"
        log(f"[MARK] {pad} {m['kind']:<4} {m['dir']:<4} sw{m['swing_no']} "
            f"@ {m['px']:.2f}  (bar {m['bar_date']})  "
            f"swing[{m['swing_kind']}] confirmed@{m['swing_confirmed_at'] or 'pending'}")
        journal({"type": "mark", **m})
    if not marks:
        log(f"[{label}] no marks on this candle (chain: {n_swings} swings)")


def run(max_seconds: float = 0):
    """Poll REST API for closed candles (more reliable than websockets)."""
    eng15, eng1h = make_engines()
    started = time.time()
    # Only process candles NEWER than the CSV's last row (avoid reprocessing history)
    last_csv_15m_ts = eng15.candles[-1]["ts"]
    last_csv_1h_ts = eng1h.candles[-1]["ts"]
    last_15m_ts = last_csv_15m_ts
    last_1h_ts = last_csv_1h_ts
    log(f"[poll] CSV last 15m: {eng15.candles[-1]['date']} | 1h: {eng1h.candles[-1]['date']}")
    log(f"[poll] polling every {POLL_SECONDS}s for NEW closed candles")
    while True:
        if max_seconds and (time.time() - started) > max_seconds:
            log(SEP)
            log(f"test window over ({max_seconds:.0f}s) — bye")
            return
        try:
            # Fetch latest closed candles
            c15 = fetch_klines(SYMBOL, "15m", 5)
            c1h = fetch_klines(SYMBOL, "1h", 5)
            now_s = int(time.time())
            # Process 15m closes (only new ones)
            for c in c15:
                if c["ts"] + 900 <= now_s and c["ts"] > last_15m_ts:
                    last_15m_ts = c["ts"]
                    candle = {"date": to_ist_wall(c["ts"]), "ts": c["ts"],
                              "open": c["open"], "high": c["high"],
                              "low": c["low"], "close": c["close"]}
                    handle_close("15m", eng15, candle)
            # Process 1h closes (only new ones)
            for c in c1h:
                if c["ts"] + 3600 <= now_s and c["ts"] > last_1h_ts:
                    last_1h_ts = c["ts"]
                    candle = {"date": to_ist_wall(c["ts"]), "ts": c["ts"],
                              "open": c["open"], "high": c["high"],
                              "low": c["low"], "close": c["close"]}
                    handle_close("1h", eng1h, candle)
        except Exception as e:
            log(f"[poll] error: {e} — reseed + retry in {POLL_SECONDS}s")
            try:
                eng15, eng1h = make_engines()
            except Exception as e2:
                log(f"[boot] reseed failed: {e2}")
        time.sleep(POLL_SECONDS)


def main():
    max_seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 0
    run(max_seconds)


if __name__ == "__main__":
    main()

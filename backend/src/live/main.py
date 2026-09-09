"""Backbencher — LIVE marks logger (run this).

Prints, in real time:
  [15m CLOSE] date | O H L C
  [ 1h CLOSE] date | O H L C
  [MARK] 15m B2   up   sw123 @ px   (bar ...)
  [MARK]  1h FLIP down sw45  @ px   (bar ...)

Every closed candle is also journaled to data/live/marks_YYYYMMDD.jsonl (L1)
for the future daily compare.

Usage:
    python backend/src/live/main.py            # runs forever
    python backend/src/live/main.py 120        # runs 120 s then exits (test)
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/

from src.live.aggregator import to_ist_wall
from src.live.boot_data import fetch_klines
from src.live.mark_engine import MarkEngine

SYMBOL = "BTCUSDT"  # REST is case-sensitive here; streams use lowercase
WS_URL = (f"wss://stream.binance.com:9443/stream"
          f"?streams={SYMBOL.lower()}@kline_15m/{SYMBOL.lower()}@kline_1h")
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "live"
SEP = "-" * 78


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


def make_engines():
    log(SEP)
    log("Backbencher | boot: fetching rolling window (spot REST)...")
    c15 = fetch_klines(SYMBOL, "15m", 2880)   # 30 days
    c1h = fetch_klines(SYMBOL, "1h", 480)     # 20 days
    # the last REST row may be the running candle — drop it if so
    import time
    now_s = int(time.time())
    c15 = [c for c in c15 if c["ts"] + 900 <= now_s]
    c1h = [c for c in c1h if c["ts"] + 3600 <= now_s]
    eng15 = MarkEngine("15m", min_bars=50, window_bars=2880)
    eng1h = MarkEngine("1h", min_bars=20, window_bars=480)
    eng15.seed(c15)
    eng1h.seed(c1h)
    log(f"seeded 15m: {len(c15)} candles ({c15[0]['date']} -> {c15[-1]['date']})")
    log(f"seeded  1h: {len(c1h)} candles ({c1h[0]['date']} -> {c1h[-1]['date']})")
    log("watching: every 15m and 1h CLOSE -> OHLC + B1/B2/FLIP marks")
    log(SEP)
    return eng15, eng1h


def handle_close(tf: str, eng: MarkEngine, k) -> None:
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


async def run(max_seconds: float = 0):
    eng15, eng1h = make_engines()
    started = asyncio.get_event_loop().time()
    attempt = 0
    while True:
        try:
            import websockets
            async with websockets.connect(WS_URL, ping_interval=20,
                                          ping_timeout=10, open_timeout=15) as ws:
                attempt = 0
                log("[ws] connected: btcusdt kline_15m + kline_1h (spot)")
                async for raw in ws:
                    if max_seconds and (asyncio.get_event_loop().time()
                                        - started) > max_seconds:
                        log(SEP)
                        log(f"test window over ({max_seconds:.0f}s) — bye")
                        return
                    data = json.loads(raw)
                    d = data.get("data", {})
                    if d.get("e") != "kline":
                        continue
                    k = d["k"]
                    if not k.get("x"):
                        continue  # running candle — act on closed bars only
                    tf = "15m" if k["i"] == "15m" else "1h"
                    eng = eng15 if tf == "15m" else eng1h
                    handle_close(tf, eng, k)
        except Exception as e:
            attempt += 1
            delay = min(60, 5 * attempt)
            log(f"[ws] disconnected ({e}) — reseed + retry in {delay}s")
            await asyncio.sleep(delay)
            try:
                eng15, eng1h = make_engines()
            except Exception as e2:
                log(f"[boot] reseed failed: {e2}")


def main():
    max_seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 0
    asyncio.run(run(max_seconds))


if __name__ == "__main__":
    main()

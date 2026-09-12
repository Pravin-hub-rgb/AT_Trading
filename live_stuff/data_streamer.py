#!/usr/bin/env python3
"""Real-time data streamer for v18 live trading."""

import asyncio
import json
import logging
import time
from datetime import timezone
from typing import Optional

import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("websockets").setLevel(logging.WARNING)

SYMBOL = "BTCUSDT"
BASE_URL = "wss://stream.binance.com/ws"


class BinanceStreamer:
    def __init__(self, on_tick, on_15m_close, on_1h_close):
        self.on_tick = on_tick
        self.on_15m_close = on_15m_close
        self.on_1h_close = on_1h_close
        self.running = False
        self.tick_queue = asyncio.Queue(maxsize=10000)
        self.kline_15m_queue = asyncio.Queue(maxsize=100)
        self.kline_1h_queue = asyncio.Queue(maxsize=100)
        self.last_closed_15m = None
        self.last_closed_1h = None
        self.symbol = SYMBOL.lower()
        self._worker_tasks = []

    async def start(self):
        self.running = True
        self._worker_tasks = [
            asyncio.create_task(self._tick_worker()),
            asyncio.create_task(self._kline_15m_worker()),
            asyncio.create_task(self._kline_1h_worker()),
        ]
        await asyncio.gather(
            self._stream_ticks(),
            self._stream_klines("15m", self.kline_15m_queue),
            self._stream_klines("1h", self.kline_1h_queue),
        )

    async def stop(self):
        self.running = False
        for task in self._worker_tasks:
            task.cancel()

    async def _stream_ticks(self):
        url = f"{BASE_URL}/{self.symbol}@trade"
        while self.running:
            try:
                async with websockets.connect(url) as ws:
                    async for msg in ws:
                        if not self.running:
                            break
                        data = json.loads(msg)
                        price = float(data["p"])
                        ts_ms = int(data["T"])
                        await self.tick_queue.put((price, ts_ms))
            except Exception as e:
                logging.error(f"Tick error: {e}")
                await asyncio.sleep(5)

    async def _stream_klines(self, interval, queue):
        url = f"{BASE_URL}/{self.symbol}@kline_{interval}"
        while self.running:
            try:
                async with websockets.connect(url) as ws:
                    async for msg in ws:
                        if not self.running:
                            break
                        data = json.loads(msg)
                        k = data["k"]
                        candle = {
                            "open_time": int(k["t"]),
                            "close_time": int(k["T"]),
                            "open": float(k["o"]),
                            "high": float(k["h"]),
                            "low": float(k["l"]),
                            "close": float(k["c"]),
                            "volume": float(k["v"]),
                            "is_closed": k["x"],
                        }
                        await queue.put(candle)
            except Exception as e:
                logging.error(f"Kline {interval} error: {e}")
                await asyncio.sleep(5)

    async def _tick_worker(self):
        while self.running:
            try:
                price, ts_ms = await asyncio.wait_for(self.tick_queue.get(), timeout=1.0)
                if self.on_tick:
                    self.on_tick(price, ts_ms)
            except asyncio.TimeoutError:
                continue

    async def _kline_15m_worker(self):
        while self.running:
            try:
                candle = await asyncio.wait_for(self.kline_15m_queue.get(), timeout=1.0)
                if candle["is_closed"]:
                    self.last_closed_15m = candle
                    if self.on_15m_close:
                        self.on_15m_close(candle)
            except asyncio.TimeoutError:
                continue

    async def _kline_1h_worker(self):
        while self.running:
            try:
                candle = await asyncio.wait_for(self.kline_1h_queue.get(), timeout=1.0)
                if candle["is_closed"]:
                    self.last_closed_1h = candle
                    if self.on_1h_close:
                        self.on_1h_close(candle)
            except asyncio.TimeoutError:
                continue


async def backfill_klines(symbol: str, interval: str, limit: int = 100) -> list[dict]:
    import urllib.request
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Backbencher/1.0")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    candles = []
    now_ms = int(time.time() * 1000)
    for k in data:
        ct = int(k[6])
        if ct > now_ms:
            continue  # skip live/incomplete candle
        candles.append({
            "open_time": int(k[0]),
            "close_time": ct,
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "is_closed": True,
        })
    return candles


async def fetch_klines_from(symbol: str, interval: str, start_ms: int, limit: int = 500) -> list[dict]:
    """Fetch klines starting from a specific timestamp (ms)."""
    import urllib.request
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_ms}&limit={limit}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Backbencher/1.0")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    candles = []
    for k in data:
        candles.append({
            "open_time": int(k[0]),
            "close_time": int(k[6]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "is_closed": True,
        })
    return candles

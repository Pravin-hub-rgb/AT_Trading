"""Bybit WebSocket streamer + REST backfill — production-grade with resilience.

Public streams (no auth):
  - kline_stream: 15m/1h candles with confirm flag
  - ticker_stream: real-time price
  - trade_stream: tick-level trades (like Binance @trade)

Private streams (auth needed for orders):
  - order stream, position stream

Bybit WebSocket: wss://stream.bybit.com/v5/public/linear (public)
                 wss://stream.bybit.com/v5/private (private)
Demo:            wss://stream-demo.bybit.com/v5/public/linear

REST:            https://api.bybit.com/v5/market/kline
Demo REST:       https://api-demo.bybit.com/v5/market/kline

NOTE: Bybit endpoints may be geo-blocked in some regions (e.g. India).
      Use a VPN if WebSocket or REST connections fail.

Resilience features:
  - Ping every 20s (Bybit requirement)
  - Exponential backoff + jitter on reconnect
  - Gap detection + REST backfill after reconnect
  - Last-message timeout (60s) for half-open connections
  - Queue size limits with drop-oldest
  - Connection state tracking + logging
"""

import asyncio
import json
import logging
import os
import random
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("bybit_streamer")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

IST = timedelta(hours=5, minutes=30)

# Bybit WebSocket URLs
PUBLIC_WS = "wss://stream.bybit.com/v5/public/linear"
PUBLIC_WS_DEMO = "wss://stream-demo.bybit.com/v5/public/linear"
PRIVATE_WS = "wss://stream.bybit.com/v5/private"
PRIVATE_WS_DEMO = "wss://stream-demo.bybit.com/v5/private"

# Bybit REST URLs
REST_BASE = "https://api.bybit.com"
REST_BASE_DEMO = "https://api-demo.bybit.com"

# Resilience constants
PING_INTERVAL = 20          # Bybit requires ping every 20s
PONG_TIMEOUT = 15           # Wait 15s for pong before treating dead
LAST_MSG_TIMEOUT = 60       # No message for 60s = half-open connection
MAX_BACKOFF = 60            # Max reconnect delay in seconds
INITIAL_BACKOFF = 1         # Start with 1s delay
MAX_RECONNECT_ATTEMPTS = 20 # Circuit breaker threshold
RECONNECT_WINDOW = 600      # 10-minute window for circuit breaker
FORCE_RECONNECT_SEC = 22 * 3600  # Force reconnect every ~22 hours


class BybitStreamer:
    """Bybit WebSocket streamer — production-grade with resilience.

    on_tick(price, ts_ms)           — real-time trade price
    on_15m_close(candle)            — closed 15m candle (dict with is_closed=True)
    on_1h_close(candle)             — closed 1h candle
    """

    def __init__(self, on_tick=None, on_15m_close=None, on_1h_close=None, demo=True, symbol="BTCUSDT"):
        self.on_tick = on_tick
        self.on_15m_close = on_15m_close
        self.on_1h_close = on_1h_close
        self.demo = demo
        self.symbol = symbol
        self.running = False

        # Queues with maxsize
        self.tick_queue = asyncio.Queue(maxsize=1000)
        self.kline_15m_queue = asyncio.Queue(maxsize=100)
        self.kline_1h_queue = asyncio.Queue(maxsize=100)

        self.last_closed_15m = None
        self.last_closed_1h = None
        self._worker_tasks = []

        # Current candle tracking (unconfirmed updates)
        self._current_15m = None
        self._current_1h = None

        # Resilience state
        self._last_msg_time = 0.0
        self._last_ping_time = 0.0
        self._ws = None
        self._reconnect_count = 0
        self._reconnect_times = []  # timestamps of recent reconnects
        self._force_reconnect_at = 0.0
        self._total_reconnects = 0
        self._gap_filled_count = 0

    @property
    def _public_ws_url(self):
        # Demo WS endpoint returns 404 — use live WS (DNS bypass handles it)
        return PUBLIC_WS

    @property
    def _rest_base(self):
        return REST_BASE_DEMO if self.demo else REST_BASE

    @property
    def _is_healthy(self):
        """Check if connection is healthy (message received recently)."""
        if self._last_msg_time == 0:
            return True  # Not connected yet
        return (time.time() - self._last_msg_time) < LAST_MSG_TIMEOUT

    def _log_status(self, msg):
        """Log with connection status context."""
        age = time.time() - self._last_msg_time if self._last_msg_time > 0 else 0
        logger.info(f"{msg} | last_msg={age:.0f}s ago | reconnects={self._total_reconnects}")

    def _should_reconnect(self):
        """Check circuit breaker — too many reconnects in short window."""
        now = time.time()
        # Clean old entries
        self._reconnect_times = [t for t in self._reconnect_times if now - t < RECONNECT_WINDOW]
        return len(self._reconnect_times) < MAX_RECONNECT_ATTEMPTS

    def _record_reconnect(self):
        """Record a reconnect attempt."""
        now = time.time()
        self._reconnect_times.append(now)
        self._total_reconnects += 1
        self._reconnect_count += 1
        self._force_reconnect_at = now + FORCE_RECONNECT_SEC

    def _reset_backoff(self):
        """Reset backoff on successful connection."""
        self._reconnect_count = 0

    async def _backoff_sleep(self):
        """Exponential backoff with jitter."""
        delay = min(INITIAL_BACKOFF * (2 ** self._reconnect_count), MAX_BACKOFF)
        jitter = random.uniform(0.8, 1.2)
        sleep_time = delay * jitter
        logger.warning(f"Reconnecting in {sleep_time:.1f}s (attempt {self._reconnect_count + 1})")
        await asyncio.sleep(sleep_time)

    async def start(self):
        self.running = True
        self._force_reconnect_at = time.time() + FORCE_RECONNECT_SEC
        self._worker_tasks = [
            asyncio.create_task(self._tick_worker()),
            asyncio.create_task(self._kline_15m_worker()),
            asyncio.create_task(self._kline_1h_worker()),
            asyncio.create_task(self._health_monitor()),
        ]
        await asyncio.gather(
            self._stream_trades(),
            self._stream_klines("15", self.kline_15m_queue),
            self._stream_klines("60", self.kline_1h_queue),
        )

    async def stop(self):
        self.running = False
        for task in self._worker_tasks:
            task.cancel()

    async def _health_monitor(self):
        """Monitor connection health — force reconnect if dead."""
        while self.running:
            await asyncio.sleep(10)
            try:
                now = time.time()

                # Check last message timeout
                if self._last_msg_time > 0 and (now - self._last_msg_time) > LAST_MSG_TIMEOUT:
                    logger.warning(f"No message for {now - self._last_msg_time:.0f}s — forcing reconnect")
                    if self._ws:
                        await self._ws.close()
                    continue

                # Check force reconnect interval
                if now > self._force_reconnect_at and self._ws:
                    logger.info(f"Force reconnect after {FORCE_RECONNECT_SEC // 3600}h")
                    await self._ws.close()
                    self._force_reconnect_at = now + FORCE_RECONNECT_SEC
                    continue

                # Log status periodically
                if int(now) % 60 == 0:
                    age = now - self._last_msg_time if self._last_msg_time > 0 else 0
                    logger.debug(f"Health: last_msg={age:.0f}s ago | reconnects={self._total_reconnects} | gaps_filled={self._gap_filled_count}")

            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    async def _send_ping(self, ws):
        """Send ping every 20s — Bybit requirement."""
        while self.running:
            try:
                await asyncio.sleep(PING_INTERVAL)
                if ws.closed:
                    break
                await ws.send(json.dumps({"op": "ping"}))
                self._last_ping_time = time.time()
                logger.debug("Ping sent")
            except Exception as e:
                logger.warning(f"Ping failed: {e}")
                break

    async def _stream_trades(self):
        """Stream real-time trades with resilience."""
        while self.running:
            if not self._should_reconnect():
                logger.error("Circuit breaker: too many reconnects. Waiting 5 minutes.")
                await asyncio.sleep(300)
                self._reconnect_times.clear()
                continue

            try:
                async with asyncio.timeout(LAST_MSG_TIMEOUT + 10):
                    async with websockets.connect(self._public_ws_url) as ws:
                        self._ws = ws
                        self._last_msg_time = time.time()
                        self._reset_backoff()

                        # Subscribe
                        topic = f"publicTrade.{self.symbol}"
                        await ws.send(json.dumps({"op": "subscribe", "args": [topic]}))
                        self._log_status(f"Connected to {topic}")

                        # Start ping task
                        ping_task = asyncio.create_task(self._send_ping(ws))

                        try:
                            async for msg in ws:
                                if not self.running:
                                    break
                                self._last_msg_time = time.time()
                                data = json.loads(msg)

                                # Handle pong
                                if data.get("op") == "pong":
                                    continue

                                if data.get("topic") != topic:
                                    continue

                                for trade in data.get("data", []):
                                    price = float(trade["p"])
                                    ts_ms = int(trade["T"])
                                    try:
                                        self.tick_queue.put_nowait((price, ts_ms))
                                    except asyncio.QueueFull:
                                        # Drop oldest
                                        try:
                                            self.tick_queue.get_nowait()
                                        except asyncio.QueueEmpty:
                                            pass
                                        self.tick_queue.put_nowait((price, ts_ms))
                                        logger.warning("Tick queue full — dropped oldest")
                        finally:
                            ping_task.cancel()

            except Exception as e:
                logger.error(f"Trade stream error: {e}")
                self._record_reconnect()
                await self._backoff_sleep()

    async def _stream_klines(self, interval: str, queue: asyncio.Queue):
        """Stream kline/candle data with resilience + gap recovery."""
        topic = f"kline.{interval}.{self.symbol}"
        step_ms = {"1": 60000, "5": 300000, "15": 900000, "60": 3600000}.get(interval, 900000)

        while self.running:
            if not self._should_reconnect():
                logger.error("Circuit breaker: too many reconnects. Waiting 5 minutes.")
                await asyncio.sleep(300)
                self._reconnect_times.clear()
                continue

            try:
                async with asyncio.timeout(LAST_MSG_TIMEOUT + 10):
                    async with websockets.connect(self._public_ws_url) as ws:
                        self._ws = ws
                        self._last_msg_time = time.time()
                        self._reset_backoff()

                        # Subscribe
                        await ws.send(json.dumps({"op": "subscribe", "args": [topic]}))
                        self._log_status(f"Connected to {topic}")

                        # Gap detection: backfill missing candles
                        await self._backfill_gap(interval, queue, step_ms)

                        # Start ping task
                        ping_task = asyncio.create_task(self._send_ping(ws))

                        try:
                            async for msg in ws:
                                if not self.running:
                                    break
                                self._last_msg_time = time.time()
                                data = json.loads(msg)

                                # Handle pong
                                if data.get("op") == "pong":
                                    continue

                                if data.get("topic") != topic:
                                    continue

                                for k in data.get("data", []):
                                    candle = {
                                        "open_time": int(k["start"]),
                                        "close_time": int(k["end"]),
                                        "open": float(k["open"]),
                                        "high": float(k["high"]),
                                        "low": float(k["low"]),
                                        "close": float(k["close"]),
                                        "volume": float(k["volume"]),
                                        "is_closed": k.get("confirm", False),
                                    }
                                    try:
                                        queue.put_nowait(candle)
                                    except asyncio.QueueFull:
                                        try:
                                            queue.get_nowait()
                                        except asyncio.QueueEmpty:
                                            pass
                                        queue.put_nowait(candle)
                                        logger.warning(f"Kline {interval} queue full — dropped oldest")
                        finally:
                            ping_task.cancel()

            except Exception as e:
                logger.error(f"Kline {interval} stream error: {e}")
                self._record_reconnect()
                await self._backoff_sleep()

    async def _backfill_gap(self, interval: str, queue: asyncio.Queue, step_ms: int):
        """Backfill missing candles after reconnect using REST API."""
        last_closed = self.last_closed_15m if interval == "15" else self.last_closed_1h
        if last_closed is None:
            return  # No gap to fill (first connect)

        last_ts = last_closed.get("open_time", 0)
        if last_ts == 0:
            return

        now_ms = int(time.time() * 1000)
        if now_ms - last_ts < step_ms * 2:
            return  # Gap is less than 2 candles — not worth backfilling

        logger.info(f"Gap detected: last closed {interval}m candle at {last_ts}, backfilling...")

        try:
            # Fetch candles from REST
            missing = self._fetch_klines_rest(interval, start_ms=last_ts + step_ms)
            if not missing:
                return

            # Dedup and enqueue
            seen = set()
            added = 0
            for candle in missing:
                if candle["open_time"] in seen:
                    continue
                seen.add(candle["open_time"])
                try:
                    queue.put_nowait(candle)
                except asyncio.QueueFull:
                    break
                added += 1
                # Update last closed
                if candle["is_closed"]:
                    if interval == "15":
                        self.last_closed_15m = candle
                    else:
                        self.last_closed_1h = candle

            self._gap_filled_count += added
            logger.info(f"Backfilled {added} {interval}m candles (deduped {len(missing) - added})")

        except Exception as e:
            logger.error(f"Backfill failed for {interval}m: {e}")

    def _fetch_klines_rest(self, interval: str, start_ms: int, limit: int = 500) -> list[dict]:
        """Fetch klines from REST API for gap backfill."""
        step_ms = {"1": 60000, "5": 300000, "15": 900000, "60": 3600000}.get(interval, 900000)
        base = REST_BASE_DEMO if self.demo else REST_BASE

        all_candles = []
        cur = start_ms
        now_ms = int(time.time() * 1000)

        while len(all_candles) < limit:
            batch_limit = min(limit - len(all_candles), 1000)
            if batch_limit <= 0:
                break

            url = f"{base}/v5/market/kline?category=linear&symbol={self.symbol}&interval={interval}&limit={batch_limit}&start={cur}"
            req = urllib.request.Request(url, headers={"User-Agent": "Backbencher/1.0"})

            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode())

            if body.get("retCode") != 0:
                raise RuntimeError(f"Bybit API error: {body.get('retMsg', 'unknown')}")

            data = body["result"]["list"]
            if not data:
                break

            for k in data:
                all_candles.append({
                    "open_time": int(k[0]),
                    "close_time": int(k[0]) + step_ms,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "is_closed": True,
                })

            nxt = int(data[-1][0]) + step_ms
            if nxt <= cur or len(data) < batch_limit:
                break
            cur = nxt

        # Bybit returns newest-first; we need oldest-first
        all_candles.reverse()

        # Filter out live/incomplete candle
        now_ms = int(time.time() * 1000)
        all_candles = [c for c in all_candles if c["close_time"] <= now_ms]

        return all_candles

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

    def get_status(self):
        """Return connection status for monitoring."""
        now = time.time()
        return {
            "running": self.running,
            "last_msg_age": now - self._last_msg_time if self._last_msg_time > 0 else None,
            "total_reconnects": self._total_reconnects,
            "gaps_filled": self._gap_filled_count,
            "is_healthy": self._is_healthy,
            "force_reconnect_in": max(0, self._force_reconnect_at - now) if self._force_reconnect_at > 0 else None,
        }


def backfill_klines_bybit(symbol: str, interval: str, limit: int = 100,
                          demo: bool = True, start_ms: int = 0) -> list[dict]:
    """Fetch historical klines from Bybit REST API.

    Args:
        symbol: e.g. "BTCUSDT"
        interval: "15" for 15m, "60" for 1h, "1" for 1m
        limit: max 1000 per request (auto-paginates if more needed)
        demo: True for demo trading endpoint
        start_ms: start time in epoch ms (0 = last N candles)
    """
    base = REST_BASE_DEMO if demo else REST_BASE
    step_ms = {"1": 60000, "5": 300000, "15": 900000, "60": 3600000, "240": 14400000}.get(interval, 900000)

    all_candles = []
    cur = start_ms if start_ms > 0 else 0
    now_ms = int(time.time() * 1000)

    while True:
        batch_limit = min(limit - len(all_candles), 1000)
        if batch_limit <= 0:
            break

        url = f"{base}/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit={batch_limit}"
        if cur > 0:
            url += f"&start={cur}"

        req = urllib.request.Request(url, headers={"User-Agent": "Backbencher/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())

        if body.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error: {body.get('retMsg', 'unknown')}")

        data = body["result"]["list"]
        if not data:
            break

        for k in data:
            all_candles.append({
                "open_time": int(k[0]),
                "close_time": int(k[0]) + step_ms,
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "is_closed": True,
            })

        nxt = int(data[-1][0]) + step_ms
        if nxt <= cur or len(data) < batch_limit:
            break
        cur = nxt

        if len(all_candles) >= limit:
            break

    # Bybit returns newest-first; we need oldest-first
    all_candles.reverse()

    # Filter out live/incomplete candle (close_time > now)
    now_ms = int(time.time() * 1000)
    all_candles = [c for c in all_candles if c["close_time"] <= now_ms]

    return all_candles

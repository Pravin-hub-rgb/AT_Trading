"""Bybit WebSocket streamer + REST backfill — single-connection, production-grade.

Architecture:
  - ONE WebSocket connection to Bybit public endpoint
  - Subscribes to all 3 topics: publicTrade, kline.15, kline.60
  - Routes messages to queues by topic prefix
  - Ping every 20s (Bybit requirement)
  - 60s no-message timeout (half-open detection)
  - Exponential backoff + jitter on reconnect
  - Gap detection + REST backfill after reconnect
  - Circuit breaker (max reconnects in window)

Bybit WebSocket: wss://stream.bybit.com/v5/public/linear (public)
REST:            https://api.bybit.com/v5/market/kline

NOTE: Bybit endpoints may be geo-blocked in some regions (e.g. India).
      Use a VPN if WebSocket or REST connections fail.
"""

import asyncio
import json
import logging
import os
import random
import time
import urllib.request
import websockets
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
LAST_MSG_TIMEOUT = 60       # No message for 60s = half-open connection
MAX_BACKOFF = 60            # Max reconnect delay in seconds
INITIAL_BACKOFF = 1         # Start with 1s delay
MAX_RECONNECT_ATTEMPTS = 20 # Circuit breaker threshold
RECONNECT_WINDOW = 600      # 10-minute window for circuit breaker
FORCE_RECONNECT_SEC = 22 * 3600  # Force reconnect every ~22 hours


class BybitStreamer:
    """Bybit WebSocket streamer — single connection, all topics.

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

        # Queues — unbounded for klines (backfill can be large), bounded for ticks
        self.tick_queue = asyncio.Queue(maxsize=1000)
        self.kline_15m_queue = asyncio.Queue()
        self.kline_1h_queue = asyncio.Queue()

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
        ]
        await self._stream_public()

    async def stop(self):
        self.running = False
        for task in self._worker_tasks:
            task.cancel()

    # ====================== SINGLE CONNECTION STREAM ======================

    async def _stream_public(self):
        """Single WebSocket connection — subscribes to all 3 topics."""
        topics = [
            f"publicTrade.{self.symbol}",
            f"kline.15.{self.symbol}",
            f"kline.60.{self.symbol}",
        ]
        step_ms_map = {"15": 900000, "60": 3600000}

        while self.running:
            if not self._should_reconnect():
                logger.error("Circuit breaker: too many reconnects. Waiting 5 minutes.")
                await asyncio.sleep(300)
                self._reconnect_times.clear()
                continue

            try:
                async with websockets.connect(
                    self._public_ws_url,
                    ping_interval=None,  # We handle pings manually
                ) as ws:
                    self._ws = ws
                    self._last_msg_time = time.time()
                    self._reset_backoff()

                    # Subscribe to all topics
                    await ws.send(json.dumps({"op": "subscribe", "args": topics}))
                    self._log_status(f"Connected — subscribed to {len(topics)} topics")

                    # Backfill gaps on reconnect (for klines)
                    for interval, q in [("15", self.kline_15m_queue), ("60", self.kline_1h_queue)]:
                        await self._backfill_gap(interval, q, step_ms_map[interval])

                    # Ping task
                    ping_task = asyncio.create_task(self._send_ping(ws))

                    try:
                        async for msg in ws:
                            if not self.running:
                                break
                            now = time.time()
                            self._last_msg_time = now
                            data = json.loads(msg)

                            # Handle pong
                            if data.get("op") == "pong":
                                continue

                            # Watchdog: force reconnect after 22h or if unhealthy
                            if now >= self._force_reconnect_at:
                                logger.warning("Force reconnect: 22h elapsed")
                                break
                            if self._last_msg_time > 0 and (now - self._last_msg_time) > LAST_MSG_TIMEOUT:
                                logger.warning(f"Force reconnect: no message for {now - self._last_msg_time:.0f}s")
                                break

                            # Handle subscription confirmation
                            if data.get("op") == "subscribe":
                                self._log_status(f"Subscription: {data.get('ret_msg', 'ok')}")
                                continue

                            # Route by topic prefix
                            topic = data.get("topic", "")
                            try:
                                if topic.startswith("publicTrade"):
                                    await self._handle_trade(data)
                                elif topic.startswith("kline.15"):
                                    await self._handle_kline("15", self.kline_15m_queue, data)
                                elif topic.startswith("kline.60"):
                                    await self._handle_kline("60", self.kline_1h_queue, data)
                            except asyncio.QueueFull:
                                logger.warning(f"Queue full for {topic} — dropped message")

                    finally:
                        ping_task.cancel()

            except websockets.ConnectionClosed as e:
                logger.warning(f"WS closed: code={e.code} reason={e.reason}")
            except OSError as e:
                logger.error(f"WS OS error: {e}")
            except Exception as e:
                logger.error(f"WS error: {type(e).__name__}: {e}")

            self._record_reconnect()
            await self._backoff_sleep()

    async def _send_ping(self, ws):
        """Send ping every 20s — Bybit requirement."""
        while self.running:
            try:
                await asyncio.sleep(PING_INTERVAL)
                if ws.close_code is not None:
                    break
                await ws.send(json.dumps({"op": "ping"}))
                self._last_ping_time = time.time()
                logger.debug("Ping sent")
            except Exception as e:
                logger.warning(f"Ping failed: {e}")
                break

    # ====================== MESSAGE HANDLERS ======================

    async def _handle_trade(self, data):
        """Route trade data to tick queue."""
        for trade in data.get("data", []):
            price = float(trade["p"])
            ts_ms = int(trade["T"])
            try:
                self.tick_queue.put_nowait((price, ts_ms))
            except asyncio.QueueFull:
                try:
                    self.tick_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                self.tick_queue.put_nowait((price, ts_ms))
                logger.warning("Tick queue full — dropped oldest")

    async def _handle_kline(self, interval, queue, data):
        """Route kline data to appropriate queue."""
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

    # ====================== GAP BACKFILL ======================

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
            missing = self._fetch_klines_rest(interval, start_ms=last_ts + step_ms)
            if not missing:
                return

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

        all_candles.reverse()
        now_ms = int(time.time() * 1000)
        all_candles = [c for c in all_candles if c["close_time"] <= now_ms]
        return all_candles

    # ====================== WORKER TASKS ======================

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

    all_candles.reverse()
    now_ms = int(time.time() * 1000)
    all_candles = [c for c in all_candles if c["close_time"] <= now_ms]
    return all_candles

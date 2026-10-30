"""Show the data source and starting point for the Oct 20 analysis."""
import sys, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff"))

from bybit_streamer import backfill_klines_bybit

IST = timedelta(hours=5, minutes=30)

print('=== DATA SOURCE ===')
print('Bybit REST: https://api.bybit.com/v5/market/kline')
print('category=linear symbol=BTCUSDT (perpetual swap = BTCUSDT.P on TradingView)')
print('demo=True (testnet endpoint)')
print()

start_dt = datetime(2026, 10, 19, 18, 30, 0, tzinfo=timezone.utc)
start_ms = int(start_dt.timestamp() * 1000)

print('=== START POINT ===')
print('UTC start: 2026-10-19 18:30:00 (epoch ms: {})'.format(start_ms))
print('IST start: Oct 20 2026 00:00:00 IST = first 15m bar open')
print()

raw = backfill_klines_bybit('BTCUSDT', '15', limit=516, demo=True, start_ms=start_ms)
now_ms = int(time.time() * 1000)
raw = [c for c in raw if c.get('close_time', 0) <= now_ms]
raw.sort(key=lambda k: k['open_time'])

print('=== FIRST 5 CANDLES (15m from Bybit) ===')
for c in raw[:5]:
    ot = c['open_time']
    ct = c['close_time']
    utc_open = datetime.fromtimestamp(ot / 1000, tz=timezone.utc)
    ist_open = utc_open + IST
    utc_close = datetime.fromtimestamp(ct / 1000, tz=timezone.utc)
    ist_close = utc_close + IST
    print('  open_time={} (UTC={} IST={})'.format(
        ot,
        utc_open.strftime('%Y-%m-%d %H:%M'),
        ist_open.strftime('%Y-%m-%d %H:%M')))
    print('    O={} H={} L={} C={}'.format(c['open'], c['high'], c['low'], c['close']))
    print('  close_time={} (UTC close={} IST close={})'.format(
        ct,
        utc_close.strftime('%Y-%m-%d %H:%M'),
        ist_close.strftime('%Y-%m-%d %H:%M')))

print()
print('Total 15m candles fetched: {}'.format(len(raw)))
print('First candle open (IST): {}'.format(
    (datetime.fromtimestamp(raw[0]['open_time'] / 1000, tz=timezone.utc) + IST).strftime('%Y-%m-%d %H:%M:%S')))
print('Last candle close (IST): {}'.format(
    (datetime.fromtimestamp(raw[-1]['close_time'] / 1000, tz=timezone.utc) + IST).strftime('%Y-%m-%d %H:%M:%S')))

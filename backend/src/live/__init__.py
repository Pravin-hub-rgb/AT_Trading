"""live — BTC v18 paper-trader package.

ONE engine, ONE strategy (v18), zero dead code. Imports the 7 shared
parity-tested modules listed in MANIFEST.md; never copies them.

Build order (each step verifiable alone):
  1. daily_fetch.py   — after UTC midnight download klines, append to data/btc CSVs
  2. compare.py       — journal vs backtester diff -> PARITY OK / MISMATCH
  3. feeder.py        — websocket 1m -> aggregate 15m/1h -> recompute -> decide -> journal
  4. deploy/          — systemd unit + cron for the daily loop

Frozen v18 parameters live in params.py. Any change there must re-pass
the 33-test checklist + daily parity before redeploy.
"""

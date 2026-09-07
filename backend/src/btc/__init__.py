"""BTC engine package — fully isolated from the Nifty pipeline.

Everything in here is BTC-only:
    - no Nifty/session/Upstox imports
    - reads CSVs from <repo>/data/btc/
    - continuous 24/7 walking (no per-day reseed by default)

server.py mounts these routes with a single app.include_router() call.
"""

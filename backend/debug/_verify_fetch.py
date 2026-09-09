"""Verify the fetch module and route import cleanly."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 1. fetch module
from src.btc.btc_fetch import refresh_all, last_ts

print("=== fetch module ===")
print("15m last:", last_ts("15m"))
print("1h last:", last_ts("1h"))

# 2. route module imports fetch cleanly
from src.btc import btc_routes

print("\n=== route module ===")
print("fetch route registered:", any(r.path == "/api/btc/fetch" for r in btc_routes.router.routes))
print("fetch/status route registered:", any(r.path == "/api/btc/fetch/status" for r in btc_routes.router.routes))

# 3. live log exists
log = Path(__file__).resolve().parents[1] / "src" / "live" / "_run_live.txt"
print("\n=== live log ===")
print("exists:", log.exists(), "| lines:", len(log.read_text(encoding="utf-8").splitlines()) if log.exists() else 0)

print("\nALL OK")

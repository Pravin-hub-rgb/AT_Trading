"""End-to-end route check on Bybit perp with the books' own parameters.

This is the only check that goes through the API rather than the engine directly,
so it catches wiring the engine-level harnesses cannot see.

Run: python -u exp_verify_route.py
"""
import json, urllib.request

QS = ("tf=15m&mode=continuous&min_bars=50&htf_min_bars=10&htf_tf=1h"
      "&symbol=BTCUSDT_BYBIT")
out = []
for v in ("v19_champion", "v19_c16", "v19_causal"):
    url = f"http://localhost:8003/api/btc/backtest?{QS}&version={v}"
    try:
        with urllib.request.urlopen(url, timeout=1200) as r:
            data = json.load(r)
        tr = [t for t in data.get("trades", []) if t.get("outcome") != "open"]
        g = sum(float(t["r_multiple"]) for t in tr)
        out.append(f"  {v:16s} n={len(tr):<5d} gross {g:+9.2f}R")
    except Exception as e:
        out.append(f"  {v:16s} ERROR {e}")

out.append("")
out.append("  harness, same rules : origin 500 / +445.22R gross, leg 499 / +355.72R gross")
txt = "\n".join(out)
print(txt)
open(r"C:\Users\Pravin\Desktop\main\AT_Trading\backtest\tests\_vroute.txt", "w",
     encoding="utf-8").write(txt)
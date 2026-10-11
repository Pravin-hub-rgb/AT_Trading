import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Pravin\Desktop\main\AT_Trading")
ENG = ROOT / "backend" / "src" / "firstswing.py"
SWG = ROOT / "backend" / "src" / "btc" / "btc_swing.py"

PROBE = r'''
import json, sys
from pathlib import Path
ROOT = Path(r"@ROOT@")
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT / "backtest/tests"))
from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
candles = list(candles); flow = list(flow)
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))
m = {}
for s in sw:
    for b in s["breaks"]:
        m.setdefault(b["time"][:16], []).append("%s %s @%.1f" % (b["kind"], b["dir"], b["px"]))
print(json.dumps({"marks": m, "swings": len(sw),
                  "nmarks": sum(len(s["breaks"]) for s in sw),
                  "candles": [[c["date"][:16], c["high"], c["low"]] for c in candles]}))
'''

CASES = [("2023-01-03", "12:45"), ("2023-02-04", "15:45"), ("2023-02-13", "16:45")]
BACK = 5
FWD = 3


def run():
    p = subprocess.run([sys.executable, "-c", PROBE.replace("@ROOT@", str(ROOT))],
                       capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        raise SystemExit(p.stderr[-600:])
    return json.loads(p.stdout)


after = run()
old_src = subprocess.run(["git", "show", "HEAD:backend/src/firstswing.py"],
                         capture_output=True, text=True, encoding="utf-8",
                         cwd=str(ROOT)).stdout
new_src = ENG.read_text(encoding="utf-8")
bak = new_src
try:
    ENG.write_text(old_src, encoding="utf-8")
    before = run()
finally:
    ENG.write_text(bak, encoding="utf-8")

print("=" * 100)
print("THE 3 CASES  -  before vs after the window-return fix")
print("=" * 100)
print("  chain:  before %d swings / %d marks      after %d swings / %d marks"
      % (before["swings"], before["nmarks"], after["swings"], after["nmarks"]))
print()

for d, t in CASES:
    key = "%s %s" % (d, t)
    b = before["marks"].get(key, [])
    a = after["marks"].get(key, [])
    idx = next((i for i, c in enumerate(before["candles"]) if c[0] == key), None)
    print("-" * 100)
    verdict = "*** REGRESSION ***" if (b and not a) else ("NEW MARK" if (a and not b) else "unchanged")
    print("  %s     BEFORE: %-22s  AFTER: %-22s  %s"
          % (key, ", ".join(b) if b else "NO MARK", ", ".join(a) if a else "NO MARK", verdict))
    if idx is not None:
        for i in range(max(0, idx - BACK), min(len(before["candles"]), idx + FWD + 1)):
            c = before["candles"][i]
            mk = ", ".join(before["marks"].get(c[0], [])) or ""
            mn = ", ".join(after["marks"].get(c[0], [])) or ""
            if i == idx:
                print("      >> %s  H=%-9.1f L=%-9.1f   before: %-18s after: %s"
                      % (c[0], c[1], c[2], mk or "-", mn or "-"))
            elif mk or mn:
                print("         %s  H=%-9.1f L=%-9.1f   before: %-18s after: %s"
                      % (c[0], c[1], c[2], mk or "-", mn or "-"))
    print()

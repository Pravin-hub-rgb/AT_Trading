"""Every mark the window-return fix removed or added, with dates, for the owner.

Owner, 2023-01-03 12:45: the B1 there is correct. The fix removed it, so the fix is
wrong. Rather than guess which way, list every difference so he can look at the chart
and say which ones are right.

A mark that DISAPPEARED and is of a kind the owner has already confirmed is a
regression. A mark that APPEARED may be the fix working, or may be the fix going too
far. He decides; this file only shows.

Both chains are built by swapping firstswing.py between HEAD and the working tree and
restoring it in a finally block.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Pravin\Desktop\main\AT_Trading")
ENG = ROOT / "backend" / "src" / "firstswing.py"

PROBE = r'''
import json, sys
from pathlib import Path
ROOT = Path(r"@ROOT@")
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT / "backtest/tests"))
from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))
m = {}
for s in sw:
    for b in s["breaks"]:
        m.setdefault(b["time"][:16], []).append([b["kind"], b["dir"], round(b["px"], 1)])
fs = {s["fs_at_time"][:16]: s["swing_index"] for s in sw if s.get("fs_at_time")}
print(json.dumps({"marks": m, "fs": fs, "swings": len(sw),
                  "n": sum(len(s["breaks"]) for s in sw)}))
'''

# the owner's confirmed marks - these must never disappear
CONFIRMED = {
    "2023-01-03 12:45": "B1", "2023-01-14 06:45": "B1", "2023-02-04 15:45": "B1",
    "2023-02-13 04:30": "B1", "2023-02-13 16:45": "B1", "2026-08-14 22:45": "B1",
    "2023-02-05 07:30": "B1", "2023-03-11 08:30": "B1",
    "2023-01-03 12:30": None, "2023-02-05 07:00": None, "2023-03-11 08:00": None,
}


def run():
    p = subprocess.run([sys.executable, "-c", PROBE.replace("@ROOT@", str(ROOT))],
                       capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        raise SystemExit(p.stderr[-600:])
    return json.loads(p.stdout)


after = run()
old = subprocess.run(["git", "show", "HEAD:backend/src/firstswing.py"],
                     capture_output=True, text=True, encoding="utf-8",
                     cwd=str(ROOT)).stdout
new = ENG.read_text(encoding="utf-8")
try:
    ENG.write_text(old, encoding="utf-8")
    before = run()
finally:
    ENG.write_text(new, encoding="utf-8")

B, A = before["marks"], after["marks"]
removed, added, changed = [], [], []
for k in sorted(set(B) | set(A)):
    b = sorted(map(tuple, B.get(k, [])))
    a = sorted(map(tuple, A.get(k, [])))
    if b == a:
        continue
    gone = [x for x in b if x not in a]
    newm = [x for x in a if x not in b]
    for g in gone:
        removed.append((k, g))
    for n_ in newm:
        added.append((k, n_))

print("=" * 100)
print("WINDOW-RETURN FIX:  every difference against the committed chain")
print("=" * 100)
print("  committed  %d swings / %d marks" % (before["swings"], before["n"]))
print("  with fix   %d swings / %d marks" % (after["swings"], after["n"]))
print("  removed %d marks, added %d marks" % (len(removed), len(added)))
print()

bykind = {}
for k, m in removed:
    bykind.setdefault(m[0], []).append(k)
print("REMOVED, by kind")
for kind in sorted(bykind):
    d = sorted(bykind[kind])
    print("  %-5s %4d   first: %s" % (kind, len(d), ", ".join(d[:3])))
print()

reg = [(k, m) for k, m in removed if k in CONFIRMED and CONFIRMED[k] == m[0]]
print("*** REMOVED MARKS THE OWNER HAD ALREADY CONFIRMED ***" if reg
      else "no confirmed mark was removed")
for k, m in sorted(reg):
    print("     %s   %s %s @%.1f     <-- HE CONFIRMED THIS" % (k, m[0], m[1], m[2]))
print()

print("OWNER'S CONFIRMED CASES - status now")
for k in sorted(CONFIRMED):
    want = CONFIRMED[k]
    a = ", ".join("%s %s @%.1f" % (x[0], x[1], x[2]) for x in A.get(k, [])) or "NO MARK"
    b = ", ".join("%s %s @%.1f" % (x[0], x[1], x[2]) for x in B.get(k, [])) or "NO MARK"
    flag = ""
    if want is None and A.get(k):
        flag = "  *** should be NO MARK ***"
    elif want and not any(x[0] == want for x in A.get(k, [])):
        flag = "  *** MISSING ***"
    print("   %s  want %-6s | committed: %-20s | now: %-20s%s" % (k, want or "none", b, a, flag))
print()

print("FIRST 30 REMOVED  (all kinds, by date)")
for k, m in sorted(removed)[:30]:
    star = "  <== CONFIRMED BY OWNER" if k in CONFIRMED else ""
    print("   %s   %s %s @%-10.1f%s" % (k, m[0], m[1], m[2], star))
print()
print("FIRST 30 ADDED")
for k, m in sorted(added)[:30]:
    print("   %s   %s %s @%-10.1f" % (k, m[0], m[1], m[2]))

(ROOT / "backtest/tests/_fix_diff.json").write_text(json.dumps({
    "before": {"swings": before["swings"], "marks": before["n"]},
    "after": {"swings": after["swings"], "marks": after["n"]},
    "removed": [{"time": k, "kind": m[0], "dir": m[1], "px": m[2]} for k, m in sorted(removed)],
    "added": [{"time": k, "kind": m[0], "dir": m[1], "px": m[2]} for k, m in sorted(added)],
}, indent=1), encoding="utf-8")

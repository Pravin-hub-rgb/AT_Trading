"""Show the owner where fs_at moved, old engine vs fixed engine, on his own dates.

The owner is looking at a chart served by a server that has not been restarted, so
what he sees is the pre-fix build. And V7 only fingerprints B1/B2/FLIP - it says
nothing about fs_at, which is the field in question. So this computes both.

Runs the chain twice by swapping firstswing.py between the committed version and the
working-tree version, and diffs fs_at per swing. The file is restored in a finally
block whichever way it exits.

For every swing whose fs_at moved, prints the candles around the OLD and the NEW
marker plus the pivot level that was broken, so the owner can judge on the chart
rather than take the number.
"""
import importlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENG = ROOT / "backend" / "src" / "firstswing.py"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

CASES = ["2025-07-20", "2024-07-16", "2025-07-09", "2025-07-21"]


def chain():
    for m in list(sys.modules):
        if m.startswith("src.firstswing") or m.startswith("src.btc.btc_swing"):
            del sys.modules[m]
    from src.btc.btc_routes import _load_window
    from src.btc.btc_swing import compute_btc_swings
    c, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
    flow = list(flow)
    sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))
    return list(c), sw


def snap(sw):
    return [{"i": s["swing_index"], "fs": s.get("fs_at_idx"), "fs_time": s.get("fs_at_time"),
             "ca": s.get("confirmed_at_idx"), "ca_time": s.get("confirmed_at_time"),
             "end": s["seg"]["end_idx"], "start": s["seg"]["start_idx"],
             "dir": s.get("dir"), "start_px": s["seg"]["start_px"], "end_px": s["seg"]["end_px"],
             "breaks": [(b["time"], b["kind"], b["dir"], b["px"]) for b in s["breaks"]]}
            for s in sw]


def main():
    old_src = subprocess.run(["git", "show", "HEAD~1:backend/src/firstswing.py"],
                             capture_output=True, text=True, encoding="utf-8",
                             cwd=str(ROOT)).stdout
    new_src = ENG.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        bak = Path(td) / "f.py"
        shutil.copy2(ENG, bak)
        try:
            ENG.write_text(old_src, encoding="utf-8")
            candles, sw_old = chain()
            old = snap(sw_old)
            ENG.write_text(new_src, encoding="utf-8")
            candles, sw_new = chain()
            new = snap(sw_new)
        finally:
            shutil.copy2(bak, ENG)

    moved = [(o, n) for o, n in zip(old, new) if o["fs"] != n["fs"]]
    print("=" * 78)
    print("fs_at: old engine vs fixed engine")
    print("=" * 78)
    print("  swings            : %d" % len(new))
    print("  fs_at moved       : %d" % len(moved))
    print()

    by_day = {}
    for o, n in zip(old, new):
        d = str(candles[n["fs"]]["date"])[:10]
        by_day.setdefault(d, []).append((o, n))

    for day in CASES:
        print("-" * 78)
        print("OWNER'S DATE: %s" % day)
        rows = by_day.get(day, [])
        if not rows:
            near = sorted(set(by_day))[max(0, sorted(set(by_day)).index(day) - 2):
                                      sorted(set(by_day)).index(day) + 3] \
                if day in by_day else []
            print("  no fs_at falls on this date")
            print("  nearest fs_at dates: %s" % (near,))
            continue
        for o, n in rows:
            tag = "MOVED" if o["fs"] != n["fs"] else "same"
            print("  swing %-5d dir=%-4s %s" % (n["i"], n["dir"], tag))
            print("     fs_at        %-20s -> %s" % (o["fs_time"], n["fs_time"]))
            print("     confirmed_at %-20s -> %s" % (o["ca_time"], n["ca_time"]))
            print("     segment      %s @%.1f -> %s @%.1f"
                  % (candles[o["start"]]["date"][:16], o["start_px"],
                     candles[o["end"]]["date"][:16], o["end_px"]))
            for t, k, d, p in n["breaks"]:
                if t[:10] == day:
                    print("       %-18s %-5s %-5s @%-10.1f" % (t, k, d, p))
        print()

    print("=" * 78)
    print("OWNER'S 2025-07-20 candles around 13:30-16:15")
    print("=" * 78)
    fs_by_idx = {n["fs"]: n for n in new}
    brk = {}
    for n in new:
        for t, k, d, p in n["breaks"]:
            brk[t] = "%s %s @%.1f" % (k, d, p)
    for i in range(len(candles)):
        c = candles[i]
        ts = str(c["date"])
        if not ts.startswith("2025-07-20"):
            continue
        t = ts[11:16]
        if not ("13:30" <= t <= "16:15"):
            continue
        tags = []
        if i in fs_by_idx:
            tags.append("<== FS %s (was %s)" % (fs_by_idx[i]["fs_time"],
                                               [o["fs_time"] for o in old if o["i"] == fs_by_idx[i]["i"]][0]))
        print("  %s  O=%-9.1f H=%-9.1f L=%-9.1f C=%-9.1f  %-16s %s"
              % (ts[:16], c["open"], c["high"], c["low"], c["close"],
                 brk.get(ts, ""), " ".join(tags)))


if __name__ == "__main__":
    main()

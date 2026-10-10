"""Freeze the candles around the 2026-08-14 B1 case so the example survives a fix.

WHY A FIXTURE
-------------
The swing chain starts at 2023-01-01 and runs forward, so changing how breaks are
suppressed shifts every swing downstream of the change. Once that happens the
2026-08-14 22:45 example no longer reproduces, and the evidence that motivated the
change evaporates. That is exactly what the owner predicted.

So: the OHLC of the window is written to disk NOW, in full float precision, with the
dates exactly as the engine stores them (IST wall time). Any later fix must still
mark a B1 at 22:45 on this frozen slice. If it does not, the fix changed something
it did not mean to.

WHAT IS STORED
--------------
  candles.json   every 15m bar in the window, plus a little context on each side so
                 the chain has something to arm from. The file is the ground truth
                 for "what the engine saw", independent of whatever the loader does
                 later.

  case.json      the two mirrored cases the owner spotted:
                   2026-08-14 05:15  a DOWN break that DID mark a B1
                   2026-08-14 22:45  an UP break that did NOT
                Same day, same engine, opposite direction. That pair is the whole
                question - whatever differs between them is the defect.

Everything is IST.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from exp_signal_metrics import load_era            # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures"

# generous window: two days before the first case, two days after the last
WIN_FROM = "2026-08-10 00:00"
WIN_TO = "2026-08-20 00:00"

CASES = [
    {"name": "marked_down", "bar_ist": "2026-08-14 05:15", "dir": "down",
     "swing_index": 2836, "marked": True,
     "why": "the owner's mirror case - a break that DID produce a B1"},
    {"name": "missing_up", "bar_ist": "2026-08-14 22:45", "dir": "up",
     "swing_index": 2837, "marked": False,
     "why": "same day, opposite direction, no B1 - the case under investigation"},
]


def main():
    OUT.mkdir(exist_ok=True)
    d = load_era("is")
    raw = d["c15"]
    win = [x for x in raw if WIN_FROM <= x["date"][:16] <= WIN_TO]
    if not win:
        print("window is empty - dates are %s .. %s"
              % (raw[0]["date"], raw[-1]["date"]))
        return 1

    payload = {
        "tf": "15m",
        "symbol": "BTCUSDT_BYBIT",
        "timezone": "IST (dates are stored exactly as the engine stores them)",
        "note": "frozen 2026-10-10, before any break-suppression change",
        "window_from": win[0]["date"],
        "window_to": win[-1]["date"],
        "count": len(win),
        "candles": [{"date": x["date"], "open": x["open"], "high": x["high"],
                     "low": x["low"], "close": x["close"]} for x in win],
    }
    (OUT / "candles.json").write_text(json.dumps(payload, indent=1),
                                      encoding="utf-8")

    idx = {}
    for i, x in enumerate(win):
        idx[x["date"][:16]] = i

    cases = []
    for c in CASES:
        key = c["bar_ist"]
        if key not in idx:
            print("case bar %s not inside the frozen window" % key)
            return 1
        i = idx[key]
        cases.append({**c, "window_idx": i,
                      "ohlc": {k: win[i][k] for k in
                               ("open", "high", "low", "close")}})
    (OUT / "cases.json").write_text(json.dumps(
        {"cases": cases, "engine_opts": {"minBars": 50}}, indent=1),
        encoding="utf-8")

    print("wrote %s" % (OUT / "candles.json"))
    print("  %d candles, %s -> %s  (all IST)" % (len(win), win[0]["date"],
                                                win[-1]["date"]))
    print("wrote %s" % (OUT / "cases.json"))
    for c in cases:
        print("  %-13s %s  %-4s  H=%.1f  marked=%s"
              % (c["name"], c["bar_ist"], c["dir"], c["ohlc"]["high"], c["marked"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
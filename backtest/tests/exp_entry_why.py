"""
What actually opens a trade, and where does a 12:15 entry come from if the
B2 mark is at 18:30.

The engine builds its entries with:

    _collect_signals(swings_ltf, "decisive", skip_first=True,
                     selection="stream", candles=candles_ltf)

"decisive" and "stream" both matter and neither means "only FLIP". This prints
the mark stream around a date window - every B1, B2 and FLIP mark with its time
- then every signal derived from those marks, then every trade the engine
actually opened, so the chain from mark to entry is visible rather than
inferred.

Run:  python -u exp_entry_why.py 2024-11-17 2024-11-20
      (no args = that same default window)
"""
import sys, os, pickle, inspect, types
import bisect as bs
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from src.btc.btc_engine import _collect_signals, CandleStore
from src.btc.btc_routes import _load_window

DAY0 = sys.argv[1] if len(sys.argv) > 1 else "2024-11-17"
DAY1 = sys.argv[2] if len(sys.argv) > 2 else "2024-11-20"

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
c15 = d["c15"]
sw15 = d["sw15"]

# index candles by date string so mark times can be lined up with bar times
idx15 = {}
for i, c in enumerate(c15):
    idx15[str(c["date"])[:10]] = i


def ts_of(date_str):
    """candle 'date' is a wall-clock string; the ts field is the epoch."""
    for c in c15:
        if str(c["date"]) == date_str:
            return int(c["ts"])
    return None


def fmt(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M")

candle_ts_htf_close = [int(c["ts"]) + 3600 for c in d["c1h"]]
_tr = [float(c["high"]) - float(c["low"]) for c in d["c1h"]]
_n = len(d["c1h"])
_pc = [float(d["c1h"][i - 1]["close"]) for i in range(1, _n)]
atrp_series = [(_tr[i] / max(_pc[i - 1], 1e-9)) * 100.0 for i in range(1, _n)]
atrp_series.insert(0, 0.5)

print("=" * 78)
print("SWING MARKS between %s and %s  (15m chain)" % (DAY0, DAY1))
print("=" * 78)
lo = min(i for k, i in idx15.items() if k >= DAY0)
hi = max(i for k, i in idx15.items() if k <= DAY1)
for s in sw15:
    seg = s.get("seg", {})
    si = int(seg.get("start_idx", -1))
    ei = int(seg.get("end_idx", -1))
    if ei < lo or si > hi:
        continue
    conf = int(s.get("confirmed_at_idx", -1))
    print("  swing #%-4d %-4s %s->%s  confirmed@%s  final=%s"
          % (s.get("swing_index", -1), s.get("dir"),
             fmt(int(c15[si]["ts"])) if 0 <= si < len(c15) else "?",
             fmt(int(c15[ei]["ts"])) if 0 <= ei < len(c15) else "?",
             fmt(int(c15[conf]["ts"])) if 0 <= conf < len(c15) else "?",
             s.get("break_kind")))
    for b in s.get("breaks", []):
        bi = int(b.get("idx", -1))
        t = fmt(int(c15[bi]["ts"])) if 0 <= bi < len(c15) else b.get("time")
        print("        mark %-5s %-5s %s  px %.2f" % (b.get("kind"), b.get("dir"), t, float(b.get("px", 0))))

print()
print("=" * 78)
print("SIGNALS produced from those swings  (decisive, stream)")
print("=" * 78)
sigs = _collect_signals(sw15, "decisive", skip_first=True,
                        selection="stream", candles=c15)
store = CandleStore(c15)
shown = 0
for s in sigs:
    bt = ts_of(s["bar"])
    if bt is None:
        continue
    day = fmt(bt)[:10]
    if day < DAY0 or day > DAY1:
        continue
    pos = store.pos(s["bar"])
    print("  %s  %-5s dir=%+d  swing#%-5s kind=%-5s  sl_pivot=%.2f  bar_px=%.2f"
          % (fmt(bt), s["kind"], int(s["dir"]), s.get("swing_no"),
             s["kind"], float(s["swing_start_px"]), float(c15[pos]["close"])))
    shown += 1
print("  (%d signals in window)" % shown)

print()
print("=" * 78)
print("REGIME  (mode=atr_high: atrp > 0.65 -> 'decisive', else 'flip')")
print("=" * 78)
prm = EXPERIMENTS["champion_multi_sw10"]["params"]
print("  mode=%s  atr_high_thresh=%s  atr_low_thresh=%s  chop_thresh=%s"
      % (prm.get("mode"), prm.get("atr_high_thresh"),
         prm.get("atr_low_thresh"), prm.get("chop_thresh")))
print()
print("  interval sets the engine can pick from:")
print("    'flip'      -> intervals_flip    (1h trades with entry_break='flip')")
print("    'b2'        -> intervals_b2      (1h trades with entry_break='b2')")
print("    'decisive'  -> intervals_decisive(1h trades with entry_break='decisive')")
print()
print("  So the mark you see is decided by the REGIME, not by preference:")
print("    low  ATR%  -> 'flip'      -> only FLIP windows open")
print("    high ATR%  -> 'decisive'  -> only DECISIVE (B2) windows open")
print("  A swing can have BOTH a B2 and a FLIP mark. Which one can trade")
print("  depends on the regime at that bar.")


def regime_at(bar_ts):
    j = bs.bisect_right(candle_ts_htf_close, bar_ts) - 1
    if j < 0 or j >= len(atrp_series):
        return None, None
    return atrp_series[j], j


print()
print("  regime at each signal in the window:")
for s in sigs:
    bt = ts_of(s["bar"])
    if bt is None:
        continue
    day = fmt(bt)[:10]
    if day < DAY0 or day > DAY1:
        continue
    a, j = regime_at(bt)
    if a is None:
        print("    %s  %-5s  regime: no ATR value" % (fmt(bt), s["kind"]))
        continue
    use = "decisive" if a > float(prm["atr_high_thresh"]) else "flip"
    print("    %s  %-5s  ATR%%=%.4f  -> regime '%s'  (HTF bar close #%d)"
          % (fmt(bt), s["kind"], a, use, j))

print()
print("=" * 78)
print("WHAT THE ENGINE ACTUALLY ENTERED  (v19 causal, IS)")
print("=" * 78)

SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
mod = types.ModuleType("ew")
mod.__file__ = "ew.py"
exec(compile(SRC, "ew.py", "exec"), mod.__dict__)
pr = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
      if k in set(inspect.signature(mod.simulate_htf_ltf_streak_halt).parameters)
      and k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}
r = mod.simulate_htf_ltf_streak_halt(d["c1h"], d["sw10"], c15, sw15,
                                     fine_ltf=d["fine"], exp_causal_sl=1, **pr)
n = 0
for t in r["ltf_trades"]:
    day = str(t["entry_date"])[:10]
    if day < DAY0 or day > DAY1:
        continue
    print("  entry %s  %-5s  swing#%-5s  %-5s  px %.2f  sl %.2f  r %s"
          % (str(t["entry_date"])[:16], t.get("dir"), t.get("swing_no"),
             t.get("break_kind"), float(t["entry_price"]), float(t["sl"]),
             t.get("r_multiple")))
    n += 1
print("  (%d trades entered in window)" % n)

"""Which candles does the L356/L360 condition actually stop?

G2 said it never rejects. That was wrong, and this file is what proves it.

G2 read _seal_h_idx BEFORE calling process_bar. The seal is written during the
walk, inside process_bar, and the gate is evaluated after the walk. So G2 was
reading the previous bar's seal index, saw it was always older than the bar, and
concluded the condition never fires. It fires; G2 just looked at the wrong moment.

exp_g2_remove_condition.py showed the size of the effect - removing the condition
turns 7,993 marks into 8,033 - but not where. This is the where.

Method: build the chain twice, once with the two conditions and once with them
replaced by the unconditional form the other two arms already use, then diff the
two mark sets. Every difference is a candle the condition stopped. No guessing,
no sampling of engine state at the wrong moment - the engine is simply run both
ways and the two answers are subtracted.

The original file is restored afterwards whatever happens.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENG = ROOT / "backend/src/firstswing.py"

OLD = """            elif self._pending_leg_dir == "up" and up_break:
                if self._seal_h_idx >= 0 and self._seal_h_idx < g_idx:
                    self.armed = True
                    self._pending_arm = False
            elif self._pending_leg_dir == "down" and down_break:
                if self._seal_l_idx >= 0 and self._seal_l_idx < g_idx:
                    self.armed = True
                    self._pending_arm = False"""

NEW = """            elif self._pending_leg_dir == "up" and up_break:
                self.armed = True
                self._pending_arm = False
            elif self._pending_leg_dir == "down" and down_break:
                self.armed = True
                self._pending_arm = False"""

PROBE = r'''
import json, sys
from pathlib import Path
ROOT = Path(r"%s")
sys.path.insert(0, str(ROOT / "backend"))
from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow)//2))
out = [{"swing": i, **{k: b[k] for k in ("idx", "time", "kind", "dir", "px")}}
       for i, s in enumerate(sw) for b in s["breaks"]]
print(json.dumps(out))
'''


def chain_now():
    p = subprocess.run([sys.executable, "-c", PROBE % str(ROOT)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("probe failed: " + p.stderr[-800:])
    return json.loads(p.stdout)


def main():
    with tempfile.TemporaryDirectory() as td:
        bak = Path(td) / "firstswing.py"
        shutil.copy2(ENG, bak)
        try:
            src = ENG.read_text(encoding="utf-8")
            if src.count(OLD) != 1:
                raise SystemExit("could not locate the two statements uniquely")
            withcond = chain_now()
            ENG.write_text(src.replace(OLD, NEW), encoding="utf-8")
            without = chain_now()
        finally:
            shutil.copy2(bak, ENG)

    ka = {(m["time"], m["px"], m["dir"]) for m in withcond}
    kb = {(m["time"], m["px"], m["dir"]) for m in without}
    added = sorted(kb - ka)
    lost = sorted(ka - kb)

    print("=" * 78)
    print("WHICH candles does the L356/L360 condition stop?")
    print("=" * 78)
    print("  with the condition    %d marks" % len(withcond))
    print("  without the condition %d marks" % len(without))
    print("")
    print("  the condition STOPS these %d marks:" % len(added))
    for t, px, d in added:
        print("     %-20s px=%-11s dir=%s" % (t, px, d))
    print("")
    print("  the condition ALLOWS these %d marks that are absent without it: %d"
          % (len(lost), len(lost)))
    for t, px, d in lost[:10]:
        print("     %-20s px=%-11s dir=%s" % (t, px, d))
    print("")
    print("  VERDICT: the condition is %s"
          % ("DOING REAL WORK - it stops %d marks" % len(added) if added
             else "still doing nothing"))

    Path(ROOT / "backtest/tests/_g2_stopped.json").write_text(json.dumps({
        "with_condition": len(withcond), "without_condition": len(without),
        "stopped_by_condition": [{"time": t, "px": px, "dir": d} for t, px, d in added],
        "allowed_only_by_condition": [{"time": t, "px": px, "dir": d} for t, px, d in lost],
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

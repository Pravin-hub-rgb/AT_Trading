"""Does the L356/L360 condition do ANY work today?

Owner: "mujhe toh samajh he nahi aya yeh g2 kya hai... jab kuch kaam he nahi karta
hai toh burden."

G2 instrumented it and found 461 evaluations, 461 accepts, 0 rejects. That is an
observation. This is the experiment: rewrite both conditional statements as the
unconditional form the other two arms already use, rebuild the chain, and compare.

    L356   if self._seal_h_idx >= 0 and self._seal_h_idx < g_idx:
               self.armed = True
      ->
    L356   self.armed = True

If the chain comes back byte-identical at 7,993 marks, the condition is not
guarding anything on this data and the only question left is whether it guards
anything on FUTURE data.

The file is edited, the chain is rebuilt, the result printed, and the original is
restored - whether the answer is yes or no.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENG = ROOT / "backend/src/firstswing.py"
PROBE = r'''
import sys
from pathlib import Path
ROOT = Path(r"%s")
sys.path.insert(0, str(ROOT / "backend"))
from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
flow = list(flow)
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow)//2))
marks = [(b["idx"], b["time"], b["kind"], b["dir"], b["px"]) for s in sw for b in s["breaks"]]
import hashlib, json
h = hashlib.sha256(json.dumps(marks, sort_keys=True).encode()).hexdigest()[:16]
print("%%d %%d %%s" %% (len(sw), len(marks), h))
'''

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


def chain_now():
    p = subprocess.run([sys.executable, "-c", PROBE % str(ROOT)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None, p.stderr[-500:]
    return p.stdout.strip(), None


def main():
    with tempfile.TemporaryDirectory() as td:
        bak = Path(td) / "firstswing.py"
        shutil.copy2(ENG, bak)
        try:
            before, err = chain_now()
            if before is None:
                print("baseline failed:", err)
                return 1
            src = ENG.read_text(encoding="utf-8")
            if src.count(OLD) != 1:
                print("could not locate the two statements uniquely; aborting")
                return 1
            ENG.write_text(src.replace(OLD, NEW), encoding="utf-8")
            after, err = chain_now()
            print("=" * 78)
            print("G2 experiment: remove the two conditions, rebuild, compare")
            print("=" * 78)
            print("  condition present : %s   (swings marks sha)" % before)
            print("  condition REMOVED : %s" % after)
            print("")
            if after is None:
                print("  rebuild failed:", err)
            elif before == after:
                print("  IDENTICAL. The condition changed nothing on 129,715 candles.")
                print("  It is not guarding anything today.")
            else:
                print("  DIFFERENT. The condition IS doing work - G2's instrumentation")
                print("  was wrong, not the engine.")
        finally:
            shutil.copy2(bak, ENG)
            print("\n  firstswing.py restored from backup")
    return 0


if __name__ == "__main__":
    sys.exit(main())

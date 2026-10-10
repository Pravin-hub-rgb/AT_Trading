"""Is the 1.07 up/down asymmetry a BUG, or just BTC trending up more?

WHY THIS CHECK HAS TO COME FIRST
--------------------------------
exp_break_symmetry.py measured 14,968 suppressed up-breaks against 13,965
suppressed down-breaks and called the ratio "1.07 - the up side loses more". The
owner read that as an asymmetry to fix and asked for a branch and a fix.

Before changing engine behaviour on that basis, the obvious control has to be run:
**how many up-breaks and down-breaks occur AT ALL?**

Bitcoin over 2021-2026 trends up more than it trends down. If raw up-breaks are
already ~1.07x raw down-breaks, then a suppressed ratio of 1.07 means suppression is
EXACTLY symmetric and there is nothing to fix. If raw up-breaks are 1.15x but only
1.07x survive as suppressed, then suppression is biased AGAINST down and that is a
real defect worth changing.

The measured quantity is the ratio of the suppressed counts. The relevant control is
the ratio of the total counts. Comparing one without the other is how a natural
property of the data becomes an invented bug.

WHAT THIS PRINTS
----------------
  raw up/down break ratio          the data's own imbalance
  suppressed up/down ratio         what exp_break_symmetry measured
  suppression RATE per side        suppressed / raw, per direction

A symmetric engine has equal suppression RATES on both sides. Equal ratios of
counts is not the test; equal rates is.

Everything is IST.
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

from exp_signal_metrics import load_era            # noqa: E402

OLD = "        if self.armed:\n            self._step(down_break, up_break)\n"
NEW = (
    "        _g = getattr(self, '_probe', None)\n"
    "        if _g is not None:\n"
    "            _g.append({'g_idx': g_idx, 'armed': self.armed,\n"
    "                       'state': self.state,\n"
    "                       'up_break': bool(up_break), 'down_break': bool(down_break)})\n"
    + OLD
)


def patch():
    p = ROOT / "backend" / "src" / "firstswing.py"
    src = p.read_text(encoding="utf-8")
    assert src.count(OLD) == 1
    name = "src.firstswing"
    mod = types.ModuleType(name)
    mod.__file__ = str(p)
    mod.__package__ = "src"
    mod.__dict__["__name__"] = name
    sys.modules[name] = mod
    exec(compile(src.replace(OLD, NEW), str(p), "exec"), mod.__dict__)
    sys.modules.pop("src.btc.btc_swing", None)
    sys.modules[name] = mod
    return mod


def main():
    patch()
    from src.btc.btc_swing import compute_btc_swings
    from src.walker import FlowCandle
    import src.firstswing as fs_mod

    d = load_era("is")
    raw = d["c15"]
    probe = []
    real_process = fs_mod.SwingEngine.process_bar

    def wrapper(self, c, g_idx):
        self._probe = probe
        return real_process(self, c, g_idx)
    fs_mod.SwingEngine.process_bar = wrapper

    candles = [FlowCandle(x["date"], x["open"], x["high"], x["low"], x["close"])
               for x in raw]
    cap = max(1, len(candles) // 2)
    swings = compute_btc_swings(candles, opts={"minBars": 50}, max_swings=cap)
    marks = {b["idx"] for s in swings for b in s.get("breaks", [])
             if b.get("idx") is not None}

    raw_up = raw_dn = 0
    sup_up = sup_dn = 0
    armed_up = armed_dn = 0

    for r in probe:
        if r["up_break"]:
            raw_up += 1
            if not r["armed"] or r["state"] != "watch":
                sup_up += 1
            if r["armed"] and r["state"] == "watch":
                armed_up += 1
        if r["down_break"]:
            raw_dn += 1
            if not r["armed"] or r["state"] != "watch":
                sup_dn += 1
            if r["armed"] and r["state"] == "watch":
                armed_dn += 1

    ru = sup_up / raw_up * 100 if raw_up else 0
    rd = sup_dn / raw_dn * 100 if raw_dn else 0

    print()
    print("=" * 112)
    print("IS THE ASYMMETRY REAL?  raw counts vs suppression rates   (%d swings, IST)"
          % len(swings))
    print("=" * 112)
    print("  %-40s %12s %12s %10s" % ("", "UP", "DOWN", "ratio"))
    print("  " + "-" * 78)
    print("  %-40s %12d %12d %10.3f"
          % ("raw breaks (all)", raw_up, raw_dn, raw_up / raw_dn if raw_dn else 0))
    print("  %-40s %12d %12d %10.3f"
          % ("suppressed", sup_up, sup_dn, sup_up / sup_dn if sup_dn else 0))
    print("  %-40s %12d %12d %10.3f"
          % ("acted on (armed and watch)", armed_up, armed_dn,
             armed_up / armed_dn if armed_dn else 0))
    print()
    print("  %-40s %11.2f%% %11.2f%% %10.3f"
          % ("SUPPRESSION RATE", ru, rd, ru / rd if rd else 0))
    print()
    print("  marks actually recorded: %d" % len(marks))
    print()
    print("=" * 112)
    print("READ")
    print("=" * 112)
    ratio_counts = (sup_up / sup_dn) if sup_dn else 0
    ratio_raw = (raw_up / raw_dn) if raw_dn else 0
    ratio_rate = (ru / rd) if rd else 0
    print("  raw up/down break ratio      : %.3f" % ratio_raw)
    print("  suppressed up/down ratio     : %.3f   <- what was reported as a bug" % ratio_counts)
    print("  suppression RATE ratio       : %.3f   <- the real test" % ratio_rate)
    print()
    if 0.97 <= ratio_rate <= 1.03:
        print("  VERDICT: SYMMETRIC. The suppressed-count ratio just mirrors the data's own")
        print("  up bias (raw %.3f). Suppression fires at %.2f%% on up-breaks and %.2f%% on"
              % (ratio_raw, ru, rd))
        print("  down-breaks - the same rate on both sides. THERE IS NO BUG TO FIX here,")
        print("  and changing the engine would alter every pinned number for nothing.")
    elif ratio_rate > 1.05:
        print("  VERDICT: REAL BIAS. The engine suppresses %.2f%% of up-breaks but only %.2f%%"
              % (ru, rd))
        print("  of down-breaks. Up entries are being dropped materially more often, which")
        print("  understates the long side. Worth investigating.")
    else:
        print("  VERDICT: REAL BIAS, against the DOWN side. Down breaks are suppressed at")
        print("  %.2f%% against up at %.2f%%. Worth investigating." % (rd, ru))
    return 0


if __name__ == "__main__":
    sys.exit(main())
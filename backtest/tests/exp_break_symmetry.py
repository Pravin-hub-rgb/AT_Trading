"""Is the suppressed-break behaviour symmetric between long and short?

THE OWNER'S HYPOTHESIS
----------------------
On 2026-08-14 the up-break of a fresh pivot at 22:45 produced no B1. They observed
the mirrored case earlier the same day DID mark its B1 (the down-break at
05:15 on swing 2836). If a break is dropped on one side and kept on the other,
that is an asymmetry, and an asymmetry in which entries fire changes every number in
the family.

DIRECTION OF ANY BIAS - WORTH STATING FIRST
-------------------------------------------
Dropping an entry can only remove trades. It cannot add them. So this mechanism is
conservative by construction: if it is asymmetric, it is asymmetric AGAINST one
side, and the affected book's net is understated rather than inflated. That is a
correctness question, not a results-inflation question, and both need separate
answers.

WHAT THIS MEASURES
------------------
Replay the real chain and count every bar where a break condition was True but no
mark could be produced, split by the break's direction (up vs down), and compare
the two rates. A ratio near 1.0 means symmetric.

"Suppressed" is counted at two depths, because they are different failures:
  dropped_at_armed   up/down_break was True while self.armed was False
  dropped_locked     up/down_break was True while armed but state was not "watch"

Written after the first two attempts at this harness produced wrong answers: one
built SwingEngine directly and missed the sustainBars/b2GapBars option defaults, the
other registered the patched module under a side name so btc_swing bound the
unpatched class. Both produced plausible-looking output. The class is now replaced
in sys.modules AS src.firstswing and the real compute_btc_swings is called with the
same minBars and cap the harness uses, so options are correct by construction.

Everything is IST.
"""
import sys
import types
from collections import Counter
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
    "                       'state': self.state, 'dir': self.dir,\n"
    "                       'dir_confirmed': self.dir_confirmed,\n"
    "                       'up_break': bool(up_break), 'down_break': bool(down_break),\n"
    "                       'flip_established': self.flip_established,\n"
    "                       'ever_b1_dir': self.ever_b1_dir,\n"
    "                       'c_high': c.high, 'c_low': c.low})\n"
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

    def dt(i):
        return raw[i]["date"][:16] if 0 <= i < len(raw) else "-"

    up_armed = dn_armed = up_locked = dn_locked = 0
    up_armed_marked = dn_armed_marked = 0
    ex_up, ex_dn = [], []

    for r in probe:
        g = r["g_idx"]
        marked = g in marks
        if r["up_break"]:
            if not r["armed"]:
                up_armed += 1
                up_armed_marked += marked
                if not marked and len(ex_up) < 4:
                    ex_up.append(g)
            elif r["state"] != "watch":
                up_locked += 1
        if r["down_break"]:
            if not r["armed"]:
                dn_armed += 1
                dn_armed_marked += marked
                if not marked and len(ex_dn) < 4:
                    ex_dn.append(g)
            elif r["state"] != "watch":
                dn_locked += 1

    print()
    print("=" * 118)
    print("SUPPRESSED BREAKS - real chain, %d swings, %d candles, all times IST" % (len(swings), len(candles)))
    print("=" * 118)
    print("  A suppressed break is a bar where the break condition was TRUE and no")
    print("  mark was produced. Dropping an entry removes a trade, so this can only")
    print("  UNDERSTATE a book - never inflate it.")
    print()
    print("  %-34s %9s %9s %8s" % ("bucket", "up-breaks", "dn-breaks", "ratio"))
    print("  " + "-" * 64)
    print("  %-34s %9d %9d %8s"
          % ("break True while armed=False", up_armed, dn_armed,
             "%.2f" % (up_armed / dn_armed if dn_armed else float("nan"))))
    print("  %-34s %9d %9d %8s"
          % ("break True while armed, not watch", up_locked, dn_locked,
             "%.2f" % (up_locked / dn_locked if dn_locked else float("nan"))))
    print()
    tot_up = up_armed + up_locked
    tot_dn = dn_armed + dn_locked
    print("  TOTAL suppressed   up %d   down %d" % (tot_up, tot_dn))
    if tot_dn:
        print("  ASYMMETRY up/down = %.2f   (1.00 would be symmetric)"
              % (tot_up / tot_dn))
        worse = "UP" if tot_up > tot_dn else "DOWN"
        print("  Side losing more breaks: %s - that side's net is understated by more."
              % worse)
    print()
    print("  of the not-armed up-breaks, %d still received a mark later" % up_armed_marked)
    print("  of the not-armed dn-breaks, %d still received a mark later" % dn_armed_marked)
    print()
    print("  sample suppressed up-break bars (IST): %s"
          % ", ".join(dt(g) for g in ex_up))
    print("  sample suppressed dn-break bars (IST): %s"
          % ", ".join(dt(g) for g in ex_dn))
    return 0


if __name__ == "__main__":
    sys.exit(main())
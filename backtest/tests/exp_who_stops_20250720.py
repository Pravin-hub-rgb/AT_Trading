"""WHO is stopping the FS at 15:15 on 2025-07-20?

Owner, verbatim: "We have to find it that who is stopping that. That's it. Just do
some reverse engineering. The thing is very simple. It is breaking a pivot, that's
it. Who is stopping it? ... Either it is 50 bar gate. Other than that, I don't know
who is stopping it."

So: instrument every way _check_chop can refuse, separately, and print which one
fires on the bar in question. No theory, no patch - just what the engine does.

The ways it can refuse, in the order they are reached:

  R1  just_fired_b2                      -> _check_chop returns immediately
  R2  bars_seen < min_bars               -> returns BEFORE the target is computed,
                                            so no gate code exists at all for this bar
  R3  _chop_target_low returns None      -> with the reason: no pivot / too young /
                                            stale structure / gap failed
  R4  the cross itself is false          -> self.lo < tgt.px does not hold
  R5  _confirm refuses                   -> time_cap, or bars_seen again

Read from inside process_bar so the bar data is aligned: every value printed is the
engine's state for the bar named, not for the bar before it.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.firstswing import SwingEngine
from src.btc.btc_routes import _load_window

DAY, LO, HI = "2025-07-20", "14:00", "16:45"
candles, flow = _load_window("15m", 200000, "BTCUSDT_BYBIT")[0]
candles = list(candles)
flow = list(flow)

ROWS = []
real_step = SwingEngine.process_bar
real_tgt_lo = SwingEngine._chop_target_low
real_tgt_hi = SwingEngine._chop_target_high
real_confirm = SwingEngine._confirm

CUR = {"i": -1, "leg": 0}


def gate_detail(self, kind):
    """Evaluate every gate by hand so each verdict is separate. No engine state is
    modified - this only reads."""
    p = self.latest_sealed_high if kind == "H" else self.latest_sealed_low
    d = {"p": p, "why": "OK"}
    if p is None:
        d["why"] = "NO_PIVOT (walker has none)"
    elif p.idx < 0:
        d["why"] = "NO_PIVOT (idx %d)" % p.idx
    elif p.idx > self.g_idx - 2:
        d["why"] = "TOO_YOUNG (pivot bar %d, needs <= %d)" % (p.idx, self.g_idx - 2)
    elif 0 <= self.dir_established_idx and p.idx <= self.dir_established_idx:
        d["why"] = "STALE_STRUCTURE (pivot %d <= dir_established %d)" % (
            p.idx, self.dir_established_idx)
    else:
        if kind == "H":
            g = self.bar_highs.get(p.idx + 1)
            bad = (g is None or g > p.px)
        else:
            g = self.bar_lows.get(p.idx + 1)
            bad = (g is None or g < p.px)
        if bad:
            d["why"] = "GAP_FAILED (next bar %s vs pivot %.1f)" % (g, p.px)
    return d


def confirm(self, src, trig=None):
    t = str(self.t)
    if t.startswith(DAY) and LO <= t[11:16] <= HI:
        why = ""
        if self.t[11:16] < self.time_cap:
            why = "R5 time_cap (%s < %s)" % (self.t[11:16], self.time_cap)
        elif self.bars_seen < self.min_bars:
            why = "R5 bars_seen %d < %d" % (self.bars_seen, self.min_bars)
        ROWS[-1]["confirmed"] = (True, why or "FIRED")
    return real_confirm(self, src, trig)


def step(self, c, i):
    t = str(c.date)
    if t.startswith(DAY) and LO <= t[11:16] <= HI:
        kind = "H" if self.dir == "down" else "L"
        d = gate_detail(self, kind)
        p = d["p"]
        bs, mbs = self.bars_seen, self.min_bars
        cross = False
        if p is not None and d["why"] == "OK":
            cross = (self.hi > p.px) if kind == "H" else (self.lo < p.px)
        ROWS.append({
            "t": t[11:16], "leg": CUR["leg"], "dir": self.dir, "state": self.state,
            "armed": self.armed, "bs": bs, "min": mbs, "kind": kind,
            "p_px": getattr(p, "px", None), "p_idx": getattr(p, "idx", None),
            "p_time": (getattr(p, "time", "") or "-")[11:16],
            "why": d["why"], "cross": cross, "hi": self.hi, "lo": self.lo,
            "jfb2": self.just_fired_b2,
            "r2": bs < mbs, "confirmed": None,
        })
    r = real_step(self, c, i)
    return r


ri = SwingEngine.__init__


def init(self, *a, **kw):
    CUR["leg"] += 1
    ri(self, *a, **kw)


SwingEngine.__init__ = init
SwingEngine.process_bar = step
SwingEngine._confirm = confirm

from src.btc.btc_swing import compute_btc_swings
sw = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=max(1, len(flow) // 2))

print("=" * 118)
print("2025-07-20 %s-%s   WHO STOPS THE FS?   (owner: it is breaking the 14:45 pivot)" % (LO, HI))
print("=" * 118)
print("  time   leg dir  state  armed bs/50  jfb2  R2   pivot      at      verdict              cross  bar H / L")
print("  " + "-" * 116)
for r in ROWS:
    print("  %s  %-4d %-4s %-6s %-6s %-5s %-5s %-4s %-11s %-7s %-20s %-6s %.1f / %.1f"
          % (r["t"], r["leg"], r["dir"], r["state"], str(r["armed"]),
             "%d/%d" % (r["bs"], r["min"]), r["jfb2"], r["r2"],
             r["p_px"] if r["p_px"] is not None else "None",
             r["p_time"],
             r["why"],
             "CROSS" if r["cross"] else "-", r["hi"], r["lo"]))

print()
print("WHERE THE FS ACTUALLY LANDS:")
for s in sw:
    if str(s.get("fs_at_time", "")).startswith(DAY):
        print("   swing %d  fs_at=%s  confirmed=%s" % (s["swing_index"], s.get("fs_at_time"),
                                                       s.get("confirmed_at_time")))
print()
print("READING THE COLUMNS")
print("   R2   True means bars_seen < min_bars, so _check_chop returns BEFORE the target")
print("        is ever computed. No pivot verdict exists for that bar at all.")
print("   cross  True means the engine's own rule says this bar breaks the pivot.")
print("   So a row with cross=True but no FS means something downstream refused it.")

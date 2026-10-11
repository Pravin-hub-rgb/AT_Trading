import sys, types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from exp_signal_metrics import load_era
from src.walker import FlowCandle

d = load_era('is')
raw = d['c15']
candles = [FlowCandle(x['date'], x['open'], x['high'], x['low'], x['close']) for x in raw]

TARGETS = {3366, 4124, 6634}

OLD = "        if self.armed:\n            self._step(down_break, up_break)\n"
NEW = (
    "        if g_idx in _T:\n"
    "            _R.append(dict(g_idx=g_idx, armed=self.armed, state=self.state, dir=self.dir,\n"
    "                up=bool(up_break), down=bool(down_break),\n"
    "                pa=self._pending_arm, pd=self._pending_leg_dir,\n"
    "                hp=(self.e_hi_pivot.px, self.e_hi_pivot.idx) if self.e_hi_pivot else None,\n"
    "                lp=(self.e_lo_pivot.px, self.e_lo_pivot.idx) if self.e_lo_pivot else None,\n"
    "                hprev=(self.e_hi_prev.px, self.e_hi_prev.idx),\n"
    "                lprev=(self.e_lo_prev.px, self.e_lo_prev.idx),\n"
    "                bs=self.bars_seen, ch=c.high, cl=c.low))\n"
    + OLD
)

p = ROOT / "backend" / "src" / "firstswing.py"
src = p.read_text(encoding="utf-8")
assert src.count(OLD) == 1, "anchor not found: %d" % src.count(OLD)

name = "src.firstswing"
mod = types.ModuleType(name)
mod.__file__ = str(p)
mod.__package__ = "src"
mod.__dict__["__name__"] = name
mod.__dict__["_T"] = TARGETS
mod.__dict__["_R"] = []
exec(compile(src.replace(OLD, NEW), str(p), "exec"), mod.__dict__)
sys.modules.pop("src.btc.btc_swing", None)
sys.modules[name] = mod

import src.walker as wm
orig_wp = wm.WalkerEngine.process_bar
seals = {}
def wrap_w(self, c, g_idx):
    r = orig_wp(self, c, g_idx)
    if g_idx in TARGETS:
        seals.setdefault(g_idx, []).extend(
            [{'k': pp.kind, 'px': pp.px, 'i': pp.idx, 's': pp.sealed} for pp in r])
    return r
wm.WalkerEngine.process_bar = wrap_w

from src.btc.btc_swing import compute_btc_swings
sw = compute_btc_swings(candles, opts={"minBars": 50}, max_swings=max(1, len(candles)//2))

wm.WalkerEngine.process_bar = orig_wp

def dt(i):
    return raw[i]['date'][:16] if 0 <= i < len(raw) else '-'

for t in sorted(TARGETS):
    print("=" * 70)
    print("BAR %d  %s" % (t, dt(t)))
    print("=" * 70)
    for s in seals.get(t, []):
        print("  SEAL: %s  px=%.1f  idx=%d  sealed=%s" % (s['k'], s['px'], s['i'], s['s']))
    for r in mod.__dict__["_R"]:
        if r['g_idx'] == t:
            print("  armed=%s  state=%s  dir=%s  pending_arm=%s  pending_dir=%s  bars_seen=%d"
                  % (r['armed'], r['state'], r['dir'], r['pa'], r['pd'], r['bs']))
            print("  up_break=%s  down_break=%s" % (r['up'], r['down']))
            print("  e_hi_pivot: px=%.1f idx=%d" % (r['hp'][0], r['hp'][1]))
            print("  e_hi_prev:  px=%.1f idx=%d" % (r['hprev'][0], r['hprev'][1]))
            print("  e_lo_pivot: px=%.1f idx=%d" % (r['lp'][0], r['lp'][1]))
            print("  e_lo_prev:  px=%.1f idx=%d" % (r['lprev'][0], r['lprev'][1]))
            print("  candle: high=%.1f low=%.1f" % (r['ch'], r['cl']))
    print()

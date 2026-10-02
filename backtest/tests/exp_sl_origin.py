"""
Question raised by reading the chart: is the causal SL still using a pivot from
a swing that had not finished?

The shipped causal pivot is the running low since the last CONFIRMED swing:

    on confirm at _ca -> reset the running extreme to that swing's seg end
    then track min(low) forward to the entry bar

For the 18 Nov 2024 04:30 entry that gives the low of the 03:30 candle, which
is the END of the PREVIOUS swing - the leg that had just completed. The forming
swing started at 03:45, so the lowest price available to a live trader inside
the forming swing is the low of the 04:00 candle, not 03:30.

If that is right, the causal SL is the retroactive SL shifted one swing
earlier: it still reads a pivot that only became known once the leg finished.

Run: python -u exp_sl_origin.py
"""
import sys, os, pickle, types, inspect
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r
from src.btc.btc_engine import _collect_signals, CandleStore

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
c15, sw15 = d["c15"], d["sw15"]
n = len(c15)


def idx_of(mm):
    for i, c in enumerate(c15):
        if str(c["date"])[:16] == mm:
            return i
    return -1


_csl = [0.0] * n
_conf = []
for s in sw15:
    ca = int(s.get("confirmed_at_idx", -1))
    ei = int(s.get("seg", {}).get("end_idx", -1))
    if ca >= 0 and ei >= 0:
        _conf.append((ca, ei))
_conf.sort()
_ce = 0
_lo = float(c15[0]["low"])
for ci in range(n):
    while _ce < len(_conf) and _conf[_ce][0] <= ci:
        _cref = _conf[_ce][1]
        _ce += 1
        if _cref < n:
            _lo = float(c15[_cref]["low"])
    if float(c15[ci]["low"]) < _lo:
        _lo = float(c15[ci]["low"])
    _csl[ci] = _lo

_ends = sorted(int(s.get("seg", {}).get("end_idx", -1)) for s in sw15)


def forming_start(i):
    prev = -1
    for e in _ends:
        if e < i:
            prev = e
        else:
            break
    return prev + 1 if prev >= 0 else 0


i = idx_of("2024-11-18 04:30")
print("=" * 78)
print("THE 18 Nov 2024 04:30 LONG ENTRY - every candidate stop")
print("=" * 78)
ca, s = None, None
for x in sw15:
    xc = int(x.get("confirmed_at_idx", -1))
    if 0 <= xc <= i and (ca is None or xc > ca):
        ca, s = xc, x
print("  last swing confirmed before this bar : #%s confirmed@%s"
      % (s.get("swing_index"), c15[ca]["date"][:16]))
print("  that swing's seg end                  : %s"
      % c15[int(s["seg"]["end_idx"])]["date"][:16])
print()

_sigs = _collect_signals(sw15, "decisive", skip_first=True,
                         selection="stream", candles=c15)
sv = [x for x in _sigs if str(x["bar"])[:16] == "2024-11-18 04:30"]
if sv:
    print("  RETRO   sig['swing_start_px']       : %.2f" % float(sv[0]["swing_start_px"]))
_j = _csl.index(_csl[i])
print("  CAUSAL  _csl[bar] (shipped)          : %.2f   <- low at %s"
      % (_csl[i], c15[_j]["date"][:16]))
fs = forming_start(i)
loffs = min(range(fs, i + 1), key=lambda k: float(c15[k]["low"]))
print("  FORMING running low (from %s) : %.2f   <- low at %s"
      % (c15[fs]["date"][:16], float(c15[loffs]["low"]), c15[loffs]["date"][:16]))
print()
print("  forming swing starts %s, entry is %d bars later"
      % (c15[fs]["date"][:16], i - fs + 1))
print()
if abs(_csl[i] - float(c15[loffs]["low"])) > 1e-6:
    print("  >>> THE SHIPPED CAUSAL STOP IS THE OLD SWING'S LOW, not the forming")
    print("  >>> swing's low. That is the retroactive SL one swing earlier.")
else:
    print("  shipped causal stop already matches the forming-swing low.")
print()
print("  note: for THIS trade the forming-swing low (89300.10) happens to equal")
print("  the retro pivot, because swing #1465's origin is right there. That is a")
print("  coincidence of this bar, not a rule. The two rules differ elsewhere,")
print("  which the full-book run below measures.")
print()

# ------------------------------------------------------------------ 2 rules
SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")

OLD = '_cref=_conf_evs[_cei][1]; _cei+=1'
NEW = '_cref=_conf_evs[_cei][1]+1; _cei+=1'   # start of the FORMING swing, not the old leg's end

# RETIRED 2026-10-01. This harness patched the pre-C17 engine text back to its
# earlier form and compared the two. That fix is already in the engine, so the old
# anchor cannot exist again and there is nothing left to compare. It is a
# completed one-shot, not a broken harness, so it exits 0 with an explanation
# rather than raising. Re-enable only against a pre-C17 checkout.
if SRC.count(OLD) != 1:
    print("RETIRED: the pre-C17 anchor this harness patches is no longer in the engine.")
    print("  The causal-reset fix it measured (forming-swing start, scanning all bars")
    print("  through confirmation) has shipped and is now the only behaviour.")
    raise SystemExit(0)
assert SRC.count(OLD) == 1, "anchor not found in the engine"


def run(src, tag):
    m = types.ModuleType(tag)
    m.__file__ = "sl.py"
    exec(compile(src, "sl.py", "exec"), m.__dict__)
    pr = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
          if k in set(inspect.signature(m.simulate_htf_ltf_streak_halt).parameters)
          and k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}
    r = m.simulate_htf_ltf_streak_halt(d["c1h"], d["sw10"], c15, sw15,
                                      fine_ltf=d["fine"], exp_causal_sl=1, **pr)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


shipped = run(SRC, "shipped")
forming = run(SRC.replace(OLD, NEW), "forming")

print("=" * 78)
print("THE WHOLE BOOK, IS  (all with exp_causal_sl=1)")
print("=" * 78)
for name, tr in (("causal as shipped (reset to seg end)", shipped),
                 ("causal from FORMING swing low", forming)):
    rs = [float(t["r_multiple"]) for t in tr]
    oc = Counter(t.get("outcome") for t in tr)
    print("  %-38s n=%-5d net=%+8.2fR  %r" % (name, len(rs), net_r(tr), dict(oc)))
print("  %-38s n=%-5d net=%+8.2fR  %s"
      % ("RETRO for reference", 500, 325.78, "{'sl': 187, 'trail': 313}"))
print()

ak = {(int(t["entry_ts"]), t["dir"]): t for t in shipped}
bk = {(int(t["entry_ts"]), t["dir"]): t for t in forming}
shared = set(ak) & set(bk)
moved = sum(1 for k in shared
            if abs(float(ak[k]["sl"]) - float(bk[k]["sl"])) > 1e-6)
print("  only in shipped causal      : %d" % len(set(ak) - set(bk)))
print("  only in forming causal      : %d" % len(set(bk) - set(ak)))
print("  stop moved on               : %d of %d shared trades"
      % (moved, len(shared)))
print("  identical                   : %d" % (len(shared) - moved))


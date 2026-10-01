"""Static sweep: syntax, pre-C16 pins, venue, registry. Read-only, no engine runs.

WHAT THIS IS NOT. This is not a health check and it does not run anything. It
cannot tell you whether a harness passes or fails, because running them takes
minutes each. An earlier version of this file claimed it could, which was
overstated. For an actual pass/fail signal use:

    python backtest/tests/exp_verify_route.py     API end to end, ~3 min
    python backtest/tests/exp_v19_matrix.py       both pivot rules, ~4 min

What it does catch, in seconds:
  1. syntax        - py_compile every .py under backend/src, backend/tests, backtest
  2. pre-C16 pins  - harnesses asserting a net-R figure anchored before 203e207,
                     which flipped the _collect_signals pivot_rule default
  3. venue         - harnesses loading Binance spot instead of Bybit perp
  4. registry      - how many experiments declare pivot_rule
  5. known red     - harnesses documented as failing, so silence is not mistaken
                     for a pass

Run: python -u exp_sweep_static.py
"""
import sys, os, re, py_compile
from pathlib import Path

ROOT = Path(r"C:/Users/Pravin/Desktop/main/AT_Trading")
for p in ("backend", "backend/tests", "backtest", "backtest/sweeps",
          "backtest/engine", "backend/src"):
    sys.path.insert(0, str(ROOT / p))

# Documented failures. Each one is a real, understood problem, not a mystery.
# If a name here starts passing, delete it - that is the signal worth noticing.
KNOWN_RED = {
    "exp_closeout_battery": "PIN_LB30 anchored at ee574f9 (2026-09-21), before the "
                            "203e207 pivot default flip. Reads _collect_signals, so "
                            "the pin is origin-era and the run is leg-era. Same "
                            "signature as the v18 re-anchor: +1 trade, -6.9R.",
    "exp_issue10_window": "imports persistence.database, a package that is not "
                          "tracked in this repo. Present on disk under "
                          "live_stuff/ but absent from version control.",
}

SPOT = "BTCUSDT"
PERP = "BTCUSDT_BYBIT"
# Net-R figures pinned against the pre-C16 origin book.
ORIGIN_PINS = ("325.78", "314.52", "247.96", "255.20")
SELF = "exp_sweep_static.py"

report = []
red = []

# ---------------------------------------------------------------- 1. syntax
bad = []
for sub in ("backend/src", "backend/tests", "backtest/tests", "backtest/engine",
            "backtest/sweeps"):
    base = ROOT / sub
    if not base.exists():
        continue
    for f in base.rglob("*.py"):
        try:
            py_compile.compile(str(f), doraise=True,
                               cfile=str(ROOT / "backtest/tests/__pycache__/_sweep.pyc"))
        except py_compile.PyCompileError as e:
            bad.append((sub + "/" + str(f.relative_to(base)), str(e).splitlines()[-1]))
report.append(f"[1] syntax      : {'OK' if not bad else str(len(bad)) + ' BROKEN'}")
for n, e in bad[:20]:
    report.append(f"      {n}  {e[:90]}")

# ------------------------------------------------------------ 2. pre-C16 pins
stale = []
for f in sorted((ROOT / "backtest/tests").glob("exp_*.py")):
    if f.name == SELF:
        continue                      # this file carries the pin list as literals
    try:
        t = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    hits = [p for p in ORIGIN_PINS if p in t]
    if hits:
        stale.append((f.name, hits))
report.append(f"[2] pre-C16 pins: {len(stale)} harness(es) assert an origin-era figure")
for n, h in stale:
    tag = "  <- KNOWN RED" if n in KNOWN_RED else ""
    report.append(f"      {n:44s} {','.join(h)}{tag}")

# ---------------------------------------------------------------- 3. venue
# Match the actual call site, not the word anywhere in the file. The previous
# version skipped any file that mentioned BTCUSDT_BYBIT at all, so a harness with
# a correct comment and a wrong call passed.
spot = []
for f in sorted((ROOT / "backtest/tests").glob("*.py")):
    if f.name == SELF:
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'_load_window\(\s*"[^"]+"\s*,\s*[^,]+,\s*"([^"]+)"', t):
        if m.group(1) != PERP:
            spot.append((f.name, m.group(1)))
        break
report.append(f"[3] venue       : {len(spot)} harness(es) load a non-Bybit symbol")
for n, s in spot:
    report.append(f"      {n:44s} {s}")

# -------------------------------------------------------------- 4. registry
sys.path.insert(0, str(ROOT / "backtest/tests"))
from experiment_registry import EXPERIMENTS
with_rule = sum(1 for v in EXPERIMENTS.values()
                if isinstance(v, dict) and "pivot_rule" in v.get("params", {}))
report.append(f"[4] registry    : {len(EXPERIMENTS)} experiments, "
              f"{with_rule} declare pivot_rule")

# -------------------------------------------------------------- 5. known red
missing = [k for k in KNOWN_RED if not (ROOT / "backtest/tests" / (k + ".py")).exists()]
for n, why in sorted(KNOWN_RED.items()):
    red.append((n, why))
report.append(f"[5] known red   : {len(KNOWN_RED)} documented as failing")
for n, why in red:
    report.append(f"      {n:44s} {why[:70]}")
if missing:
    report.append(f"      WARNING: listed but absent: {', '.join(missing)}")

out = "\n".join(report)
print(out)
print()
print(f"  NOTE: items 1-4 are static only. {len(stale)} harness(es) need an actual run.")
(ROOT / "backtest/tests/_sweep.txt").write_text(out, encoding="utf-8")
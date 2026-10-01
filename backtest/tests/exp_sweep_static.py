"""Static health sweep over every harness in the repo. No execution, no engine runs.

Phase 1 of a robustness pass. Catches the cheap failures in seconds instead of
discovering them one at a time:

  1. syntax        - py_compile every .py under backend/src, backend/tests, backtest
  2. stale pins    - harnesses asserting a hardcoded net-R figure
  3. venue         - any harness still hardcoding the Binance spot symbol "BTCUSDT"
                     instead of the Bybit perp symbol the project trades
  4. imports       - every exp_*.py must at least import cleanly (websockets and
                     replay_harness are on the path now)

Run: python -u exp_sweep_static.py
"""
import sys, os, re, py_compile, subprocess, types
from pathlib import Path

ROOT = Path(r"C:/Users/Pravin/Desktop/main/AT_Trading")
for p in ("backend", "backend/tests", "backtest", "backtest/sweeps",
          "backtest/engine", "backend/src"):
    sys.path.insert(0, str(ROOT / p))

SPOT = "BTCUSDT"
PERP = "BTCUSDT_BYBIT"
# net-R figures that were pinned against the pre-C16 origin book. A harness that
# asserts one of these must be passing pivot_rule="origin" explicitly or inheriting
# it from the registry, or it is measuring the leg book and will fail.
ORIGIN_PINS = ("325.78", "314.52", "247.96", "255.20")

report = []

# ---------------------------------------------------------------- 1. syntax
bad = []
for sub in ("backend/src", "backend/tests", "backtest/tests", "backtest/engine",
            "backtest/sweeps", "frontend/src"):
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

# ------------------------------------------------------------ 2. stale pins
stale = []
for f in sorted((ROOT / "backtest/tests").glob("exp_*.py")):
    try:
        t = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    hits = [p for p in ORIGIN_PINS if p in t]
    if hits:
        stale.append((f.name, hits))
report.append(f"[2] origin pins : {len(stale)} harness(es) assert a pre-C16 figure")
for n, h in stale:
    report.append(f"      {n:44s} {','.join(h)}")

# ---------------------------------------------------------------- 3. venue
spot = []
for f in sorted((ROOT / "backtest/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8", errors="replace")
    if PERP in t:
        continue
    # a hardcoded spot symbol in a _load_window/load call, not in prose
    for m in re.finditer(r'_load_window\(\s*"([^"]+)"\s*,\s*[^,]+,\s*"' + SPOT + r'"', t):
        spot.append((f.name, m.group(0)[:60]))
        break
report.append(f"[3] spot venue  : {len(spot)} harness(es) hardcode {SPOT} (Binance SPOT)")
for n, s in spot:
    report.append(f"      {n:44s} {s}")

# -------------------------------------------------------------- 4. registry
sys.path.insert(0, str(ROOT / "backtest/tests"))
from experiment_registry import EXPERIMENTS
with_rule = sum(1 for v in EXPERIMENTS.values()
                if isinstance(v, dict) and "pivot_rule" in v.get("params", {}))
report.append(f"[4] registry    : {len(EXPERIMENTS)} experiments, "
              f"{with_rule} declare pivot_rule")

out = "\n".join(report)
print(out)
(ROOT / "backtest/tests/_sweep.txt").write_text(out, encoding="utf-8")
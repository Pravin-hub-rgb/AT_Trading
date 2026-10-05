"""Static sweep: syntax, pre-C16 pins, venue, registry. Read-only, no engine runs.

WHAT THIS IS NOT. This is not a health check and it does not run anything. It
cannot tell you whether a harness passes or fails, because running them takes
minutes each. An earlier version of this file claimed it could, which was
overstated. For an actual pass/fail signal use:

    python backtest/checks/exp_verify_route.py   API end to end, ~3 min
    python backtest/tests/exp_v19_matrix.py       both pivot rules, ~4 min

What it does catch, in seconds:
  1. syntax        - py_compile every .py under backend/src, backend/tests, backtest
  2. pre-C16 pins  - harnesses asserting a net-R figure anchored before 203e207,
                     which flipped the _collect_signals pivot_rule default
  3. venue         - harnesses loading Binance spot instead of Bybit perp
  4. registry      - how many experiments declare pivot_rule
  5. known red     - harnesses documented as failing, so silence is not mistaken
                     for a pass

SCOPE LIMIT, stated so nobody trusts it further than it goes. Item 2 matches on
  net-R anchors only. It cannot catch a stale claim that quotes an AUC or a trade
  count, because those shapes never appear in RETRACTED_ANCHORS. method/INSIDE80_P95.md was
  reported clean by this sweep while its headline "0.847 / separates" was dead -
  the same blind spot as a check matching on the wrong shape, which is what the
  `if PERP in t: continue` bug was. An honest scope beats an implied one.
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
# Compile to a scratch file outside the repo. Writing into backtest/tests/__pycache__
# races with anything else compiling there and fails with PermissionError on
# Windows when two runs overlap.
_SCRATCH = Path(os.environ.get("TEMP", ".")) / "_sweep_compile.pyc"
bad = []
for sub in ("backend/src", "backend/tests", "backtest/tests", "backtest/engine",
            "backtest/sweeps"):
    base = ROOT / sub
    if not base.exists():
        continue
    for f in base.rglob("*.py"):
        try:
          # FOURTH BLIND SPOT, found 2026-10-01: this check does not detect a
          # document that PROPOSES a knob it elsewhere reports as CLOSED.
          # method/ROUND_SUMMARY_P55_P95.md:292 ranked exp_window_entry_cap as Rank 1
          # while :416 of the same file recorded that it had already run and was
          # "OOS-only, NOT ROBUST". Both readable, neither marked. That is a
          # third variant of the stale-claim family - not a wrong number, not a
          # fictional feature, but two contradictory statements about one object
          # in one file. Cheap to catch, and this check does not catch it: it
          # needs both a proposal framing and a closed verdict for the same knob
          # in one document. Documented, not implemented - that needs a real
          # parser, not a grep.
            py_compile.compile(str(f), doraise=True, cfile=str(_SCRATCH))
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

# ------------------------------------------------- 4b. champion book usage
# champion_multi_sw10 is the PRE-C16 origin book. champion_multi_sw10_leg is the
# one that ships. Anything reading the former by name is measuring a lookahead
# book, so the number of readers is worth keeping visible.
LEG = "champion_multi_sw10_leg"
mentions = 0
mention_files = set()
readers = set()
for f in (ROOT / "backtest/tests").glob("*.py"):
    if f.name == SELF:
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    for line in t.splitlines():
        if LEG in line:
            continue
        if "champion_multi_sw10" in line:
            mentions += 1
            mention_files.add(f.name)
            # A registry reader touches EXPERIMENTS[...]["params"] somewhere.
            # A harness that binds the key on one line and uses it on another is
            # counted as a mention but not a reader, so readers is a floor.
            if "EXPERIMENTS[" in line or "params" in line:
                readers.add(f.name)

report.append(f"[4b] champion   : {mentions} mentions of champion_multi_sw10 across "
              f"{len(mention_files)} file(s) under backtest/tests")
report.append(f"      {len(readers)} of those files touch EXPERIMENTS[]/params on the "
              f"same line as the mention")
report.append(f"      (a harness that binds the key on one line and reads it on another")
report.append(f"       is counted as a mention but not a reader, so the reader count is")
report.append(f"       a floor, not a total)")
report.append(f"      champion_multi_sw10 is the PRE-C16 origin book. The shipping book")
report.append(f"      is champion_multi_sw10_leg. Check pivot_rule, not the name.")
report.append(f"      Earlier commits quoted a harness count here from memory rather than")
report.append(f"      by counting. Read these figures off the code above; do not quote a")
report.append(f"      number that did not come out of a run.")

# -------------------------------------------------------------- 5. known red
missing = [k for k in KNOWN_RED if not (ROOT / "backtest/tests" / (k + ".py")).exists()]
for n, why in sorted(KNOWN_RED.items()):
    red.append((n, why))
report.append(f"[5] known red   : {len(KNOWN_RED)} documented as failing")
for n, why in red:
    report.append(f"      {n:44s} {why[:70]}")
if missing:
    report.append(f"      WARNING: listed but absent: {', '.join(missing)}")

# ------------------------------------------- 6. C16-era anchors still quoted
# C16's signature, seen five times now: one stop rule changed the trade count by
# exactly +/-1 and moved R by more than a few percent.
#
#   v18 re-anchor      +1 trade   +0.2pt WR
#   closeout_battery   +1 trade   -6.9R
#   champion book      -1 trade   +86.7R
#   identity gate      -1 trade   +12.3R
#   champion OOS       +1 trade   +2.7R
#
# Every value below is an anchor measured before 203e207 flipped the pivot
# default. A file still quoting one without a retraction marker is either wrong,
# or was silently re-baselined by C16 without anyone saying so. This does not know
# which. It only knows what is still un-marked, which is the half that has been
# costing time.
# RENAMED from C16_ANCHORS 2026-10-01 and merged with the P91 values. The
# concept was never C16-specific - it is "a number that has been retracted and
# will keep propagating until something stops it". Two lists of retracted
# numbers are one concept, and two lists drift exactly the way two documents
# drifted. C16 is a source of entries here, not the definition of the set.
RETRACTED_ANCHORS = {
    "325.78": "champion origin IS net",
    "314.52": "champion causal IS net",
    "247.96": "champion C17-only IS net",
    "255.20": "champion C17-only IS net, upper",
    "225.3":  "identity gate origin coarse gross",
    "193.4":  "base-book null M, OOS, origin",
    "479.9":  "base-book null M, IS, origin",
    "170.5":  "closeout_battery PIN_LB30 net",
    # P91 short-side absolutes. Retracted 2026-10-01: abs_return() never read
    # t["dir"], so (exit-entry)/entry - the NEGATIVE of short PnL - was tabulated
    # and read as a loss. True values are +0.4415 IS / +0.7471 OOS and they
    # AGREE with R; there is no divergence. These two numbers propagated across
    # three documents and produced a Rank-8 queue entry on a dead premise.
    "0.4415": "P91 short absolute IS (origin) - SIGN ERROR",
    "0.7471": "P91 short absolute OOS (origin) - SIGN ERROR",
}
C16_ANCHORS = RETRACTED_ANCHORS  # back-compat name; kept so nothing breaks
MARKERS = ("RETRACT", "SUPERSEDED", "superseded", "RESOLVED", "KNOWN RED",
           "STALE", "stale", "VOID", "void", "RE-DERIVED", "re-derived",
           "origin-era", "ORIGIN-era", "origin book", "pre-C16", "PRE-C16",
           "not shippable", "withdrawn", "WITHDRAWN")
DOCS = ROOT / "backtest/docs"
stale_docs = []
for val, what in C16_ANCHORS.items():
    hits = []
    for f in list(DOCS.glob("*.md")) + sorted((ROOT / "backtest/tests").glob("*.py")):
        if f.name == SELF:
            continue
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if val not in t:
            continue
        if not any(m in t for m in MARKERS):
            hits.append(f.name)
    if hits:
        stale_docs.append((val, what, hits))
report.append(f"[6] C16 anchors : {len(stale_docs)} value(s) quoted with no "
              f"retraction marker anywhere in the file")
for val, what, hits in stale_docs:
    report.append(f"      {val:8s} ({what}) -> {len(hits)} unmarked file(s)")
    for h in hits[:8]:
        report.append(f"          {h}")

out = "\n".join(report)
print(out)
print()
print(f"  NOTE: items 1-4 are static only. {len(stale)} harness(es) need an actual run.")
(ROOT / "backtest/checks/_sweep.txt").write_text(out, encoding="utf-8")
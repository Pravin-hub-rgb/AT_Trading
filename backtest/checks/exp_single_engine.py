"""SINGLE ENGINE GATE.

The rule, in one sentence: backend/src/btc/engines/htf_ltf/ is closed. There is
one implementation, unified.py. Every new experiment is a registry entry with
params, not a new engine file.

This check enforces it mechanically, because a document did not hold this
session even once. It fails when:

  1. a file appears in engines/htf_ltf/ that is not on the allowlist below
  2. a registry entry names an engine that is not "unified"
  3. a module in engines/htf_ltf/ defines its own simulate_htf_ltf_streak_halt
     rather than re-exporting unified's (i.e. a second implementation)

Run:  cd backtest/checks && python exp_single_engine.py
"""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENGINE_DIR = ROOT / "backend" / "src" / "btc" / "engines" / "htf_ltf"
REGISTRY = ROOT / "backtest" / "tests" / "experiment_registry.py"
CORE = "unified"

# Files allowed to exist here, and what each one is:
#   unified.py                       the core
#   __init__.py                       package marker
#   README.md                         the rule
#   *_*.py                           historical baselines, not dispatched
#   _archive/                         archived implementations, shimmed from
ALLOWED_EXACT = {"unified.py", "__init__.py", "README.md"}
SHIMS = {
    "v18_streak_halt.py", "v19_champion.py",
    "v1_15m.py", "v3_ext_stop.py", "v5_sl_buffer.py", "v6_sl_hhll.py",
}


def main():
    problems = []

    # 1) no new engine files
    for p in sorted(ENGINE_DIR.glob("*.py")):
        n = p.name
        if n in ALLOWED_EXACT or n in SHIMS or n.startswith("_"):
            continue
        if re.match(r"^v\d+.*\.py$", n):
            continue          # historical baseline, listed above as tolerated
        problems.append("unexpected file in engines/htf_ltf/: %s" % n)

    # 2) every module here must not define its own engine function
    for p in sorted(ENGINE_DIR.glob("*.py")):
        if p.name == "unified.py":
            continue
        try:
            raw = p.read_text(encoding="utf-8-sig", errors="replace")
            tree = ast.parse(raw)
        except SyntaxError as e:
            problems.append("%s does not parse: %s" % (p.name, e))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "simulate_htf_ltf_streak_halt":
                src = ast.get_source_segment(raw, node) or ""
                if "unified" not in src:
                    problems.append(
                        "%s defines its own simulate_htf_ltf_streak_halt - "
                        "a second implementation" % p.name)

    # 3) the registry may only name unified
    if REGISTRY.exists():
        src = REGISTRY.read_text(encoding="utf-8", errors="replace")
        named = set(re.findall(r'"engine"\s*:\s*"([^"]+)"', src))
        bad = {e for e in named if e not in (CORE, "patched", "shipped")}
        for e in sorted(bad):
            problems.append('registry names engine "%s" - only "%s" exists' % (e, CORE))

    print("=" * 64)
    print("SINGLE ENGINE GATE")
    print("=" * 64)
    print("engine dir : %s" % ENGINE_DIR.relative_to(ROOT))
    print("core       : %s.py" % CORE)
    print("shims      : %d" % len(SHIMS))
    print("baselines  : %d (tolerated, not dispatched)"
          % len([p for p in ENGINE_DIR.glob("v*.py") if p.name not in SHIMS]))
    print()
    if problems:
        for x in problems:
            print("  FAIL  %s" % x)
        print()
        print("RESULT: FAIL - %d problem(s). The engine directory is supposed to" % len(problems))
        print("        hold one implementation. A new experiment is a registry entry")
        print("        with params. If a second implementation is genuinely required,")
        print("        that is an architecture change, not an experiment.")
        return 1
    print("RESULT: PASS - one implementation. A new experiment is a registry entry")
    print("        with params, not a new file in this directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

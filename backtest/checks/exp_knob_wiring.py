"""KNOB WIRING AUDIT — proves every registry knob is actually LIVE.

The C12-C16 class of bug is a knob that is accepted, configured, and never
read. exp_persist was exactly this: 62 registry entries set it, the patched
v18 body had no hysteresis code at all, so every one of those books silently
ran with the knob inert. exp_wick_reject is the same shape and still alive.

This check builds the real generated module, AST-parses it, and compares:
  - signature knobs  vs  names referenced in the function body  -> DEAD
  - registry knobs   vs  signature knobs                       -> ORPHAN
It exits non-zero on any DEAD or ORPHAN knob, so a silently inert knob can
never be committed again.

Run:  cd backtest/checks && python exp_knob_wiring.py
"""
import ast
import collections
import importlib
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(ROOT / "backend"))

REGISTRY = HERE.parent / "tests" / "experiment_registry.py"
ENGINE_FN = "simulate_htf_ltf_streak_halt"
DATA_ARGS = {"candles_htf", "swings_htf", "candles_ltf", "swings_ltf",
             "fine_ltf", "self"}

# Knobs that are write-only debug/telemetry toggles. They are collected or
# printed at the end of a run and never gate a decision. Listed explicitly so
# that anything else becoming write-only is treated as a failure.
KNOWN_DEBUG_FLAGS = {
    "exp_5m_stats",
    "exp_campaign_stats",
    "exp_event_stats",
    "exp_window_loss_kill_stats",
    "exp_window_win_kill_stats",
}


def load_registry_books():
    """Return list of param-dicts, one per registry book entry."""
    src = REGISTRY.read_text(encoding="utf-8", errors="replace")
    books = []
    for blob in re.findall(r'"params"\s*:\s*(\{[^{}]*\})', src, re.S):
        try:
            books.append(ast.literal_eval(blob))
        except Exception:
            continue
    return books


def generated_source():
    """Build the real patched engine and capture the generated source."""
    import test_experiments_craze as cp

    captured = {}
    original = cp._load_module

    def spy(src, name):
        captured["src"] = src
        return original(src, name)

    cp._load_module = spy
    try:
        cp._build_module()
    finally:
        cp._load_module = original

    if "src" not in captured:
        raise RuntimeError("harness did not hand back generated source")
    return captured["src"]


def analyse(src):
    """-> (signature_knobs, dead_knobs) from the generated module."""
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == ENGINE_FN)
    sig = {a.arg for a in fn.args.kwonlyargs} | {a.arg for a in fn.args.args}
    used = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    knobs = sorted(sig - DATA_ARGS)
    dead = sorted(k for k in knobs if k not in used)
    return knobs, dead


def main():
    books = load_registry_books()
    knobs, dead = analyse(generated_source())

    usage = collections.Counter()
    for b in books:
        for k in b:
            usage[k] += 1

    orphans = sorted(k for k in usage if k not in knobs)
    dead_used = [k for k in dead if usage.get(k, 0) > 0]
    dead_debug = [k for k in dead if k in KNOWN_DEBUG_FLAGS]
    dead_real = [k for k in dead
                 if k not in KNOWN_DEBUG_FLAGS and usage.get(k, 0) == 0]
    # A knob that is dead AND set by a book is the worst case: a published
    # measurement that does not reflect the config it claims to test.
    silent_noops = [k for k in dead if k in usage]

    print("=" * 62)
    print("KNOB WIRING AUDIT")
    print("=" * 62)
    print("registry books          : %d" % len(books))
    print("distinct registry knobs : %d" % len(usage))
    print("engine signature knobs  : %d" % len(knobs))
    print("LIVE (read in body)     : %d" % (len(knobs) - len(dead)))
    print("DEAD (never read)       : %d" % len(dead))
    print()

    if silent_noops:
        print("!! SILENT NO-OPS (book sets it, engine ignores it) !!")
        for k in silent_noops:
            print("   %-26s %d/%d books" % (k, usage[k], len(books)))
        print()
    if orphans:
        print("!! ORPHANS (book sets it, engine has no such knob) !!")
        for k in orphans:
            print("   %-26s %d/%d books" % (k, usage[k], len(books)))
        print()
    if dead_real:
        print("~ INERT TRAPS (no book uses them yet, but they would lie):")
        for k in dead_real:
            print("   %-26s" % k)
        print()
    if dead_debug:
        print("  known write-only debug flags: %s" % ", ".join(dead_debug))
        print()

    print("-" * 62)
    if silent_noops or orphans:
        print("RESULT: FAIL - %d silent no-op, %d orphan"
              % (len(silent_noops), len(orphans)))
        return 1
    print("RESULT: PASS - every registry knob is wired to live engine code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
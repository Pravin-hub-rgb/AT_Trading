"""NO ORIGIN STOP.

seg_start is the swing's structural extreme. On a flip or B2 entry the swing is
still FORMING; its extreme is not final until the first-swing print arrives,
which is after the entry bar. So a stop taken from it can only be computed with
bars the trade did not have. It is the one stop source in this engine that
fails "no SL may be placed after entry".

Both legs use btc_engine._collect_signals, so both are affected: the HTF leg
through simulate_btc_trades_v7, the LTF leg through _collect_signals in
unified.py. That is why removing origin on both sides moved 500 trades to 499
and the net by 86R.

leg and leg_no_entry are NOT affected. Both read candles[swing_start :
break_bar] - never past the break.

This check fails if the registry names pivot_rule="origin", and reports what
still does so the research baseline can be removed deliberately.

Run:  cd backtest/checks && python exp_no_origin_stop.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "backtest" / "tests" / "experiment_registry.py"
ROUTE = ROOT / "backend" / "src" / "btc" / "btc_routes.py"
# Historical baseline only. Listed, not silently tolerated - when it is deleted
# this goes with it.
#
# champion_multi_sw10 is the RETRO research book.
# btc_routes.py:1441 is the v19_champion branch that serves it. Both exist so
# the before/after comparison stays reproducible. Neither is a shipping book
# and neither is in the dropdown.
KNOWN_RESEARCH_ONLY = {"champion_multi_sw10", "btc_routes.py:1441"}


def main():
    findings = []
    if REGISTRY.exists():
        src = REGISTRY.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'"([A-Za-z0-9_]+)"\s*:\s*\{(.*?)\n    \}', src, re.S):
            key, body = m.group(1), m.group(2)
            if '"pivot_rule": "origin"' in body or "'pivot_rule': 'origin'" in body:
                findings.append((key, "registry entry sets pivot_rule=origin"))
    if ROUTE.exists():
        for i, line in enumerate(ROUTE.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            if 'pivot_rule="origin"' in line:
                findings.append(("btc_routes.py:%d" % i, "route passes pivot_rule=origin"))

    print("=" * 64)
    print("NO ORIGIN STOP")
    print("=" * 64)
    print("known research-only keys, permitted until removed: %s"
          % ", ".join(sorted(KNOWN_RESEARCH_ONLY)))
    print()
    if findings:
        for key, why in findings:
            tag = "research baseline" if key in KNOWN_RESEARCH_ONLY else "UNAUTHORISED"
            print("  %-32s %-42s [%s]" % (key, why, tag))
        print()
        bad = [f for f in findings if f[0] not in KNOWN_RESEARCH_ONLY]
        if bad:
            print("RESULT: FAIL - %d unauthorised use(s) of the origin stop." % len(bad))
            print("        seg_start is not knowable at the entry bar. No book may use it.")
            return 1
        print("RESULT: PASS with exceptions - only the listed research baseline still")
        print("        names pivot_rule=origin, which is deliberate and labelled.")
        return 0
    print("RESULT: PASS - no book reaches for the origin stop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

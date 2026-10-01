"""STRUCTURE PROBE - run this BEFORE writing a harness on a new idea.

WHY THIS FILE EXISTS
====================
Three times in one session I wrote a harness against a structure I had not
read, and each time the assumption was wrong:

  1. "the 1m swing compute is memory-bound" - taken from the handover.
     It runs in 18.5s. Had to run it to know.
  2. "sw10/sw20 are built from the 15m stream" - taken from the handover.
     They are built from 1h (`exp_5m_confirm.py:186-187`). A second
     researcher caught it, not me.
  3. "swings can be read as Elliott waves" - my own assumption. The chain
     is STITCHED: `btc_swing.py:150-152` seeds a fresh SwingEngine at the
     bar after each swing's end, so swings tile the timeline and alternate
     by construction. There is no wave 1 to retrace from, so the P1/P2
     ratio is undefined. The P1/P2 harness produced ONE candidate in 2,900
     swings before I opened the file and read five lines.

The common mistake is not sloppiness, it is checking SHAPE instead of
MEANING. Signatures, key names, counts, anchors - all verified - while the
thing the idea actually rests on was assumed.

THE RULE THIS ENCODES
=====================
Before a harness that depends on a structural claim, run the matching
probe here and READ the output. Each probe answers one question that has
already been got wrong at least once, or is an obvious next trap.

Cost: seconds. Cost of not doing it: a full harness, a run, and a
post-mortem.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u probe_structure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))


def probe_swing_chain_shape():
    """Is the swing chain NESTED (waves) or STITCHED (legs)?

    This is THE question P1/P2 got wrong.
    """
    from exp_5m_confirm import load_book
    data, _ = load_book("is")
    sw15, c15 = data["sw15"], data["c15"]
    print("PROBE 1 - swing chain: nested waves or stitched legs?")
    print(f"  swings: {len(sw15):,}   bars: {len(c15):,}")
    idx = [int(s.get("swing_index", -1)) for s in sw15]
    print(f"  swing_index range: {min(idx)} .. {max(idx)}  (0-based: the "
          f"counter is stored before the increment at btc_swing.py:146)")
    contig = sum(1 for a, b in zip(sw15, sw15[1:])
                 if int(b["seg"]["start_idx"]) == int(a["seg"]["end_idx"]) + 1)
    gaps = [int(b["seg"]["start_idx"]) - int(a["seg"]["end_idx"]) - 1
            for a, b in zip(sw15, sw15[1:])]
    mean_gap = sum(gaps) / len(gaps)
    alt = sum(1 for a, b in zip(sw15, sw15[1:])
              if a.get("dir") != b.get("dir"))
    print(f"  swings starting EXACTLY at prev end + 1: {contig}/"
          f"{len(sw15) - 1}")
    print(f"  gap between prev end and next start: mean {mean_gap:.1f} bars, "
          f"max {max(gaps)}")
    print(f"  consecutive swings with opposite direction: {alt}/{len(sw15) - 1}")
    # The first version of this probe used contig > 0.9 as the test and
    # printed "NESTED - a wave ratio may be meaningful". That was WRONG:
    # only 853/2899 are contiguous, but a mean gap of 10.3 bars means the
    # swings SKIP bars between them, which is the opposite of nested. The
    # correct test is the MEAN GAP, not the contiguous fraction.
    if mean_gap < 1.5:
        v = ("STITCHED - swings tile the timeline with no gaps, so they are "
             "legs of one sequence, NOT nested waves. A wave ratio "
             "(P1/P2, ABCD) is UNDEFINED.")
    else:
        v = (f"CHAINED WITH GAPS - mean {mean_gap:.1f} bars are skipped "
             f"between swings. The chain is still sequential (each swing is "
             f"seeded after the previous end, btc_swing.py:150-152), so it "
             f"is a SEQUENCE, not nested waves. A wave ratio may be "
             f"DEFINED but the gaps mean 'wave 2' starts after idle bars.")
    print(f"  => {v}\n")
    return v



def probe_timeframe_provenance():
    """Which stream does each swing key actually come from?

    This is THE question the second-researcher round got wrong (in my
    briefing, propagated from the handover).
    """
    import re
    print("PROBE 2 - which candles build each swing key?")
    src = (ROOT / "backtest/tests/exp_5m_confirm.py").read_text(
        encoding="utf-8")
    for m in re.finditer(r'"(sw\d+)":\s*_compute_swings\(\s*_flow\((\w+)\)',
                         src):
        key, var = m.group(1), m.group(2)
        which = {"c15": "15m", "c1h": "1h", "c5": "5m"}.get(var, var)
        print(f"  {key:<6} built from _flow({var})  -> the {which} stream")
    print("  => read this before claiming two swing keys share a timeframe\n")


def probe_inert_params(lane="champion_multi_sw10"):
    """Is every documented parameter actually read on the shipped lane?

    This is THE question Big Pickle got right: chop_thresh=58.0 is inert
    under mode="atr_high".
    """
    from experiment_registry import BP, EXPERIMENTS
    p = {**BP, **EXPERIMENTS[lane]["params"]}
    mode = p.get("mode", "chop")
    inert = {"atr_high": ["chop_thresh"],
             "atr_low": ["chop_thresh", "atr_high_thresh"],
             "chop": ["atr_low_thresh", "atr_high_thresh"]}.get(mode, [])
    print(f"PROBE 3 - parameter liveness on {lane} (mode={mode!r})")
    print(f"  IGNORED by this branch: {inert or 'none'}")
    for k in inert:
        print(f"    {k}={p.get(k)}  <- varies nothing on this lane")
    print("  => a sweep of an ignored parameter produces deltas that are\n"
          "     not about the champion at all\n")


def probe_forward_coverage():
    """Does the forward slice exist, and how much can it rule on?

    Not run against the slice - only its size. LOOKING is safe; running
    spends it.
    """
    import csv
    d = ROOT / "data/forward/bybit/BTCUSDT_15m.csv"
    print("PROBE 4 - forward slice (DO NOT RUN THE ENGINE ON THIS)")
    if not d.exists():
        print("  no forward slice on disk\n")
        return
    with d.open(encoding="utf-8") as f:
        body = [r for r in list(csv.reader(f))[1:] if r and r[0]]
    first, last = body[0][0], body[-1][0]
    days = len(body) * 15 / 1440.0
    print(f"  15m bars: {len(body):,}   {first} -> {last}   ~{days:.0f} days")
    print(f"  at the champion's ~136 trades/yr that is roughly "
          f"{days * 136 / 3.67:.0f} trades")
    print("  => enough to KILL a candidate; nowhere near enough to CONFIRM "
          "one.\n")


if __name__ == "__main__":
    print("=" * 78)
    print("  STRUCTURE PROBES - read these before writing a harness")
    print("=" * 78)
    probe_swing_chain_shape()
    probe_timeframe_provenance()
    probe_inert_params()
    probe_forward_coverage()

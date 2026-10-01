"""VERIFICATION of Stage B bleed autopsy: causality audit of chain_r_so_far.

FINDING UNDER TEST
------------------
`exp_bleed_autopsy.enrich_sequential` walks trades in ENTRY order and folds each
trade's FINAL net R into the chain accumulator immediately:

    for i in order:                       # entry_ts ascending
        cr = ck_r.get(ck, 0.0)
        feats[i]["chain_r_so_far"] = cr    # READ
        ck_r[ck] = cr + nets[i]           # WRITE this trade's FINAL net R

With `exp_mltf=True` (multi-position) the engine holds CONCURRENT trades, so a
prior trade can still be OPEN at the current entry instant. Its final R is then
future information relative to the entry.

The rest of this project already fixed exactly this class of bug (loss-streak
work: "only trades exited by the candidate entry timestamp may contribute").

WHAT THIS SCRIPT DOES
--------------------
Re-runs the ENTIRE bleed pipeline with a corrected enrich that only counts
trades CLOSED at or before the cutoff, and reports:
  - how many trades change bucket
  - how many prior-by-entry trades were still open at cutoff (the leak size)
  - the removal rule result under BOTH definitions
Everything else (bucket edges, find_rule, removal_rule, curve_better) is reused
unchanged, so this is an apples-to-apples comparison.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

import exp_bleed_autopsy as B
from run_experiment import net_r
from exp_boundary_state_autopsy import obs_ts

LEAK = {"prior_open_at_cutoff": 0, "prior_trades_examined": 0, "trades_with_leak": 0}


def enrich_closed_only(trades, feats):
    """Corrected: only trades whose exit_ts <= cutoff may contribute."""
    order = sorted(range(len(trades)), key=lambda i: int(trades[i]["entry_ts"]))
    nets = [net_r([trades[i]]) for i in range(len(trades))]
    exits = [int(trades[i].get("exit_ts") or trades[i]["entry_ts"]) for i in range(len(trades))]
    # per chain: list of (exit_ts, netR)
    ck_closed: dict = {}
    g_closed: list = []          # (exit_ts, netR) globally, for prev_* ltf state
    g_entries: list = []
    recent: list = []

    for i in order:
        if not feats[i].get("ok"):
            continue
        cutoff = obs_ts(trades[i])
        ck = feats[i].get("_ckey")

        # --- leak instrumentation -------------------------------------
        seen = ck_closed.get(ck, [])
        LEAK["prior_trades_examined"] += len(seen)
        open_now = [e for e in seen if e[0] > cutoff]
        if open_now:
            LEAK["prior_open_at_cutoff"] += len(open_now)
            LEAK["trades_with_leak"] += 1
        # ----------------------------------------------------------------

        done = sorted([e for e in ck_closed.get(ck, []) if e[0] <= cutoff])
        cr = round(sum(nd for _, nd in done), 6)
        # signed W-L streak over CLOSED trades, in exit order
        cs = 0
        for _, nd in done:
            w = 1 if nd > 0 else -1
            cs = w if cs == 0 or ((cs > 0) != (w > 0)) else cs + w
        feats[i]["chain_r_so_far"] = round(cr, 2)
        feats[i]["chain_wl_streak"] = cs
        feats[i]["_cr_closed"] = cr

        gdone = sorted([e for e in g_closed if e[0] <= cutoff])
        feats[i]["prev_net_cum20"] = round(sum(nd for _, nd in gdone[-20:]), 2)
        gstreak = 0
        for _, nd in gdone:
            w = 1 if nd > 0 else -1
            gstreak = w if gstreak == 0 or ((gstreak > 0) != (w > 0)) else gstreak + w
        feats[i]["prev_streak"] = gstreak

        while g_entries and g_entries[0] < cutoff - 86400:
            g_entries.pop(0)
        feats[i]["entries_24h"] = len(g_entries)

        nd = nets[i]
        ck_closed.setdefault(ck, []).append((exits[i], nd))
        g_closed.append((exits[i], nd))
        recent.append(nd)
        if len(recent) > 20:
            recent.pop(0)
        g_entries.append(int(trades[i]["entry_ts"]))
    return nets


def main():
    orig = B.enrich_sequential
    B.enrich_sequential = enrich_closed_only
    B.OUT = ROOT / "backtest/tests/_bleed_autopsy_CLOSEDONLY.json"
    B.main()
    B.enrich_sequential = orig
    print("\nLEAK INSTRUMENTATION:", json.dumps(LEAK, indent=2))


if __name__ == "__main__":
    main()

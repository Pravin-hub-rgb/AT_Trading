"""
GATE - no two pinned books may be the same trade set.

WHY THIS EXISTS

On 2026-10-14 the corrected-mark sweep re-fit five books and reported

    TOTAL IS = +3340.9R over 5 books

There are not five books. `fsent_champ_long_mcloff` is `fsent_champ_long` with
`max_consecutive_losses` set to 0. Proven trade-for-trade, not by total:

    long   mcl=3 vs mcloff mcl=3   -> n=497, sha 0ee53f50459e, IDENTICAL
    long   mcl=0 vs mcloff mcl=0   -> n=533, sha cead182faa85, IDENTICAL

`ext_stop_r` (0.0 vs 3.0) and `max_positions` (None vs 0) also differ between the
two configs and are inert here, so the loss-halt is the only live difference.
The portfolio is FOUR distinct books. Any "5 books" total counts the same
strategy twice, and the second copy differs only by whether it stops trading
after three losses.

This is the same failure shape as the "extreme pivot" incident: the CONFIG claims
something the CODE does not do. The registry entry named mcloff reads like a
fifth strategy and behaves like a switch. Nothing in the name said so.

WHAT IT CHECKS

  1. Builds each book on IS at its own pin and hashes the closed-trade set.
  2. HARD FAIL if two books hash identically. Those are one strategy counted
     twice under two names.
  3. Otherwise REPORTS the variant structure: for each pair, which single live
     mechanism separates them.

Step 3 is not a failure and must not be. Several earlier drafts of this gate
tried to make it one and both were wrong.

The first draft failed only on identical hashes and passed - correctly, because
no two books share a trade set at their own pins. The second draft called a pair
"duplicate" when realigning ONE differing parameter made the hashes match. That
is a tautology: two books differing only in `exp_fs_entry_side` always match when
you set one side to the other, because a long book and a short book differ by
definition in their side. It fired on long-vs-short and long-vs-htffs, which are
the most legitimate pairs in the set.

The distinction that actually matters is:

  IDENTICAL   same trade set at own pins -> one strategy, two names -> FAIL
  VARIANT     differs by one live mechanism -> a real slice of the signal ->
              legitimate, but it CORROBORATES NOTHING INDEPENDENTLY

So this gate reports the variant structure and lets the owner decide what counts
as independent confirmation. That judgment is not a script's to make.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\backend\\venv\\Scripts\\python.exe -u exp_book_uniqueness.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOKS = ["fsent_champ_long", "fsent_champ_short", "fsent_champ_long_htf15",
         "fsent_champ_long_htffs", "fsent_champ_long_mcloff"]


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, get_data
    from engine.v18_params import SWING
    from experiment_registry import EXPERIMENTS
    from src.btc.btc_swing import compute_btc_swings

    sim = build_family_module()
    d = get_data()

    def chain(cd, fl, mb, gap=1):
        return compute_btc_swings(
            fl, opts={"minBars": max(2, int(mb)), "b2GapBars": gap},
            max_swings=max(1, len(fl) // 2))

    sw15 = chain(d["c15"], d["f15"], SWING["min_bars_15m"])
    sw10 = chain(d["c1h"], d["f1h"], 10)
    htf15 = chain(d["c1h"], d["f1h"], 15)
    sw20 = chain(d["c1h"], d["f1h"], SWING["min_bars_1h"])
    pick = {"sw10": sw10, "sw20": sw20, "htf15": htf15}

    print("=" * 78)
    print("BOOK UNIQUENESS GATE - each pinned book must be a distinct trade set")
    print("=" * 78)
    print()

    def trades(b, override=None):
        cfg = EXPERIMENTS[b]
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        if override:
            p.update(override)
        sw = pick.get(cfg.get("swing") or "sw10", sw10)
        res = sim(d["c1h"], sw, d["c15"], sw15, fine_ltf=d["fine"], **p)
        tr = res["ltf_trades"] if isinstance(res, dict) else res
        rows = []
        for x in tr:
            if str(x.get("outcome", "")).lower() == "open":
                continue
            rows.append("%s|%s|%.4f" % (x.get("entry_time") or x.get("entry")
                                        or x.get("entry_idx"),
                                        x.get("dir"), x.get("r_multiple") or 0.0))
        rows.sort()
        return len(rows), hashlib.sha256(chr(10).join(rows).encode()).hexdigest()[:12]

    own = {}
    for b in BOOKS:
        if not isinstance(EXPERIMENTS.get(b), dict):
            print("  [skip] %s not a dict entry" % b)
            continue
        n, h = trades(b)
        own[b] = (n, h)
        print("  %-28s n=%-4d  %s   (own pin)" % (b, n, h))

    print()
    byhash = {}
    for b, (n, h) in own.items():
        byhash.setdefault(h, []).append(b)

    hard = [(v[0], b, v[1]) for v in byhash.values() if len(v) > 1 for b in v[1:]]
    if hard:
        print("  [FAIL] identical trade sets - one strategy under two names:")
        for a, b, h in hard:
            print("      %s == %s  (%s)" % (a, b, h))
        return 1
    print("  [ok] no two books share a trade set at their own pins.")
    print()

    print("  ---- VARIANT STRUCTURE (report, not failure) ----")
    print("  How many LIVE mechanisms separate each pair. 1 means the two books")
    print("  are one signal sliced two ways, not two independent confirmations.")
    print()
    variants = []
    for i, a in enumerate(list(own)):
        for b in list(own)[i + 1:]:
            pa = {**BP, **EXPERIMENTS[a]["params"]}
            pb = {**BP, **EXPERIMENTS[b]["params"]}
            differ = [k for k in set(pa) | set(pb)
                      if repr(pa.get(k)) != repr(pb.get(k))]
            # the swing chain is a registry key, not a param, but it is the most
            # structural difference a book can have - it redraws every entry.
            if (EXPERIMENTS[a].get("swing") or "sw10") != (EXPERIMENTS[b].get("swing") or "sw10"):
                differ.append("<swing chain>")
            live = []
            for k in differ:
                if k in ("exp_fs_entry_side", "<swing chain>"):
                    live.append(k)
                    continue
                _, h = trades(a, {k: pb.get(k)})
                if h != own[a][1]:
                    live.append(k)
            if len(live) <= 1:
                mech = live[0] if live else "(none - configs differ only in inert keys)"
                print("    %-28s vs %-28s  1 live mechanism: %s"
                      % (a, b, mech))
                variants.append((a, b, mech))

    print()
    if variants:
        print("  RESULT: pass - no duplicates. %d pair(s) are variants of one signal:" % len(variants))
        for a, b, m in variants:
            print("     - %s / %s differ by %s" % (a, b, m))
        print()
        print("  These are legitimate slices, but they share one signal. Counting")
        print("  them as separate confirmations overstates the evidence. Whether a")
        print("  variant counts as independent confirmation is the owner's call.")
    else:
        print("  RESULT: pass - every book differs from every other by >1 mechanism.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
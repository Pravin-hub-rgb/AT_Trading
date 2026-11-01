"""B3/flipb ENTRY - the user's sequence theory on the Book 107 config.

THE IDEA
    Book 107 enters on 15m FS prints with 1h windows opened on 1h flip/b2
    breaks. The user wants the sequence-confirming marks instead, on BOTH
    planes:
      LTF: enter on 15m b3 / flipb marks (the global sequence labels)
      HTF: open the 1h windows on 1h b3 / flipb trades instead of
           flip/decisive/b2.  Mapping: decisive -> b3, flip -> flipb,
           b2 -> flipb (the b2 bucket is unused in the atr_high router).

    Direction policing is unchanged: LTF entries must match the 1h window
    direction (the engine's `if sig["dir"] != d: continue` gate), exactly
    as Book 107 does with its flip/dec windows and fs_long side.

ARMS - PRE-REGISTERED, EIGHT
    base       fs entry, HTF pools flip/dec/b2      (= Book 107, re-measured)
    htf        fs entry, HTF pools -> b3/flipb      (HTF change alone)
    b3         LTF entry=b3, HTF pools shipped
    flipb      LTF entry=flipb, HTF pools shipped
    flipb2     LTF entry=flipb2  (the owner's ordinal ask, 2026-11-01: skip
               the first flipb mark of the swing, enter on the SECOND - the
               third flip-side mark after the FLIP; a swing with fewer
               never trades)
    b3b2       LTF entry=b3b2    (same ordinal idea: skip the first B3,
               enter on the second B3 mark - the 4th+ same-dir break)
    b3+htf     LTF b3 entry + HTF pools b3/flipb    (the user's full idea)
    flipb+htf  LTF flipb entry + HTF pools b3/flipb

MECHANICS
    LTF: unified's exp_entry_break parameter (priority above
    exp_fs_entry_side) is already shipped - no source patch. The engine
    walk (backend/src/btc/btc_engine.py) labels every mark and only
    relabels B2->B3/flipb; a b3/flipb selection returns those exact marks.
    HTF: simulate_btc_trades_v7 is imported at function level inside
    unified, so wrapping src.btc.engines.v7_timecap.simulate_btc_trades_v7
    reroutes all three pools without touching the engine source.
"""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

import experiment_registry as reg
import run_experiment as re_
import exp_equity_quality as eq
import src.btc.engines.v7_timecap as v7m

BOOK = reg.EXPERIMENTS["fsent_champ_long_mcloff_htf15"]
SWING_KEY = BOOK["swing"]            # htf15
# Union exactly as the harness measures Book 107: BP under the book params.
BASE_PARAMS = {**re_.BP, **dict(BOOK["params"])}

_v7_orig = v7m.simulate_btc_trades_v7


def _v7_b3flipb(candles, swings, *, entry_break="", **kw):
    eb = {"decisive": "b3", "flip": "flipb", "b2": "flipb"}.get(entry_break, entry_break)
    return _v7_orig(candles, swings, entry_break=eb, **kw)


ARMS = [
    ("base      fs/htf:flip,dec,b2", {}, False),
    ("htf       fs/htf:b3,flipb",    {}, True),
    ("b3        ltf only",           {"exp_entry_break": "b3"}, False),
    ("flipb     ltf only",           {"exp_entry_break": "flipb"}, False),
    ("flipb2    ltf only, 2nd",      {"exp_entry_break": "flipb2"}, False),
    ("b3b2      ltf only, 2nd",      {"exp_entry_break": "b3b2"}, False),
    ("b3+htf    both changed",       {"exp_entry_break": "b3"}, True),
    ("flipb+htf both changed",       {"exp_entry_break": "flipb"}, True),
]


def run(sim, data, params):
    # FRESH CHAINS PER RUN - the walk relabels the shared swing dicts in
    # place, so consecutive arms in one process would otherwise see each
    # other's labels. Every /backtest request rebuilds its chains, and this
    # replay must match that: one pass of the walk per freshly built chain.
    # (Discovered the hard way: the flipb arm measured 523 IS entries off
    # the b3 arm's gasped chain while the engine's first-pass answer is
    # ~470 - the walk was not idempotent until btc_engine got kind0
    # eligibility; copies keep every future arm honest regardless.)
    sw15 = copy.deepcopy(data["sw15"])
    sw_win = copy.deepcopy(data[SWING_KEY])
    out = sim(
        data["c1h"], sw_win, data["c15"], sw15,
        fine_ltf=data["fine"], **params,
    )
    return out["ltf_trades"]


def row(tr):
    n = len(tr)
    if not n:
        return (0, 0, 0, 0.0, 0.0, 0.0, 0.0)
    gross = sum(float(t["r_multiple"]) for t in tr)
    net = re_.net_r(tr)
    dd = re_._net_dd(tr)
    wr = sum(1 for t in tr if float(t["r_multiple"]) > 0) / n
    lt = sum(1 for t in tr if str(t.get("dir", "")) in ("1", "long", "up"))
    return (n, lt, n - lt, gross, net, dd, wr)


def main():
    data = {s: eq.load_scope(s) for s in ("is", "oos")}
    sim = re_.build_module()
    for s in ("is", "oos"):
        print(f"\n=== {s.upper()} (swing={SWING_KEY}) ===")
        print(f"{'arm':<26}{'n':>6}{'lt':>6}{'st':>6}{'gross':>10}{'net':>10}{'dd':>8}{'wr%':>7}")
        for name, ov, htf_swap in ARMS:
            params = {**BASE_PARAMS, **ov}
            if htf_swap:
                v7m.simulate_btc_trades_v7 = _v7_b3flipb
                try:
                    tr = run(sim, data[s], params)
                finally:
                    v7m.simulate_btc_trades_v7 = _v7_orig
            else:
                tr = run(sim, data[s], params)
            n, lt, st, gross, net, dd, wr = row(tr)
            print(f"{name:<26}{n:>6}{lt:>6}{st:>6}{gross:>10.1f}{net:>10.1f}{dd:>8.1f}{wr * 100:>7.1f}")


def halves(tr):
    tr = sorted(tr, key=lambda t: int(t.get("entry_ts", 0) or 0))
    m = len(tr) // 2
    return tr[:m], tr[m:]


def net_only(tr):
    return re_.net_r(tr) if tr else 0.0


def main_halves():
    data = {s: eq.load_scope(s) for s in ("is", "oos")}
    sim = re_.build_module()
    keep = ("base      fs/htf:flip,dec,b2", "b3        ltf only",
            "flipb     ltf only", "flipb2    ltf only, 2nd",
            "b3b2      ltf only, 2nd")
    for s in ("is", "oos"):
        print(f"\n=== {s.upper()} halves partition (base vs b3 vs flipb vs ordinals) ===")
        arms_tr = {}
        for _, ov, _ in [a for a in ARMS if a[0] in keep]:
            params = {**BASE_PARAMS, **ov}
            arms_tr[ov.get("exp_entry_break", "base")] = run(sim, data[s], params)
        for k, tr in arms_tr.items():
            a, b = halves(tr)
            print(f"  {k:<6} H1 n={len(a):>4} net={net_only(a):>8.1f}   "
                  f"H2 n={len(b):>4} net={net_only(b):>8.1f}")
        base, flipb = arms_tr.get("base", []), arms_tr.get("flipb", [])
        if base:
            cells = {}
            for t in base:
                k = str(t.get("exit_date", ""))[:7]
                cells.setdefault(k, [[], []])[0].append(t)
            for t in flipb:
                k = str(t.get("exit_date", ""))[:7]
                cells.setdefault(k, [[], []])[1].append(t)
            wins = sum(1 for b_, f_ in cells.values() if net_only(f_) > net_only(b_))
            ties = sum(1 for b_, f_ in cells.values() if net_only(f_) == net_only(b_))
            print(f"  month cells flipb>base (net): {wins} >, {ties} ties, "
                  f"{len(cells) - wins - ties} <, of {len(cells)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "halves":
        main_halves()
    else:
        main()

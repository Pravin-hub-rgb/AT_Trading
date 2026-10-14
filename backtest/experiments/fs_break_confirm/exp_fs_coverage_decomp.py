"""
P83 - the FS coverage question, and the trade-level decomposition P74 asked for.

WHY THIS EXISTS

`method/FS_ENTRY.md` left one thing open: "2900 swings exist in IS and 1634 in
OOS, all with an FS - so a *true* FS-only engine could in principle take swings
that never produced a B2/flip entry, which would be a much larger book. That is
not simulated here."

`method/FS_ONLY_ENGINE.md` answered it on 2026-09-28: **zero** swings lacked a
B2/FLIP mark, so the FS-only book is SMALLER, not larger (263t IS, 108t OOS).
That was measured on the pre-volatile-B1-fix chain. Re-verified here first,
because the chain changed on 2026-10-13 and the answer is one count.

Then the thing P74 named as "the number the owner's question is really asking"
and which was never run: a **trade-level decomposition**. P73 reported 646 trades
against a 500-trade champion and "+146 for +79.4R", and P74 showed that reading
was unsafe because the routed path stops producing break entries, so the two
books share trades only where the untouched paths happened to coincide.
"Without it, +146 trades for +79.4R is not a claim, it is an arithmetic
coincidence."

This answers it: of the FS-routed book's trades, how many SURVIVE from the base,
how many are NEW, and what each group is actually worth.

ARMS
  base        - the book as pinned
  FS on both  - exp_fs_entry_side="both" and exp_htf_fs_entry="all", i.e. every
                entry routed to the FS print instead of a break mark. This is
                the configuration P73 called "FS-only" and P74 correctly renamed
                a hybrid; here BOTH sides are rerouted, so the LTF layer really
                is FS-only and the label is not being borrowed.

KEY
  (entry_ts, dir, swing_no) - the same identity the repo already uses for mark
  dedup, so "survivor" means the same trade, not merely the same count.

CAUSALITY
  Nothing new is read. exp_fs_entry_side and exp_htf_fs_entry are shipped,
  already-causal knobs: fs_at_idx is at or after seg.end_idx so the FS candle has
  closed before the print is used. This harness routes entries; it does not
  invent a trigger.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_fs_coverage_decomp.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
BOOKS = ["fsent_champ_long", "fsent_champ_short"]


def load_era(era: str) -> dict:
    if era == "is":
        from run_experiment import get_data
        return get_data()
    from test_4_new_concepts import load_unseen, load_fine_1m as load_fine
    from engine.v18_params import SWING
    from src.btc.btc_routes import _compute_swings
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
            "sw15": _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
            "sw10": _compute_swings(f1h, "continuous", min_bars=10),
            "sw20": _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
            "htf15": _compute_swings(f1h, "continuous", min_bars=15),
            "fine": load_fine(c15[0]["ts"], c15[-1]["ts"])}


def key(t: dict) -> tuple:
    return (t.get("entry_ts"), t.get("dir"), t.get("swing_no"))


def rs(trades: list[dict]) -> dict:
    closed = [t for t in trades if str(t.get("outcome", "")).lower() != "open"]
    v = [float(t["r_multiple"]) for t in closed if t.get("r_multiple") is not None]
    n = len(v)
    net = sum(v)
    wins = [x for x in v if x > 0]
    losses = [x for x in v if x <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    return {"n": n, "net": round(net, 2),
            "avgR": round(net / n, 3) if n else 0.0,
            "pf": round(pf, 2) if pf is not None else None}


def coverage(candles: list[dict], swings: list[dict]) -> dict:
    """The FS_ENTRY.md open question, re-verified on the current chain."""
    have_fs = no_mark = with_mark = 0
    for s in swings:
        fi = s.get("fs_at_idx")
        if fi is None or not (0 <= int(fi) < len(candles)):
            continue
        have_fs += 1
        kinds = {b.get("kind") for b in (s.get("breaks") or [])}
        if kinds & {"B2", "FLIP"}:
            with_mark += 1
        else:
            no_mark += 1
    return {"swings_with_fs": have_fs, "also_have_B2_or_FLIP": with_mark,
            "FS_only_no_break_mark": no_mark}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, get_swings
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    data = {e: load_era(e) for e in ("is", "oos")}

    print("=" * 78)
    print("FS COVERAGE - FS_ENTRY.md's open question, on the CURRENT chain")
    print("=" * 78)
    out = {"stage": "fs_coverage_decomp", "coverage": {}, "decomp": {}}
    for era in ("is", "oos"):
        c = coverage(data[era]["c15"], data[era]["sw15"])
        out["coverage"][era] = c
        print("  %-4s swings with an FS      : %d" % (era, c["swings_with_fs"]))
        print("        ...that also carry a  : %d" % c["also_have_B2_or_FLIP"])
        print("           B2/FLIP mark")
        print("        FS-ONLY, no break mark: %d" % c["FS_only_no_break_mark"])
        print("        -> an FS-only book is %s"
              % ("LARGER" if c["FS_only_no_break_mark"] else "NOT larger - it is smaller"))
    print()

    print("=" * 78)
    print("TRADE-LEVEL DECOMPOSITION - the number P74 asked for")
    print("=" * 78)
    for book in BOOKS:
        cfg = EXPERIMENTS.get(book)
        if not isinstance(cfg, dict):
            continue
        print("\n=== %s ===" % book)
        out["decomp"][book] = {}
        for era in ("is", "oos"):
            d = data[era]
            base = {**BP, **cfg["params"]}
            base.setdefault("exp_partial_r", 0.0)
            sw = get_swings(d, cfg.get("swing") or "sw10")
            common = dict(base)
            fsarm = {**base, "exp_fs_entry_side": "both", "exp_htf_fs_entry": "all"}

            rb = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **common)
            tb = rb["ltf_trades"] if isinstance(rb, dict) else rb
            ra = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **fsarm)
            ta = ra["ltf_trades"] if isinstance(ra, dict) else ra

            kb = {key(t): t for t in tb}
            ka = {key(t): t for t in ta}
            surv = [kb[k] for k in kb if k in ka]
            new = [ka[k] for k in ka if k not in kb]
            gone = [kb[k] for k in kb if k not in ka]

            sb, sa, sn, sg = rs(tb), rs(ta), rs(new), rs(gone)
            print("  --- %s ---" % era.upper())
            print("    base (pinned)      n=%-4d net=%+9.2fR  avgR=%+.3f PF=%s"
                  % (sb["n"], sb["net"], sb["avgR"], sb["pf"]))
            print("    FS-routed both     n=%-4d net=%+9.2fR  avgR=%+.3f PF=%s"
                  % (sa["n"], sa["net"], sa["avgR"], sa["pf"]))
            print("    delta              n %+d   net %+.2fR"
                  % (sa["n"] - sb["n"], sa["net"] - sb["net"]))
            print()
            print("    decomposition of the FS-routed book:")
            print("      SURVIVORS (same trade in both) n=%-4d net=%+9.2fR  avgR=%+.3f"
                  % (rs(surv)["n"], rs(surv)["net"], rs(surv)["avgR"]))
            print("      NEWCOMERS (FS arm only)        n=%-4d net=%+9.2fR  avgR=%+.3f"
                  % (sn["n"], sn["net"], sn["avgR"]))
            print("      and the base trades the FS arm DROPPED  n=%-4d net=%+9.2fR  avgR=%+.3f"
                  % (rs(gone)["n"], rs(gone)["net"], rs(gone)["avgR"]))
            if sn["n"]:
                print("      -> each newcomer is worth %+.3fR; each dropped survivor was worth %+.3fR"
                      % (sn["avgR"], rs(gone)["avgR"]))
            out["decomp"][book][era] = {"base": sb, "fs_both": sa,
                                        "survivors": rs(surv), "newcomers": sn,
                                        "dropped_from_base": rs(gone)}
    (HERE / "fs_coverage_decomp_results.json").write_text(json.dumps(out, indent=2),
                                                          encoding="utf-8")
    print("\nwrote %s" % (HERE / "fs_coverage_decomp_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""exp_mode_autopsy - why did ch=55 gain 42R on two trades, and what does ch=50 cost?

WHAT THE SWEEP SAID, AND WHY NONE OF IT IS ADOPTABLE YET
=========================================================
exp_mode_decide.py found two arms that are not worse in either era:

  decisive_vs_flip_chop ch=50   IS +41.2R  OOS +18.6R   IS n 577 (+49)  IS dd 28.2 (+14.8)
  decisive_vs_flip_chop ch=55   IS +42.2R  OOS  +8.9R   IS n 526 (  -2)  IS dd 13.4 ( 0.0)

Both numbers are real and neither is adoptable on this evidence, for opposite
reasons:

  ch=55 gains 42R out of sample... in sample, by REMOVING TWO TRADES. Two trades
  worth 21R each. The per-trade arithmetic is the tell: no regime router should
  be worth 21R per trade. That is a specific pair of trades, and a router tuned
  to exclude two known trades is a fit to them.

  ch=50 gains more out of sample (+18.6R) and is broadly distributed rather than
  concentrated (49 more trades in sample at +0.84R each). But it roughly
  DOUBLES in-sample drawdown, 13.4R to 28.2R. The sweep printed net R and dd;
  only one of those is a reason to trade something. A book that buys 41R by
  risking 28R of drawdown instead of 13R is a different risk profile, and the
  halt governance decision already established that drawdown is not a number to
  be spent casually.

So this harness answers the two questions that decide it:
  1. which trades does each threshold actually remove, and what are they worth
  2. what does ch=50 do to the drawdown's SHAPE, not just its depth

Run:  cd backtest/tests
      python -u exp_mode_autopsy.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
CANDS = (50, 55)
OUT_JSON = Path(__file__).parent / "_mode_autopsy.json"
OUT_MD = Path(__file__).parent / "_mode_autopsy.md"

FIELDS = ("entry_ts", "dir", "entry_price", "sl", "exit_ts", "exit_price", "r_multiple")


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)

    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], cfg.get("swing") or "sw10")

    def run(era, mode, cthr):
        p = dict(base)
        p["mode"] = mode
        if cthr is not None:
            p["chop_thresh"] = cthr
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        m = compute([net_r([t]) for t in tr], [t.get("entry_date", "") for t in tr])
        return tr, m

    print("=" * 96)
    print("MODE AUTOPSY - which trades each threshold removes, and what they are worth")
    print("=" * 96)

    report = {}
    for era in ("is", "oos"):
        ship_tr, ship_m = run(era, "atr_high", None)
        ship_d = {int(t["entry_ts"]): t for t in ship_tr}
        print("\n" + "#" * 96)
        print("# %s   shipping atr_high: n=%d  net %+.1f  dd %.1f"
              % (era.upper(), ship_m["n"], ship_m["net"], ship_m.get("max_dd", 0)))
        print("#" * 96)

        for c in CANDS:
            tr, m = run(era, "decisive_vs_flip_chop", c)
            cand_d = {int(t["entry_ts"]): t for t in tr}
            only_ship = sorted(set(ship_d) - set(cand_d))
            only_cand = sorted(set(cand_d) - set(ship_d))
            s_removed = [net_r([ship_d[t]]) for t in only_ship]
            s_added = [net_r([cand_d[t]]) for t in only_cand]

            print("\n  --- chop_thresh=%d ---" % c)
            print("  n %d -> %d   net %+.1f -> %+.1f   dd %.1f -> %.1f   max_uw %s -> %s"
                  % (ship_m["n"], m["n"], ship_m["net"], m["net"],
                     ship_m.get("max_dd", 0), m.get("max_dd", 0),
                     ship_m.get("max_uw", "?"), m.get("max_uw", "?")))
            print("  REMOVED vs shipping: %d trades, %+.2fR"
                  % (len(s_removed), sum(s_removed)))
            print("  ADDED   vs shipping: %d trades, %+.2fR"
                  % (len(s_added), sum(s_added)))
            for ts, v in sorted(zip(only_ship, s_removed), key=lambda kv: -kv[1])[:8]:
                t = ship_d[ts]
                hold = (int(t["exit_ts"]) - int(t["entry_ts"])) / 86400.0
                print("      removed %s  %-4s  %+7.3fR   hold %.1fd"
                      % (ts, t.get("dir"), v, hold))
            for ts, v in sorted(zip(only_cand, s_added), key=lambda kv: -kv[1])[:8]:
                t = cand_d[ts]
                hold = (int(t["exit_ts"]) - int(t["entry_ts"])) / 86400.0
                print("      added   %s  %-4s  %+7.3fR   hold %.1fd"
                      % (ts, t.get("dir"), v, hold))
            rem = sorted(s_removed, reverse=True)
            if rem:
                tot = sum(rem)
                print("      top removed trade %+.3fR of %+.2fR removed (%.0f%%)"
                      % (rem[0], tot, 100.0 * rem[0] / tot if tot else 0))
                if len(rem) <= 5:
                    print("      ^^ only %d trades removed; this is the whole argument"
                          % len(rem))
            report.setdefault(era, {})[str(c)] = {
                "n": m["n"], "net": round(m["net"], 2), "dd": round(m.get("max_dd", 0), 2),
                "ship_n": ship_m["n"], "ship_net": round(ship_m["net"], 2),
                "ship_dd": round(ship_m.get("max_dd", 0), 2),
                "removed": [{"ts": t, "r": round(v, 3)} for t, v in zip(only_ship, s_removed)],
                "added": [{"ts": t, "r": round(v, 3)} for t, v in zip(only_cand, s_added)],
            }

    OUT_JSON.write_text(json.dumps({"book": BOOK, "report": report}, indent=2) + "\n",
                        encoding="utf-8")
    print("\nwrote %s" % OUT_JSON.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
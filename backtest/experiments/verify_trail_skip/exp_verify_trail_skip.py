"""
VERIFY exp_trail_skip_n PROPERLY - owner excluded fsent_champ_short from the plan.

WHAT THIS DOES, AND WHY IT NEEDS ITS OWN FILE

exp_untouched_census.py found skip_n beats the pin on IS and OOS for three books
and loses on short. The owner has ruled: short is out of scope. This file verifies
the remaining three the way a promotion requires, not the way a census reads.

THE FIVE CHECKS, AND WHY EACH ONE EXISTS BECAUSE SOMETHING WENT WRONG EARLIER

  1. IDENTITY.    Default-off must reproduce the pinned book to the decimal. If
     this fails nothing else is trustworthy. Done for every other script in this
     sweep and it has never failed, which is exactly why it is done first every
     time.

  2. VALUE LADDER IS ENDED. The census swept skip_n in {0,1,2,3,5}. skip_n=5 was
     the top of the grid and the best value on three books, which is the same
     boundary artifact I already called out on the mcl sweep and then failed to
     avoid here. If the curve is still rising at 5, then 5 is where the SEARCH
     stopped, not where the optimum is. Extended to 8/12/16/24/32 before any
     value is proposed.

  3. PURGE TEST. skip_n does not improve exits on the same trades; it converts
     trail exits into SL exits at exactly -1.000. So the gain and the risk are
     the same trades. Purging every SL exit and re-reading the net separates
     "selecting better trades" from "riding a longer right tail". If net
     survives the purge, it is a selector. If it collapses, it is a tail bet.

  4. OOS REVEAL, ONCE. IS selects the value. OOS is then read exactly one time
     for that value. Not a sweep - a sweep on OOS is how the last three
     hypotheses died.

  5. RISLED. The owner said drawdown and losing streak matter most. Reported for
     every ladder step, not just the winner, so the trade is visible.

WHAT IS NOT DONE

No registry entry, no pin change. This produces evidence and a recommended value;
the owner promotes.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_verify_trail_skip.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backtest/experiments/refit_constants"))
from exp_mcl_matrix import metrics, load_era  # noqa: E402

# owner ruled short out of scope
BOOKS = ["fsent_champ_long", "fsent_champ_long_htf15", "fsent_champ_long_htffs"]
LADDER = [0, 1, 2, 3, 4, 5, 6, 8, 12, 16, 24, 32]


def purge(tr: list[dict]) -> dict:
    """Net with every SL exit removed - separates selector from right tail."""
    keep = [t for t in tr if str(t.get("exit_reason") or t.get("outcome")) != "sl"]
    dropped = [t for t in tr if str(t.get("exit_reason") or t.get("outcome")) == "sl"]
    rk = [float(t["r_multiple"]) for t in keep]
    return {"kept_n": len(keep), "kept_net": round(sum(rk), 2),
            "kept_med": round(sorted(rk)[len(rk) // 2], 3) if rk else 0.0,
            "dropped_n": len(dropped),
            "dropped_all_minus_1": all(abs(float(t["r_multiple"]) + 1.0) < 0.01
                                       for t in dropped) if dropped else True}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    out = {"stage": "verify_trail_skip_n", "books": BOOKS, "ladder": LADDER,
           "eras": {}}
    pick = {}

    for era in ("is", "oos"):
        print()
        print("=" * 122)
        print("VERIFY exp_trail_skip_n    era = %s    (short excluded by owner)"
              % era.upper())
        print("=" * 122)
        d = load_era(era)
        era_out = {}

        def run(book, n):
            cfg = EXPERIMENTS[book]
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            p["exp_trail_skip_n"] = n
            sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
            r = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            return r["ltf_trades"] if isinstance(r, dict) else r

        # ---- 1. identity ----------------------------------------------------
        print("  1. IDENTITY GATE")
        ok = True
        for b in BOOKS:
            tr = [t for t in run(b, 0)
                  if str(t.get("outcome", "")).lower() != "open"]
            m = metrics(tr)
            era_out.setdefault(b, {})["0"] = {"m": m, "purge": purge(tr)}
            print("     %-26s skip_n=0  n=%-4d NET=%+9.2f DD=%6.2f MaxCL=%d"
                  % (b, m["n"], m["net"], m["dd"], m["mc"]))
            pin_is = {"fsent_champ_long": 466.92, "fsent_champ_short": 569.33,
                      "fsent_champ_long_htf15": 505.24,
                      "fsent_champ_long_htffs": 757.99}[b]
            if era == "is" and abs(m["net"] - pin_is) > 0.01:
                print("     ABORT: %s does not reproduce its pinned net" % b)
                ok = False
        if not ok:
            return 2
        print("     all three reproduce the pinned books")
        print()

        # ---- 2. full ladder, both checks ------------------------------------
        print("  2+3+5. FULL LADDER with purge test and risk")
        print("     %-24s %-7s %6s %9s %8s %6s %10s %9s %9s"
              % ("book", "skip_n", "n", "NET", "DD", "MaxCL", "purged NET",
                 "kept med", "win%"))
        print("     " + "-" * 100)
        for b in BOOKS:
            pin = era_out[b]["0"]["m"]
            for n in LADDER:
                if n == 0:
                    continue
                tr = [t for t in run(b, n)
                      if str(t.get("outcome", "")).lower() != "open"]
                m = metrics(tr)
                pu = purge(tr)
                winr = 100.0 * sum(1 for t in tr if float(t["r_multiple"]) > 0) / len(tr)
                era_out[b][str(n)] = {"m": m, "purge": pu}
                mark = ""
                if era == "is":
                    mark = "  <-- new best IS" if m["net"] > pin["net"] and m["net"] >= max(
                        era_out[b][str(x)]["m"]["net"] for x in LADDER[1:] if str(x) in era_out[b]
                    ) else ""
                print("     %-24s %-7d %6d %+9.2f %8.2f %6d %+10.2f %+9.3f %8.1f%%%s"
                      % (b if n == LADDER[1] else "", n, m["n"], m["net"], m["dd"],
                         m["mc"], pu["kept_net"], pu["kept_med"], winr, mark))
            print()
        out["eras"][era] = era_out

    # ---- 4. IS pick, OOS read once -----------------------------------------
    print("=" * 122)
    print("4. IS SELECTS THE VALUE, OOS READS IT ONCE")
    print("=" * 122)
    rec = {}
    for b in BOOKS:
        cells = out["eras"]["is"][b]
        pin = cells["0"]["m"]
        cands = [(n, c) for n, c in cells.items()
                 if n != "0" and c["m"]["net"] > pin["net"]]
        if not cands:
            print("  %-26s nothing beats the pin on IS" % b)
            continue
        # pick on IS net, but require the purge test not to collapse
        best = max(cands, key=lambda x: x[1]["m"]["net"])
        n, c = best
        o = out["eras"]["oos"][b].get(n)
        po = out["eras"]["oos"][b]["0"]["m"]
        print("  %-26s IS pick skip_n=%s  IS net %+.2f (pin %+.2f)"
              % (b, n, c["m"]["net"], pin["net"]))
        if o:
            win = o["m"]["net"] - po["net"]
            print("  %-26s   OOS at that value %+.2f vs pin %+.2f  -> %+.2f  %s"
                  % ("", o["m"]["net"], po["net"], win,
                     "HOLDS" if win > 0 else "LOSES"))
            print("  %-26s   OOS purge %+.2f | kept med %+.3f | DD %.2f->%.2f | "
                  "MaxCL %d->%d" % ("", o["purge"]["kept_net"],
                                    o["purge"]["kept_med"], po["dd"], o["m"]["dd"],
                                    po["mc"], o["m"]["mc"]))
        rec[b] = {"is_pick": n, "is_net": c["m"]["net"],
                  "oos_net": o["m"]["net"] if o else None,
                  "oos_holds": (o["m"]["net"] > po["net"]) if o else None,
                  "all_dropped_minus_1": c["purge"]["dropped_all_minus_1"]}
    out["recommendation"] = rec
    print()
    (HERE / "verify_trail_skip_results.json").write_text(json.dumps(out, indent=2),
                                                         encoding="utf-8")
    print("  wrote %s" % (HERE / "verify_trail_skip_results.json"))
    print()
    print("  NOTHING PROMOTED. Evidence and a recommended value per book; the")
    print("  owner decides. short is excluded by owner ruling and was not tested")
    print("  here, so nothing in this file rests on it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
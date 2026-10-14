"""
MCL MATRIX - the loss-halt measured on NET, both eras, full metrics.

WHY THIS FILE EXISTS

The earlier sweep said max_consecutive_losses=0 beat the pin of 3 by +44R on
IS. That number is GROSS. r_multiple is gross R; the canonical book table is
NET = gross - fees - funding. And mcl=0 produces MORE trades (533 vs 497 on long,
36 extra round trips), so the +44R carries 36 extra costs that were never
subtracted. The advantage could shrink or invert on net.

The owner caught this before I did: "matlab mcl=0 behtar lag raha tha, par wo
abhi PROVE nahi hua... pehle net pe measure karo." Correct. The +44R is not a
result until it survives costs.

THE LADDER IS THE FULL RANGE, NOT JUST {0, 3}

mcl=1 cost ~225R gross on long, far more than mcl=2 or mcl=3. A curve where the
neighbour of the optimum is catastrophic and the optimum itself is worse than no
halt at all is not a risk-control result, it is a shape nobody designed. You only
see that by plotting the whole ladder, which is why it is here rather than a
two-point comparison.

DISCIPLINE

  - IS is the decision surface. OOS is computed and shown for honesty but the
    recommendation column comes from IS only. Tuning against both is how the last
    mistake was made.
  - fsent_champ_long_mcloff is EXCLUDED from the ladder. Its pin is already 0, so
    sweeping it answers nothing. It is instead used as an independent cross-check
    on long@mcl=0: if the two agree, the NET accounting is trustworthy.
  - 4 books x 8 mcl x 2 eras = 64 runs.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_mcl_matrix.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent

# mcl=3 books. mcloff (pin 0) is the cross-check, not a ladder point.
LADDER_BOOKS = ["fsent_champ_long", "fsent_champ_short",
                "fsent_champ_long_htf15", "fsent_champ_long_htffs"]
CHECK_BOOK = "fsent_champ_long_mcloff"
LADDER = [0, 1, 2, 3, 4, 6, 8, 12]

INSTRUMENT = "BTCUSDT_BYBIT"


def load_era(era: str) -> dict:
    """Copied verbatim from exp_baseline_freeze.py so the era split, the chains
    and the fine-fill window are identical to the A1 freeze. Re-implementing this
    is how numbers silently stop being comparable to the published baseline."""
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


def metrics(tr: list[dict]) -> dict:
    """NET metrics, canonical convention - identical to exp29_final_metrics.py:
    WR/PF/DD/MaxConsecL on GROSS r_multiple; NET = gross - fees/slip - funding
    at 0.01%/8h, leverage-adjusted from the SL distance. Trade ORDER is
    preserved because drawdown and losing-streak are path dependent."""
    from collections import defaultdict
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import get_v18_params

    tr = [t for t in tr if str(t.get("outcome", "")).lower() != "open"]
    n = len(tr)
    if not n:
        return {"n": 0}
    rs = [float(t["r_multiple"]) for t in tr]
    g = get_v18_params(INSTRUMENT)
    c2, _ = _trade_costs(tr, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])

    fund = 0.0
    for t in tr:
        try:
            entry = float(t["entry_price"]); sl = float(t["sl"])
            risk = abs(entry - sl)
            if risk > 0 and entry > 0:
                fund += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (entry / risk)
        except (TypeError, ValueError, KeyError):
            pass

    gross = sum(rs)
    net = gross - c2 - fund
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 0.0

    peak = cum = dd = 0.0
    pk_i = tr_i = pk_ts = tr_ts = b_pk_i = b_pk_ts = 0
    mc = cur = 0
    for i, r in enumerate(rs):
        cum += r
        if cum > peak:
            peak, pk_i, pk_ts = cum, i, int(tr[i].get("exit_ts") or 0)
        dd_ = peak - cum
        if dd_ > dd:
            dd, tr_i, tr_ts = dd_, i, int(tr[i].get("exit_ts") or 0)
            b_pk_i, b_pk_ts = pk_i, pk_ts
        if r <= 0:
            cur += 1
            mc = max(mc, cur)
        else:
            cur = 0

    hold = sum(int(t.get("bars_held") or 0) for t in tr) / n
    span = (int(tr[-1].get("exit_ts") or 0) - int(tr[0].get("entry_ts") or 0)) / 86400.0
    return {"n": n, "gross": round(gross, 2), "cost": round(c2, 2), "fund": round(fund, 2),
            "net": round(net, 2), "npt": round(net / n, 3),
            "wr": round(100.0 * len(wins) / n, 1), "aw": round(aw, 2), "al": round(al, 2),
            "payo": round(aw / abs(al), 2) if al else 0.0, "pf": round(pf, 2),
            "dd": round(dd, 2), "ddt": tr_i - b_pk_i, "ddd": round((tr_ts - b_pk_ts) / 86400.0, 1),
            "mc": mc, "hold_h": round(hold * 0.25, 1),
            "tpy": round(n / (span / 365.0), 1) if span else 0.0,
            "net_dd": round(net / dd, 1) if dd > 0 else 0.0}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()

    print("=" * 128)
    print("MCL MATRIX  -  NET of fees/slip/funding.  IS decides; OOS is shown, not used.")
    print("=" * 128)

    out = {"stage": "mcl_matrix", "ladder": LADDER, "eras": {}}
    tables = {}

    cache = HERE / "mcl_matrix_results.json"
    if cache.exists() and "--force" not in sys.argv:
        out = json.loads(cache.read_text(encoding="utf-8"))
        tables = out["eras"]
        print("\n  loaded cached matrix from %s (pass --force to recompute)" % cache.name)
    else:
        for era in ("is", "oos"):
            print("\n  loading %s ..." % era.upper())
            d = load_era(era)
            res = {}

            def run(book, mcl=None):
                cfg = EXPERIMENTS[book]
                p = {**BP, **cfg["params"]}
                p.setdefault("exp_partial_r", 0.0)
                if mcl is not None:
                    p["max_consecutive_losses"] = mcl
                sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
                r = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
                return r["ltf_trades"] if isinstance(r, dict) else r

            for b in LADDER_BOOKS:
                row = {}
                for m in LADDER:
                    row[str(m)] = metrics(run(b, m))
                    print("    %-28s mcl=%-3d n=%-4d NET=%+9.2fR  DD=%6.2f  MaxConsecL=%-3d PF=%.2f"
                          % (b, m, row[str(m)]["n"], row[str(m)]["net"],
                             row[str(m)]["dd"], row[str(m)]["mc"], row[str(m)]["pf"]))
                res[b] = row

            res[CHECK_BOOK] = {"own": metrics(run(CHECK_BOOK))}
            out["eras"][era] = res
            print()

        tables = out["eras"]
        cache.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("\n  computed and cached -> %s" % cache.name)

    # ---- cross-check: mcloff IS long@mcl=0 ----------------------------------
    print("=" * 128)
    print("CROSS-CHECK - mcloff (pin mcl=0) vs long at mcl=0. Same book, different knob.")
    print("  If these disagree, the NET accounting is wrong and nothing below is usable.")
    print("=" * 128)
    ck = []
    for era in ("is", "oos"):
        a = tables[era][CHECK_BOOK]["own"]
        b = tables[era]["fsent_champ_long"]["0"]
        same = abs(a["net"] - b["net"]) < 0.01 and a["n"] == b["n"]
        ck.append(same)
        print("  %-4s mcloff  n=%-4d NET=%+9.2fR DD=%6.2f mc=%-3d" % (era.upper(), a["n"], a["net"], a["dd"], a["mc"]))
        print("       long@0  n=%-4d NET=%+9.2fR DD=%6.2f mc=%-3d" % (b["n"], b["net"], b["dd"], b["mc"]))
        print("       -> %s" % ("MATCH - NET accounting verified" if same else "MISMATCH - investigate"))
    print()

    # ---- the decision table ---------------------------------------------------
    print("=" * 128)
    print("DECISION TABLE - mcl=0 vs the pin mcl=3.  IS is the decision surface.")
    print("=" * 128)
    print("  %-24s %-3s %-5s %5s %9s %8s %8s %7s %6s %6s %6s"
          % ("book", "mcl", "era", "n", "NET", "DD", "NET/DD", "MaxCL", "PF", "WR%", "hold"))
    print("  " + "-" * 112)
    for b in LADDER_BOOKS:
        for m in (0, 3):
            for era in ("is", "oos"):
                r = tables[era][b][str(m)]
                tag = " <- pin" if m == 3 else ""
                print("  %-24s %-3d %-5s %5d %+9.2f %8.2f %8.1f %7d %6.2f %6.1f %6.1f%s"
                      % (b, m, era.upper(), r["n"], r["net"], r["dd"], r["net_dd"],
                         r["mc"], r["pf"], r["wr"], r["hold_h"], tag))
        print("  " + "-" * 112)

    print()
    print("  DELTA mcl=0 minus mcl=3   (positive = the halt COSTS you, you lose more by halting)")
    print("  %-24s %14s %14s %14s" % ("book", "dNET IS", "dNET OOS", "agree?"))
    for b in LADDER_BOOKS:
        di = tables["is"][b]["0"]["net"] - tables["is"][b]["3"]["net"]
        do = tables["oos"][b]["0"]["net"] - tables["oos"][b]["3"]["net"]
        agree = "same sign" if (di > 0) == (do > 0) else "*** SIGN FLIP ***"
        print("  %-24s %+14.2f %+14.2f %14s" % (b, di, do, agree))
    print()
    print("  A sign flip between eras means the choice does not generalise, whatever")
    print("  it looks like on the surface it was tuned on.")

    # losing streak, since that is what the owner actually cares about
    print()
    print("  MAX LOSING STREAK across the ladder (IS):")
    print("  %-24s %s" % ("book", "".join("%9s" % ("mcl=%d" % m) for m in LADDER)))
    for b in LADDER_BOOKS:
        print("  %-24s %s" % (b, "".join("%9d" % tables["is"][b][str(m)]["mc"] for m in LADDER)))
    print()
    print("  MAX DRAWDOWN across the ladder (IS):")
    print("  %-24s %s" % ("book", "".join("%9s" % ("mcl=%d" % m) for m in LADDER)))
    for b in LADDER_BOOKS:
        print("  %-24s %s" % (b, "".join("%9.1f" % tables["is"][b][str(m)]["dd"] for m in LADDER)))
    print()
    print("  TRADING COST across the ladder (IS, fees+slip+funding):")
    print("  %-24s %s" % ("book", "".join("%9s" % ("mcl=%d" % m) for m in LADDER)))
    for b in LADDER_BOOKS:
        print("  %-24s %s" % (b, "".join("%9.1f" % (tables["is"][b][str(m)]["cost"] + tables["is"][b][str(m)]["fund"]) for m in LADDER)))

    out["cross_check_pass"] = all(ck)
    if not all(ck):
        print()
        print("  WARNING: cross-check failed - NET accounting disagrees with the registry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
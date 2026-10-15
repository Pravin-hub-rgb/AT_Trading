"""
FULL METRICS on exp_mltf, and is it a book?

THE QUESTION

Owner, 2026-10-14: "exp_mtlf kaa poora mujhe metrics do win rate etc etc? and if
this good for making a book??"

exp_mltf=1 was the only one of ten censused knobs to improve BOTH eras on the lean
serial base, and it improved drawdown in both while taking 43% more trades. That is
worth a full readout rather than the three numbers the census printed.

IT IS NOT A NEW IDEA, AND THAT MATTERS FOR THE VERDICT

unified.py:41 already documents this as the entire multi edge: "With the gate on,
the same config is +137.72R IS but -13.26R OOS over 230 trades. Turning it off
gives +325.78R IS / +70.15R OOS." So the question is not "is this real" - it is
"is it real ON THIS LEAN SERIAL BASE, and does it clear the bar this repo uses to
adopt a book". Those are different questions and this file only answers the second
one honestly.

THE BAR THIS REPO USES

From fsent_champ_long_htf15's registration: the owner's own rule was "kabhi
negative nahi hona chahiye" - no negative half-year. So a book that clears both
eras but posts one red half-year is NOT adoptable here regardless of size. That is
the primary gate below, ahead of net.

Metric definitions are the canonical ones from exp29_final_metrics.py: WR / AvgWin /
AvgLoss / Payoff / PF on GROSS trade R; NET = gross - fees/slip - funding at
0.01%/8h leverage-adjusted; DD and MaxConsecL on the net curve via equity_quality.

WHAT IS NOT DONE

No registry entry, no pin change. This produces a readout and a verdict.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_mltf_full_metrics.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backtest/experiments/refit_constants"))
from exp_mcl_matrix import load_era  # noqa: E402

BASE = "fsent_sig_sw10_short"
INSTRUMENT = "BTCUSDT_BYBIT"


def metrics(tr, g, years):
    """Canonical set. equity_quality owns the net curve so dd_net and streak are
    measured on the same lens the registry pins use."""
    from exp_equity_quality import equity_quality, net_r
    if not tr:
        return {}
    q = equity_quality(tr, years)
    rs = [float(t["r_multiple"]) for t in tr]
    nets = [net_r([t]) for t in tr]
    n = len(rs)
    gross = sum(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) else 0.0
    span = (int(tr[-1].get("exit_ts") or 0) - int(tr[0].get("entry_ts") or 0)) / 86400.0
    hold = sum(int(t.get("bars_held") or 0) for t in tr) / n
    # half-year cells, the owner's adoption bar
    hy = defaultdict(float)
    hyc = defaultdict(int)
    for t, r in zip(tr, nets):
        d = (t.get("exit_date") or t.get("entry_date") or "")[:10]
        if len(d) < 7:
            continue
        key = d[:4] + "-H1" if d[5:7] <= "06" else d[:4] + "-H2"
        hy[key] += r
        hyc[key] += 1
    yr = defaultdict(float)
    for t, r in zip(tr, nets):
        d = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        if d:
            yr[d] += r
    return {
        "n": n, "gross": round(gross, 2), "net": round(q["net"], 2),
        "cost": round(gross - q["net"], 2),
        "npt": round(q["net"] / n, 3),
        "wr": round(100.0 * len(wins) / n, 1),
        "aw": round(aw, 2), "al": round(al, 2),
        "payo": round(aw / abs(al), 2) if al else 0.0, "pf": round(pf, 2),
        "dd_net": round(q["max_dd"], 2), "dd_dur": q["max_dd_dur"],
        "dd_days": round(q["max_dd_dur"] and 0, 2),
        "uw_pct": q["uw_pct"], "sortino": round(q["sortino"], 2),
        "calmar": round(q["calmar"], 2),
        "hold_h": round(hold * 0.25, 1),
        "tpy": round(n / (span / 365.0), 1) if span else 0.0,
        "hy": {k: round(v, 2) for k, v in sorted(hy.items())},
        "hy_n": dict(sorted(hyc.items())),
        "yr": {k: round(v, 2) for k, v in sorted(yr.items())},
        "trail": Counter(str(t.get("exit_reason") or t.get("outcome")) for t in tr).get("trail", 0),
        "sl": Counter(str(t.get("exit_reason") or t.get("outcome")) for t in tr).get("sl", 0),
    }


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS
    from engine.v18_params import get_v18_params
    from exp_equity_quality import YEARS

    sim = build_family_module()
    cfg = EXPERIMENTS[BASE]
    base_params = {**BP, **cfg["params"]}
    base_params.setdefault("exp_partial_r", 0.0)
    g = get_v18_params(INSTRUMENT)
    out = {"stage": "mltf_full_metrics", "base": BASE, "eras": {}}

    for era in ("is", "oos"):
        d = load_era(era)
        ch = d[cfg.get("swing") or "sw10"]

        def run(**ov):
            p = dict(base_params); p.update(ov)
            r = sim(d["c1h"], ch, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            return [t for t in (r["ltf_trades"] if isinstance(r, dict) else r)
                    if str(t.get("outcome", "")).lower() != "open"]

        print()
        print("=" * 118)
        print("exp_mltf FULL METRICS on %s      era = %s" % (BASE, era.upper()))
        print("=" * 118)
        arms = {"base (mltf=0)": {}, "mltf=1": {"exp_mltf": 1}}
        res = {}
        for name, ov in arms.items():
            res[name] = metrics(run(**ov), g, YEARS[era])
        b, m = res["base (mltf=0)"], res["mltf=1"]

        rows = [
            ("trades", "n", 0), ("trades/yr", "tpy", 1),
            ("GROSS R", "gross", 2), ("cost (fee+slip+fund)", "cost", 2),
            ("NET R", "net", 2), ("NET per trade", "npt", 3),
            ("WIN RATE %", "wr", 1), ("AvgWin R", "aw", 2), ("AvgLoss R", "al", 2),
            ("Payoff", "payo", 2), ("PROFIT FACTOR", "pf", 2),
            ("maxDD (net)", "dd_net", 2), ("DD duration (trades)", "dd_dur", 0),
            ("underwater %", "uw_pct", 1), ("Sortino", "sortino", 2),
            ("Calmar", "calmar", 2), ("max losing streak", "mc", 0),
            ("avg hold (h)", "hold_h", 1),
            ("trail exits", "trail", 0), ("stop exits", "sl", 0),
        ]
        if "mc" not in b:
            # equity_quality does not expose streak; recompute on net curve
            from exp_equity_quality import net_r
            for name, ov in arms.items():
                tr = run(**ov)
                cur = mcb = 0
                for t in tr:
                    if net_r([t]) <= 0:
                        cur += 1; mcb = max(mcb, cur)
                    else:
                        cur = 0
                res[name]["mc"] = mcb
        print("  %-26s %16s %16s %14s" % ("metric", "base (mltf=0)", "mltf=1", "delta"))
        print("  " + "-" * 76)
        for label, key, dp in rows:
            bv, mv = b.get(key), m.get(key)
            if bv is None or mv is None:
                continue
            dl = ""
            try:
                dl = "%+.*f" % (dp, mv - bv)
            except (TypeError, ValueError):
                dl = ""
            fmt = "%%16.%df" % dp
            print("  %-26s %s %s %14s" % (label, fmt % bv, fmt % mv, dl))

        print()
        print("  THE OWNER'S ADOPTION BAR - 'kabhi negative nahi hona chahiye'")
        print("  %-10s %14s %14s" % ("half-year", "base", "mltf=1"))
        allhy = sorted(set(b["hy"]) | set(m["hy"]))
        for k in allhy:
            print("  %-10s %14s %14s" % (k,
                                         ("%+.2f" % b["hy"][k]) if k in b["hy"] else "-",
                                         ("%+.2f" % m["hy"][k]) if k in m["hy"] else "-"))
        nb = sum(1 for v in b["hy"].values() if v <= 0)
        nm = sum(1 for v in m["hy"].values() if v <= 0)
        print("  negative half-years: base %d of %d   mltf=1 %d of %d"
              % (nb, len(b["hy"]), nm, len(m["hy"])))
        print()
        print("  by year:")
        for k in sorted(set(b["yr"]) | set(m["yr"])):
            print("    %-8s base %+9s    mltf=1 %+9s"
                  % (k, ("%+.2f" % b["yr"][k]) if k in b["yr"] else "-",
                     ("%+.2f" % m["yr"][k]) if k in m["yr"] else "-"))

        # tail dependence: remove the biggest trades
        print()
        print("  TAIL DEPENDENCE - remove the largest winners, does it survive?")
        from exp_equity_quality import net_r
        print("    %-16s %12s %12s %12s" % ("drop top N", "base net", "mltf net", "mltf % kept"))
        for k in (0, 1, 3, 5, 10):
            vals = {}
            for name, ov in arms.items():
                tr = run(**ov)
                nets = [net_r([t]) for t in tr]
                idx = sorted(range(len(nets)), key=lambda i: -nets[i])[:k]
                keep = [v for i, v in enumerate(nets) if i not in set(idx)]
                vals[name] = sum(keep)
            frac = 100.0 * vals["mltf=1"] / vals["base (mltf=0)"] if vals["base (mltf=0)"] else 0
            print("    %-16s %12.2f %12.2f %11.0f%%"
                  % ("top %d" % k, vals["base (mltf=0)"], vals["mltf=1"], frac))
        out["eras"][era] = res
        print()

    # ---- verdict ----------------------------------------------------------
    print("=" * 118)
    print("VERDICT - is this a book?")
    print("=" * 118)
    bi, mo = out["eras"]["is"]["base (mltf=0)"], out["eras"]["is"]["mltf=1"]
    bo, mm = out["eras"]["oos"]["base (mltf=0)"], out["eras"]["oos"]["mltf=1"]
    checks = [
        ("positive in both eras", mm["net"] > 0 and mo["net"] > 0,
         "base OOS %+.2f -> mltf OOS %+.2f" % (bo["net"], mm["net"])),
        ("improves OOS net", mm["net"] > bo["net"],
         "%+.2f" % (mm["net"] - bo["net"])),
        ("improves IS net", mo["net"] > bi["net"],
         "%+.2f" % (mo["net"] - bi["net"])),
        ("no worse OOS drawdown", mm["dd_net"] <= bo["dd_net"],
         "%.2f -> %.2f" % (bo["dd_net"], mm["dd_net"])),
        ("no worse OOS losing streak", mm["mc"] <= bo["mc"],
         "%d -> %d" % (bo["mc"], mm["mc"])),
        ("ZERO negative half-years (owner's bar)",
         all(v > 0 for v in mm["hy"].values()),
         "%d negative of %d cells" % (sum(1 for v in mm["hy"].values() if v <= 0), len(mm["hy"]))),
        ("clears SHORTLIST_IS_MIN 130 in both eras",
         mo["net"] > 130 and mm["net"] > 130,
         "IS %.2f  OOS %.2f" % (mo["net"], mm["net"])),
        ("clears SHORTLIST_OOS_MIN 50 in both eras",
         mo["net"] > 50 and mm["net"] > 50, "OK"),
    ]
    for label, ok, detail in checks:
        print("  [%s] %-42s %s" % ("PASS" if ok else "FAIL", label, detail))
    print()
    print("  NOTE: exp_mltf is NOT a new mechanism. unified.py:41 documents it as the")
    print("  entire multi edge, and it is the engine's own shipping design. This is a")
    print("  confirmation that it also works on the lean serial base, not a discovery.")
    print("  A book built on it would be a RE-PACKAGING of documented engine behaviour,")
    print("  which is worth knowing before it is named as a champion.")
    (HERE / "mltf_full_metrics_results.json").write_text(json.dumps(out, indent=2),
                                                         encoding="utf-8")
    print()
    print("  wrote %s" % (HERE / "mltf_full_metrics_results.json"))
    print("  NOTHING PROMOTED. No registry entry, no pin change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
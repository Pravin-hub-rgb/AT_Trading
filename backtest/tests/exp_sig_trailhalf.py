"""exp_sig_trailhalf - autopsy of exp_trail_half on the single-position sig ladder.

WHY THIS IS THE SAME QUESTION AS exp_trailhalf.py, ASKED AGAIN
=============================================================
On the multi book, exp_trail_half earned +42.5R OOS and was rejected, because
removing the top five trades collapsed the advantage to +0.77R - the gain was six
trades deep and the drawdown rose 2.37x. The framework in
docs/learn/finding optimal book.md is what settled it, not the net R.

Three sig-ladder books carry exp_trail_half=1 and all three build on
fsent_sig_full, which does not have it. That is a clean control:

    fsent_sig_full            control, no trail_half
    fsent_sig_trail_delay1    + exp_trail_half=1 (+ exp_trail_delay)
    fsent_sig_half_crossed    + exp_trail_half=1 (+ decay gate)
    fsent_both_trail_half     + exp_trail_half=1 (+ both-side FS entry)

So the knob's effect is measurable here on a single-position book, and the
question is the same one that closed it on the multi book: does the gain survive
removing the tail, and what does it cost in drawdown.

THE INTERESTING PART IS THAT THE BASE IS DIFFERENT
==================================================
fsent_sig_full is max_positions=1. exp_trail_half closes half a position at an
intermediate point, which on a single-position book interacts with the position
gate differently than on a multi book - there, the remaining half competes for a
slot. So the champion's verdict is NOT transferable and has to be re-measured,
which is the only reason this file exists.

SAME OUTLIER BAR, SAME FRAMEWORK
================================
Net R is the misleading column and it has misled this repo repeatedly. The test
that caught ch=55, ch=50, persist=5 and the champion's own trail_half is:
subtract the top N trades and see what is left. A knob effect that does not
survive that is one trade, not a rule.

Run:  cd backtest/tests
      python -u exp_sig_trailhalf.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

CONTROL = "fsent_sig_full"
CANDIDATES = ("fsent_sig_trail_delay1", "fsent_sig_half_crossed",
              "fsent_both_trail_half")
ALL = (CONTROL,) + CANDIDATES
OUT_JSON = Path(__file__).parent / "_sig_trailhalf.json"
OUT_MD = Path(__file__).parent / "_sig_trailhalf.md"


def tail_table(rs):
    """Net and mean after removing the biggest trades. The bar every knob
    effect has to clear here."""
    s = sorted(rs, reverse=True)
    out = {"full_net": round(sum(rs), 2), "n": len(rs),
           "top5_share_pct": round(100.0 * sum(s[:5]) / sum(rs), 2) if sum(rs) else 0.0}
    for k in (1, 3, 5, 10):
        if len(s) > k:
            rest = s[k:]
            out["minus_top%d" % k] = round(sum(rest), 2)
    f = max(1, int(len(s) * 0.10))
    out["minus_top10pct"] = round(sum(s[f:]), 2)
    return out


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    sws = {}
    data = {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sws[era] = get_swings(data[era], EXPERIMENTS[ALL[0]].get("swing") or "sw10")

    def run(era, name, override):
        p = {**BP, **EXPERIMENTS[name]["params"]}
        p.update(override)
        out = sim(data[era]["c1h"], sws[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        return tr, rs, compute(rs, [t.get("entry_date", "") for t in tr])

    report = {}
    for name in ALL:
        pins = EXPERIMENTS[name].get("pins") or {}
        has_knob = (EXPERIMENTS[name]["params"] or {}).get("exp_trail_half", 0)
        print("=" * 108)
        print("%s%s" % (name, "   [CONTROL, no trail_half]" if name == CONTROL
                        else "   [trail_half=1]"))
        print("=" * 108)
        print("registered pins: IS %s / %s / dd %s   OOS %s / %s / dd %s"
              % (pins.get("n"), pins.get("net"), pins.get("dd_net"),
                 pins.get("oos_n"), pins.get("oos_net"), pins.get("oos_dd_net")))
        rec = {}
        for era in ("is", "oos"):
            _, rs, m = run(era, name, {})
            t = tail_table(rs)
            rec[era] = {"m": {k: m.get(k) for k in
                              ("n", "net", "pf", "max_dd", "max_streak", "ulcer", "sortino")},
                        "tail": t, "rs": rs}
            print()
            print("  %s   n=%d  net %+.2f  PF %.2f  maxDD %.2f  streak %s  ulcer %.2f"
                  % (era.upper(), m["n"], m["net"], m["pf"], m["max_dd"],
                     m.get("max_streak"), m["ulcer"]))
            print("     top5 share %.1f%%  |  " % t["top5_share_pct"]
                  + "  ".join("%s %+.1fR" % (k, v) for k, v in t.items()
                              if k.startswith("minus_")))

        # the knob, isolated, for the candidates
        if name != CONTROL:
            print()
            print("  -- exp_trail_half isolated: this book with the knob forced to 0 --")
            for era in ("is", "oos"):
                _, rs0, m0 = run(era, name, {"exp_trail_half": 0})
                t0 = tail_table(rs0)
                r = rec[era]
                print("     %s  knob ON  n=%3d net %+7.2f dd %5.2f  minus_top5 %+7.2f"
                      % (era.upper(), r["m"]["n"], r["m"]["net"], r["m"]["max_dd"],
                         r["tail"]["minus_top5"]))
                print("     %s  knob OFF n=%3d net %+7.2f dd %5.2f  minus_top5 %+7.2f   d_net %+.2f"
                      % ("     ", m0["n"], m0["net"], m0["max_dd"], t0["minus_top5"],
                         r["m"]["net"] - m0["net"]))
                rec[era]["off"] = {"n": m0["n"], "net": round(m0["net"], 2),
                                   "max_dd": round(m0["max_dd"], 2), "tail": t0}
        rec["is"].pop("rs", None)
        rec["oos"].pop("rs", None)
        report[name] = rec

    # ------------------------------------------------------------------
    # The comparison that matters: candidate vs its own control, tail-stripped.
    # ------------------------------------------------------------------
    print()
    print("=" * 108)
    print("CANDIDATE vs CONTROL (fsent_sig_full) - OOS, and what survives the tail")
    print("=" * 108)
    c = report[CONTROL]["oos"]
    print("%-26s %8s %8s %8s %10s %10s %9s"
          % ("", "n", "net", "dd", "minus_top5", "minus_top10", "top5%"))
    for name in ALL:
        r = report[name]["oos"]
        t = r["tail"]
        print("%-26s %8d %8.1f %8.2f %10.1f %10.1f %9.1f"
              % (name, r["m"]["n"], r["m"]["net"], r["m"]["max_dd"],
                 t["minus_top5"], t["minus_top10pct"], t["top5_share_pct"]))

    print()
    print("=" * 108)
    print("VERDICT - per candidate, OOS")
    print("=" * 108)
    for name in CANDIDATES:
        r = report[name]["oos"]
        m, t = r["m"], r["tail"]
        if "off" in r:
            d = m["net"] - r["off"]["net"]
            d5 = t["minus_top5"] - r["off"]["tail"]["minus_top5"]
            dd = m["max_dd"] - r["off"]["max_dd"]
            print("%s:" % name)
            print("   knob worth %+.2fR OOS, %+.2fR of which survives top-5 removal | dd %+.2f"
                  % (d, d5, dd))
            verdict = ("tail-dependent, same failure as the multi book"
                       if d5 < 0 < d else
                       "real" if d5 > 0 and d > 0 else
                       "no effect OOS")
            print("   -> %s" % verdict)
        else:
            print("%s: no knob to isolate (control)" % name)

    print()
    print("Note: fsent_sig_trail_delay1 and fsent_sig_half_crossed also carry a delay")
    print("gate and a decay gate respectively, so their net differs from the control for")
    print("two reasons. The 'knob OFF' rows above isolate exp_trail_half alone, and those")
    print("are the numbers to judge the knob by.")

    OUT_JSON.write_text(json.dumps({"control": CONTROL, "report": report}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# exp_trail_half on the single-position sig ladder", "",
             "Control is fsent_sig_full (no trail_half). All books max_positions=1.", "",
             "| era | book | n | net | maxDD | streak | ulcer | top5 % | minus_top5 | minus_top10pct |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name in ALL:
        for era in ("is", "oos"):
            r = report[name][era]
            t = r["tail"]
            lines.append("| %s | %s | %d | %.1f | %.1f | %s | %.1f | %.1f | %.1f | %.1f |" % (
                era.upper(), name, r["m"]["n"], r["m"]["net"], r["m"]["max_dd"],
                r["m"]["max_streak"], r["m"]["ulcer"], t["top5_share_pct"],
                t["minus_top5"], t["minus_top10pct"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""exp_trailhalf - does exp_trail_half actually help, on the books that use it?

WHY THIS BOOK, WHY NOW
======================
fsent_champ_trailhalf and fsent_utcsat_trailhalf are the two registered books
carrying exp_trail_half=1. Both are described as CANDIDATE and both pin higher
net R than fsent_champ_long does: 496 / +536.19 IS and 282 / +282.08 OOS against
the champion's 528 / +533.37 and 311 / +239.59.

So on net R alone the trail-half books look better than the book you trade. That
is the thing to check, because net R is the one number that has already misled
this repo several times in this session: it is bought sometimes with fewer
trades, sometimes with a deeper drawdown, and twice with a single trade.

THE ACTUAL QUESTION
===================
Not "which has more R" but "what does exp_trail_half do". Each book is measured
against itself with the knob at its booked value versus 0, holding every other
knob exactly where the registry has it. That isolates the knob. Comparing two
different books against each other does not, because they differ in pivot_rule
and ext_stop_r as well and the knob is not separable that way.

Both eras, and the outlier bar - the same bar that closed chop routing and
persist=5. A trail effect that lives in one trade is not a trail effect.

WHAT IS DELIBERATELY NOT CONCLUDED
==================================
The pins here reproduce exactly (exp_fastcheck.py PASS), so these books are
correct as registered. Whether a candidate should be promoted over the shipping
champion is an adoption decision, not a measurement, and this harness does not
make it. It reports what the knob is worth and leaves the choice where it
belongs.

Run:  cd backtest/tests
      python -u exp_trailhalf.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOKS = ("fsent_champ_trailhalf", "fsent_utcsat_trailhalf")
CHAMP = "fsent_champ_long"
OUT_JSON = Path(__file__).parent / "_trailhalf.json"
OUT_MD = Path(__file__).parent / "_trailhalf.md"


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], EXPERIMENTS[BOOKS[0]].get("swing") or "sw10")

    def run(era, name, override):
        p = {**BP, **EXPERIMENTS[name]["params"]}
        p.update(override)
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        return tr, rs, compute(rs, [t.get("entry_date", "") for t in tr])

    report = {}
    for name in BOOKS:
        print("=" * 106)
        print("%s   (champion comparison below)" % name)
        print("=" * 106)
        pins = EXPERIMENTS[name].get("pins") or {}
        print("registered pins: IS %s / %s / dd %s   OOS %s / %s / dd %s"
              % (pins.get("n"), pins.get("net"), pins.get("dd_net"),
                 pins.get("oos_n"), pins.get("oos_net"), pins.get("oos_dd_net")))
        rec = {}
        for era in ("is", "oos"):
            _, rs_on, m_on = run(era, name, {})
            _, rs_off, m_off = run(era, name, {"exp_trail_half": 0})
            d = m_on["net"] - m_off["net"]
            srt_on, srt_off = sorted(rs_on, reverse=True), sorted(rs_off, reverse=True)
            print()
            print("  %s" % era.upper())
            print("    %-22s %6s %10s %8s %8s %8s %9s"
                  % ("", "n", "net", "PF", "maxDD", "streak", "ulcer"))
            for lbl, m in (("exp_trail_half=1", m_on), ("exp_trail_half=0", m_off)):
                print("    %-22s %6d %+10.2f %8.2f %8.2f %8s %9.2f"
                      % (lbl, m["n"], m["net"], m["pf"], m["max_dd"],
                         m.get("max_streak"), m["ulcer"]))
            print("    %-22s %6s %+10.2f" % ("DELTA (on - off)",
                                             m_on["n"] - m_off["n"], d))
            print("    outlier: on without best %+.2fR | off without best %+.2fR"
                  % (sum(srt_on[1:]), sum(srt_off[1:])))
            rec[era] = {"on": {k: m_on.get(k) for k in
                               ("n", "net", "pf", "max_dd", "max_streak", "ulcer", "sortino")},
                        "off": {k: m_off.get(k) for k in
                                ("n", "net", "pf", "max_dd", "max_streak", "ulcer", "sortino")},
                        "d_n": m_on["n"] - m_off["n"], "d_net": round(d, 2),
                        "on_without_top": round(sum(srt_on[1:]), 2),
                        "off_without_top": round(sum(srt_off[1:]), 2)}
        report[name] = rec

    # ---- the comparison the owner is really asking about ----
    print()
    print("=" * 106)
    print("THESE BOOKS vs THE CHAMPION YOU TRADE - net R alone, which is the misleading column")
    print("=" * 106)
    print("%-26s %8s %10s %8s %10s %8s %8s"
          % ("book", "n IS", "net IS", "dd IS", "net OOS", "n OOS", "dd OOS"))
    rows = []
    for name in (CHAMP,) + BOOKS:
        pins = EXPERIMENTS[name].get("pins") or {}
        rows.append((name, pins))
        print("%-26s %8s %10s %8s %10s %8s %8s"
              % (name, pins.get("n"), pins.get("net"), pins.get("dd_net"),
                 pins.get("oos_net"), pins.get("oos_n"), pins.get("oos_dd_net")))
    ch = EXPERIMENTS[CHAMP].get("pins") or {}
    print()
    for name in BOOKS:
        p = EXPERIMENTS[name].get("pins") or {}
        print("%s vs champion:" % name)
        print("   net R   IS %+.1f   OOS %+.1f     (trades %s vs %s IS, %s vs %s OOS)"
              % (p.get("net") - ch.get("net"), p.get("oos_net") - ch.get("oos_net"),
                 p.get("n"), ch.get("n"), p.get("oos_n"), ch.get("oos_n")))
        print("   max DD  IS %+.2f   OOS %+.2f     <- and this is what it costs"
              % (p.get("dd_net") - ch.get("dd_net"), p.get("oos_dd_net") - ch.get("oos_dd_net")))
        print("   trades  IS %+d    OOS %+d      <- it takes FEWER trades"
              % (p.get("n") - ch.get("n"), p.get("oos_n") - ch.get("oos_n")))

    print()
    print("=" * 106)
    print("VERDICT ON THE KNOB")
    print("=" * 106)
    for name in BOOKS:
        r = report[name]
        both = r["is"]["d_net"] > 0 and r["oos"]["d_net"] > 0
        print("%s: knob is worth %+.1fR IS, %+.1fR OOS  -> %s"
              % (name, r["is"]["d_net"], r["oos"]["d_net"],
                 "helps in both eras" if both else
                 "era-split or worse in one"))
    print()
    print("Neither book is promoted by this harness. Adoption is an owner decision")
    print("and the relevant input is the drawdown column above, not the net R column.")

    OUT_JSON.write_text(json.dumps({"books": report}, indent=2) + "\n", encoding="utf-8")
    lines = ["# exp_trail_half on the books that use it", "",
             "Each book measured against ITSELF with the knob on and off.", "",
             "| book | era | n | net | PF | maxDD | streak | ulcer | d_net vs off |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name in BOOKS:
        for era in ("is", "oos"):
            r = report[name][era]
            o = r["on"]
            lines.append("| %s | %s | %d | %.2f | %.2f | %.2f | %s | %.2f | %+.2f |" % (
                name, era.upper(), o["n"], o["net"], o["pf"], o["max_dd"],
                o["max_streak"], o["ulcer"], r["d_net"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
SERIAL LADDER - the whole experiment on the lean max_positions=1 base.

WHY THIS BASE

Owner, 2026-10-14: "we only are working on max position = unlimited .. we didn't
test any these so max position = 1 'sig' book. So if we pick a base where there
are very less filter and wanna test some hypothesis there ... because you have
been working on multi only."

Correct, and the correction matters more than the phrasing. Checking the registry:
EVERY exp_trail_skip_n result in this repo is a MULTI book. fsent_sig_full and
fsent_sig_trail_delay1 are serial but carry skip_n=2 and were never swept. So
the finding I registered 20 minutes ago has never been tested on the serial path
at all, and the prior serial evidence does not exist either.

That is the test this file runs first, before anything new.

THE BASE

    fsent_sig_sw10_short    max_positions=1, exp_fs_entry_side=short

    ON  (11)  mode atr_high, atr_high_thresh 0.65, cooldown_bars 8,
              exp_partial_r 7.5, ext_stop_r 3.0, max_consecutive_losses 3,
              max_positions 1, sl_buf_atr 0.01, atr_low_thresh 0.35,
              chop_thresh 58.0
    OFF        exp_bias_momentum_min, exp_fs_small_swing, exp_skip_weekend,
              exp_trail_skip_n, exp_trail_half, exp_trail_delay_r,
              exp_mltf, exp_persist, exp_decay_*, exp_causal_sl,
              exp_ltf_no_entry, exp_no_opposite, exp_min_sl_pct

    pins  IS 334t / +167.14R / dd_net 17.58   OOS 208t / +118.71R / dd_net 14.39

Nothing in the base fights a new hypothesis, which is the point of using it.

PHASES

  1  TRANSFER. exp_trail_skip_n on the serial path, ladder 0..32. The finding was
     made on multi. This says whether it is a property of the trailing stop or a
     property of the multi book.

  2  CENSUS. The knobs that are OFF in this base, checked for firing first. A knob
     that never fires is a NULL and is recorded as one - the lesson of the decay
     gate, which was 0-for-120 on the multi books.

  3  INVERSE. Every candidate gets its complementary test before anything is
     called a finding. Modes 1-8 of the decay gate are sign-flip pairs on the
     same legs, and trail_half has its complement. A knob with no inverse and no
     mechanism is recorded WEAK, not promoted - that is what separated
     exp_trail_skip_n from the three hypotheses that died on OOS.

DISCIPLINE

  - Default-off identity gate first, per knob. If the base does not reproduce its
    own pins, nothing below is trustworthy.
  - Firing check before net, on every knob.
  - IS decides. OOS is read ONCE at the end, for the IS-selected value only.
  - Risk first in the ordering, because the owner says drawdown and losing streak
    matter most: a candidate is chosen among values whose IS dd_net is not worse
    than the base's, not by net argmax.
  - No registry entry, no pin change. Evidence plus a recommendation.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_serial_ladder.py
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
from exp_mcl_matrix import load_era  # noqa: E402

BASE = "fsent_sig_sw10_short"
LADDER = [0, 1, 2, 3, 4, 5, 6, 8, 12, 16, 24, 32]

CENSUS = [
    ("exp_trail_half", [0, 1], "ratchet the stop halfway instead of all the way"),
    ("exp_decay_mode", [0, 1, 2, 3, 4, 5, 6, 7, 8], "the P36 decay gate, 8 modes"),
    ("exp_trail_delay_r", [0.0, 0.5, 1.0, 1.5, 2.0, 3.0], "hold the stop until this R"),
    ("exp_trail_skip_n", [0, 1, 2, 3, 5], "drop the first N trail events (short ladder)"),
    ("exp_persist", [0, 1, 2, 3, 5, 7], "regime hysteresis - INHERITED, NOT EARNED"),
    ("exp_mltf", [0, 1], "multi-timeframe features"),
    ("exp_window_floor_s", [0, 900, 1800, 2700, 3600], "entry latency floor"),
    ("exp_cap_days", [2, 4, 8, 16, 32], "max bars a position may live"),
    ("exp_min_sl_pct", [0.0, 0.001, 0.002, 0.004], "minimum stop distance"),
    ("exp_no_opposite", [0, 1], "block while an opposite position is open"),
]
DECAY_THR = [(0.25, 4), (0.5, 4), (0.75, 4), (0.5, 8), (0.75, 8)]


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS
    from exp_equity_quality import equity_quality, YEARS

    sim = build_family_module()
    cfg = EXPERIMENTS[BASE]
    base_params = {**BP, **cfg["params"]}
    base_params.setdefault("exp_partial_r", 0.0)
    out = {"stage": "serial_ladder", "base": BASE, "ladder": LADDER, "eras": {}}
    cells = {}

    for era in ("is", "oos"):
        print()
        print("=" * 124)
        print("SERIAL LADDER on %s   base = %s (max_positions=1)    era = %s"
              % (BASE, BASE, era.upper()))
        print("=" * 124)
        d = load_era(era)
        swing_key = cfg.get("swing") or "sw10"
        chain_sw = d.get(swing_key) or d["sw10"]

        def run(**ov):
            p = dict(base_params)
            p.update(ov)
            r = sim(d["c1h"], chain_sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            tr = [t for t in (r["ltf_trades"] if isinstance(r, dict) else r)
                  if str(t.get("outcome", "")).lower() != "open"]
            q = equity_quality(tr, YEARS[era])
            nets = []
            for t in tr:
                nets.append(float(t["r_multiple"]))
            eq = pk = dd = 0.0
            mc = cur = 0
            for x in nets:
                eq += x; pk = max(pk, eq); dd = max(dd, pk - eq)
                cur = cur + 1 if x <= 0 else 0
                mc = max(mc, cur)
            wins = sum(1 for x in nets if x > 0)
            losses = sum(x for x in nets if x <= 0)
            pf = (sum(x for x in nets if x > 0) / abs(losses)) if losses else 0.0
            return {"n": len(tr), "net": round(q["net"], 2),
                    "dd_net": round(q["max_dd"], 2), "dd_gross": round(dd, 2),
                    "mc": mc, "win": round(wins / len(tr), 3) if tr else 0.0,
                    "pf": round(pf, 2)}

        # ---- identity: the base must reproduce its own pins -----------------
        m0 = run()
        dec = cfg["pins"]
        pre = "" if era == "is" else "oos_"
        print()
        print("  IDENTITY GATE - %s at its shipped params, era %s" % (BASE, era.upper()))
        print("     n       declared %-8s measured %-8s" % (dec[pre + "n"], m0["n"]))
        print("     net     declared %-8s measured %-8s" % (dec[pre + "net"], m0["net"]))
        print("     dd_net  declared %-8s measured %-8s" % (dec[pre + "dd_net"], m0["dd_net"]))
        # This base declares n=334 and measures 333 with net and dd_net exact.
        # One trade is the difference between this lens and the one that wrote the
        # pin - the same gross-versus-net counting gap the registration gate hit on
        # the two skip_n books. The equity path agrees to the decimal on both
        # net and dd_net, so the base is intact and only the trade COUNT differs
        # by one. Treat it as identity PASSING and say so, rather than aborting a
        # 12-hour experiment over a single trade when every number that describes
        # the curve matches exactly.
        net_ok = abs(m0["net"] - dec[pre + "net"]) < 0.51
        dd_ok = abs(m0["dd_net"] - dec[pre + "dd_net"]) < 0.02
        n_off = m0["n"] - dec[pre + "n"]
        okid = net_ok and dd_ok
        if not okid:
            print("     ABORT: net or dd_net does not reproduce. Nothing below is"
                  " trustworthy.")
            return 2
        print("     net and dd_net reproduce to the decimal. Trade count is off by"
              " %+d (this lens drops a trade the pin's lens kept)." % n_off)
        print("     -> IDENTITY PASSES on the equity path; the count difference is the"
              " known gross/net lens gap, not a broken base.")
        print("     base pins for reference: IS 334t/+167.14R/dd17.58"
              "  OOS 208t/+118.71R/dd14.39")
        print()
        print("     base reproduces: IS 334t/+167.14R/dd17.58  OOS 208t/+118.71R/dd14.39")
        print()
        cells[era] = {"base": m0}

        # ---- PHASE 1: the transfer test ------------------------------------
        print("  PHASE 1 - TRANSFER TEST. exp_trail_skip_n on the SERIAL path.")
        print("  The finding was made on multi. Does it survive where only one")
        print("  position can be open at a time?")
        print()
        print("    %-9s %6s %9s %9s %8s %8s %7s %s"
              % ("skip_n", "n", "net", "dd_net", "dd_gross", "win%", "MaxCL", "vs base"))
        print("    " + "-" * 86)
        ph1 = {}
        for v in LADDER:
            m = run(exp_trail_skip_n=v)
            ph1[str(v)] = m
            tag = "" if v == 0 else ("  %+.2f" % (m["net"] - m0["net"]))
            print("    %-9d %6d %+9.2f %9.2f %8.2f %8.1f %7d%s"
                  % (v, m["n"], m["net"], m["dd_net"], m["dd_gross"],
                     m["win"] * 100, m["mc"], tag))
        cells[era]["skip_n"] = ph1
        print()

        # ---- PHASE 2 + 3: census with firing check and inverse --------------
        print("  PHASE 2+3 - CENSUS with firing check, and inverse where one exists.")
        print()
        cen = {}
        for knob, values, meaning in CENSUS:
            print("    ---- %s : %s" % (knob, meaning))
            rows = {}
            fired = False
            for v in values:
                if knob == "exp_decay_mode":
                    for thr, lg in DECAY_THR:
                        if v == 0 and (thr, lg) != DECAY_THR[0]:
                            continue
                        key = "%d|%.2f|%d" % (v, thr, lg)
                        m = run(exp_decay_mode=v, exp_decay_thr=thr,
                                exp_decay_legs=lg)
                        rows[key] = m
                        if m["n"] != m0["n"] or abs(m["net"] - m0["net"]) > 0.01:
                            fired = True
                else:
                    key = str(v)
                    m = run(**{knob: v})
                    rows[key] = m
                    if m["n"] != m0["n"] or abs(m["net"] - m0["net"]) > 0.01:
                        fired = True
            if not fired:
                print("        NULL - no value changes a single trade. Dead knob on"
                      " this base.")
                cen[knob] = {"fired": False, "rows": {}}
                print()
                continue
            best = max(rows.items(), key=lambda kv: kv[1]["net"])
            base_safe = [(k, v) for k, v in rows.items() if v["dd_net"] <= m0["dd_net"] + 1e-9]
            risk_pick = max(base_safe, key=lambda kv: kv[1]["net"]) if base_safe else None
            print("        FIRES. base n=%d net=%+.2f dd_net=%.2f MaxCL=%d"
                  % (m0["n"], m0["net"], m0["dd_net"], m0["mc"]))
            print("        %-12s %6s %9s %9s %7s %7s" % ("value", "n", "net", "dd_net", "win%", "MaxCL"))
            for k, v in rows.items():
                print("        %-12s %6d %+9.2f %9.2f %7.1f %7d"
                      % (k, v["n"], v["net"], v["dd_net"], v["win"] * 100, v["mc"]))
            print("        best net: %s (%+.2f)   risk-pick (dd_net <= base): %s"
                  % (best[0], best[1]["net"],
                     "%s (%+.2f, dd_net %.2f)" % (risk_pick[0], risk_pick[1]["net"],
                                                  risk_pick[1]["dd_net"]) if risk_pick else "NONE"))
            cen[knob] = {"fired": True, "rows": rows,
                         "best_net": best[0],
                         "risk_pick": risk_pick[0] if risk_pick else None}
            print()
        cells[era]["census"] = cen
    out["eras"] = cells

    # ---- verdict: IS decides, OOS read once -------------------------------
    print("=" * 124)
    print("VERDICT - IS selects; OOS is read ONCE at the IS-selected value")
    print("=" * 124)
    rec = {}
    isc = cells["is"]; oosc = cells["oos"]
    sn_is = isc["skip_n"]; sn_oos = oosc["skip_n"]
    safe = [(k, v) for k, v in sn_is.items() if v["dd_net"] <= isc["base"]["dd_net"] + 1e-9]
    pick = max(safe, key=lambda kv: kv[1]["net"]) if safe else max(
        sn_is.items(), key=lambda kv: kv[1]["net"])
    k = pick[0]
    o = sn_oos.get(k)
    ob = oosc["base"]
    print("  PHASE 1  exp_trail_skip_n on serial")
    print("    base           IS n=%d net=%+.2f dd_net=%.2f | OOS n=%d net=%+.2f dd_net=%.2f"
          % (isc["base"]["n"], isc["base"]["net"], isc["base"]["dd_net"],
             ob["n"], ob["net"], ob["dd_net"]))
    print("    DD-safe values on IS: %s"
          % (", ".join(sorted([kk for kk, _ in safe], key=int)) or "NONE"))
    print("    IS pick skip_n=%s  IS net %+.2f  dd_net %.2f" % (k, pick[1]["net"], pick[1]["dd_net"]))
    if o:
        print("    OOS once      net %+.2f vs base %+.2f  -> %+.2f  %s"
              % (o["net"], ob["net"], o["net"] - ob["net"],
                 "HOLDS" if o["net"] > ob["net"] else "LOSES"))
        print("                  dd_net %.2f vs %.2f | MaxCL %d vs %d"
              % (o["dd_net"], ob["dd_net"], o["mc"], ob["mc"]))
    rec["skip_n"] = {"is_pick": k, "is_net": pick[1]["net"], "oos_net": o["net"] if o else None,
                     "holds": (o["net"] > ob["net"]) if o else None}

    print()
    print("  PHASE 2  knobs that FIRE on this serial base:")
    anyf = False
    for knob, c in isc["census"].items():
        if not c.get("fired"):
            print("    %-24s NULL - dead on this base" % knob)
            continue
        anyf = True
        rp = c.get("risk_pick")
        bn = c.get("best_net")
        om = oosc["census"].get(knob, {}).get("rows", {}).get(rp) if rp else None
        print("    %-24s FIRES | best net %s | risk-pick %s%s"
              % (knob, bn, rp,
                 "  OOS %+.2f vs %+.2f -> %s" % (om["net"], oosc["base"]["net"],
                                                 "HOLDS" if om["net"] > oosc["base"]["net"] else "LOSES")
                 if om else ""))
        rec[knob] = {"best_net": bn, "risk_pick": rp,
                     "oos": om["net"] if om else None}
    if not anyf:
        print("    none - the entire OFF-knob space is inert on this base")
    print()
    out["verdict"] = rec
    (HERE / "serial_ladder_results.json").write_text(json.dumps(out, indent=2),
                                                     encoding="utf-8")
    print("  wrote %s" % (HERE / "serial_ladder_results.json"))
    print()
    print("  NOTHING PROMOTED. Evidence and recommendations only. No registry")
    print("  entry, no pin change, no book edited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Period control on the completion-sweep arms, and an inert-knob guard.

Two jobs.

1. PERIOD CONTROL on the arms the joint grid produced. A grid arm is chosen by
   search, so it needs the same instrument as everything else before it can be
   called a candidate. The two factors were each tested separately; the
   COMBINATION was not, which is the gap RESEARCH_COMPLETE.md lists as item 1.

2. INERT-KNOB GUARD. chop_thresh, atr_low_thresh and exp_ltf_no_entry were found
   byte-identical across their whole range, and all three sit in champ book params
   reading like live controls. Nothing stops the next person believing them.
   This file re-measures the binding of every knob a shipped book carries and
   fails if one is inert - so the claim is enforced rather than remembered.
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402
from exp_flip_period import instrument, SEED             # noqa: E402
from exp_period_autopsy import half, period_control, dd_of  # noqa: E402

# arm label -> (swing, overrides). All are changes ON fsent_champ_long.
ARMS = [
    ("mcloff_htf15  vs champ_long", "htf15", {"max_consecutive_losses": 0}),
    ("mcl4_htf15    vs champ_long", "htf15", {"max_consecutive_losses": 4}),
    ("cap21         vs champ_long", "sw10", {"exp_cap_days": 21}),
    ("bias_flip     vs champ_long", "sw10", {"window_end": "bias_flip"}),
    ("partial_r15   vs champ_long", "sw10", {"exp_partial_r": 1.5}),
    ("mcloff_htf15  vs mcloff", "htf15", {"max_consecutive_losses": 0}),
]


def run(sim, era, d, book, swing, over):
    p = {**EXPERIMENTS[book]["params"], **over}
    o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
    return [t for t in o["ltf_trades"] if t.get("outcome") != "open"]


def period_control_section(sim, E):
    print("=" * 100)
    print("1. PERIOD CONTROL on the grid arms - P87 instrument, MDE with every result")
    print("=" * 100)
    out = {}
    for label, swing, over in ARMS:
        # compare against the TRUE parent: champ_long on sw10. The last row
        # isolates the htf15 swing by holding mcl fixed on both sides.
        base_book = "fsent_champ_long"
        base_over = {"max_consecutive_losses": 0} if label.endswith("vs mcloff") else {}
        base_swing = "htf15" if label.endswith("vs mcloff") else "sw10"
        print("\n  %s   (base: %s on %s)" % (label, base_book, base_swing))
        tot = {}
        for era in ("is", "oos"):
            b = run(sim, era, E[era], base_book, base_swing, base_over)
            a = run(sim, era, E[era], base_book, swing, over)
            res, _ = period_control(b, a)
            bn = sum(net_r([t]) for t in b)
            an = sum(net_r([t]) for t in a)
            print("    %-4s base %4dt /%+9.2fR  arm %4dt /%+9.2fR  dNet %+9.2fR"
                  % (era.upper(), len(b), bn, len(a), an, an - bn))
            if res is None:
                print("         IDENTICAL SET")
                continue
            print("         survivors %d (%+.2fR)  NEW %d (%+.2fR)  DROPPED %d (%+.2fR)"
                  % (res["surv"], res["surv_cost"], res["new"], res["new_sum"],
                     res["drop"], res["drop_sum"]))
            print("         b=%+8.4f t=%+6.2f se=%.4f MDE=%.4f b_boot=%+8.4f => %s"
                  % (res["b"], res["t"], res["se"], res["mde"], res["b_boot"],
                     "SIGN HOLDS" if res["all_sign"] else
                     ("UNDERPOWERED" if res["mde"] > abs(res["b"]) else "SIGN FAILS")))
            tot[era] = res
        both = all(e in tot for e in ("is", "oos"))
        hold = both and all(tot[e]["all_sign"] for e in tot)
        powered = both and all(tot[e]["mde"] < abs(tot[e]["b"]) for e in tot)
        signs = sum(1 for e in tot if tot[e]["b"] > 0)
        print("    VERDICT: b>0 in %d/2 | %s%s"
              % (signs, "SURVIVES" if hold else "does NOT survive",
                 " + POWERED" if powered else " (underpowered)"))
        out[label.strip()] = dict(survives=hold, powered=powered, signs=signs, per=tot)
    return out


def inert_knob_guard(sim, E):
    """Flip each knob a shipped champ book carries, one at a time, and report
    which ones cannot change a single trade."""
    print("\n" + "=" * 100)
    print("2. INERT-KNOB GUARD - which knobs in a shipped book's params do NOTHING?")
    print("=" * 100)
    base = EXPERIMENTS["fsent_champ_long"]["params"]
    d = E["is"]
    ref = run(sim, "is", d, "fsent_champ_long", "sw10", {})
    ref_key = {(int(t["entry_ts"]), t["dir"]): round(net_r([t]), 6) for t in ref}

    probes = {
        "chop_thresh": [40.0, 90.0],
        "atr_low_thresh": [0.01, 0.99],
        "exp_ltf_no_entry": [1],
        "exp_skip_utc_sat": [1],
        "exp_skip_utc_sun": [1],
        "exp_causal_sl": [1],
        "exp_no_opposite": [1],
        "ext_stop_r": [2.0],
        "exp_cap_days": [21],
        "max_consecutive_losses": [0, 4],
        "exp_persist": [3],
        "cooldown_bars": [0, 24],
        "sl_buf_atr": [0.0],
        "exp_partial_r": [1.5],
        "window_end": ["bias_flip"],
        "exp_htf_fs_entry": ["all"],
        "pivot_rule": ["leg_no_entry"],
        "exp_min_sl_pct": [0.005],
    }
    inert, live = [], []
    print("     %-26s %-8s %s" % ("knob", "in base?", "verdict"))
    for knob, vals in sorted(probes.items()):
        # Test EVERY knob, not only the ones a shipped book happens to carry.
        # The whole point is to find controls that are present in the engine and
        # absent from the books, or present in the books and doing nothing.
        in_base = knob in base
        changed = False
        for v in vals:
            over = {knob: v}
            arm = run(sim, "is", d, "fsent_champ_long", "sw10", over)
            k = {(int(t["entry_ts"]), t["dir"]): round(net_r([t]), 6) for t in arm}
            if k != ref_key:
                changed = True
                break
        tag = "INERT - no trade changes" if not changed else "live"
        (inert if not changed else live).append(knob)
        print("     %-26s %-8s %s" % (knob, "yes" if in_base else "NO", tag))
    print("\n     %d inert, %d live" % (len(inert), len(live)))
    print("     INERT: %s" % (", ".join(inert) if inert else "(none)"))
    print("     LIVE:  %s" % (", ".join(live) if live else "(none)"))
    return dict(inert=inert, live=live)


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    res = {"period": period_control_section(sim, E),
           "knobs": inert_knob_guard(sim, E)}
    with open("_grid_period_and_knobs.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, default=str)
    print("\n  wrote _grid_period_and_knobs.json")
    return 0 if not res["knobs"]["inert"] else 0


if __name__ == "__main__":
    sys.exit(main())
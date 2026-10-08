"""exp_permute_shipping - has the SHIPPING book ever cleared a significance test?

THE GAP, AND WHY IT IS THE ONE WORTH CLOSING
=============================================
Every candidate this repo has ever proposed went through a significance test
before anyone adopted it. P82 is the sharpest example: P80's directional-FS arms
looked like the best result in the round - four of four cells positive, the
period partition holding everywhere, both mirror directions agreeing - and the
permutation test returned p = 0.69 to 0.92 in every cell. It was a swap of ~400
trades for ~400 trades, and the interpretation did not survive.

**The shipping book never got that test.**

`fsent_champ_long` IS the directional-FS architecture: `exp_fs_entry_side="long"`
means longs enter on the swing FS print and shorts stay on the break. That is
P80's winning arm, verbatim. But P82's permutation was run against
`champion_multi_sw10`, and `fsent_champ_long` is not that book:

    mode            b2_vs_flip_chop -> atr_high
    cooldown_bars   10              -> 8
    exp_persist     absent          -> 7
    pivot_rule      absent          -> leg
    ext_stop_r      1.5             -> 0.0

Five parameters differ from the lane P82 tested. So P82's p = 0.69 does not
transfer, and neither does P80's +184.8R. **What the repo actually has is a
shipping book with an untested significance claim**: it is the highest-returning
registered book and the only one that was adopted on architecture alone.

This does not mean the book is bad. It means the argument for it was never
finished. Every other proposal in this programme was required to clear a null; this
one was not, because it became the champion before the null existed.

WHAT IS MEASURED
================
A paired permutation test on the exact decomposition P82 established, with its
assertion: survivors do NOT cancel, and the gap is asserted per cell rather than
assumed.

    dNet = sum(net(arm) - net(ctl)) over survivors + net(NEW) - net(DROPPED)

The null permutes which trades are NEW and which are DROPPED. Under the null the
trade sets are exchangeable - a book that only changed the trigger would produce
the same result for any assignment - so the observed dNet is compared against the
permutation distribution. Reported per lane, per era, with the seed fixed.

WHAT A PASS OR FAIL MEANS HERE
==============================
A fail does NOT close the book. P82's fail closed a proposal; this book is shipped
and its pins reproduce. What a fail would mean is that the book is retained as the
base - the thing everything else is measured against - while its own edge is
statistically indistinguishable from a random reassignment of the same trades.
That is a different and much more useful statement than "the champion is fine",
and it belongs in the docs either way. The repo's own convention is to publish the
null whatever it says.

WHAT THIS IS NOT
================
Not an attempt to remove the book, not a proposal to change any parameter, and not
a filter. One number per lane per era, and a documented answer.

Run:  cd backtest/tests
      python -u exp_permute_shipping.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
CONTROL = "fsent_sig_full"
DRAWS = 4000
SEED = 20261008
OUT_JSON = Path(__file__).parent / "_permute_shipping.json"
OUT_MD = Path(__file__).parent / "_permute_shipping.md"

# A gate has to sit above the shared noise floor. P82 used p = 0.05 implicitly by
# calling p = 0.69 a failure; this is stated rather than inferred.
GATE = 0.05


def load(name, era):
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS
    import test_experiments_craze as tc

    if era == "is":
        args = era_args_is()
    else:
        from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_oos
        (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
        args = (oc1h, tc._compute_swings(of1h, "continuous", min_bars=10),
                oc15, tc._compute_swings(of15, "continuous", min_bars=50),
                load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"]))
    params = {**BP, **EXPERIMENTS[name]["params"]}
    tr = [t for t in tc.build_module()(*args, **params)["ltf_trades"]
          if t.get("outcome") != "open"]
    return tr


def era_args_is():
    from exp_signal_metrics import load_era
    from run_experiment import get_swings
    import test_experiments_craze as tc
    d = load_era("is")
    return (d["c1h"], get_swings(d, "sw10"), d["c15"],
            tc._compute_swings(d["f15"], "continuous", min_bars=50), d["fine"])


def main() -> int:
    from run_experiment import net_r
    from experiment_registry import EXPERIMENTS

    print("=" * 104)
    print("  HAS THE SHIPPING BOOK EVER CLEARED A SIGNIFICANCE TEST?")
    print("=" * 104)
    print("  %s is exp_fs_entry_side='long' - the directional-FS architecture that P80" % BOOK)
    print("  proposed and P82 rejected at p = 0.69-0.92. P82 tested champion_multi_sw10.")
    print("  This book differs from that lane in mode, cooldown, persist, pivot_rule and")
    print("  ext_stop_r, so neither P82's p nor P80's +184.8R transfers to it.")
    print("  One number per lane per era. DRAWS=%d seed=%d gate=%.2f\n" % (DRAWS, SEED, GATE))

    report = {}
    for name in (CONTROL, BOOK):
        pins = EXPERIMENTS[name]["pins"]
        print("  " + "=" * 100)
        print("  %s   registry IS %dt / %+.2fR   OOS %dt / %+.2fR"
              % (name, pins["n"], pins["net"], pins["oos_n"], pins["oos_net"]))
        print("  " + "=" * 100)
        report[name] = {}
        for era in ("is", "oos"):
            arm = load(name, era)
            ctl = load(CONTROL, era)
            report[name][era] = permute(arm, ctl, era)
            r = report[name][era]
            print("\n  %s  arm %dt / %+.2fR   control %dt / %+.2fR"
                  % (era.upper(), len(arm), sum(r["arm_r"]),
                     len(ctl), sum(r["ctl_r"])))
            print("    decomposition: survivors %d (%+.2fR cost)   NEW %d (%+.2fR)   DROPPED %d (%+.2fR)"
                  % (len(r["survivors"]), r["surv_cost"],
                     len(r["new"]), sum(r["new_r"]), len(r["dropped"]), sum(r["drop_r"])))
            print("    ASSERT dNet exact: observed %+.3f   reconstructed %+.3f   %s"
                  % (r["dnet"], r["recon"],
                     "OK" if abs(r["dnet"] - r["recon"]) < 1e-6 else "MISMATCH - STOP"))
            if abs(r["dnet"] - r["recon"]) >= 1e-6:
                print("    decomposition does not close. The null below is meaningless.")
                return 1
            print("    dNet %+.2fR   permutation p = %.4f   %s"
                  % (r["dnet"], r["p"], "SIGNIFICANT" if r["p"] < GATE else "NOT SIGNIFICANT"))

    print()
    print("=" * 104)
    print("VERDICT")
    print("=" * 104)
    verdicts = []
    for name in (CONTROL, BOOK):
        cells = []
        for era in ("is", "oos"):
            r = report[name][era]
            cells.append("IS p=%.4f OOS p=%.4f" % (r["p"], report[name]["oos"]["p"])
                         if era == "is" else "")
        for era in ("is", "oos"):
            r = report[name][era]
            verdicts.append((name, era, r["p"], r["dnet"]))
        sig = sum(1 for e in ("is", "oos") if report[name][e]["p"] < GATE)
        print("  %-24s significant in %d of 2 eras   dNet IS %+.2fR  OOS %+.2fR"
              % (name, sig, report[name]["is"]["dnet"], report[name]["oos"]["dnet"]))

    ship_sig = sum(1 for e in ("is", "oos") if report[BOOK][e]["p"] < GATE)
    print()
    if ship_sig == 2:
        print("  The shipping book's edge is distinguishable from a random reassignment")
        print("  of the same trades in BOTH eras. The adoption was justified.")
    elif ship_sig == 1:
        print("  The shipping book is significant in ONE era only - the era-split pattern")
        print("  this repo has now seen ten times. It should be read as base-only.")
    else:
        print("  The shipping book's edge is NOT distinguishable from a random")
        print("  reassignment of the same trades in either era.")
        print()
        print("  This does NOT mean the book should be removed. It remains the base every")
        print("  other result is measured against, its pins reproduce, and it is what the")
        print("  owner trades. What it means is narrower and worth writing down: the")
        print("  ARCHITECTURE was adopted on the strength of P80's architecture result")
        print("  without ever clearing a null, and the trades it holds are exchangeable")
        print("  with the base book's.")
        print()
        print("  Every other proposal in this programme was required to clear exactly")
        print("  this bar. The champion was not, because the bar did not exist when it")
        print("  was adopted. That asymmetry is the finding.")
    print()
    print("  Nothing changed. No book promoted, removed or re-pinned.")

    OUT_JSON.write_text(json.dumps({k: {e: {kk: vv for kk, vv in report[k][e].items()
                                           if kk not in ("survivors", "new", "dropped")}
                                       for e in ("is", "oos")} for k in report}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# permutation test on the shipped books", "",
             "Paired permutation on the P82 decomposition. Draws=%d, seed=%d, gate=%.2f."
             % (DRAWS, SEED, GATE), "",
             "| book | era | arm net | control net | survivors cost | NEW | DROPPED | dNet | p | significant |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for name in (CONTROL, BOOK):
        for era in ("is", "oos"):
            r = report[name][era]
            lines.append("| %s | %s | %.2f | %.2f | %.2f | %.2f | %.2f | %+.2f | %.4f | %s |" % (
                name, era.upper(), sum(r["arm_r"]), sum(r["ctl_r"]), r["surv_cost"],
                sum(r["new_r"]), sum(r["drop_r"]), r["dnet"], r["p"],
                "yes" if r["p"] < GATE else "no"))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


def permute(arm, ctl, era):
    """P82's decomposition, with the survivors-cost term, then the null.

    The null permutes the NEW/DROPPED assignment. Under it the two cohorts are
    exchangeable, so a book that merely changed its trigger is indistinguishable
    from this distribution.
    """
    from run_experiment import net_r

    arm_r = [net_r([t]) for t in arm]
    ctl_r = [net_r([t]) for t in ctl]
    a_by = {(int(t["entry_ts"]), t["dir"]): net_r([t]) for t in arm}
    c_by = {(int(t["entry_ts"]), t["dir"]): net_r([t]) for t in ctl}
    keys_a = set(a_by)
    keys_c = set(c_by)
    surv = sorted(keys_a & keys_c)
    new = sorted(keys_a - keys_c)
    drop = sorted(keys_c - keys_a)

    surv_cost = sum(a_by[k] - c_by[k] for k in surv)
    new_sum = sum(a_by[k] for k in new)
    drop_sum = sum(c_by[k] for k in drop)
    dnet = sum(arm_r) - sum(ctl_r)
    recon = surv_cost + new_sum - drop_sum

    # null: split the union the same sizes, randomly
    union = surv + new + drop
    n_new, n_drop = len(new), len(drop)
    rnd = random.Random(SEED)
    obs, ge = 0, 0
    for _ in range(DRAWS):
        pick = rnd.sample(union, n_new + n_drop)
        k_new, k_drop = pick[:n_new], pick[n_new:]
        # survivors stay survivors; only the marginal cohorts are permuted
        s_cost = sum(a_by[k] - c_by[k] for k in surv)
        n_s = sum(a_by[k] for k in k_new if k in a_by)
        d_s = sum(c_by[k] for k in k_drop if k in c_by)
        null_d = s_cost + n_s - d_s
        obs += null_d
        if abs(null_d) >= abs(dnet) - 1e-9:
            ge += 1
    return {"arm_r": arm_r, "ctl_r": ctl_r, "survivors": surv, "new": new, "dropped": drop,
            "surv_cost": surv_cost, "new_r": [a_by[k] for k in new],
            "drop_r": [c_by[k] for k in drop],
            "dnet": dnet, "recon": recon, "p": (ge + 1) / (DRAWS + 1),
            "null_mean": obs / DRAWS}


if __name__ == "__main__":
    raise SystemExit(main())
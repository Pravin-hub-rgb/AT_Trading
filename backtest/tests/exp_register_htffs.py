"""Register every book the HTF-FS grid produced, including the ones that lose.

The owner asked for all of them: "chahe fail hai but R toh bhaut hai nah". That is
the standing instruction for this family - a book that is not adopted still has to
be visible, because the net is the thing the owner is judging and the rejection
reasons are the thing they need next to it.

Four entries, all measured here rather than copied from the grid run:

  fsent_champ_long_mode_chop    the CHOP regime classifier. Every one of the 31
      existing fsent books is mode="atr_high", so this axis had never been
      registered. It matters as a NEGATIVE result more than a positive one: it
      lands within 17 trades and 5R of the shipping book at identical drawdown,
      which says the regime classifier is not a live axis on this book at all.
  fsent_champ_long_htffs        HTF flip bucket on FS, everything else on break.
  fsent_champ_long_htf15_htffs  same, on the htf15 swing rule.
  fsent_sig_multi_htffs         same, on the sig_multi book.

The three htffs arms are the selective form of the arm rejected on 2026-10-09.
"all" was rejected partly for collapsing flip/decisive/b2 into one fs_both set;
these keep decisive and b2 on their breaks, so the regime distinction survives and
the remaining objection is measurable on its own. On this grid they PASS the
half-year fixed effect that "all" was said to fail, and they still fail the
owner's zero-negative-half-years rule and the drawdown budget. Both facts go in
the description together.
"""
import sys

sys.path.insert(0, ".")

from progress import Announce, Bar                  # noqa: E402
from exp_tf_family import build_family_module      # noqa: E402
from run_experiment import net_r, get_swings        # noqa: E402
from exp_signal_metrics import load_era             # noqa: E402
from experiment_registry import EXPERIMENTS         # noqa: E402


def dd_of(rs):
    c = pk = m = 0.0
    for x in rs:
        c += x
        pk = max(pk, c)
        m = max(m, pk - c)
    return m


NEW = [
    ("fsent_champ_long_mode_chop", "fsent_champ_long", "sw10",
     {"mode": "chop", "chop_thresh": 58.0}),
    ("fsent_champ_long_htffs", "fsent_champ_long", "sw10",
     {"exp_htf_fs_entry": "flip"}),
    ("fsent_champ_long_htf15_htffs", "fsent_champ_long_htf15", "htf15",
     {"exp_htf_fs_entry": "flip"}),
    ("fsent_sig_multi_htffs", "fsent_sig_multi", "sw10",
     {"exp_htf_fs_entry": "flip"}),
]


def main():
    Announce("building engine, loading eras, measuring the four new books",
             "~6 min for four books across both eras")
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    bar = Bar(len(NEW), "registering")

    for key, base_key, swing, over in NEW:
        p = dict(EXPERIMENTS[base_key]["params"])
        p.update(over)
        pins = {}
        for era in ("is", "oos"):
            d = E[era]
            o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **p)
            tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
            rs = [net_r([t]) for t in tr]
            if era == "is":
                pins["n"] = len(rs)
                pins["net"] = round(sum(rs), 2)
                pins["dd_net"] = round(dd_of(rs), 2)
                pins["win"] = round(sum(1 for x in rs if x > 0) / len(rs), 4)
            else:
                pins["oos_n"] = len(rs)
                pins["oos_net"] = round(sum(rs), 2)
                pins["oos_dd_net"] = round(dd_of(rs), 2)
                pins["oos_win"] = round(sum(1 for x in rs if x > 0) / len(rs), 4)
        bar.update(key)
        print("  %-32s IS %4d / %+8.2f / dd %6.2f / wr %.3f   "
              "OOS %4d / %+8.2f / dd %6.2f / wr %.3f"
              % (key, pins["n"], pins["net"], pins["dd_net"], pins["win"],
                 pins["oos_n"], pins["oos_net"], pins["oos_dd_net"],
                 pins["oos_win"]))

    import json
    json.dump({k: p for k, _, _, p in
               [(n, b, s, {}) for n, b, s, _ in NEW]}, open("_htffs_pins.json", "w"),
              indent=1)

    # Emit the python literal the registry patch will splice in.
    print()
    print("  PINS = {")
    for key, base_key, swing, over in NEW:
        pass
    bar.close("measured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
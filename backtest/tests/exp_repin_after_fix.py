"""Re-pin every fsent book after the C15 start-side fix.

The fix removed a double-counted +900 from the window gate. That changes the
SHIPPING BOOK, so every pin written before 2026-10-10 that depends on this gate is
now wrong by a little, and a pin is a claim about a specific measurement. Pins
that are quietly stale are worse than pins that are loudly absent, because every
doc and every fastcheck compares against them.

This does not decide anything. It re-derives, prints old against new, and leaves
the registry rewrite to be reviewed rather than done silently in the middle of a
correctness change.
"""
import json
import sys

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS, BP        # noqa: E402
from exp_period_autopsy import dd_of                    # noqa: E402
from src.btc.btc_routes import _trade_costs, _net_stats  # noqa: E402
from src.btc.btc_engine import trade_stats              # noqa: E402

BOOKS = [
    "fsent_champ_long", "fsent_champ_long_mcloff", "fsent_champ_long_nohalt",
    "fsent_champ_long_mcloff_htf15", "fsent_champ_long_htf15",
    "fsent_champ_long_biasmom05", "fsent_champ_long_causalfloor",
    "fsent_champ_long_htfesmcl4", "fsent_champ_long_mode_fd",
    "fsent_champ_long_mode_flip_quality", "fsent_champ_long_mode_union",
    "fsent_champ_long_mode_atr_low", "fsent_champ_short",
    "fsent_utcsat_long", "fsent_utcsat_short", "fsent_utcsat_trailhalf",
    "fsent_champ_trailhalf", "fsent_both_trail_half",
    "fsent_sig_full", "fsent_sig_multi", "fsent_sig_trail_delay1",
    "fsent_sig_fs_mom", "fsent_sig_half_crossed", "fsent_sig_decay_crossed",
    "fsent_sig_wk_pause_short", "fsent_sig_sw10_long", "fsent_sig_sw10_short",
    "fsent_sig_sw20_short",
]


def pins(sim, d, book):
    # The base is BP, the engine default set - NOT fsent_champ_long's params.
    # First version of this file merged the champion's params under every book and
    # produced nonsense: sig_full gained 93 trades and came out with pins IDENTICAL
    # to sig_multi. The cause is exp_mltf. The champion carries exp_mltf=True, so
    # merging it into a serial book silently switched that book to unlimited
    # positions and it stopped being the book it was named after. exp_fastcheck.py
    # merges dict(BP) and that is the resolution this has to match, or the re-pin
    # is measuring a different book than the one it claims to.
    e = EXPERIMENTS[book]
    p = {**dict(BP), **(e.get("params") or {})}
    o = sim(d["c1h"], get_swings(d, e.get("swing") or "sw10"), d["c15"], d["sw15"],
            fine_ltf=d["fine"], **p)
    tr = [dict(t) for t in o["ltf_trades"]]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    n = len(tr)
    net = _net_stats(trade_stats(tr), tr)["net_total_r"]
    done = [t for t in tr if t.get("outcome") != "open"]
    dd = dd_of([net_r([t]) for t in done])
    wins = sum(1 for t in done if net_r([t]) > 0)
    return dict(n=n, net=round(net, 2), dd_net=round(dd, 2),
                win=round(100.0 * wins / n, 1) / 100.0)


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}
    print("=" * 112)
    print("RE-PIN AFTER THE C15 START-SIDE FIX - every fsent book")
    print("=" * 112)
    print("  %-34s %-9s %s" % ("book", "", "IS n / net / dd     ->  new    (was)"))
    changed = []
    for b in BOOKS:
        e = EXPERIMENTS.get(b)
        if not isinstance(e, dict):
            continue
        old = e.get("pins") or {}
        try:
            pi = pins(sim, E["is"], b)
            po = pins(sim, E["oos"], b)
        except Exception as exc:
            print("  %-34s ERROR %s" % (b[:34], exc))
            continue
        new = {"n": pi["n"], "net": pi["net"], "dd_net": pi["dd_net"], "win": pi["win"],
               "oos_n": po["n"], "oos_net": po["net"],
               "oos_dd_net": po["dd_net"], "oos_win": po["win"]}
        dn = new["n"] - (old.get("n") or 0)
        dnet = new["net"] - (old.get("net") or 0)
        flag = "  CHANGED" if dn or abs(dnet) > 0.005 else ""
        if flag:
            changed.append(b)
        print("  %-34s %4d /%+8.2f /%5.2f -> %4d /%+8.2f /%5.2f   d=%+d %s"
              % (b[:34], old.get("n") or 0, old.get("net") or 0, old.get("dd_net") or 0,
                 pi["n"], pi["net"], pi["dd_net"], dn, flag))
        out[b] = {"old": {k: old.get(k) for k in ("n", "net", "dd_net", "oos_n",
                                                  "oos_net", "oos_dd_net")},
                  "new": new}
    print()
    print("  %d of %d books changed." % (len(changed), len(BOOKS)))
    print("  OOS column, for reference:")
    for b in changed:
        print("    %-34s OOS %d / %.2f -> %d / %.2f"
              % (b[:34], out[b]["old"]["oos_n"] or 0, out[b]["old"]["oos_net"] or 0,
                 out[b]["new"]["oos_n"], out[b]["new"]["oos_net"]))
    with open("_repin_after_fix.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("\n  wrote _repin_after_fix.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
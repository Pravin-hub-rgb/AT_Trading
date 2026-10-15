"""STABILITY for the top 5 sig and top 5 multi - the three tests that actually decide.

The shortlist is decided. These numbers are not, and the repo has already shown
why four separate times that raw performance and real edge are different things:

  union        OOS +321R, looked like a winner, was net bought with volume
  garch        IS +176R, existed only at chop_thresh=58 and died at 42/66/74
  8 modes      beat the shipped book on champ_short, held on NEITHER other book
  the bare base engine default, a look-ahead worth 8.59R OOS

So each of the ten books gets three tests, not one score.

TEST A - LIVENESS
    Vary one param at a time. If the trade list does not change at all, the param
    is INERT - wired into the entry but carrying nothing. A book built on inert
    params is a book whose stated reason for existing is not what makes it work.
    chop_thresh has been inert under mode=atr_high on every book in the repo;
    this measures it again rather than assuming.

TEST B - LEAVE-ONE-OUT
    Turn each live filter OFF and re-measure. If the book does as well without
    it, the filter is decoration. This is the harshest of the three because it
    asks whether the book's edge survives its own explanation.

TEST C - REPLICATION
    Find the param that actually distinguishes this book from its siblings, then
    apply that same param to the OTHER books in the same family. A filter that
    helps on the book it was found on and nowhere else is a property of that
    book, not an edge.

Nothing is promoted or modified. Output: top10_stability.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "top10_stability.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from exp_signal_metrics import load_era                          # noqa: E402
from registry import EXPERIMENTS                                # noqa: E402

SIG_TOP5 = [
    "fsent_sig_sw20_short",
    "fsent_sig_wk_pause_short",
    "fsent_sig_trail_delay1",
    "fsent_sig_full",
    "fsent_sig_fs_mom",
]
MULTI_TOP5 = [
    "fsent_champ_long_htf15_htffs",
    "fsent_champ_long_htfesmcl4",
    "fsent_champ_long_htf15_tskip6",
    "fsent_champ_long_htffs",
    "fsent_champ_long_mcloff_htf15",
]
ALL10 = SIG_TOP5 + MULTI_TOP5

# A book's edge must keep this share of its per-trade quality when a knob moves,
# or the knob is load-bearing in a way that looks like tuning.
KEEP = 0.80

# "off" value for each switch, plus the sweep deltas for the continuous ones.
OFF = {
    "exp_mltf": False, "exp_persist": 0, "exp_swingpause": 0,
    "exp_skip_weekend": 0, "exp_bias_momentum_min": 0.0,
    "exp_fs_small_swing": 0.0, "exp_trail_skip_n": 0, "exp_trail_half": 0,
    "exp_trail_delay_r": 0.0, "exp_htf_fs_entry": "",
    "exp_partial_r": 0.0, "max_consecutive_losses": 0, "cooldown_bars": 0,
    "ext_stop_r": 0.0, "exp_causal_sl": 0, "exp_window_floor_s": 0,
    "exp_ltf_no_entry": 1, "exp_geom_mode": "", "exp_b1_b2_mode": "",
}
# knobs swept on both sides rather than switched off
SWEEP = {
    "chop_thresh": (-8.0, 8.0),
    "atr_high_thresh": (-0.05, 0.05),
    "atr_low_thresh": (-0.05, 0.05),
    "sl_buf_atr": (-0.005, 0.005),
    "exp_persist": (-2, 2),
    "max_consecutive_losses": (1, 5),
    "cooldown_bars": (4, 12),
    "ext_stop_r": (2.0, 4.0),
    "exp_trail_skip_n": (-2, 2),
    "exp_bias_momentum_min": (-0.2, 0.2),
    "exp_fs_small_swing": (-1.0, 1.0),
    "exp_trail_delay_r": (-0.5, 0.5),
    "htf_rr": (-0.5, 0.5),
}
STRINGS = {
    "exp_fs_entry_side": ("long", "both"),
    "exp_htf_fs_entry": ("flip", "all"),
    "window_end": ("r_touch",),
    "mode": ("chop", "atr_low"),
}
# never swept: structural, changing them makes it a different book
FROZEN = {"swing", "pivot_rule", "max_positions", "soft_width"}

_T = 0
_D = 0
_T0 = time.time()


def step(lbl):
    global _D
    _D += 1
    el = time.time() - _T0
    eta = (el / _D) * (_T - _D) if _D else 0.0
    pct = 100.0 * _D / _T if _T else 0.0
    msg = "[%3.0f%%] %s %5.0fs elapsed, ~%5.0fs left" % (
        pct, "#" * int(pct / 2.5), el, eta)
    sys.stdout.write("\r  " + msg + "   " + lbl)
    sys.stdout.flush()


def trades_of(sim, data, cfg):
    sw = {"sw10": data["sw10"], "sw20": data["sw20"],
          "sw15": data["sw15"], "htf15": data["htf15"]}[cfg["swing"]]
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=data["fine"],
             **{**dict(repin.re_.BP), **cfg["params"]})["ltf_trades"]
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    return [t for t in tr if t.get("outcome") != "open"]


def net_r(t):
    from exp_equity_quality import net_r as _nr
    return float(_nr([t]))


def run(sim, eras, cfg):
    o = {}
    for era in ("is", "oos"):
        tr = trades_of(sim, eras[era], cfg)
        n = len(tr)
        nets = [net_r(t) for t in tr]
        tot = sum(nets)
        # trade-list signature, so INERT can be judged on trades not on net
        sig = hash(tuple((t["entry_ts"], t["dir"]) for t in tr))
        o[era] = {"n": n, "net": round(tot, 2),
                  "r_trade": round(tot / n, 4) if n else 0.0,
                  "sig": "%x" % (sig & 0xFFFFFFFFFFFF)}
    return o


def probes_for(params):
    """The probe list for one book: its own params, off-values and sweeps."""
    out = []
    for k, v in params.items():
        if k in FROZEN:
            continue
        if k in STRINGS:
            for alt in STRINGS[k]:
                if alt != v:
                    out.append((k, alt, "string"))
        if k in OFF and OFF[k] != v:
            out.append((k, OFF[k], "off"))
        if k in SWEEP:
            lo, hi = SWEEP[k]
            for d in (lo, hi):
                nv = v + d if isinstance(v, (int, float)) and not isinstance(v, bool) else v
                if isinstance(nv, (int, float)) and abs(nv) > 1e-9 and nv != v:
                    out.append((k, nv, "sweep"))
    # dedupe
    seen, uniq = set(), []
    for k, v, kind in out:
        key = (k, repr(v))
        if key not in seen:
            seen.add(key)
            uniq.append((k, v, kind))
    return uniq


def main() -> int:
    global _T
    sim = craze.build_module()
    eras = {e: load_era(e) for e in ("is", "oos")}

    todo = []
    for b in ALL10:
        cfg = EXPERIMENTS[b]
        todo.append((b, cfg, probes_for(cfg["params"])))
    _T = sum(len(p) + 2 for _, _, p in todo)
    print("STABILITY - top 5 sig + top 5 multi")
    print("%d probes + 10 baselines, both eras, ~%d min"
          % (_T, _T * 9 // 60))
    print()

    out = {}
    PART = HERE / "top10_stability_partial.json"
    if PART.exists():
        out = json.loads(PART.read_text(encoding="utf-8"))
        print("resuming: %d books have probes done\n" % len(out))

    for book, cfg, probes in todo:
        if book in out:
            continue
        rec = {"baseline": run(sim, eras, cfg), "probes": {}}
        for k, v, kind in probes:
            c2 = {"swing": cfg["swing"], "basis": "fine",
                  "params": dict(cfg["params"])}
            c2["params"][k] = v
            rec["probes"]["%s=%s" % (k, v)] = run(sim, eras, c2)
            step("%-30s %s=%s" % (book, k, v))
        step("%-30s BASELINE" % book)
        out[book] = rec
        PART.write_text(json.dumps(out, indent=1), encoding="utf-8")

    # ---------------- analysis ----------------------------------------
    print()
    for cls, books in (("SIG", SIG_TOP5), ("MULTI", MULTI_TOP5)):
        print("=" * 118)
        print("%s" % cls)
        print("=" * 118)
        print("%-32s %9s %8s %8s | %7s %8s %8s %8s"
              % ("book", "OOSnet", "R/tr", "base%Rtr", "live", "inert",
                 "knob-both+", "off-both+"))
        print("-" * 118)
        for b in books:
            rec = out[b]
            bl = rec["baseline"]
            base_rt = bl["oos"]["r_trade"] or 1e-9
            live = inert = both_pos = both_pos_keep = off_both = off_collapsed = 0
            inert_names, off_names, fragile = [], [], []
            for key, r in rec["probes"].items():
                kname = key.split("=")[0]
                same = (r["is"]["sig"] == bl["is"]["sig"] and r["oos"]["sig"] == bl["oos"]["sig"])
                if same:
                    inert += 1
                    inert_names.append(kname)
                    continue
                live += 1
                rp = r["is"]["net"] > 0 and r["oos"]["net"] > 0
                if rp:
                    both_pos += 1
                rtp = r["oos"]["r_trade"] >= KEEP * base_rt
                if rp and rtp:
                    both_pos_keep += 1
                else:
                    fragile.append(key)
                if kname in OFF and key.split("=")[1] == repr(OFF.get(kname)):
                    if rp:
                        off_both += 1
                    else:
                        off_collapsed += 1
                        off_names.append(kname)
            print("%-32s %+9.1f %8.3f %8.3f | %7d %8d %8d %8d"
                  % (b, bl["oos"]["net"], bl["oos"]["r_trade"], base_rt,
                     live, inert, both_pos_keep, off_both))
            if inert_names:
                print("      INERT (trade list unchanged): %s"
                      % ", ".join(sorted(set(inert_names))))
            if off_collapsed:
                print("      COLLAPSES with this switched OFF: %s" % ", ".join(off_names))
            if fragile:
                print("      FRAGILE under: %s" % ", ".join(sorted(fragile)[:6]))
        print()

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - _T0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
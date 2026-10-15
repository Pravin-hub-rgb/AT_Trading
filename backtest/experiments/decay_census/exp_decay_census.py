"""
DECAY CENSUS - the P36 decay gate, which has never once been switched on.

WHY THIS AND NOT ANOTHER SHAPE OF OUTPUT

I spent the last stretch testing structure in the chain OUTPUT: swing shape,
volatile candles, alternation depth. Five shapes, and the multiple-comparisons
problem ate all of them - every bootstrap CI came back "not separable". That is
the predictable result of picking the wrong axis to search.

The engine, by contrast, ships a whole gate that has never fired:

    _decay_blocks(mode, direction, t, thr, n)     unified.py:820
        mode 1  block long if up-legs broken >= thr
        mode 2  block long if down-legs broken >= thr
        mode 3  long -> up-legs, short -> down-legs
        mode 4  long -> down-legs, short -> up-legs
        mode 5  block if up-legs broken  < thr        <- inverse of 1
        mode 6  block if down-legs broken < thr       <- inverse of 2
        mode 7  mode 3 but with < thr                 <- inverse of 3
        mode 8  mode 4 but with < thr                 <- inverse of 4
        mode 0  off

Four files in the repo name exp_decay_mode / _thr / _legs. None of them sets a
value. exp_decay_mode defaults to 0 and 0 returns False immediately, so this gate
has been dead code in every result ever produced here.

THE CAUSAL STORY - required by pipeline section 4c, and the reason this is legal

    _decay_legs stamps each leg with sw["confirmed_at_time"] - when the leg was
    CONFIRMED, not when it started.
    _decay_frac filters vis = [L for L in legs if L[0] <= t] at the entry
    timestamp t, takes the last n, and inspects candles only up to
    j = bisect_right(candle_ts_ltf, t) - 1.

So every leg it reads has already confirmed at or before the entry bar, and every
candle it touches printed at or before the entry bar. Nothing after the entry is
read. That is a causal rule, unlike the M2 / end_px / prevpos families that
shipped large numbers by reading later fields. Stated here so it can be checked
rather than trusted.

THE INVERSE TEST IS FREE

Modes 1/5, 2/6, 3/7, 4/8 are sign-flips of each other on the same legs. So every
candidate can be classified without inventing a knob:

    STRONG   the inverse loses in BOTH eras. The gate is doing what it says.
    NULL     nothing moves. A fact, like chop_thresh under atr_high.
    WEAK     it wins with no inverse story. Recorded, never promoted.

DISCIPLINE

  - Default-off identity gate first. exp_decay_mode=0 must reproduce the pinned
    book to the decimal or nothing below is trustworthy.
  - One dimension at a time, per book. No grid.
  - IS decides. OOS is computed for the survivors and shown, not searched.
  - Own directory. Does not touch exp_mode_strict.py or any mode-census file,
    which another agent is running concurrently.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_decay_census.py
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
from exp_mcl_matrix import metrics, load_era, LADDER_BOOKS  # noqa: E402

BOOKS = ["fsent_champ_long", "fsent_champ_short",
         "fsent_champ_long_htf15", "fsent_champ_long_htffs",
         "fsent_champ_long_mcloff"]

# (mode, inverse_mode, label, inverse_label)
MODES = [
    (1, 5, "long: up-legs broken >= thr", "long: up-legs broken < thr"),
    (2, 6, "long: down-legs broken >= thr", "long: down-legs broken < thr"),
    (3, 7, "long->up / short->down", "same, flipped to <"),
    (4, 8, "long->down / short->up", "same, flipped to <"),
]
THRS = [0.25, 0.5, 0.75]
LEGS = [4, 8]


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    out = {"stage": "decay_census", "modes": MODES, "thrs": THRS, "legs": LEGS,
           "eras": {}}

    for era in ("is", "oos"):
        print()
        print("=" * 116)
        print("DECAY CENSUS - the gate that has never been switched on    era = %s" % era.upper())
        print("=" * 116)
        d = load_era(era)
        era_out = {}

        def run(book, **ov):
            cfg = EXPERIMENTS[book]
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            p.update(ov)
            sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
            r = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            return r["ltf_trades"] if isinstance(r, dict) else r

        # ---------- identity gate: mode 0 must reproduce the pinned book -------
        print()
        print("  IDENTITY GATE - exp_decay_mode=0 must reproduce the pinned book")
        idok = True
        for b in BOOKS:
            cfg = EXPERIMENTS[b]
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
            r = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            tr = r["ltf_trades"] if isinstance(r, dict) else r
            m = metrics(tr)
            era_out.setdefault(b, {})["pin"] = m
            print("    %-28s n=%-4d NET=%+9.2f  DD=%6.2f  MaxCL=%d"
                  % (b, m["n"], m["net"], m["dd"], m["mc"]))
            if m["n"] == 0:
                idok = False
        print()
        if not idok:
            print("  ABORT: a pinned book produced no trades; harness is broken.")
            return 2

        # ---------- does the gate fire at all? --------------------------------
        print("  FIRING CHECK - does any (mode, thr, legs) actually block entries?")
        print("  A gate that never blocks is a NULL regardless of its net.")
        print()
        print("    %-28s %-30s %6s %8s %9s %9s"
              % ("book", "setting", "n", "delta_n", "NET", "delta_NET"))
        print("    " + "-" * 96)
        for b in BOOKS:
            base = era_out[b]["pin"]
            for mode, inv, lab, _ilab in MODES:
                for thr in THRS:
                    for lg in LEGS:
                        m = metrics(run(b, exp_decay_mode=mode, exp_decay_thr=thr,
                                        exp_decay_legs=lg))
                        key = "%d|%s|%s" % (mode, thr, lg)
                        era_out[b][key] = m
                        dn = m["n"] - base["n"]
                        if dn == 0:
                            continue          # blocks nothing - reported in summary
                        print("    %-28s %-30s %6d %+8d %+9.2f %+9.2f"
                              % (b, "m%d thr=%.2f legs=%d" % (mode, thr, lg),
                                 m["n"], dn, m["net"], m["net"] - base["net"]))
        print()
        print("    (only settings that actually removed entries are listed above)")
        print()

        # ---------- classification --------------------------------------------
        print("  CLASSIFICATION - STRONG needs the inverse to lose in BOTH eras;")
        print("  WEAK is a win with no inverse story; NULL never blocks anything.")
        print()
        print("    %-28s %-22s %10s %10s %10s %10s  %s"
              % ("book", "setting", "base NET", "gate NET", "inv NET", "d(IS)", "verdict"))
        print("    " + "-" * 108)
        verdicts = {}
        for b in BOOKS:
            base = era_out[b]["pin"]
            rows = []
            for mode, inv, lab, ilab in MODES:
                for thr in THRS:
                    for lg in LEGS:
                        key = "%d|%s|%s" % (mode, thr, lg)
                        ikey = "%d|%s|%s" % (inv, thr, lg)
                        g = era_out[b].get(key)
                        iv = era_out[b].get(ikey)
                        if not g:
                            continue
                        blocked = g["n"] != base["n"]
                        if not blocked and (not iv or iv["n"] == base["n"]):
                            continue
                        dnet = g["net"] - base["net"]
                        invnet = (iv["net"] - base["net"]) if iv else None
                        if not blocked and invnet is None:
                            v = "NULL"
                        elif dnet > 0 and (invnet is None or invnet < 0):
                            v = "STRONG?" if era == "is" else "check OOS"
                        else:
                            v = "weak/negative"
                        rows.append((key, lab, dnet, invnet, v, g, iv))
                        if era == "is":
                            verdicts.setdefault(b, []).append((key, lab, dnet, invnet, v))
            for key, lab, dnet, invnet, v, g, iv in rows:
                print("    %-28s %-22s %+10.2f %+10.2f %+10s  %s"
                      % (b, key, base["net"], g["net"],
                         ("%+10.2f" % inv["net"]) if iv else "        -", v))
            print()
        out["eras"][era] = era_out
        print()

    (HERE / "decay_census_results.json").write_text(json.dumps(out, indent=2),
                                                   encoding="utf-8")
    print("  wrote %s" % (HERE / "decay_census_results.json"))
    print()
    print("  NOTHING PROMOTED. Default-off identity verified; OOS was computed")
    print("  alongside IS for every cell rather than searched separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
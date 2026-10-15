"""E4 - the modes that are strictly better than the shipped one, and whether they hold.

WHY THIS EXPERIMENT EXISTS
--------------------------
exp_mode_census.py ranked all 26 modes on NET and found a mode beating the
shipped atr_high in both eras on 5 books out of 5. Two of those were registered.
One of the two, fsent_champ_long_htf15_union, was then removed by the owner
after the year-by-year and per-trade numbers were laid out, and it was right to
remove it:

    htf15 shipped   500 IS trades  1.010 R/trade  281 OOS trades  0.907 R/trade
    + union         786 IS trades  0.733 R/trade  451 OOS trades  0.713 R/trade

Net pays for volume. union takes both HTF windows so it simply takes more
trades; per-trade quality fell 27% in both eras and its worst IS year paid
12.28R. That is dilution, not edge, and no amount of net would have said so.

THE CORRECTED SELECTION RULE, used from here on
----------------------------------------------
A mode is a candidate only if, against the shipped mode on the same book, in
BOTH eras:

    net          >  shipped net
    R per trade  >  shipped R per trade
    trades       <= shipped trades        (it may not buy its net with volume)

R per trade is total net / n, both taken after _trade_costs. Under this rule
4 of the 5 census books have NO candidate at all. fsent_champ_short has 8.

WHAT IS TESTED HERE
-------------------
  1. IDENTITY GATE on the shipped mode, both eras, before anything else.
  2. KNOB SWEEP for each candidate, on the knob that candidate actually routes
     on - read off the branch, not assumed. hmm and flip_quality both route on
     chop_thresh; chop_and_atr_low also on atr_low_thresh; soft_atr on
     atr_high_thresh and soft_width. A gain that only exists at the shipped
     value is a tuned number, and the 58 that 86 books already use has already
     been measured DEAD under atr_high.
  3. REPLICATION on two books the candidates were NOT selected on. Selection
     happened on fsent_champ_short alone; anything that only works there is a
     property of that book, not of the mode.

PIPELINE DISCIPLINE
Identity gate first. Both eras. Nothing promoted.

Output: mode_strict_results.json
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
RESULTS = HERE / "mode_strict_results.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from exp_signal_metrics import load_era                          # noqa: E402
from registry import EXPERIMENTS                                # noqa: E402

SHIPPED = "atr_high"

# Candidates are the 8 modes that pass the strict rule on fsent_champ_short.
# The knob each one routes on, read from unified.py. Empty tuple = nothing to
# sweep, recorded SKIPPED rather than passed.
CANDIDATES = [
    ("hmm",                  ("chop_thresh",),      "hmm range-score vs chop_thresh"),
    ("flip_quality",         ("chop_thresh",),      "b2_vs_flip_chop + htf_mag floor"),
    ("chop",                 ("chop_thresh",),      "decisive when chop high"),
    ("b2_vs_flip_chop",      ("chop_thresh",),      "B2 when chop high"),
    ("decisive_vs_flip_chop", ("chop_thresh",),     "decisive when chop high"),
    ("htf_mag_inv",          ("chop_thresh",),      "inverted on HTF magnitude"),
    ("chop_and_atr_low",     ("chop_thresh", "atr_low_thresh"), "decisive on BOTH"),
    ("soft_atr",             ("atr_high_thresh", "soft_width"), "soft band on ATR%"),
]

CHOP_OFFSETS = [-16, -8, 0, 8, 16]
ATR_OFFSETS = [-0.10, -0.05, 0, 0.05, 0.10]

# Selection happened on fsent_champ_short. These two are the replication set.
REPLICATE_ON = ["fsent_champ_long", "fsent_champ_long_htf15"]

SELECT_BOOK = "fsent_champ_short"

_D = 0
_T0 = time.time()


def run(sim, eras, book, mode, extra=None):
    cfg = dict(EXPERIMENTS[book])
    params = dict(cfg["params"], mode=mode)
    if extra:
        params.update(extra)
    cfg["params"] = params
    out = {}
    for era in ("is", "oos"):
        m = repin.measure(sim, eras[era], cfg)
        out[era] = m
    return out


def step(label):
    global _D
    _D += 1
    el = time.time() - _T0
    pct = 100.0 * _D / _TOTAL
    eta = (el / _D) * (_TOTAL - _D) if _D else 0.0
    sys.stdout.write("\r  [%3.0f%%] %s %5.0fs elapsed, ~%4.0fs left   %s"
                     % (pct, "#" * int(pct / 2.5), el, eta, label))
    sys.stdout.flush()


def rp(m):
    return m["net"] / m["n"] if m["n"] else 0.0


def main() -> int:
    global _TOTAL
    _TOTAL = 2 + len(CANDIDATES) * 2 + sum(
        len(CHOP_OFFSETS) + (len(ATR_OFFSETS) - 1 if len(k) > 1 else 0)
        for _, k, _ in CANDIDATES) * 2 + len(REPLICATE_ON) * len(CANDIDATES) * 2

    print("E4 - STRICT SELECTION: better net AND better per-trade quality AND no extra trades")
    print("8 candidates on %s, knob sweeps, replication on %s"
          % (SELECT_BOOK, ", ".join(REPLICATE_ON)))
    print("estimated ~%d min\n" % (_TOTAL * 9 // 60))
    t0 = time.time()
    sim = craze.build_module()
    eras = {"is": load_era("is"), "oos": load_era("oos")}
    print("loaded (%.0fs)\n" % (time.time() - t0))

    out = {"select_book": SELECT_BOOK, "shipped_mode": SHIPPED, "candidates": {}}

    # ---- 1. IDENTITY GATE -------------------------------------------------
    print("=" * 100)
    print("IDENTITY GATE")
    print("=" * 100)
    gate_ok = True
    for book in [SELECT_BOOK] + REPLICATE_ON:
        cfg = dict(EXPERIMENTS[book])
        cfg["basis"] = "fine"
        pin = cfg.get("pins") or {}
        for era in ("is", "oos"):
            m = repin.measure(sim, eras[era], cfg)
            step("%s OWN %s" % (book, era))
            wn = pin.get("n") if era == "is" else pin.get("oos_n")
            wt = pin.get("net") if era == "is" else pin.get("oos_net")
            ok = m["n"] == wn and abs(m["net"] - wt) < 0.01
            gate_ok = gate_ok and ok
            print("  %-28s %-4s n=%-5d net=%9.2f pin %9.2f  %s"
                  % (book, era, m["n"], m["net"], wt, "OK" if ok else "*** MISMATCH ***"))
    out["identity_ok"] = gate_ok
    print()
    if not gate_ok:
        print("!! GATE FAILED"); RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8"); return 1
    print("gate passed.\n")

    base = run(sim, eras, SELECT_BOOK, SHIPPED)
    bi, bo = rp(base["is"]), rp(base["oos"])
    print("shipped %s on %s: IS %d tr / %.2fR / %.3f per trade  |  OOS %d tr / %.2fR / %.3f per trade"
          % (SHIPPED, SELECT_BOOK, base["is"]["n"], base["is"]["net"], bi,
             base["oos"]["n"], base["oos"]["net"], bo))
    out["shipped"] = base
    print()

    # ---- 2. CANDIDATES: strict rule, then knob sweep ----------------------
    for mode, knobs, desc in CANDIDATES:
        r = run(sim, eras, SELECT_BOOK, mode)
        step("%s %s both" % (SELECT_BOOK, mode))
        ai, ao = rp(r["is"]), rp(r["oos"])
        strict = (r["is"]["net"] > base["is"]["net"] and r["oos"]["net"] > base["oos"]["net"]
                  and ai > bi and ao > bo
                  and r["is"]["n"] <= base["is"]["n"] and r["oos"]["n"] <= base["oos"]["n"])
        print("=" * 100)
        print("%-18s  %s" % (mode, desc))
        print("  IS  %4d tr %+8.2fR %+.3f/tr   (shipped %+8.2fR %+.3f/tr, %d tr)"
              % (r["is"]["n"], r["is"]["net"], ai, base["is"]["net"], bi, base["is"]["n"]))
        print("  OOS %4d tr %+8.2fR %+.3f/tr   (shipped %+8.2fR %+.3f/tr, %d tr)"
              % (r["oos"]["n"], r["oos"]["net"], ao, base["oos"]["net"], bo, base["oos"]["n"]))
        print("  strict rule: %s" % ("PASS" if strict else "FAIL"))

        sweep = {}
        verdict = "no knob to sweep - SKIPPED, not passed"
        for ki, knob in enumerate(knobs):
            offs = ATR_OFFSETS if knob in ("atr_low_thresh", "atr_high_thresh") else CHOP_OFFSETS
            ship_val = float(EXPERIMENTS[SELECT_BOOK]["params"].get(knob, 58))
            ship_val = ship_val if ship_val else 58.0
            cols, lines = [], []
            for off in offs:
                val = ship_val + off
                s = run(sim, eras, SELECT_BOOK, mode, {knob: val})
                step("%s %s=%s" % (SELECT_BOOK, mode, knob))
                sweep["%s=%s" % (knob, val)] = s
                lines.append("    %-14s %.4f  IS %+8.2fR (%+7.2f) %4d tr   OOS %+8.2fR (%+7.2f) %4d tr%s"
                             % (knob, val, s["is"]["net"], s["is"]["net"] - base["is"]["net"],
                                s["is"]["n"], s["oos"]["net"], s["oos"]["net"] - base["oos"]["net"],
                                s["oos"]["n"], "  <- shipped" if off == 0 else ""))
            print("  knob %s (shipped %.4f):" % (knob, ship_val))
            for ln in lines:
                print(ln)
            gains_i = [v["is"]["net"] - base["is"]["net"] for v in sweep.values()
                       if "=%s" % knob == ("=" + knob) or True]
            gains_i = []
            gains_o = []
            for off in offs:
                key = "%s=%s" % (knob, ship_val + off)
                gains_i.append(sweep[key]["is"]["net"] - base["is"]["net"])
                gains_o.append(sweep[key]["oos"]["net"] - base["oos"]["net"])
            spread = max(gains_i) - min(gains_i)
            pos_i = sum(1 for g in gains_i if g > 0)
            pos_o = sum(1 for g in gains_o if g > 0)
            if spread < 1.0:
                verdict = "DEAD - identical across the sweep, so %s is not winning via %s" % (mode, knob)
            elif pos_i == len(offs) and pos_o == len(offs):
                verdict = "REGIONAL - %d/%d IS and %d/%d OOS positive, spread %.1fR" % (
                    pos_i, len(offs), pos_o, len(offs), spread)
            elif pos_i >= len(offs) - 1 and pos_o >= len(offs) - 1:
                verdict = "MOSTLY REGIONAL - %d/%d IS, %d/%d OOS positive, spread %.1fR" % (
                    pos_i, len(offs), pos_o, len(offs), spread)
            else:
                verdict = "PATCHY - %d/%d IS, %d/%d OOS positive, spread %.1fR" % (
                    pos_i, len(offs), pos_o, len(offs), spread)
            print("  -> %s" % verdict)

        out["candidates"][mode] = {
            "desc": desc, "knobs": list(knobs), "result": r,
            "strict_pass": strict, "sweep": sweep, "verdict": verdict,
            "replication": {},
        }

    # ---- 3. REPLICATION on books it was not selected on -------------------
    print()
    print("=" * 100)
    print("REPLICATION - the candidates were chosen on %s only" % SELECT_BOOK)
    print("=" * 100)
    for book in REPLICATE_ON:
        b = run(sim, eras, book, SHIPPED)
        cbi, cbo = rp(b["is"]), rp(b["oos"])
        print()
        print("%s  shipped: IS %d tr %.3f/tr | OOS %d tr %.3f/tr"
              % (book, b["is"]["n"], cbi, b["oos"]["n"], cbo))
        held = []
        for mode, _, _ in CANDIDATES:
            r = run(sim, eras, book, mode)
            step("%s %s replicate" % (book, mode))
            ok = (r["is"]["net"] > b["is"]["net"] and r["oos"]["net"] > b["oos"]["net"]
                  and rp(r["is"]) > cbi and rp(r["oos"]) > cbo
                  and r["is"]["n"] <= b["is"]["n"] and r["oos"]["n"] <= b["oos"]["n"])
            out["candidates"][mode]["replication"][book] = {
                "result": r, "strict_pass": ok}
            if ok:
                held.append(mode)
            print("  %-18s IS %+8.2fR %+.3f/tr %4d tr   OOS %+8.2fR %+.3f/tr %4d tr   %s"
                  % (mode, r["is"]["net"], rp(r["is"]), r["is"]["n"],
                     r["oos"]["net"], rp(r["oos"]), r["oos"]["n"],
                     "HOLDS" if ok else "-"))
        out["replication_held"] = out.get("replication_held", {})
        out["replication_held"][book] = held
        print("  held on %s: %s" % (book, held or "none"))

    # ---- SUMMARY ---------------------------------------------------------
    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print("%-18s %-8s %-46s %s" % ("mode", "strict", "knob verdict", "replication"))
    for mode, _, _ in CANDIDATES:
        c = out["candidates"][mode]
        rep_ = " ".join("%s:%s" % (b.split("_")[-1], "+" if c["replication"][b]["strict_pass"] else "-")
                        for b in REPLICATE_ON)
        print("%-18s %-8s %-46s %s" % (mode, "PASS" if c["strict_pass"] else "fail",
                                       c["verdict"][:46], rep_))
    print()
    print("  Nothing promoted. A candidate needs: strict PASS, a REGIONAL knob")
    print("  verdict, and to hold on a book it was not selected on.")

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print()
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
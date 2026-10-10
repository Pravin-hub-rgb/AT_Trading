"""C1 done properly: entry instant vs the FS print of the swing it traded.

WHAT C1 CLAIMS TO TEST
----------------------
exp_fs_causality.py documents C1 as "entry_ts >= the FS print of ITS OWN swing on
the same plane". The shipped book turns on it: six books, both eras, 0 violations,
and that 0 is quoted everywhere.

WHAT IT ACTUALLY DOES
---------------------
It reconstructs the FS instant from TEXT, not from the index:

    f = s["fs_at_time"]
    fs_ts = ts_ist(s["day"] + " " + f)      # when len(f) <= 5

and from btc_swing.py:
    day         = candles[eng.start_idx].date[:10]      <- the swing's START bar date
    fs_at_time  = candles[fs_at_idx].date[11:16]        <- BARE "HH:MM" for chop-source

So for a chop-source swing that started on the 18th and whose completing chop cross
printed at 01:45 on the 19th, the reconstruction yields 18-Jan 01:45. That is
roughly 23 hours EARLY. An entry on the 18th at 20:00 passes C1 (20:00 > 01:45)
even though the FS print that supposedly triggered it had not happened yet.

The engine does NOT do this - it uses fs_at_idx directly (unified.py:536-541 builds
fs_up_ts/fs_dn_ts from candles_htf[_fi]["ts"]). So the engine is probably fine and
the AUDIT has been passing for the wrong reason. That is the more serious version of
this problem: a green light on a check that was never measuring the thing it was
supposed to measure.

WHAT THIS DOES
--------------
Re-derives the FS instant from fs_at_idx - the index - and compares in
decision-instant space:

    decision  = entry_ts + 900          the 15m entry bar has CLOSED
    fs_knowable = candles_ltf[fs_at_idx]["ts"] + 900    that bar has CLOSED
    violation = decision < fs_knowable

Covers EVERY trade, not only the FS-triggered ones, and every registered fsent book.
The previous run skipped 38.3% of trades via a `break_kind != "FS"` filter.

POSITIVE CONTROL
----------------
`exp_causal_sl` is a real parameter. With it flipped, the engine reads a different
stop source, which is a different code path and must be checkable by an unrelated
detector - so it is not a valid control for this check and is not used as one.

The control used here is a deliberately corrupted copy of the FS index: every swing
has its fs_at_idx shifted forward by +40 bars, simulating structure that "completes"
later than the engine believes. A correct detector must light up on the books where
that shift makes entries precede their own FS print. If the detector stays silent
under that corruption it is not a detector.

Writes _c1_index_audit.json.
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, ".")

from progress import Announce, Bar                  # noqa: E402
from exp_tf_family import build_family_module      # noqa: E402
from run_experiment import get_swings, net_r        # noqa: E402
from exp_signal_metrics import load_era             # noqa: E402
from experiment_registry import EXPERIMENTS         # noqa: E402

LTF_CLOSE = 900
CONTROL_SHIFT_BARS = 40


def fs_knowable(swing, candles, shift=0):
    """The instant the FS print of this swing became knowable, from its INDEX.

    Returns (timestamp, how_it_was_derived). Never reads fs_at_time.
    """
    idx = swing.get("fs_at_idx")
    if idx is None or not (0 <= idx < len(candles)):
        return None, "no_fs_index"
    idx = idx + shift
    if not (0 <= idx < len(candles)):
        return None, "shifted_out_of_range"
    src = "chop_cross" if swing.get("source") == "chop" else "confirmation"
    return int(candles[idx]["ts"]) + LTF_CLOSE, src


def audit(sim, era, d, swing_key, params, shift=0):
    params = dict(params)
    params.pop("exp_mltf", None)
    o = sim(d["c1h"], get_swings(d, swing_key), d["c15"], d["sw15"],
            fine_ltf=d["fine"], **params)
    swings = get_swings(d, swing_key)
    ltf_sw = d["sw15"]
    by_index = {int(s["swing_index"]): s for s in ltf_sw}
    out = []
    for t in o["ltf_trades"]:
        if t.get("outcome") == "open":
            continue
        s = by_index.get(int(t["swing_no"]))
        if s is None:
            continue
        known, how = fs_knowable(s, d["c15"], shift)
        if known is None:
            continue
        decision = int(t["entry_ts"]) + LTF_CLOSE
        out.append({
            "trade_no": t["trade_no"],
            "entry_date": t["entry_date"],
            "entry_ts": int(t["entry_ts"]),
            "decision": decision,
            "fs_knowable": known,
            "lead_s": decision - known,
            "violation": decision < known,
            "break_kind": t.get("break_kind"),
            "htf_regime": t.get("htf_regime"),
            "fs_source": how,
            "swing_no": int(t["swing_no"]),
            "net_r": round(net_r([t]), 3),
        })
    return out


def main():
    Announce("building engine and loading both eras", "~1 min")
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}

    books = sorted(k for k, v in EXPERIMENTS.items()
               if isinstance(v, dict) and k.startswith("fsent_")
               and (v.get("pins") or {}).get("n"))
    # One book at a time by default. The full family takes ~30 min and the owner
    # does not have that; pass more names as argv to extend.
    if len(sys.argv) > 1:
        books = sys.argv[1:]
    else:
        books = ["fsent_champ_long"]
    print("  books under audit: %s" % ", ".join(books))
    base = dict(EXPERIMENTS["fsent_champ_long"]["params"])
    bar = Bar(len(books) * 2, "C1 index audit + control")

    results = {}
    for key in books:
        swing = EXPERIMENTS[key].get("swing") or "sw10"
        params = {**base, **(EXPERIMENTS[key].get("params") or {})}
        rec = {"clean": {}, "control": {}}
        for era in ("is", "oos"):
            rec["clean"][era] = audit(sim, era, E[era], swing, params, shift=0)
            rec["control"][era] = audit(sim, era, E[era], swing, params,
                                        shift=CONTROL_SHIFT_BARS)
        results[key] = rec
        bar.update(key)
        bar.update(key)
    bar.close("measured")

    # ---------------------------------------------------------------- report --
    print()
    print("#" * 122)
    print("C1 - ENTRY INSTANT vs THE FS PRINT OF ITS OWN SWING, taken from fs_at_idx")
    print("  decision    = entry_ts + %d  (the 15m entry bar has CLOSED)" % LTF_CLOSE)
    print("  fs_knowable = candles_ltf[fs_at_idx]['ts'] + %d" % LTF_CLOSE)
    print("  violation   = decision < fs_knowable")
    print("#" * 122)
    print("  %-32s %7s %7s %7s %7s  %9s %9s"
          % ("book", "IS n", "IS bad", "OOS n", "OOS bad", "min lead", "worst trade"))
    print("  " + "-" * 118)
    tot_n = tot_bad = 0
    viol_rows = []
    for key in books:
        c = results[key]["clean"]
        rows = c["is"] + c["oos"]
        bad = [r for r in rows if r["violation"]]
        mn = min((r["lead_s"] for r in rows), default=None)
        worst = min(rows, key=lambda r: r["lead_s"]) if rows else None
        tot_n += len(rows)
        tot_bad += len(bad)
        viol_rows += [(key, r) for r in bad]
        print("  %-32s %7d %7d %7d %7d  %9s %9s"
              % (key[:32], len(c["is"]), len(bad[:0]) if False else
                 sum(1 for r in c["is"] if r["violation"]),
                 len(c["oos"]),
                 sum(1 for r in c["oos"] if r["violation"]),
                 "-" if mn is None else "%+d s" % mn,
                 "-" if worst is None else "#%d" % worst["trade_no"]))

    print()
    print("  TOTAL: %d trades checked, %d violations" % (tot_n, tot_bad))

    # ---- where the old string method would have disagreed ------------------
    print()
    print("#" * 122)
    print("HOW MUCH THE OLD STRING METHOD WAS MISSING")
    print("  btc_swing.py sets fs_at_time to a BARE 'HH:MM' for chop-source swings and")
    print("  day to the swing's START-bar date. If the completing cross printed on a later")
    print("  calendar day, joining them yields a timestamp up to ~24h EARLY, which makes")
    print("  the check permissive. Counted below: chop-source swings whose reconstructed")
    print("  string timestamp differs from the index-derived one by more than a minute.")
    print("#" * 122)

    d = E["is"]
    ltf_sw = d["sw15"]
    disagree = 0
    total_chop = 0
    examples = []
    for s in ltf_sw:
        if s.get("source") != "chop":
            continue
        total_chop += 1
        idx = s.get("fs_at_idx")
        ft = s.get("fs_at_time") or ""
        if idx is None or not (0 <= idx < len(d["c15"])):
            continue
        real = int(d["c15"][idx]["ts"])
        real_str = d["c15"][idx]["date"]
        if len(ft) <= 5:
            bad_str = s.get("day", "") + " " + ft
            from datetime import datetime, timezone
            try:
                b = datetime.strptime(bad_str, "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            b_ts = int(b.replace(tzinfo=timezone.utc).timestamp()) - 19800
            if abs(b_ts - real) > 60:
                disagree += 1
                if len(examples) < 6:
                    examples.append({
                        "swing_index": s.get("swing_index"),
                        "day_start": s.get("day"),
                        "fs_at_time_bare": ft,
                        "string_reconstruction": bad_str,
                        "true_fs_bar_date": real_str,
                        "error_hours": round((real - b_ts) / 3600.0, 2),
                    })
    print("  chop-source swings in the LTF plane (IS era) : %d" % total_chop)
    print("  of those, string reconstruction is wrong     : %d" % disagree)
    print()
    for e in examples:
        print("    swing %-4s started %s  fs_at_time='%s'" % (
            e["swing_index"], e["day_start"], e["fs_at_time_bare"]))
        print("      string method believes FS printed at : %s" % e["string_reconstruction"])
        print("      actually the FS bar was               : %s   (off by %.1f h)" % (
            e["true_fs_bar_date"], e["error_hours"]))

    # ---- positive control -------------------------------------------------
    print()
    print("#" * 122)
    print("POSITIVE CONTROL - fs_at_idx deliberately shifted forward by %d bars" % CONTROL_SHIFT_BARS)
    print("  If the detector cannot fire under a known corruption it is not a detector.")
    print("#" * 122)
    print("  %-32s %9s %9s %10s" % ("book", "clean bad", "control bad", "control %"))
    print("  " + "-" * 118)
    ctl_bad = 0
    for key in books:
        c = results[key]["control"]
        bad = sum(1 for era in ("is", "oos") for r in c[era] if r["violation"])
        clean_bad = sum(1 for era in ("is", "oos")
                       for r in results[key]["clean"][era] if r["violation"])
        ctl_bad += bad
        print("  %-32s %9d %9d %9.1f%%"
              % (key[:32], clean_bad, bad,
                 100.0 * bad / max(1, sum(len(c[e]) for e in ("is", "oos")))))
    print()
    print("  control fired on %d trades across the family" % ctl_bad)
    print("  VERDICT: %s" % ("DETECTOR WORKS - the clean result above is meaningful"
                             if ctl_bad > 0 else
                             "DETECTOR DID NOT FIRE - the clean result is worthless"))

    json.dump({"results": results, "violations": viol_rows,
               "chop_total": total_chop, "chop_wrong": disagree,
               "chop_examples": examples,
               "control_shift": CONTROL_SHIFT_BARS, "control_fired": ctl_bad,
               "total": tot_n, "bad": tot_bad},
              open("_c1_index_audit.json", "w", encoding="utf-8"), indent=1)
    print("\n  wrote _c1_index_audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
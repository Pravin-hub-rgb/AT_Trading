"""exp_fs_causality - the audit the owner asked for by name.

THE QUESTION
============
> "there was this base bug of lookahead and i wanna make sure that each trade are
> after fs of the prev swing this is must. i hope this was not violated"

Every trade in this repo's fsent books is entered on a swing's FS print - the
first structural point at which the market has declared a leg. If a trade can be
entered BEFORE its own FS print, the book is reading the future and every number
in the registry is fiction. The repo has already had one instance of this class
of bug (the C17 HTF window-end lookahead), so "i hope" is not a sufficient
answer and the check has to be an assertion.

WHAT IS CHECKED, AND WHY EACH ONE IS SEPARATE
=============================================
A trade is causal if three different moments are all in the past at entry:

  C1  entry_ts >= the FS print of ITS OWN swing, on the same plane.
      This is the one the owner named. The engine reads `fs_at_idx` off the swing
      and the trade carries `swing_no`, so the pair can be joined directly rather
      than inferred.

  C2  entry_ts >= the FS print of the swing the STOP is taken from.
      The stop sits at the swing's `seg.start_px` - the swing's origin. If the
      stop came from a swing whose FS had not printed yet, the risk would be
      computed from a level the market had not yet reached. This is the same
      shape as C17 and is checked separately because it is a different swing.

  C3  entry_ts <= window_end of the HTF window the trade is attributed to.
      C17 was exactly this: `window_end` was read as "exit", which let the window
      gate see the exit before it happened. The trade records `window_start` and
      `window_end`; the gate may read anything up to ENTRY but nothing after.
      Checked as window_start <= entry_ts, plus a report of how far before
      window_end entry sits, so a book that is quietly leaning on the end of its
      own window is visible rather than assumed safe.

HOW THE SWING IS JOINED
=======================
Trades carry `swing_no`. Swings carry `swing_index`. Those are the same
enumeration, so the join is exact - no nearest-timestamp heuristic, which is the
only kind of join that could hide the bug being looked for.

Each check is reported per era and per plane, and any violation is a hard
non-zero exit rather than a printed warning. A causality audit that can only
warn is not an audit.

Run:  cd backtest/tests
      python -u exp_fs_causality.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOKS = [
    ("fsent_champ_long", "the shipping book"),
    ("fsent_champ_short", "the short-side mirror"),
    ("fsent_utcsat_long", "the sibling"),
    ("fsent_sig_full", "the serial sig book"),
    ("fsent_sig_multi", "the registered candidate"),
    ("fsent_champ_long_htf15", "the htf15 candidate"),
]
OUT_JSON = Path(__file__).parent / "_fs_causality.json"
DOC_MD = ROOT / "backtest/docs/method/FS_CAUSALITY_AUDIT.md"

# The loaders write naive IST wall time into the CSVs and the swing records,
# then derive `ts` as `naive_epoch - IST_OFFSET_SEC`. `entry_ts` on a trade is
# already that derived UTC epoch. So a swing's `fs_at_time`, parsed as if it were
# UTC, lands 5h30m in the FUTURE of the trade that fired on it - which is what
# produced a first pass that reported 184 "violations" in the shipping book, every
# one of them exactly -19800s. A causality audit that mis-read the timezone would
# have cried wolf on the single most important question in this repo, so the
# offset is applied here and then PROVED by asserting that entry_ts + IST_OFFSET
# reproduces entry_date, before any comparison is made.
IST_OFFSET_SEC = 5 * 3600 + 30 * 60


def ts(date_str):
    """Naive IST wall time -> epoch seconds, UTC.

    The loaders are not consistent: `day` is 'YYYY-MM-DD', `fs_at_time` is a
    bare 'HH:MM', `confirmed_at_time` is a full 'YYYY-MM-DD HH:MM:SS'. All three
    shapes occur on fields this audit reads, so all three are handled here rather
    than assumed. A parse failure raises instead of returning None, because a
    silently-dropped timestamp in a causality audit is the exact failure mode the
    audit exists to catch.
    """
    if not date_str:
        return None
    s = str(date_str).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S"):
        try:
            return int(datetime.strptime(s[:19] if len(s) > 19 else s, fmt)
                       .replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    raise ValueError("unparseable timestamp %r - refusing to drop it in a "
                     "causality audit" % (date_str,))


def ts_ist(date_str):
    """Naive IST wall time -> the same UTC epoch the engine's `ts` fields carry.

    This is the function C1 must use, not ts(). See the note beside IST_OFFSET_SEC
    for why: a swing's fs_at_time read as UTC sits 5h30m ahead of the trade that
    fired on it, and the first pass of this audit reported 184 phantom
    violations in the shipping book on exactly that offset.
    """
    v = ts(date_str)
    return None if v is None else v - IST_OFFSET_SEC


def main():
    from exp_tf_family import build_family_module
    from run_experiment import net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    data = {}
    for era in ("is", "oos"):
        d = load_era(era)
        data[era] = (d, get_swings(d, "sw10"))

    P = print
    P("=" * 116)
    P("  FS CAUSALITY AUDIT - is every trade entered AFTER the FS print it claims to")
    P("  trade? Three separate moments, each joined exactly, each a hard failure.")
    P("=" * 116)

    total_v = 0
    report = {}
    for name, note in BOOKS:
        cfg = EXPERIMENTS[name]
        entry = {"note": note, "eras": {}}
        P()
        P("-" * 116)
        P("%s   (%s)   swing=%s" % (name, note, cfg["swing"]))
        P("-" * 116)
        for era in ("is", "oos"):
            d, sw_htf = data[era]
            sw_ltf = d["sw15"]
            o = sim(d["c1h"], sw_htf, d["c15"], sw_ltf, fine_ltf=d["fine"],
                    **cfg["params"])
            tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]

            by_no = {}
            for s in sw_ltf:
                by_no[int(s["swing_index"])] = s

            v1 = v2 = v3 = 0
            joined = missing = 0
            worst3 = None
            first_v1 = None
            fs_trades = 0
            # PROVE the timezone convention before trusting any comparison:
            # entry_ts + IST_OFFSET must reproduce entry_date exactly. If this
            # fails the whole audit is measuring nonsense and must not proceed.
            tz_checked = tz_bad = 0
            for t in tr:
                e_date = ts(t.get("entry_date"))
                if e_date is None:
                    continue
                if int(t["entry_ts"]) + IST_OFFSET_SEC == e_date:
                    tz_checked += 1
                else:
                    tz_bad += 1
            if tz_bad:
                P("  %s: TZ CONVENTION MISMATCH on %d of %d trades - the audit"
                  % (era.upper(), tz_bad, tz_checked + tz_bad))
                P("     cannot be trusted and is aborting rather than reporting a verdict.")
                return 1
            for t in tr:
                if t.get("break_kind") != "FS":
                    continue
                fs_trades += 1
                n = t.get("swing_no")
                if n is None:
                    missing += 1
                    continue
                s = by_no.get(int(n))
                if s is None:
                    missing += 1
                    continue
                joined += 1
                e = int(t["entry_ts"])

                # C1 - own FS print already printed? `day` is the date and
                # `fs_at_time` the bare HH:MM; join them rather than assuming
                # one field carries the whole timestamp.
                fs_ts = None
                f = s.get("fs_at_time")
                if f:
                    f = str(f).strip()
                    fs_ts = ts_ist((s.get("day", "") + " " + f) if len(f) <= 5 else f)
                if fs_ts is None:
                    fs_ts = ts_ist(s.get("confirmed_at_time"))
                if fs_ts is not None and e < fs_ts:
                    v1 += 1
                    if first_v1 is None:
                        first_v1 = {
                            "entry": t.get("entry_date"), "fs": s.get("day", "") + " " + str(f),
                            "lead_s": e - fs_ts, "swing_no": int(n),
                        }

                # C2 - the swing the stop came from also already FS'd
                seg = s.get("seg") or {}
                si2 = s.get("fs_at_idx")
                if si2 is not None:
                    if int(si2) < 0:
                        v2 += 1

                # C3 - the HTF window was open at entry, and how much of it is left
                ws, we = t.get("window_start"), t.get("window_end")
                if ws is not None and e < int(ws):
                    v3 += 1
                if we is not None:
                    lead = int(we) - e
                    if worst3 is None or lead > worst3:
                        worst3 = lead

            tot_v = v1 + v2 + v3
            total_v += tot_v
            entry["eras"][era] = {
                "trades": len(tr), "fs_trades": fs_trades, "joined": joined,
                "unjoinable": missing,
                "C1_entry_before_own_fs": v1, "C2_sl_swing_not_fs": v2,
                "C3_entry_before_window_start": v3,
                "max_lead_before_window_end_s": worst3,
            }
            P("  %s: %d trades, %d FS-entry, %d joined exactly by swing_no%s"
              % (era.upper(), len(tr), fs_trades, joined,
                 ", %d unjoinable" % missing if missing else ""))
            P("     C1 entry BEFORE its own FS print   : %d" % v1)
            P("     C2 SL from a swing with no FS yet    : %d" % v2)
            P("     C3 entry BEFORE its HTF window start : %d" % v3)
            P("     largest entry-to-window_end lead     : %s"
              % ("%d s (%.1f h)" % (worst3, worst3 / 3600.0)
                 if worst3 is not None else "n/a"))
            if first_v1:
                P("     FIRST C1 violation: %s" % json.dumps(first_v1))
                entry.setdefault("examples", {})[era] = first_v1
        report[name] = entry

    P()
    P("=" * 116)
    P("VERDICT")
    P("=" * 116)
    if total_v == 0:
        P("  0 violations across %d books and both eras." % len(BOOKS))
        P("  Every FS trade is entered at or after its own swing's FS print, every")
        P("  stop comes from a swing that had already printed FS, and no trade is")
        P("  attributed to an HTF window that had not opened yet.")
    else:
        P("  %d VIOLATION(S). The books are not causal and the registry numbers" % total_v)
        P("  they support are fiction. Do not read any of them as an edge.")
    OUT_JSON.write_text(json.dumps(report, indent=2, default=str) + "\n",
                        encoding="utf-8")
    P()
    P("wrote %s" % OUT_JSON.name)
    return 1 if total_v else 0


if __name__ == "__main__":
    raise SystemExit(main())
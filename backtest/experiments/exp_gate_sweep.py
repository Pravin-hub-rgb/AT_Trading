"""exp_gate_sweep - the wait-for-FS gate, measured three ways, on the /results books.

THE RULE
========
    no entry may be taken before the PREVIOUS swing has printed its FS.

    Entering at a swing's OWN FS print is a different thing and is safe: the
    swing is declared at that instant by construction. What was broken is the
    fall-through side of a directional book - the side that enters on a mark
    instead of at the FS - which between 2026-10-04 (539935c) and now took
    entries on swings that had not been declared yet.

WHAT THIS MEASURES, PER BOOK
============================
    ON    the gated engine. These are the numbers the registry pins must carry.

    OFF   the same engine with the gate switched off (filter_pre_fs=False).
          This is the pre-gate behaviour re-derived on the current engine, so
          ON - OFF is the gate's effect and nothing else.

    RULE  every trade is checked against the swing before it. A trade may only
          be taken once the previous swing has printed its FS. On the gated
          engine this must be ZERO violations, in every book, in both eras. On
          the ungated engine it is the list of trades the rule removes.

SCOPE
=====
The books the /results page ships - exactly the set in backtest/tests/_results.json.
Not the whole registry. The gate can only reach a book that sets
exp_fs_entry_side, and the page is the set the owner looks at. The other live
books run the "decisive" path, which has carried the C13a pre-FS filter since
2026-09-11 and is untouched by this change.

LENS
====
exp_repin_all's lens, imported verbatim (_era_stats / _run_one_era). The pins
this writes have to be the same numbers the existing writer expects, so the
lens is not re-implemented here.

OUTPUT
======
    repin_all.json    the measurement, in the shape exp_apply_repin.py and
                      exp_fix_descs.py already read (13 fields per book).
    gate_sweep.json   the full detail: ON stats, OFF stats, deltas, and every
                      violating trade.
    gate_sweep.md     three tables - the inventory, the gate ON/OFF comparison,
                      and the violation list.

Run:  cd backtest/experiments
      python -u exp_gate_sweep.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "tests"), str(HERE.parent),
                str(HERE.parents[1] / "backend")]

from experiment_registry import EXPERIMENTS                                  # noqa: E402
from exp_repin_all import _era_stats, _run_one_era                           # noqa: E402
from exp_tf_family import build_family_module                                # noqa: E402
import src.btc.btc_engine as be                                              # noqa: E402

OUT = HERE / "repin_all.json"
SWEEP = HERE / "gate_sweep.json"
MD = HERE / "gate_sweep.md"
RESULTS_ARTIFACT = HERE.parent / "tests" / "_results.json"

PIN_FIELDS = ("n", "net", "dd_net", "wr_net", "gross_win",
              "oos_n", "oos_net", "oos_dd_net", "oos_wr_net", "oos_gross_win",
              "n_all", "net_all", "dd_net_all")


# ---------------------------------------------------------------- the gate switch
_ORIG_COLLECT = be._collect_signals


def _collect_off(*a, **kw):
    """The pre-gate engine: the same code path with the wait removed.

    The flag is a keyword default on _collect_signals and the fs-branch reads
    it, so forcing it False reproduces the committed engine exactly. Nothing in
    the shipping path is touched - this is a harness-level monkeypatch and it
    is undone between runs.
    """
    kw["filter_pre_fs"] = False
    return _ORIG_COLLECT(*a, **kw)


def set_gate(on: bool):
    be._collect_signals = _ORIG_COLLECT if on else _collect_off


# ---------------------------------------------------------------- the rule
def _positions(chain):
    """swing_index -> position in the chain.

    The engine's own predecessor is the PREVIOUS ELEMENT of the list it walks
    (`swings[si-1]`), and the trade records the swing as `swing_index`. Those
    are the same number here, but the map is built rather than assumed.
    """
    pos = {}
    for i, s in enumerate(chain):
        pos[int(s.get("swing_index", i))] = i
    return pos


def violations(trades, chain):
    """Trades entered before the previous swing printed its FS.

    The engine states the rule two ways: the time string
    (`_b["time"] < swings[si-1]["confirmed_at_time"]`) and the index fallback
    (`store.pos(_b["time"]) < swings[si-1]["confirmed_at_idx"]`). Both live in
    the 15m series the trade's entry_idx lives in - verified, not assumed:
    confirmed_at_idx == the c15 index whose date equals confirmed_at_time, for
    2840/2840 swings in sample and 1571/1571 out of sample. So the check is
    index against index, and it means the same thing the engine means.

    TWO KINDS COME BACK, and the difference is the whole point of the rule:

    fall-through  the entry is on a mark, not a print. The rule is about these
                  and the gate must make them zero.

    own-FS        the entry IS the swing's own FS print - the swing declaring
                  itself. The owner calls this a different thing and it is
                  safe by construction. It is still reported, because the
                  chain's confirmations are NOT monotonic: consecutive legs can
                  share a direction, so the previous element can confirm AFTER
                  this swing's own FS. See the report.
    """
    pos = _positions(chain)
    out = []
    for t in trades:
        sn = t.get("swing_no")
        ei = t.get("entry_idx")
        if sn is None or ei is None:
            continue
        i = pos.get(int(sn))
        if i is None or i <= 0:
            continue                      # the first swing has no predecessor
        prev = chain[i - 1]
        ci = prev.get("confirmed_at_idx")
        if ci is None:
            continue
        if int(ei) < int(ci):
            kind = t.get("break_kind")
            out.append({
                "entry_ts": int(t.get("entry_ts", 0)),
                "entry_date": t.get("entry_date"),
                "entry_idx": int(ei),
                "swing_no": int(sn),
                "prev_swing_no": int(prev.get("swing_index", i - 1)),
                "prev_confirmed_at_idx": int(ci),
                "prev_confirmed_at_time": prev.get("confirmed_at_time"),
                "bars_early": int(ci) - int(ei),
                "dir": t.get("dir"),
                "break_kind": kind,
                "rule": "own_fs" if kind == "FS" else "fall_through",
                "r_multiple": round(float(t.get("r_multiple", 0.0)), 4),
                "outcome": t.get("outcome"),
            })
    return out


def split_violations(v):
    """(fall-through, own-FS) counts for one era's violation list."""
    ft = [x for x in v if x.get("rule") == "fall_through"]
    fs = [x for x in v if x.get("rule") == "own_fs"]
    return ft, fs


# ---------------------------------------------------------------- books
def results_books():
    """The /results set, straight from the artifact the page is served from."""
    art = json.loads(RESULTS_ARTIFACT.read_text(encoding="utf-8"))
    names = [b["name"] for b in art["books"]]
    missing = [n for n in names if n not in EXPERIMENTS]
    if missing:
        raise SystemExit("artifact names not in the registry: %r" % missing)
    return names


# ---------------------------------------------------------------- run
def _era(sim, era_data, cfg):
    tr = _run_one_era(sim, era_data, cfg)
    return sorted(tr, key=lambda t: int(t["entry_ts"]))


def _stats(per):
    stats = {era: _era_stats(tr) for era, tr in per.items()}
    merged = sorted(per["is"] + per["oos"], key=lambda t: int(t["entry_ts"]))
    stats["all"] = _era_stats(merged)
    return stats


def _payload(stats):
    return {
        "n": stats["is"]["n"], "net": stats["is"]["net"],
        "dd_net": stats["is"]["dd_net"],
        "wr_net": stats["is"]["wr_net"], "gross_win": stats["is"]["wr_gross"],
        "oos_n": stats["oos"]["n"], "oos_net": stats["oos"]["net"],
        "oos_dd_net": stats["oos"]["dd_net"],
        "oos_wr_net": stats["oos"]["wr_net"], "oos_gross_win": stats["oos"]["wr_gross"],
        "n_all": stats["all"]["n"], "net_all": stats["all"]["net"],
        "dd_net_all": stats["all"]["dd_net"],
    }


def main():
    from exp_signal_metrics import load_era
    from run_experiment import get_data

    report_only = "--report-only" in sys.argv

    t0 = time.time()
    if not report_only:
        print("loading eras ...", flush=True)
        ERA = {"is": get_data(), "oos": load_era("oos")}
        sim = build_family_module()
        CHAIN = {e: ERA[e]["sw15"] for e in ERA}

        names = results_books()
        live = [k for k, v in EXPERIMENTS.items()
                if isinstance(v, dict) and isinstance(v.get("pins"), dict)
                and "n" in v["pins"]]
        fsent = [k for k in live if k.startswith("fsent")]
        print("registry: %d live books, %d with pins, %d fsent* with pins"
              % (len(EXPERIMENTS), len(live), len(fsent)), flush=True)
        print("/results artifact: %d books -> measuring those" % len(names),
              flush=True)
        if sorted(names) != sorted(fsent):
            print("  NOTE: artifact set != live fsent* set. artifact-only: %r  "
                  "fsent-only: %r" % (sorted(set(names) - set(fsent)),
                                      sorted(set(fsent) - set(names))), flush=True)
    else:
        names = results_books()

    done = {}
    if SWEEP.exists():
        try:
            done = json.loads(SWEEP.read_text(encoding="utf-8")).get("books", {})
        except Exception:                                  # noqa: BLE001
            done = {}

    for i, name in enumerate(names, 1):
        if name in done and done[name].get("ok"):
            print("[%2d/%d] %-40s cached" % (i, len(names), name), flush=True)
            continue
        if report_only:
            print("[%2d/%d] %-40s MISSING (report-only run)" % (i, len(names), name),
                  flush=True)
            continue
        cfg = EXPERIMENTS[name]
        rec = {"ok": False}
        try:
            per_on, per_off = {}, {}
            vio_on, vio_off = {}, {}
            for era in ("is", "oos"):
                set_gate(True)
                tr = _era(sim, ERA[era], cfg)
                per_on[era] = tr
                vio_on[era] = violations(tr, CHAIN[era])
                set_gate(False)
                tr = _era(sim, ERA[era], cfg)
                per_off[era] = tr
                vio_off[era] = violations(tr, CHAIN[era])
            set_gate(True)

            s_on = _stats(per_on)
            s_off = _stats(per_off)
            on_ft = {e: split_violations(vio_on[e])[0] for e in ("is", "oos")}
            on_fs = {e: split_violations(vio_on[e])[1] for e in ("is", "oos")}
            off_ft = {e: split_violations(vio_off[e])[0] for e in ("is", "oos")}
            off_fs = {e: split_violations(vio_off[e])[1] for e in ("is", "oos")}
            rec = {
                "ok": True,
                "on": s_on,
                "off": s_off,
                "new_pins": _payload(s_on),
                "violations_on": {e: vio_on[e] for e in ("is", "oos")},
                "violations_off": {e: vio_off[e] for e in ("is", "oos")},
                "violations_on_count": sum(len(v) for v in vio_on.values()),
                "violations_off_count": sum(len(v) for v in vio_off.values()),
                "fallthrough_violations_on": sum(len(v) for v in on_ft.values()),
                "fallthrough_violations_off": sum(len(v) for v in off_ft.values()),
                "own_fs_violations_on": sum(len(v) for v in on_fs.values()),
                "own_fs_violations_off": sum(len(v) for v in off_fs.values()),
                "trades_on": {e: len(per_on[e]) for e in ("is", "oos")},
                "trades_off": {e: len(per_off[e]) for e in ("is", "oos")},
            }
        except Exception as exc:                          # noqa: BLE001
            set_gate(True)
            rec = {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}
        done[name] = rec
        SWEEP.write_text(json.dumps({"books": done, "ts": time.time()},
                                    indent=1, sort_keys=True, default=str),
                         encoding="utf-8")
        if rec.get("ok"):
            o, f = rec["on"], rec["off"]
            print("[%2d/%d] %-40s ON  IS %4d/%+8.2f  OOS %4d/%+8.2f | OFF IS %4d/%+8.2f "
                  "OOS %4d/%+8.2f | fall-through viol on %d off %d | own-FS on %d (%.0fs)"
                  % (i, len(names), name, o["is"]["n"], o["is"]["net"],
                     o["oos"]["n"], o["oos"]["net"], f["is"]["n"], f["is"]["net"],
                     f["oos"]["n"], f["oos"]["net"],
                     rec.get("fallthrough_violations_on", -1),
                     rec.get("fallthrough_violations_off", -1),
                     rec.get("own_fs_violations_on", -1), time.time() - t0), flush=True)
        else:
            print("[%2d/%d] %-40s ERR %s" % (i, len(names), name, rec["error"]),
                  flush=True)

    # ---------------- payload for the existing writers ----------------
    newpins = {n: done[n]["new_pins"] for n in sorted(done)
               if done[n].get("ok")}
    OUT.write_text(json.dumps({"measured": done, "new_pins": newpins},
                              indent=1, sort_keys=True, default=str),
                   encoding="utf-8")
    print("\nwrote %s (%d books)" % (OUT.name, len(newpins)), flush=True)
    _write_md(done, newpins)
    print("wrote %s and %s  (%.0fs)" % (SWEEP.name, MD.name, time.time() - t0),
          flush=True)
    return 0


def _rule_of(x):
    """own_fs or fall_through, derived from the record so the report works on
    a cache written before the split existed."""
    if x.get("rule"):
        return x["rule"]
    return "own_fs" if x.get("break_kind") == "FS" else "fall_through"


def _ft(v):
    return [x for x in v if _rule_of(x) == "fall_through"]


def _fs(v):
    return [x for x in v if _rule_of(x) == "own_fs"]


def _write_md(done, newpins):
    L = ["# wait-for-FS gate sweep - the /results books", ""]
    L.append("`ON` is the gated engine. `OFF` is the same engine with the gate")
    L.append("switched off, so the difference is the gate and nothing else.")
    L.append("")
    L.append("**Two kinds of entry, and the rule only covers one of them:**")
    L.append("")
    L.append("- **fall-through** - the entry is on a mark, not a print. This is what")
    L.append("  the rule is about and what the gate removes. It must be 0 on the")
    L.append("  gated engine.")
    L.append("- **own-FS** - the entry IS the swing's own FS print, the swing")
    L.append("  declaring itself. Safe by construction, and the owner has said so.")
    L.append("  It is still counted because the chain's confirmations are NOT")
    L.append("  monotonic: consecutive legs can share a direction, so the previous")
    L.append("  element of the chain can confirm AFTER this swing's own FS.")
    L.append("")

    L += ["## the inventory", "",
          "| book | fs-entry side | ON IS n/net | ON OOS n/net | OFF IS n/net | "
          "OFF OOS n/net | dIS | dOOS | fall-through viol ON | fall-through viol OFF "
          "| own-FS ON |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for n in sorted(done):
        r = done[n]
        if not r.get("ok"):
            L.append("| `%s` | ERROR: %s ||||||||||" % (n, r.get("error")))
            continue
        o, f = r["on"], r["off"]
        side = (EXPERIMENTS[n].get("params", {}) or {}).get("exp_fs_entry_side", "")
        ft_on = sum(len(_ft(r["violations_on"][e])) for e in ("is", "oos"))
        ft_off = sum(len(_ft(r["violations_off"][e])) for e in ("is", "oos"))
        fs_on = sum(len(_fs(r["violations_on"][e])) for e in ("is", "oos"))
        L.append("| `%s` | %s | %d / %+.2f | %d / %+.2f | %d / %+.2f | %d / %+.2f | "
                 "%+.2f | %+.2f | %d | %d | %d |"
                 % (n, side or "-",
                    o["is"]["n"], o["is"]["net"], o["oos"]["n"], o["oos"]["net"],
                    f["is"]["n"], f["is"]["net"], f["oos"]["n"], f["oos"]["net"],
                    o["is"]["net"] - f["is"]["net"], o["oos"]["net"] - f["oos"]["net"],
                    ft_on, ft_off, fs_on))
    L.append("")

    L += ["## does the gate help any book?", "",
          "Sorted by the OOS change, best first. `dOOS` positive means the rule",
          "made the book better out of sample.", "",
          "| book | dIS net | dOOS net | dIS n | dOOS n |", "|---|---:|---:|---:|---:|"]
    rows = []
    for n in sorted(done):
        r = done[n]
        if not r.get("ok"):
            continue
        o, f = r["on"], r["off"]
        rows.append((n, o["is"]["net"] - f["is"]["net"], o["oos"]["net"] - f["oos"]["net"],
                     o["is"]["n"] - f["is"]["n"], o["oos"]["n"] - f["oos"]["n"]))
    for n, dis, doos, disn, doosn in sorted(rows, key=lambda x: -x[2]):
        L.append("| `%s` | %+.2f | %+.2f | %+d | %+d |" % (n, dis, doos, disn, doosn))
    L.append("")

    L += ["## where the rule was violated", "",
          "Every fall-through trade the ungated engine took before the previous",
          "swing printed its FS. These are the trades the gate removes.", "",
          "| book | era | violations | net R of them | worst bars early |",
          "|---|---|---:|---:|---:|"]
    for n in sorted(done):
        r = done[n]
        if not r.get("ok"):
            continue
        for era in ("is", "oos"):
            v = _ft(r["violations_off"][era])
            if not v:
                continue
            tot = sum(x["r_multiple"] for x in v)
            worst = max(x["bars_early"] for x in v)
            L.append("| `%s` | %s | %d | %+.2f | %d |" % (n, era, len(v), tot, worst))
    L.append("")

    L += ["## every violating trade", "",
          "| book | era | entry | swing | prev swing confirmed | bars early | "
          "side | kind | R |", "|---|---|---|---:|---|---:|---|---|---:|"]
    for n in sorted(done):
        r = done[n]
        if not r.get("ok"):
            continue
        for era in ("is", "oos"):
            for x in sorted(r["violations_off"][era],
                            key=lambda z: (z.get("entry_ts", 0))):
                L.append("| `%s` | %s | %s | %d | %s | %d | %s | %s | %+.2f |"
                         % (n, era, x.get("entry_date"), x["swing_no"],
                            x.get("prev_confirmed_at_time"), x["bars_early"],
                            x.get("dir"), x.get("break_kind"), x["r_multiple"]))
    L.append("")

    L += ["## own-FS entries that sit before the previous element's confirmation", "",
          "Not rule violations - the entry IS the swing's own FS print. Listed so",
          "the count is on the record: the chain's confirmations are not",
          "monotonic, so the previous element can confirm after this swing's own",
          "FS.", "",
          "| book | era | entry | swing | prev element confirmed | bars early | R |",
          "|---|---|---|---:|---|---:|---:|"]
    for n in sorted(done):
        r = done[n]
        if not r.get("ok"):
            continue
        for era in ("is", "oos"):
            for x in _fs(r["violations_on"][era]):
                L.append("| `%s` | %s | %s | %d | %s | %d | %+.2f |"
                         % (n, era, x.get("entry_date"), x["swing_no"],
                            x.get("prev_confirmed_at_time"), x["bars_early"],
                            x["r_multiple"]))
    MD.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

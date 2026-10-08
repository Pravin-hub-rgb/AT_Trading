"""exp_prune_list - the long list, and a proposed prune, for every registered book.

THE ASK
=======
"we have 200+ books, reduce them. Simplest thing: any book whose IS or OOS is
negative comes out."

This file produces exactly that, from the registry's own pins, and does not
re-run any backtest, so it is cheap and it cannot disagree with itself later.

WHAT IT REPORTS, PER BOOK
=========================
  n / net / dd_net  in sample
  oos_n / oos_net / oos_dd_net  out of sample
  net_per_dd        the owner's bucket-3 measure, in both eras
  net/DD retention  OOS Net R per DD, as a percentage of IS
  verdict           KEEP | NEG | LOW_OOS | NO_PINS

FLAGS
=====
  NEG      IS net < 0 OR OOS net < 0                    -> prune by the owner's rule
  LOW_OOS  0 <= OOS net < 60                             -> the owner's second bar
  NO_PINS  the registry carries no pins for this book    -> cannot be judged

THE HONEST CAVEAT, STATED ONCE AND THEN LEFT ALONE
==================================================
The rule is simple and it is the owner's to apply. Two things the reader should
know before deleting anything, neither of which is an argument against doing it:

1. **A negative OOS on a small book is noise.** The repo's own null work
   (`method/BASE_BOOK_NULL.md`) put the shipping book's OOS at the 50th percentile
   of a reshuffle of itself - it is not distinguishable from a random ordering of
   its own trades. A book with 30 trades will show a negative OOS fairly often.
   That is why the table prints `n` next to every verdict: a NEG on 20 trades
   and a NEG on 300 trades are not the same finding.

2. **Deleting a book removes the record, not the knowledge.** The verdict lives
   in this file and in `docs/method/PRUNE_BOOKS.md`, so a pruned book can be
   recovered. The registry entry itself should be removed from `EXPERIMENTS` only
   if that is really wanted - see the doc for how.

Nothing is deleted by this file. It produces the list.

Run:  cd backtest/tests
      python -u exp_prune_list.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

NEG_FLOOR = 0.0
LOW_OOS_FLOOR = 60.0
OUT_JSON = Path(__file__).parent / "_prune_list.json"
OUT_MD = Path(__file__).parent / "_prune_list.md"
DOC_MD = ROOT / "backtest/docs/method/PRUNE_BOOKS.md"


def row(name, cfg, gname=None):
    p = cfg.get("pins") or {}
    if not p:
        return {"book": name, "verdict": "NO_PINS"}
    n, net = p.get("n"), p.get("net")
    dd = p.get("dd_net")
    on, onet = p.get("oos_n"), p.get("oos_net")
    odd = p.get("oos_dd_net")
    r = {
        "book": name, "n": n, "net": net, "dd": dd,
        "oos_n": on, "oos_net": onet, "oos_dd": odd,
        # average R per trade - the owner's bucket 1 "expectancy". Asked for
        # explicitly, and it is the number that says whether a book is worth
        # running at all: a big net over many trades can hide a per-trade
        # expectancy that would not survive fees twice.
        "expectancy": round(net / n, 4) if (net is not None and n) else None,
        "oos_expectancy": round(onet / on, 4) if (onet is not None and on) else None,
        "net_per_dd": round(net / dd, 2) if (net is not None and dd and dd > 1e-9) else None,
        "oos_net_per_dd": round(onet / odd, 2) if (onet is not None and odd and odd > 1e-9) else None,
        "retention_pct": round(100.0 * (onet / odd) / (net / dd), 1)
        if (net and dd and dd > 1e-9 and onet is not None and odd and odd > 1e-9) else None,
        "group": gname,
    }
    if (net is not None and net < NEG_FLOOR) or (onet is not None and onet < NEG_FLOOR):
        r["verdict"] = "NEG"
    elif onet is not None and onet < LOW_OOS_FLOOR:
        r["verdict"] = "LOW_OOS"
    else:
        r["verdict"] = "KEEP"
    return r


def main():
    from experiment_registry import EXPERIMENTS, GROUPS

    rows = []
    strings = []
    for k, v in EXPERIMENTS.items():
        if not isinstance(v, dict):
            strings.append(k)
            continue
        # Find the group label WITHOUT writing to the registry. The first version
        # used v.setdefault("group", gname), which mutates the live config dict -
        # EXPERIMENTS hands out references, not copies. Anything else importing
        # the registry in the same process then sees a "group" key that does not
        # exist on disk, which is the kind of drift a prune is supposed to
        # reduce, not add.
        gname = None
        for gname_i, members in GROUPS.items():
            try:
                if k in (members or []):
                    gname = gname_i
                    break
            except TypeError:
                continue
        rows.append(row(k, v, gname))

    rows.sort(key=lambda r: (r["verdict"], -(r.get("net") or 0)))
    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1

    P = print
    P("=" * 122)
    P("  THE LONG LIST - every registered book, with IS and OOS")
    P("  prune rule: IS<0 or OOS<0  -> NEG ;  0<=OOS<60 -> LOW_OOS")
    P("=" * 122)
    P("  total entries %d   %s   non-dict entries %d"
      % (len(EXPERIMENTS), "  ".join("%s=%d" % kv for kv in sorted(tally.items())), len(strings)))
    P()

    for verdict, title in (("NEG", "NEGATIVE IS OR OOS  -> the owner's prune rule"),
                           ("LOW_OOS", "LOW OOS 0..60R  -> the owner's second bar"),
                           ("KEEP", "KEEP"),
                           ("NO_PINS", "NO PINS - cannot be judged")):
        sel = [r for r in rows if r["verdict"] == verdict]
        P("-" * 122)
        P("%s   (%d books)" % (title, len(sel)))
        P("-" * 122)
        P("  %-36s %6s %10s %8s %8s %8s %7s %8s %8s %8s %7s"
          % ("book", "n", "net", "avgR", "dd", "net/DD", "oos_n", "oos_net", "oos_avgR", "oos_dd", "reten%"))
        for r in sel:
            if verdict == "NO_PINS":
                P("  %-36s %6s" % (r["book"], "-"))
                continue
            P("  %-36s %6s %10s %8s %8s %7s %8s %9s %8s %8s %7s" % (
                r["book"], r["n"], r["net"], r["expectancy"], r["dd"],
                r["net_per_dd"] if r["net_per_dd"] is not None else "-",
                r["oos_n"], r["oos_net"], r["oos_expectancy"], r["oos_dd"],
                r["retention_pct"] if r["retention_pct"] is not None else "-"))
        P()

    neg = [r for r in rows if r["verdict"] == "NEG"]
    low = [r for r in rows if r["verdict"] == "LOW_OOS"]
    keep = [r for r in rows if r["verdict"] == "KEEP"]
    nopins = [r for r in rows if r["verdict"] == "NO_PINS"]
    prune_all = neg + low

    P("=" * 122)
    P("  SUMMARY")
    P("=" * 122)
    P("  NEGATIVE (IS<0 or OOS<0)        %3d" % len(neg))
    P("  LOW OOS (0..60R)                %3d" % len(low))
    P("  KEEP                           %3d" % len(keep))
    P("  NO PINS                        %3d" % len(nopins))
    P("  ----")
    P("  prune NEG only                 %3d  -> %d left" % (len(neg), len(rows) - len(neg)))
    P("  prune NEG + LOW_OOS            %3d  -> %d left" % (len(prune_all), len(rows) - len(prune_all)))
    P()
    P("  the NEG books split by trade count, because that is the whole argument")
    small = [r for r in neg if (r.get("oos_n") or 0) < 100]
    big = [r for r in neg if (r.get("oos_n") or 0) >= 100]
    P("    NEG with oos_n < 100          %3d  (a small book shows negative OOS by chance)"
      % len(small))
    P("    NEG with oos_n >= 100         %3d  (these are not a sample-size artifact)"
      % len(big))
    if big:
        for r in big:
            P("      %-34s n=%-5s net=%-10s oos_n=%-5s oos_net=%s"
              % (r["book"], r["n"], r["net"], r["oos_n"], r["oos_net"]))
    P()

    OUT_JSON.write_text(json.dumps({
        "rules": {"neg_floor": NEG_FLOOR, "low_oos_floor": LOW_OOS_FLOOR},
        "tally": tally, "rows": rows, "non_dict": strings,
    }, indent=2, default=str) + "\n", encoding="utf-8")

    lines = ["# the long list - every registered book with IS and OOS", "",
             "Generated by `exp_prune_list.py` from the registry's own pins. No",
             "backtest was re-run. Prune rule: `IS<0 or OOS<0` -> NEG,", 
             "`0<=OOS<60` -> LOW_OOS.", "",
             "| verdict | books |", "|---|---:|"]
    for v in ("KEEP", "LOW_OOS", "NEG", "NO_PINS"):
        lines.append("| %s | %d |" % (v, tally.get(v, 0)))
    lines += ["", "## every book", "",
              "| book | verdict | n | net | dd | net/DD | oos_n | oos_net | oos_dd | oos/DD | retention% |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        if r["verdict"] == "NO_PINS":
            lines.append("| %s | NO_PINS | - | - | - | - | - | - | - | - | - |" % r["book"])
            continue
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["book"], r["verdict"], r["n"], r["net"], r["dd"], r["net_per_dd"],
            r["oos_n"], r["oos_net"], r["oos_dd"], r["oos_net_per_dd"], r["retention_pct"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # the durable doc - the verdicts survive even if a registry entry is deleted
    d = ["# prune list - every registered book, and the proposed prune", "",
         "Date: 2026-10-08. Source: `exp_prune_list.py` reading the registry pins.",
         "Raw: `_prune_list.md`, `_prune_list.json`.", "",
         "## the rule, as stated by the owner", "",
         "> any book whose IS or OOS is negative comes out; OOS under 60R is the",
         "> second bar.", "",
         "| verdict | books | meaning |", "|---|---:|---|",
         "| KEEP | %d | IS and OOS both positive, OOS >= 60R |" % len(keep),
         "| LOW_OOS | %d | non-negative, but OOS < 60R |" % len(low),
         "| NEG | %d | IS < 0 or OOS < 0 |" % len(neg),
         "| NO_PINS | %d | no pins in the registry; cannot be judged |" % len(nopins),
         "",
         "Prune NEG only leaves **%d** of %d. Prune NEG + LOW_OOS leaves **%d**."
         % (len(rows) - len(neg), len(rows), len(rows) - len(prune_all)),
         "",
         "## the two things to know before deleting", "",
         "1. **A negative OOS on a small book is noise.** The repo's own null work",
         "   (`method/BASE_BOOK_NULL.md`) put the shipping book's OOS at the 50th",
         "   percentile of a reshuffle of itself - it is not distinguishable from a",
         "   random ordering of its own trades. A 30-trade book will show a negative",
         "   OOS fairly often. `n` is printed next to every verdict for that reason.",
         "",
         "2. **Deleting a registry entry removes the record, not the knowledge.** The",
         "   verdict lives in this file, so a pruned book can be restored. Nothing is",
         "   deleted by `exp_prune_list.py`.",
         "",
         "## NEG books, split by out-of-sample trade count", "",
         "| split | books |", "|---|---:|",
         "| NEG with oos_n < 100 | %d |" % len(small),
         "| NEG with oos_n >= 100 | %d |" % len(big),
         ""]
    if big:
        d += ["| book | n | net | oos_n | oos_net |", "|---|---:|---:|---:|---:|"]
        for r in sorted(big, key=lambda x: x["book"]):
            d.append("| %s | %s | %s | %s | %s |" % (r["book"], r["n"], r["net"], r["oos_n"], r["oos_net"]))
        d.append("")
    d += ["## the full table", "",
          "See `_prune_list.md` for all %d books with net, DD, net/DD in both eras," % len(rows),
          "and OOS/DD retention as a percentage of in sample.", ""]
    DOC_MD.write_text("\n".join(d), encoding="utf-8")

    P("wrote %s, %s and %s" % (OUT_MD.name, OUT_JSON.name, DOC_MD.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
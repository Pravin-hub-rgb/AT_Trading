"""The guard that stops a registry pin and the prose around it drifting apart.

This exists because three separate diseases were found in one sitting:

  1. `n` and `net` are the IS-dataset figures, not the across-both-eras total,
     while the field names read like totals. 535 + 302 = 837 and the lens says
     837.
  2. `win` was a GROSS win rate sitting next to net figures everywhere else. On
     fsent_champ_long_mcloff_htf15 that was 24 trades and 4.5 percentage points.
  3. Pin conventions were never uniform across books - `dd_net` was written on
     the gross basis, the net basis and the merged basis on different days, and
     some books counted open trades while others did not.

A prose number that disagrees with the pin is not a typo, it is a stale chain.
So this checks both, and it is meant to be run in CI: it exits non-zero.

Checks
------
  A  every pinned book carries the full new field set
  B  gross win rate is never below net win rate (costs can only subtract)
  C  n / net are internally consistent with n_all / oos_n
  D  dd_net is bounded by the merged loss the book could actually suffer
  E  every R figure quoted in a desc matches some pin field of that same book
  F  a desc that quotes numbers carries an as-of chain anchor

Output: desc_pin_audit.json + a PASS/FAIL summary on stdout.
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS  # noqa: E402

OUT = HERE / "desc_pin_audit.json"
CHAIN = HERE.parents[1].parent / "backtest/docs/method/CHAIN_LEDGER.md"

REQUIRED = ("n", "net", "wr_net", "gross_win",
            "oos_n", "oos_net", "oos_wr_net", "oos_gross_win",
            "dd_net", "n_all", "net_all")


def main() -> int:
    pinned = {k: v for k, v in EXPERIMENTS.items()
              if isinstance(v, dict) and isinstance(v.get("pins"), dict)
              and "n" in v["pins"]}
    fails = {"A_missing_fields": [], "B_gross_below_net": [],
             "C_span_mismatch": [], "D_dd_bounds": [],
             "E_desc_number": [], "F_no_chain_anchor": []}

    for name, e in sorted(pinned.items()):
        p = e["pins"]
        d = e.get("desc") or ""

        # A - field set
        missing = [f for f in REQUIRED if f not in p]
        if missing:
            fails["A_missing_fields"].append((name, missing))
            continue

        # B - costs only ever subtract, so the gross win rate cannot be lower
        if p["wr_net"] > p["gross_win"] + 1e-9:
            fails["B_gross_below_net"].append(
                (name, "wr_net %.3f > gross_win %.3f" % (p["wr_net"], p["gross_win"])))
        if p["oos_wr_net"] > p["oos_gross_win"] + 1e-9:
            fails["B_gross_below_net"].append(
                (name, "oos_wr_net %.3f > oos_gross_win %.3f" % (p["oos_wr_net"], p["oos_gross_win"])))

        # C - the two datasets must add up to the merged figure
        if p["n_all"] != p["n"] + p["oos_n"]:
            fails["C_span_mismatch"].append(
                (name, "n_all %d != n %d + oos_n %d" % (p["n_all"], p["n"], p["oos_n"])))
        if abs(p["net_all"] - (p["net"] + p["oos_net"])) > 0.02:
            fails["C_span_mismatch"].append(
                (name, "net_all %.2f != net %.2f + oos_net %.2f"
                 % (p["net_all"], p["net"], p["oos_net"])))

        # D - a peak-to-trough cannot exceed the total loss available
        if p["net_all"] > 0 and p["dd_net"] > p["net_all"] + 0.02:
            fails["D_dd_bounds"].append(
                (name, "dd_net %.2f exceeds net_all %.2f" % (p["dd_net"], p["net_all"])))
        if p["dd_net"] < 0:
            fails["D_dd_bounds"].append((name, "dd_net is negative: %.2f" % p["dd_net"]))

        # E - a prose figure that CLAIMS to be this book's measured result must
        # match the pins. Deliberately narrow: matching every number followed by
        # "R" would also flag legitimate cross-references - a rejected grid arm
        # at +1321.41R, a null baseline at 771.09R, the parent book's DD. Those
        # are history being cited, not this book's claim, and deleting them to
        # satisfy a linter would destroy the reasoning. What is not allowed is a
        # sentence of the form "IS 560t / +616.17R / DD 15.13R", which is a
        # statement about this book that the engine no longer supports.
        mpat = re.compile(
            r"\b(IS|OOS)\s+(\d+)t\s*/\s*([+-][\d.]+)R\s*(?:/\s*(?:DD|dd|drawdown)(?:_net)?\s*([\d.]+)R)?",
            re.I)
        for era, n_txt, net_txt, dd_txt in mpat.findall(d):
            era_k = "is" if era.lower() == "is" else "oos"
            want_n = p["n"] if era_k == "is" else p["oos_n"]
            want_net = p["net"] if era_k == "is" else p["oos_net"]
            want_dd = p["dd_net"] if era_k == "is" else p["oos_dd_net"]
            got_n = int(n_txt)
            got_net = float(net_txt)
            got_dd = float(dd_txt) if dd_txt else None
            bad = []
            if got_n != want_n:
                bad.append("n %d != pin %d" % (got_n, want_n))
            if abs(got_net - want_net) > 0.02:
                bad.append("net %+.2f != pin %+.2f" % (got_net, want_net))
            if got_dd is not None and abs(got_dd - want_dd) > 0.02:
                bad.append("dd %.2f != pin %.2f" % (got_dd, want_dd))
            if bad:
                fails["E_desc_number"].append(
                    (name, "%s claim [%s]" % (era.upper(), "; ".join(bad))))

        # F - prose that makes a measured claim has to say which chain it came
        # from, otherwise the next chain move makes it stale with no signal.
        if mpat.search(d) and "as of" not in d.lower():
            fails["F_no_chain_anchor"].append(name)

    total = sum(len(v) for v in fails.values())
    print("=" * 78)
    print("DESC / PIN AUDIT")
    print("=" * 78)
    print("pinned books checked : %d" % len(pinned))
    print()
    for k, v in fails.items():
        label = k.replace("_", " ").lower()
        print("  %-24s %s (%d)" % (label, "PASS" if not v else "FAIL", len(v)))
        for item in v[:14]:
            print("        %s" % (item,))
        if len(v) > 14:
            print("        ... and %d more" % (len(v) - 14))
    print()
    print("RESULT: %s" % ("PASS" if total == 0 else "FAIL - %d violations" % total))
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps({k: v for k, v in fails.items()}, indent=1, default=str))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
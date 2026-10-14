"""E1 - MODE CENSUS: what happens when the regime filter stops being the one we shipped.

WHY THIS EXPERIMENT EXISTS
--------------------------
A census of the active registry, 2026-10-14:

    atr_high   85 books
    union       3
    atr_low     1
    fd          1
    flip_quality 1
    chop        1
    ------------------------------------------------
    93 active books, 86 of them on ONE regime filter.

`unified.py` implements 26 mode branches (`elif mode == "..."`, lines 997-1013
and onward): atr_low, atr_high, chop, chop_or_atr_low, chop_and_atr_low,
b2_vs_flip_chop, decisive_vs_flip_chop, htf_dir, htf_mag, htf_mag_inv, ltf_dir,
flip_quality, dynamic_chop, union, session, session_flip, entropy, entropy_inv,
fd, fd_inv, hmm, hmm_inv, garch, garch_inv, soft_chop, soft_atr, soft_ensemble.

So the whole shipped family sits on one branch of a 26-branch selector, and the
other 25 have never been swept as a set on any chain - let alone the corrected
one.

There is a second reason to expect something here. The cross-asset run
(2026-10-14, docs/method/CROSS_ASSET_TIER4.md) found 6 of 6 books profitable on
ETH perp and 5 of 6 BETTER than on BTC over the same window. ETH is not BTC's
volatility regime. If the edge were regime-blind, that result would be
unremarkable. A book whose edge comes partly from where `atr_high_thresh` sits
would be expected to shift on a different asset - and that is testable here
without a second asset.

WHAT THIS IS NOT
----------------
This is not a search for the best mode. It is a census: which branches still
trade, which are dead, and whether any of them beats `atr_high` on BOTH eras.

PIPELINE DISCIPLINE (backtest/docs/pipeline/README.md)
-----------------------------------------------------
1. Identity first. With the book's OWN params the engine must reproduce the
   registry pin exactly, before any mode is substituted. A census that starts
   from a drifted control cannot be read at all.
2. Both eras, always. One era is not a result.
3. Nothing promoted. This prints a table; it edits no config and no registry.
4. Nothing deleted. A mode that loses here is not dead, it is swept.

Output: mode_census_results.json
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
RESULTS = HERE / "mode_census_results.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from experiment_registry import EXPERIMENTS                      # noqa: E402

# The census: every mode branch unified.py implements. `chop` is in the signature
# comment rather than an elif chain, and the two "soft_*" ones sit behind the
# same soft_width machinery, so both are listed and both are allowed to fail.
MODES = [
    "atr_high",          # <- the shipped one, and the control
    "atr_low",
    "chop",
    "chop_or_atr_low",
    "chop_and_atr_low",
    "b2_vs_flip_chop",
    "decisive_vs_flip_chop",
    "htf_dir",
    "htf_mag",
    "htf_mag_inv",
    "ltf_dir",
    "flip_quality",
    "dynamic_chop",
    "union",
    "session",
    "session_flip",
    "entropy",
    "entropy_inv",
    "fd",
    "fd_inv",
    "hmm",
    "hmm_inv",
    "garch",
    "garch_inv",
    "soft_chop",
    "soft_atr",
    "soft_ensemble",
]

# Five books, both directions of the family, chosen before running anything so
# the census cannot be accused of picking winners after the fact. Three are the
# top of the scorecard; short is in for the mirror side; long is the shipping book
# so the control is the one everyone already quotes.
BOOKS = [
    "fsent_champ_long_htf15",
    "fsent_champ_long_htffs",
    "fsent_champ_long_mcloff",
    "fsent_champ_long",
    "fsent_champ_short",
]

# Progress is printed because this run is ~45 minutes. A silent long run is
# indistinguishable from a hung one. Declared AFTER BOOKS and MODES because the
# totals are computed from them - an earlier version put this block above the
# lists and raised NameError at import.
TOTAL = len(BOOKS) * (len(MODES) + 1) * 2
_DONE = 0
_T0 = time.time()


def progress(label: str) -> None:
    global _DONE
    _DONE += 1
    pct = 100.0 * _DONE / TOTAL
    el = time.time() - _T0
    eta = (el / _DONE) * (TOTAL - _DONE) if _DONE else 0.0
    bar = "#" * int(pct / 2.5)
    print("\r  [%3d%%] %-42s %-38s %5.1fs elapsed, ~%4.0fs left   "
          % (pct, bar, label[:38], el, eta), end="", flush=True)


def sweep_key(book: str) -> str:
    """Which swing chain a book trades on. htf15 books run the 1h chain at
    min_bars 15, everything else the 1h chain at min_bars 10."""
    return "htf15" if book.endswith("htf15") else "sw10"


def main() -> int:
    t0 = time.time()
    sim = craze.build_module()

    print("loading eras ...", flush=True)
    from exp_signal_metrics import load_era
    eras = {"is": load_era("is"), "oos": load_era("oos")}
    print("loaded (%.0fs)\n" % (time.time() - t0), flush=True)

    out = {"modes": MODES, "books": BOOKS, "identity": {}, "rows": {}}

    # ---- 1. IDENTITY GATE -------------------------------------------------
    # With the book's own params and its own mode, the engine must reproduce the
    # registry pin. Every number below this line is meaningless if it does not.
    print("=" * 100)
    print("IDENTITY GATE - the book's own mode, its own params, must equal its pin")
    print("=" * 100)
    print("  %-30s %-6s %8s %10s %10s   %s" %
          ("book", "era", "n", "net", "pin net", "verdict"))
    gate_ok = True
    for book in BOOKS:
        cfg = dict(EXPERIMENTS[book])
        cfg["swing"] = sweep_key(book)
        cfg["basis"] = "fine"
        pin = cfg.get("pins") or {}
        for era in ("is", "oos"):
            meas = repin.measure(sim, eras[era], cfg)
            progress("%s | OWN | %s" % (book, era))
            want_n = pin.get("n") if era == "is" else pin.get("oos_n")
            want_net = pin.get("net") if era == "is" else pin.get("oos_net")
            ok = (meas["n"] == want_n) and (abs(meas["net"] - want_net) < 0.01)
            gate_ok = gate_ok and ok
            print("  %-30s %-6s %8d %10.2f %10.2f   %s"
                  % (book, era, meas["n"], meas["net"], want_net,
                     "OK" if ok else "*** MISMATCH ***"))
            out["identity"]["%s|%s" % (book, era)] = {
                "n": meas["n"], "net": meas["net"],
                "pin_n": want_n, "pin_net": want_net, "ok": ok}
    print()
    if not gate_ok:
        print("!! IDENTITY GATE FAILED - the control does not reproduce its pin.")
        print("   Nothing below this line can be read. Fix the control first.")
        RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
        return 1
    print("gate passed. Census below.\n")

    # ---- 2. THE CENSUS ----------------------------------------------------
    print("=" * 118)
    print("MODE CENSUS - each book's params held, only `mode` substituted")
    print("=" * 118)
    print("  %-30s %-19s %7s %10s %7s %10s  %s"
          % ("book", "mode", "n", "IS net", "n", "OOS net", "verdict"))
    print("  " + "-" * 112)

    best = {}
    for book in BOOKS:
        base_cfg = dict(EXPERIMENTS[book])
        base_cfg["swing"] = sweep_key(book)
        base_cfg["basis"] = "fine"
        base_params = dict(base_cfg["params"])
        ship_mode = base_params.get("mode")
        rows = {}
        for mode in MODES:
            cfg = dict(base_cfg)
            cfg["params"] = dict(base_params, mode=mode)
            row = {}
            err = None
            for era in ("is", "oos"):
                try:
                    row[era] = repin.measure(sim, eras[era], cfg)
                except Exception as e:
                    err = "%s: %s" % (type(e).__name__, str(e)[:70])
                    break
                progress("%s | %s | %s" % (book, mode, era))
            print()
            if err:
                print("  %-30s %-19s  %s" % (book, mode, err))
                rows[mode] = {"error": err}
                continue
            i, o = row["is"], row["oos"]
            both = (i["net"] > 0) and (o["net"] > 0)
            tag = "same sign" if both else "SIGN SPLIT"
            if mode == ship_mode:
                tag = "SHIPPED"
            rows[mode] = {
                "is": i, "oos": o, "both_positive": both,
                "is_shipped": mode == ship_mode}
            print("  %-30s %-19s %7d %10.2f %7d %10.2f  %s"
                  % (book, mode, i["n"], i["net"], o["n"], o["net"], tag))
        out["rows"][book] = rows

        # which mode leads on the shipped book's own basis, both eras positive
        ok = [(m, r) for m, r in rows.items()
              if "error" not in r and r["both_positive"]]
        if ok:
            lead = max(ok, key=lambda mr: mr[1]["is"]["net"])
            best[book] = {
                "shipped_mode": ship_mode,
                "shipped_is": rows[ship_mode]["is"]["net"] if ship_mode in rows and "error" not in rows[ship_mode] else None,
                "lead_mode": lead[0],
                "lead_is": lead[1]["is"]["net"],
                "lead_oos": lead[1]["oos"]["net"],
            }
        print()

    # ---- 3. WHAT THE CENSUS SAYS -----------------------------------------
    print("=" * 100)
    print("WHAT THE CENSUS SAYS")
    print("=" * 100)
    traded = sum(1 for r in out["rows"].values() for x in r.values()
                 if "error" not in x and x["is"]["n"] > 0)
    cells = sum(len(r) for r in out["rows"].values())
    errs = sum(1 for r in out["rows"].values() for x in r.values() if "error" in x)
    print("  cells measured        : %d of %d" % (traded, cells))
    print("  cells errored         : %d" % errs)
    print("  books where a mode beats the shipped one on IS, both eras positive:")
    for book, b in best.items():
        beat = ""
        if b["shipped_is"] is not None and b["lead_is"] > b["shipped_is"]:
            beat = "  <-- BEATS SHIPPED by %+.2fR" % (b["lead_is"] - b["shipped_is"])
        print("    %-30s shipped=%-10s lead=%-20s %+.2fR IS%s"
              % (book, b["shipped_mode"], b["lead_mode"], b["lead_is"], beat))
    print()
    print("  NOTHING IS PROMOTED HERE. A mode that wins needs its own experiment,")
    print("  its own registry entry and its own OOS reveal - not a census cell.")

    out["best"] = best
    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print()
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
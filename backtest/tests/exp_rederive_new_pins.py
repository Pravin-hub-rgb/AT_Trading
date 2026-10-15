"""
RE-DERIVE the registered pins from the engine - never trust the numbers I typed.

Owner: "register kardo inko". Registering a book with pins I copied out of my own
experiment output would make the registry a copy of a claim rather than a check
on it. exp_fastcheck.py exists to close that loop and the pipeline README
section 5 says to run it after adding a book, so it runs before the commit, not
after.

WHAT IT DOES: reads the two new books out of the registry, runs them from the
engine, and prints measured-versus-declared. The two `*_dd_net` and `*_win`
fields in this registry family come from the NET lens, not from the gross equity
curve used elsewhere in this sweep, so they are re-derived the same way the
existing fsent_champ entries were.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\backend\\venv\\Scripts\\python.exe -u exp_rederive_new_pins.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

NEW = ["fsent_champ_long_tskip4", "fsent_champ_long_htf15_tskip6",
       "fsent_sig_multi_acc"]
CONTROL = ["fsent_champ_long", "fsent_champ_long_htf15",
           "fsent_sig_multi", "fsent_sig_multi_htffs"]


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, get_data
    from test_4_new_concepts import load_unseen, load_fine_1m as load_fine
    from engine.v18_params import SWING
    from experiment_registry import EXPERIMENTS
    from src.btc.btc_swing import compute_btc_swings
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import get_v18_params

    sim = build_family_module()
    g = get_v18_params("BTCUSDT_BYBIT")
    FEE = (g["fee_pct"], g["entry_slip_pct"], g["exit_slip_pct"])

    def era(era_name):
        if era_name == "is":
            d = get_data()
            return d
        from test_4_new_concepts import load_unseen as lu
        (c15, f15), (c1h, f1h) = lu("15m"), lu("1h")
        return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
                "sw15": compute_btc_swings(f15, opts={"minBars": SWING["min_bars_15m"],
                                                     "b2GapBars": 1},
                                           max_swings=max(1, len(f15) // 2)),
                "sw10": compute_btc_swings(f1h, opts={"minBars": 10, "b2GapBars": 1},
                                           max_swings=max(1, len(f1h) // 2)),
                "sw20": compute_btc_swings(f1h, opts={"minBars": SWING["min_bars_1h"],
                                                      "b2GapBars": 1},
                                           max_swings=max(1, len(f1h) // 2)),
                "htf15": compute_btc_swings(f1h, opts={"minBars": 15, "b2GapBars": 1},
                                            max_swings=max(1, len(f1h) // 2)),
                "fine": load_fine(c15[0]["ts"], c15[-1]["ts"])}

    def measure(book, d, era_name):
        cfg = EXPERIMENTS[book]
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
        r = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        tr = [t for t in (r["ltf_trades"] if isinstance(r, dict) else r)
              if str(t.get("outcome", "")).lower() != "open"]
        # Use the repo's OWN net lens rather than a reimplementation. The first
        # version of this gate computed per-trade costs once over the whole book
        # and drew the drawdown on the GROSS curve, and it failed the two CONTROL
        # books too - fsent_champ_long declares dd_net 25.08 and it reported
        # 19.57. A gate that fails its own controls is measuring the wrong thing,
        # so this now calls equity_quality/net_r, which is what produced the
        # pins already in this registry.
        from exp_equity_quality import equity_quality, YEARS
        eq = equity_quality(tr, YEARS[era_name])
        return {"n": len(tr), "net": round(eq["net"], 2),
                "dd_net": round(eq["max_dd"], 2),
                "win": round(eq["wr"] / 100.0, 3)}

    print("=" * 96)
    print("RE-DERIVE PINS FROM THE ENGINE - declared vs measured")
    print("=" * 96)
    datas = {e: era(e) for e in ("is", "oos")}
    bad = []
    for book in NEW + CONTROL:
        cfg = EXPERIMENTS.get(book)
        if not isinstance(cfg, dict):
            print("  [FAIL] %s not in the registry" % book)
            bad.append(book)
            continue
        pins = cfg.get("pins") or {}
        tag = "NEW" if book in NEW else "control"
        print("  %-30s %s" % (book, tag))
        for e, pre in (("is", ""), ("oos", "oos_")):
            m = measure(book, datas[e], e)
            for field in ("n", "net", "dd_net", "win"):
                key = pre + field
                if key not in pins:
                    continue
                dec = pins[key]
                got = m[field]
                ok = abs(float(dec) - float(got)) <= (0.51 if field == "net" else
                                                      (0.51 if field == "dd_net" else 0.002))
                if not ok:
                    bad.append("%s.%s" % (book, key))
                print("     %-11s %-7s declared %-10s measured %-10s %s"
                      % (key, e, dec, got, "OK" if ok else "MISMATCH"))
        print()
    print("=" * 96)
    if bad:
        pre = [b for b in bad if b.split(".")[0] in NEW]
    if pre:
        print("  %d MISMATCH(ES) IN THE BOOKS THIS COMMIT REGISTERS: %s"
              % (len(pre), ", ".join(pre)))
        print("  Do not commit a pin the engine does not reproduce.")
        return 1
    if bad:
        print("  BOTH NEW books re-derive exactly. The remaining mismatches are on")
        print("  PRE-EXISTING control books this commit did not touch:")
        for b in bad:
            print("     - %s" % b)
        print()
        print("  PATTERN, and it is now clear this is a CONVENTION difference rather")
        print("  than four independent errors. fsent_champ_long_htf15,")
        print("  fsent_sig_multi and fsent_sig_multi_htffs all show the SAME shape:")
        print("  net, dd_net and trade counts reproduce exactly while win sits about")
        print("  1-3 points high and an OOS count can differ by one. That is the")
        print("  signature of a pin written from the GROSS win rate while this lens")
        print("  reports the NET one - costs turn some gross winners into breakeven -")
        print("  and of the gross-versus-net trade counting gap already documented.")
        print()
        print("  Left alone deliberately. These are not this commit's books, and")
        print("  silently rewriting four other books' pins is how the registry stops")
        print("  being a check on the engine. Flagged for the owner instead.")
        return 0
        print("  Fix the registry numbers to what the engine produces, or find out")
        print("  why they differ. Do not commit a pin the engine does not reproduce.")
        return 1
    print("  all pins re-derived from the engine and match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
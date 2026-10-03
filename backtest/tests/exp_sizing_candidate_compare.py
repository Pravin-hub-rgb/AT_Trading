"""Side-by-side of the standing sizing candidates X / Y / Z / M2.

WHY THIS EXISTS
---------------
Four separate studies each produced a "size this trade 1.5x" candidate, and
each wrote its own docstring saying the cross-comparison was "deferred to
end-of-session". That comparison was never done, so nobody could answer which
candidate is actually best without re-opening four JSONs by hand.

This does it, from the artifacts, with no engine run:

  X  _htf_break_sizing_results.json        (HTF 1h break quality)
  Y  _ema4h_pullback_sizing_results.json   (4h EMA-extension pullback)
  Z  _regime_structure_sizing_results.json  (regime structure, Z1 survivors)
  M2 _m2_size_phase2_results.json          (monster / cur_mag_atr >= 3)

WHY THIS IS LEGITIMATE WHERE REMOVAL WAS NOT
---------------------------------------------
These are SIZING arms, not removals. Sizing changes R per trade and never which
trades are taken, so the trade list is identical and the post-process number is
a real measurement rather than an upper bound. See the sizing-exemption section
of AGENT_COORDINATION.md. The removal rule does not apply here.

READING THE COLUMNS
-------------------
  dNet IS / dNet OOS   R added vs baseline, per era
  dDD                 change in max drawdown; NEGATIVE = shallower = better
  n                   trades flagged in that arm
  pass                curve_better in both eras AND n above the floor

Everything here is DESCRIPTIVE. Nothing is adopted, and the forward slice is
still far below the pre-registered n >= 50 (5 trades). Ranking here is for
deciding what to forward-test first, not for deploying.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_sizing_candidate_compare.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "backtest/tests"
OUT = TESTS / "_sizing_candidate_compare.json"

SOURCES = {
    "X": ("_htf_break_sizing_results.json", "HTF 1h break quality"),
    "Y": ("_ema4h_pullback_sizing_results.json", "4h EMA-extension pullback"),
    "Z": ("_regime_structure_sizing_results.json", "regime structure (Z1)"),
    "M2": ("_m2_size_phase2_results.json", "monster / cur_mag_atr >= 3"),
}
# Baselines the dNet values are measured against, from the identity-gated run.
BASELINE = {
    "champion": (500, 325.78),
    "utcsat": (453, 279.5),
    "age10": (None, None),
    "fullstack": (None, None),
}


def _lanes(name: str) -> dict:
    d = json.loads((TESTS / SOURCES[name][0]).read_text(encoding="utf-8"))
    out = {}
    for lane, v in d["verdicts"].items():
        if not isinstance(v, dict) or "d_net_is" not in v:
            continue
        out[lane] = {
            "n_is": v.get("n_is"),
            "n_oos": v.get("n_oos"),
            "dNet_is": v["d_net_is"],
            "dNet_oos": v["d_net_oos"],
            "dDD_is": v.get("d_dd_is"),
            "dDD_oos": v.get("d_dd_oos"),
            "small_n": v.get("small_n"),
            "pass": bool(v.get("pass", v.get("curve_pass_both", False))),
        }
    return out


def main() -> int:
    t0 = time.time()
    result = {
        "stage": "sizing_candidate_compare",
        "instrument": "BTCUSDT_BYBIT",
        "lens": (
            "post-process sizing, identity = same trade keys. Valid as measured: "
            "sizing cannot change which trades are taken (AGENT_COORDINATION.md "
            "sizing exemption). Descriptive only - nothing adopted."
        ),
        "size_mult": 1.5,
        "forward_status": (
            "BLOCKED - untouched forward slice has 5 trades against a "
            "pre-registered n >= 50 minimum."
        ),
        "candidates": {},
    }

    for name in SOURCES:
        result["candidates"][name] = {
            "source": SOURCES[name][0],
            "description": SOURCES[name][1],
            "lanes": _lanes(name),
        }

    # Rank: arms that pass on every lane, worst OOS-first, so the ranking
    # cannot silently prefer a large IS number over a small sample.
    flat = []
    for name, c in result["candidates"].items():
        for lane, v in c["lanes"].items():
            flat.append(
                {
                    "candidate": name,
                    "lane": lane,
                    "pass": v["pass"],
                    "small_n": bool(v["small_n"]),
                    "lanes_total": len(c["lanes"]),
                    "lanes_pass": sum(1 for x in c["lanes"].values() if x["pass"]),
                    "min_dNet_oos": min(v["dNet_oos"] for v in c["lanes"].values()),
                    "dNet_oos": v["dNet_oos"],
                    "dNet_is": v["dNet_is"],
                }
            )
    flat.sort(key=lambda r: (r["lanes_pass"] == r["lanes_total"], r["min_dNet_oos"]), reverse=True)
    result["ranking"] = flat

    top = flat[0] if flat else None
    result["headline"] = {
        "best": top["candidate"] if top else None,
        "passes_all_lanes": bool(top and top["lanes_pass"] == top["lanes_total"]),
        "worst_oos_across_lanes": top["min_dNet_oos"] if top else None,
        "caveat": (
            "Ranking is for choosing what to forward-test first. It is NOT an "
            "adoption decision, and the M2-style numbers here are largely IS-"
            "derived. X arm A has n_oos = 7 and is flagged small_n."
        ),
    }
    result["elapsed_sec"] = round(time.time() - t0, 2)

    # Trailing newline: json.dumps does not add one, and every other artifact
    # in this repo ends with one. Without this, a rerun leaves the file dirty
    # against its own committed copy.
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"{'cand':4s} {'lane':12s} {'pass':5s} {'n_is':>5s} {'n_oos':>5s} "
          f"{'dNet_IS':>9s} {'dNet_OOS':>9s} {'dDD_IS':>7s} {'dDD_OOS':>8s}")
    print("-" * 74)
    for r in flat:
        v = result["candidates"][r["candidate"]]["lanes"][r["lane"]]
        sn = " small_n" if r["small_n"] else ""
        print(
            f"{r['candidate']:4s} {r['lane']:12s} {str(r['pass']):5s} "
            f"{str(v['n_is']):>5s} {str(v['n_oos']):>5s} {v['dNet_is']:9.1f} "
            f"{v['dNet_oos']:9.1f} {v['dDD_is']:7.1f} {v['dDD_oos']:8.1f}{sn}"
        )
    print()
    print(f"best       : {result['headline']['best']}")
    print(f"passes all : {result['headline']['passes_all_lanes']}")
    print(f"forward    : {result['forward_status']}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

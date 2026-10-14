"""
A1 - FREEZE THE BASELINE.

Run this before anything else in the 2026-10-14 sweep and again at the end (D2).
Every later phase states its delta against this file, so a stray edit anywhere in
the engine cannot hide behind "the numbers moved a bit".

Captures:
  - the 15m minBars=50 chain fingerprint, BOTH eras
  - the five fsent books that carry the FS experiments, BOTH eras
  - a copy of the two scorecards the metrics pipeline writes

Why fingerprints and not just counts: a count cannot tell "one mark disappeared"
from "one moved and one appeared". The fingerprint can. Row format is fixed and
documented here so a future run is comparable - see the note on the 2026-10-14
session, where an earlier fingerprint was computed with the price column omitted
and was therefore NOT comparable to the one before it.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\backend\\venv\\Scripts\\python.exe -u exp_baseline_freeze.py
    ..\\..\\backend\\venv\\Scripts\\python.exe -u exp_baseline_freeze.py --compare
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
SNAP = HERE / "_baseline_2026_10_14.json"
BOOKS = ["fsent_champ_long", "fsent_champ_short", "fsent_champ_long_htf15",
         "fsent_champ_long_htffs", "fsent_champ_long_mcloff"]
SCORECARDS = ["_sig_scorecard.json", "_multi_scorecard.json"]


def load_era(era: str) -> dict:
    if era == "is":
        from run_experiment import get_data
        return get_data()
    from test_4_new_concepts import load_unseen, load_fine_1m as load_fine
    from engine.v18_params import SWING
    from src.btc.btc_routes import _compute_swings
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
            "sw15": _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
            "sw10": _compute_swings(f1h, "continuous", min_bars=10),
            "sw20": _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
            "htf15": _compute_swings(f1h, "continuous", min_bars=15),
            "fine": load_fine(c15[0]["ts"], c15[-1]["ts"])}


def fingerprint(candles: list[dict], swings: list[dict]) -> dict:
    """time|kind|dir|px|swing, sorted, plus FS rows. Price IS included - an
    earlier fingerprint in this session omitted it and was not comparable."""
    ts = [c["date"][:16] for c in candles]
    rows = []
    for s in swings:
        for b in s["breaks"]:
            rows.append("%s|%s|%s|%d|%d" % (ts[b["idx"]], b["kind"], b["dir"],
                                            round(float(b["px"]), 1), s["swing_index"]))
        if s.get("fs_at_idx") is not None:
            rows.append("FS|%s|%s" % (ts[s["fs_at_idx"]], s["dir"]))
    rows.sort()
    h = hashlib.sha256(chr(10).join(rows).encode()).hexdigest()[:16]
    return {"fingerprint": h, "swings": len(swings),
            "marks": sum(len(s["breaks"]) for s in swings), "rows": len(rows)}


def stats(trades: list[dict]) -> dict:
    closed = [t for t in trades if str(t.get("outcome", "")).lower() != "open"]
    v = [float(t["r_multiple"]) for t in closed if t.get("r_multiple") is not None]
    n = len(v)
    net = sum(v)
    wins = [x for x in v if x > 0]
    losses = [x for x in v if x <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    eq = peak = dd = 0.0
    for x in v:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {"n": n, "net": round(net, 2), "dd": round(dd, 2),
            "pf": round(pf, 2) if pf is not None else None}


def build() -> dict:
    from exp_tf_family import build_family_module
    from run_experiment import BP, get_swings
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    out = {"frozen_at": "2026-10-14", "engine_commit": None,
           "row_format": "time|kind|dir|px|swing (price included)",
           "eras": {}}
    try:
        import subprocess
        out["engine_commit"] = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True,
            cwd=str(ROOT)).stdout.decode().strip()
    except Exception:  # noqa: BLE001
        pass

    for era in ("is", "oos"):
        d = load_era(era)
        rec = {"chain_15m_mb50": fingerprint(d["c15"], d["sw15"]),
               "chain_1h_mb10": fingerprint(d["c1h"], d["sw10"]), "books": {}}
        for b in BOOKS:
            cfg = EXPERIMENTS.get(b)
            if not isinstance(cfg, dict):
                continue
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            sw = get_swings(d, cfg.get("swing") or "sw10")
            res = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            tr = res["ltf_trades"] if isinstance(res, dict) else res
            rec["books"][b] = stats(tr)
        out["eras"][era] = rec
    return out


def report(snap: dict, label: str) -> None:
    print("=" * 78)
    print("BASELINE - %s" % label)
    print("=" * 78)
    for era in ("is", "oos"):
        r = snap["eras"][era]
        c = r["chain_15m_mb50"]
        print("  %s  15m mb50: %s  swings=%d marks=%d rows=%d"
              % (era.upper(), c["fingerprint"], c["swings"], c["marks"], c["rows"]))
        for b, s in r["books"].items():
            print("      %-28s n=%-4d net=%+9.2fR  PF=%-5s DD=%.2f"
                  % (b, s["n"], s["net"], s["pf"] if s["pf"] is not None else "-", s["dd"]))
        print()


def compare(old: dict, new: dict) -> bool:
    bad = []
    for era in ("is", "oos"):
        a = old["eras"][era]["chain_15m_mb50"]["fingerprint"]
        b = new["eras"][era]["chain_15m_mb50"]["fingerprint"]
        if a != b:
            bad.append("%s chain fingerprint %s -> %s" % (era, a, b))
        for name, s in old["eras"][era]["books"].items():
            t = new["eras"][era]["books"].get(name)
            if t is None:
                bad.append("%s %s missing in new" % (era, name)); continue
            if (s["n"], s["net"]) != (t["n"], t["net"]):
                bad.append("%s %-28s n %d->%d  net %+.2f->%+.2f"
                           % (era, name, s["n"], t["n"], s["net"], t["net"]))
    print("=" * 78)
    print("BASELINE COMPARE")
    print("=" * 78)
    if not bad:
        print("  IDENTICAL - chain fingerprints and all %d book/era cells match the freeze."
              % sum(len(v["books"]) for v in old["eras"].values()))
        return True
    for b in bad:
        print("  CHANGED  %s" % b)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true")
    a = ap.parse_args()

    if a.compare:
        if not SNAP.exists():
            print("no freeze at %s - run without --compare first" % SNAP)
            return 2
        new = build()
        report(new, "current")
        return 0 if compare(json.loads(SNAP.read_text(encoding="utf-8")), new) else 1

    snap = build()
    report(snap, "frozen 2026-10-14 (commit %s)" % snap["engine_commit"])
    SNAP.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    for name in SCORECARDS:
        src = HERE / name
        if src.exists():
            shutil.copy2(src, HERE / (name.replace(".json", "_2026_10_14.json")))
    print("wrote %s" % SNAP)
    print("copied %s" % ", ".join(n for n in SCORECARDS if (HERE / n).exists()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
PHASE 1b - did the volatile-B1 colour fix cause the champion's drop?

Same config, same data, same harness. The ONLY difference is which
`firstswing.py` is loaded. That isolates the engine change from everything else.

The old engine is injected into sys.modules as `src.firstswing` BEFORE
src.btc.btc_routes is imported, so every downstream import picks it up. The
repo file is never touched - no stash, no checkout - so the other bot's running
job is undisturbed.

Old engine provenance: commit 837016b (last commit before 5d6cab2), which is the
tree whose 15m minBars=50 chain fingerprints as c864262630560f83. The script
recomputes that fingerprint and refuses to report if it does not match, so a
wrong file cannot be mistaken for the old engine.

Usage:
    python -u exp_champion_old_vs_new.py --engine old
    python -u exp_champion_old_vs_new.py --engine new
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_ENGINE = Path(r"C:\Users\Pravin\AppData\Local\Temp\opencode\firstswing_old.py")
OLD_FINGERPRINT = "c864262630560f83"

PARAMS = dict(
    sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high", chop_thresh=58.0,
    cooldown_bars=8, max_consecutive_losses=3, htf_rr=3.0, window_end="exit",
    max_positions=0, exp_persist=7, pivot_rule="leg",
)


def install_old_engine() -> None:
    """Put the pre-fix firstswing into sys.modules under its real name."""
    if not OLD_ENGINE.exists():
        raise SystemExit("old engine not materialised: %s" % OLD_ENGINE)
    for p in ("backtest/tests", "backtest", "backend"):
        sys.path.insert(0, str(ROOT / p))
    import src  # noqa: F401  - real package, so the submodule key is valid
    spec = importlib.util.spec_from_file_location("src.firstswing", OLD_ENGINE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["src.firstswing"] = mod
    spec.loader.exec_module(mod)


def install_new_engine() -> None:
    for p in ("backtest/tests", "backtest", "backend"):
        sys.path.insert(0, str(ROOT / p))


def fingerprint(flow, candles) -> tuple[str, int, int]:
    from src.btc.btc_swing import compute_btc_swings
    swings = compute_btc_swings(flow, opts={"minBars": 50},
                                max_swings=max(1, len(candles) // 2))
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
    n_marks = sum(len(s["breaks"]) for s in swings)
    return h, len(swings), n_marks


def stats(trades: list[dict]) -> dict:
    closed = [t for t in trades if str(t.get("outcome", "")).lower() != "open"]
    rs = [float(t["r_multiple"]) for t in closed if t.get("r_multiple") is not None]
    n = len(rs)
    net = sum(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    eq = peak = dd = 0.0
    for x in rs:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {"n": n, "net": round(net, 2), "open": len(trades) - n,
            "win": round(len(wins) / n * 100, 1) if n else 0.0,
            "pf": round(pf, 2) if pf is not None else None, "dd": round(dd, 1),
            "avgR": round(net / n, 3) if n else 0.0}


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=("old", "new"), required=True)
    a = ap.parse_args()

    if a.engine == "old":
        install_old_engine()
    else:
        install_new_engine()

    # prove which engine is loaded before trusting any number
    data = load_era("is")
    fp, nsw, nmarks = fingerprint(data["f15"], data["c15"])
    print("engine=%s  chain fingerprint=%s  swings=%d  marks=%d"
          % (a.engine, fp, nsw, nmarks))
    if a.engine == "old" and fp != OLD_FINGERPRINT:
        print("REFUSING: old engine did not reproduce %s. Wrong file."
              % OLD_FINGERPRINT)
        return 2

    from exp_tf_family import build_family_module
    sim = build_family_module()

    res = {"engine": a.engine, "fingerprint": fp, "swings": nsw, "marks": nmarks,
           "params": PARAMS, "eras": {}}
    for era in ("is", "oos"):
        d = data if era == "is" else load_era(era)
        out = sim(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], **PARAMS)
        tr = out["ltf_trades"] if isinstance(out, dict) else out
        s = stats(tr)
        res["eras"][era] = s
        print("  %-4s n=%-4d net=%+8.2fR  WR=%.1f%%  PF=%s  DD=%.1f  open=%d"
              % (era, s["n"], s["net"], s["win"],
                 s["pf"] if s["pf"] is not None else "-", s["dd"], s["open"]))

    dest = Path(r"C:\Users\Pravin\AppData\Local\Temp\opencode\champion_%s.json" % a.engine)
    dest.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("wrote %s" % dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
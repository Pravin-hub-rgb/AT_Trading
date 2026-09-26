"""Stage ZCX cross-venue - does the M2-free causal combo transfer to Binance?

WHY
---
`exp_zx_causal_combo.py` found uZX / sZX (ZC OR X, no M2) at 5/6 on Bybit, failing
only age10 OOS on curve shape while dNet stayed positive. Both flags are
send-time computable - ZC is a 7d-vs-prior-7d volume ratio, X is a configured
window risk_pct, and neither reads `seg.end_px` (which IS forward-looking:
`backend_check_wd_days.py:108` asserts `fs_at_idx >= seg.end_idx`).

The one structural objection left on that result is portability. ZC was dropped
standalone in 24.82 precisely because a Bybit-volume-derived ratio threshold did
not transfer to Binance perp (binance IS curve FALSE, ulcer 110 -> 134). So the
honest next question is not "does it work on Bybit" but "does the union survive a
venue change at all", and specifically whether age10's curve failure is a Bybit
quirk or structural.

PRE-REGISTERED BEFORE THE RUN (2026-09-26)
------------------------------------------
  Venues: bybit (CONTROL, established loaders) vs binance-perp (TEST, 24.82 data).
  Lanes: champion / utcsat / age10 flat configs, frozen, NO retuning.
  Scopes: IS + OOS, era windows mirrored from the Bybit files.
  Arms: base, ZC, X, uZX, sZX - identical definitions to 24.85, no new search.
  TRANSFER lane PASS = binance base net > 0 AND n >= 30 in BOTH eras.
  FLAG arm PASS = dNet > 0 AND curve_better in ALL 6 cells, on the TEST venue.
  Controls: bybit base ledgers asserted against 24.79/24.85 refs; bybit uZX/sZX
  must reproduce the 5/6 result (+124.0/+33.6 champion) or abort - a control
  mismatch means the harness is wrong, not the venue.

  Note the threshold is NOT re-derived here. ZC keeps vol7_prev7 <= 0.846 exactly
  as frozen on Bybit. Re-deriving it per venue would be a new pre-registered
  experiment, and would defeat the point of a transfer test.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_zx_cross_venue.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_zx_cross_venue_results.json"
SIZE = 1.5
VOL7PREV_Q1 = 0.846
RISK_PCT_MAX = 1.0
TRANSFER_MIN_N = 30

# bybit control refs from 24.85 (exp_zx_causal_combo)
BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}
BYBIT_UZX_CONTROL = {"champion": (124.0, 33.6), "utcsat": (130.6, 41.1),
                    "age10": (115.5, 5.1)}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)

ARMS = (
    ("base", (), "union"),
    ("ZC", ("ZC",), "union"),
    ("X", ("X",), "union"),
    ("uZX", ("ZC", "X"), "union"),
    ("sZX", ("ZC", "X"), "stack"),
)
COMBO_ARMS = ("uZX", "sZX")
ARM_DESC = {
    "base": "1x reference",
    "ZC": f"x{SIZE} on vol7_prev7 <= {VOL7PREV_Q1}",
    "X": f"x{SIZE} on parent risk_pct < {RISK_PCT_MAX}",
    "uZX": f"x{SIZE} when ZC OR X (M2-free union)",
    "sZX": f"x{SIZE}^count on ZC/X (M2-free stack)",
}

# the audited sizing post-process (identity assert inside)
from exp_sizing_combo import apply_arm  # noqa: E402


def run_venue(venue, data, sim, sim_fn, years, out):
    """Compute every arm for every lane on one venue's data bundle."""
    from experiment_registry import BP, EXPERIMENTS
    from exp_regime_structure_autopsy import build_arrays, compute_features
    from exp_htf_break_sizing import flagged_keys
    from exp_htf_break_measures import flatten_breaks, enrich_windows
    from exp_thesis_htf_deep_atlas import build_windows, window_rows
    from exp_equity_quality import equity_quality, arm_scores, curve_better
    from src.btc.btc_routes import _compute_swings
    from engine.v18_params import SWING
    from exp_regime_structure_autopsy import _chop_series_1h

    arr = build_arrays(data["c1h"])
    conf = []
    for s in data["sw10"]:
        ci = s.get("confirmed_at_idx")
        if ci is None or not (0 <= ci < arr["n"]):
            continue
        dur = max(0, (s["seg"]["end_idx"] - s["seg"]["start_idx"]))
        conf.append((arr["ts"][ci], s["dir"], float(dur)))
    conf.sort(key=lambda x: x[0])
    chop = _chop_series_1h(data["c1h"], lb=14)
    ctx0 = {"arr": arr, "chop": chop,
            "conf_ts": [x[0] for x in conf], "conf_dir": [x[1] for x in conf],
            "conf_dur": [x[2] for x in conf]}

    fine_ts = [int(c["ts"]) for c in data["fine"]]
    breaks = flatten_breaks(data["sw10"])
    raw = build_windows(data, 3.0, 16)
    windows = {lane: window_rows(rows, data["fine"], fine_ts, lane)
               for lane, rows in raw.items()}
    for lane in windows:
        enrich_windows(windows[lane], data["c1h"], breaks)

    res = {}
    for name, key in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        trades = sim_fn(sim, data, params)
        m_base = equity_quality(trades, years)
        feats = [compute_features(t, ctx0) for t in trades]
        k_zc = {(int(t["entry_ts"]), int(t["exit_ts"])) for t, f in zip(trades, feats)
                if f.get("vol7_prev7") is not None and f["vol7_prev7"] <= VOL7PREV_Q1}
        k_x = flagged_keys(trades, windows, "risk_pct", -1e9, RISK_PCT_MAX)
        fam = {"ZC": k_zc, "X": k_x}
        arms_out = {}
        for arm, fams, mode in ARMS:
            if arm == "base":
                m, n_aff = m_base, 0
            else:
                book = apply_arm(trades, fam, fams, mode)
                n_aff = sum(1 for t in trades
                            if any((int(t["entry_ts"]), int(t["exit_ts"])) in fam[f] for f in fams))
                m = equity_quality(book, years)
            d = arm_scores(m, m_base)
            arms_out[arm] = {"n_affected": n_aff, "metric": m, "delta": d,
                             "d_net": d.get("d_net"), "curve_better": curve_better(d)}
        res[name] = {"n": m_base["n"], "net": m_base["net"],
                     "flag_counts": {"ZC": len(k_zc), "X": len(k_x)}, "arms": arms_out}
    return res


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  ZCX CROSS-VENUE - does the M2-free causal combo transfer to Binance?",
          flush=True)
    print("=" * 100, flush=True)

    from test_experiments_craze import build_module
    from run_experiment import get_data, identity_gate
    from test_4_new_concepts import load_fine_1m, load_unseen
    from exp_cross_instrument_transfer import (
        load_bybit, bybit_bounds, load_binance, BINANCE_DIR)
    from exp_equity_quality import equity_quality
    from exp_sizing_combo import run as sim_fn

    sim = build_module()
    payload = {
        "instrument_test": "BINANCE_FAPI_BTCUSDT_PERP (data/btc-fut, 24.82)",
        "instrument_control": "BTCUSDT_BYBIT (established loaders)",
        "stage": "zx_cross_venue",
        "lens": ("ZC and X only - neither reads seg.end_px; sizing post-process, "
                 "trade keys unchanged (sizing exemption)"),
        "arms": ARM_DESC,
        "years": {}, "scopes": {"bybit": {}, "binance": {}},
        "pre_registered": {
            "transfer_lane": "binance base net>0 AND n>=30 in BOTH eras",
            "flag_arm": "dNet>0 AND curve_better in ALL 6 cells on the TEST venue",
            "threshold": ("ZC keeps vol7_prev7 <= 0.846 exactly as frozen on Bybit - "
                          "re-deriving per venue would be a new experiment and would "
                          "defeat the point of a transfer test"),
            "control": "bybit base ledgers AND bybit uZX dNet must reproduce 24.85",
        },
    }

    years = {"is": 3.67, "oos": 2.0}
    payload["years"] = years

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        byb = load_bybit(scope, sim)
        r_byb = run_venue("bybit", byb, sim, sim_fn, years[scope], payload)

        # controls on Bybit - a mismatch means the harness is wrong
        for name, _ in LANES:
            exp_n, exp_net = BYBIT_BASE[name][scope]
            got = r_byb[name]
            assert got["n"] == exp_n, (
                f"CONTROL FAIL bybit/{scope}/{name} n: {got['n']} != {exp_n}")
            assert abs(got["net"] - exp_net) < 0.5, (
                f"CONTROL FAIL bybit/{scope}/{name} net: {got['net']} != {exp_net}")
        for name, (d_is_ref, d_oos_ref) in BYBIT_UZX_CONTROL.items():
            a = r_byb[name]["arms"]["uZX"]["d_net"]
            ref = d_is_ref if scope == "is" else d_oos_ref
            assert abs(a - ref) < 2.0, (
                f"CONTROL FAIL bybit/{scope}/{name} uZX dNet: {a} != {ref} "
                f"(24.85) - harness is wrong, not the venue")
        print(f"  [control-ok] bybit/{scope}: base ledgers + uZX dNet reproduce 24.85",
              flush=True)
        payload["scopes"]["bybit"][scope] = r_byb

        bounds = bybit_bounds(byb, scope)
        bin_ = load_binance(scope, bounds)
        r_bin = run_venue("binance", bin_, sim, sim_fn, years[scope], payload)
        payload["scopes"]["binance"][scope] = r_bin

        for name, _ in LANES:
            b = r_bin[name]
            print(f"  binance/{scope:<3} {name:<9} n={b['n']:>4} "
                  f"net={b['net']:>+8.1f} ZC={b['flag_counts']['ZC']:>3} "
                  f"X={b['flag_counts']['X']:>3}", flush=True)
            for arm in ("ZC", "X", "uZX", "sZX"):
                a = b["arms"][arm]
                print(f"      {arm:<4} nAff={a['n_affected']:>4} "
                      f"dNet={a['d_net']:>+7.1f} curve={a['curve_better']}", flush=True)

    # ---- verdicts -------------------------------------------------------
    transfer = {}
    for name, _ in LANES:
        ok = all(payload["scopes"]["binance"][s][name]["net"] > 0
                 and payload["scopes"]["binance"][s][name]["n"] >= TRANSFER_MIN_N
                 for s in ("is", "oos"))
        transfer[name] = ok
    payload["transfer_lane_pass"] = transfer
    payload["transfer_all_3"] = all(transfer.values())

    flag_pass = {}
    for arm in ("ZC", "X", "uZX", "sZX"):
        cells = []
        for name, _ in LANES:
            for s in ("is", "oos"):
                a = payload["scopes"]["binance"][s][name]["arms"][arm]
                cells.append((a["d_net"] or 0) > 0 and a["curve_better"])
        flag_pass[arm] = all(cells)
    payload["flag_pass_6"] = flag_pass
    payload["combo_transfer"] = {a: flag_pass[a] for a in COMBO_ARMS}
    payload["combo_transfer_all"] = all(flag_pass[a] for a in COMBO_ARMS)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\n" + "=" * 100, flush=True)
    print("  TRANSFER LANES (binance base profitable + n>=30 both eras):", flush=True)
    for k, v in transfer.items():
        print(f"    {k:<10} {v}", flush=True)
    print("  FLAG ARMS 6/6 ON BINANCE:", flush=True)
    for arm, v in flag_pass.items():
        print(f"    {arm:<5} {v}", flush=True)
    print("=" * 100, flush=True)
    print(f"  uZX/sZX TRANSFER: "
          f"{'YES' if payload['combo_transfer_all'] else 'NO'}", flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()

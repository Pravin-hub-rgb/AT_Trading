"""Stage CrossInstrument - cross-instrument + flag transfer to Binance BTCUSDT perp (2026-09-26).

Tests CROSS_INSTRUMENT_V18.md claims ("architecture universal, only knobs
differ" - single-period, no era split) with the CURRENT champion params,
properly IS/OOS, plus flag transfer of the validated sizing flags.

Data: data/btc-fut backfilled 2020-12-31 18:00 -> 2026-09-13 23:59 UTC
(fapi.binance.com, 0 gaps all TFs; 1h rewritten WITH volume column - legacy
file had none, ZC needs it; 1m prepended for 2021-22; originals backed up
in data/btc-fut/backup_legacy_20260926/). Era windows MIRRORED from the
bybit files per scope (same window, different venue). Cost model = Bybit
BTC (equity_quality/net_r), per exp_cross_asset_replication precedent.

PRE-REGISTERED BEFORE THE RUN (2026-09-26):
  Venues: bybit (CONTROL, established loaders) vs binance-perp (TEST).
  Lanes: champion / utcsat / age10 flat configs (frozen, NO retuning).
  Scopes: IS + OOS (identical era windows per venue).
  Arms (ALL reported, both venues): base, M2, ZC, X, uMZX (x1.5).
  Controls (abort if failed):
    - bybit EXPECT_FLAT ledger (n/net, 6 cells) - exact reference books.
    - bybit M2 + uMZX dNet vs _sizing_combo_results.json (24.78/24.79,
      tol 0.01) - proves flag machinery reproduced bit-for-bit.
  TRANSFER (base edge on binance): lane PASS = binance base net > 0 in
    BOTH eras AND n >= 30 in BOTH eras.
  FLAG PASS (per arm on binance): dNet > 0 AND curve_better TRUE in ALL
    6 cells (3 lanes x 2 eras) - the 24.79 rule, unchanged.
  Flag paths: M2 trade_rows (24.78); ZC compute_features (Stage Z2,
    vol7_prev7 on binance 1h VOLUME - ratio threshold so venue scale
    cancels); X flagged_keys windows (Stage X).
  Fine parity note: bybit OOS fine starts 5h after scope start (legacy
    data/unseen/bybit layout); binance OOS fine covers the full window.
RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic adoption.

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_cross_instrument_transfer.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING
from src.walker import FlowCandle
from exp_thesis_swing_geometry_deep import trade_rows

from exp_equity_quality import equity_quality, arm_scores, curve_better
from exp_regime_structure_autopsy import build_arrays, compute_features
from exp_htf_break_sizing import flagged_keys
from exp_htf_break_measures import flatten_breaks, enrich_windows
from exp_thesis_htf_deep_atlas import build_windows, window_rows

OUT = ROOT / "live_stuff/tests/_cross_instrument_results.json"
COMBO_REF = ROOT / "live_stuff/tests/_sizing_combo_results.json"
BINANCE_DIR = ROOT / "data" / "btc-fut"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 1.5
M2_MIN_ATR = 3.0
VOL7PREV_Q1 = 0.846
IST_OFFSET_SEC = 5 * 3600 + 30 * 60
STEP_SECONDS = {"15m": 900, "1h": 3600, "1m": 60}

EXPECT_FLAT = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)

ARMS = (
    ("base", (), "union"),
    ("M2", ("M2",), "union"),
    ("ZC", ("ZC",), "union"),
    ("X", ("X",), "union"),
    ("uMZX", ("M2", "ZC", "X"), "union"),
)

ARM_DESC = {
    "base": "1x reference",
    "M2": f"x{SIZE} on cur_mag_atr >= {M2_MIN_ATR}",
    "ZC": f"x{SIZE} on vol7_prev7 <= {VOL7PREV_Q1}",
    "X": f"x{SIZE} on parent risk_pct < 1.0",
    "uMZX": f"x{SIZE} when M2 OR ZC OR X (union)",
}

TRANSFER_MIN_N = 30

_bin_cache: dict = {}


def _read_binance(tf: str) -> pd.DataFrame:
    key = f"df_{tf}"
    if key in _bin_cache:
        return _bin_cache[key]
    path = BINANCE_DIR / f"BTCUSDT_{tf}.csv"
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError(f"missing timestamp column: {path}")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = (df.sort_values("timestamp")
            .drop_duplicates(subset="timestamp", keep="last")
            .reset_index(drop=True))
    epoch = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    diffs = epoch.diff().dropna()
    gaps = int((diffs != STEP_SECONDS[tf]).sum())
    if gaps:
        raise ValueError(f"{path} has {gaps} timestamp gaps; max={diffs.max()}s")
    df["ts"] = epoch
    _bin_cache[key] = df
    return df


def _candles(df: pd.DataFrame) -> tuple[list[dict], list[FlowCandle]]:
    candles, flow = [], []
    for row in df.itertuples(index=False):
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        o, h, lo, c = float(row.open), float(row.high), float(row.low), float(row.close)
        candles.append({"date": date, "ts": int(row.ts), "open": o,
                        "high": h, "low": lo, "close": c,
                        "volume": float(getattr(row, "volume", 0.0) or 0.0)})
        flow.append(FlowCandle(date=date, open=o, high=h, low=lo, close=c))
    return candles, flow


def load_bybit(scope, sim):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        sw20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
        return {
            "c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
            "sw15": sw15, "sw10": sw10, "sw20": sw20,
            "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"]),
        }
    data = get_data()
    identity_gate(data, sim)
    return data


def bybit_bounds(data, scope):
    c15, c1h = data["c15"], data["c1h"]
    if scope == "oos":
        fine = (c15[0]["ts"], c15[-1]["ts"])
    else:
        fine = (min(c1h[0]["ts"], c15[0]["ts"]),
                max(c1h[-1]["ts"], c15[-1]["ts"]))
    return {"15m": (c15[0]["ts"], c15[-1]["ts"]),
            "1h": (c1h[0]["ts"], c1h[-1]["ts"]), "fine": fine}


def load_binance(scope, bounds):
    lo15, hi15 = bounds["15m"]
    lo1h, hi1h = bounds["1h"]
    lof, hif = bounds["fine"]
    df15 = _read_binance("15m")
    df15 = df15[(df15["ts"] >= lo15) & (df15["ts"] <= hi15)].reset_index(drop=True)
    df1h = _read_binance("1h")
    df1h = df1h[(df1h["ts"] >= lo1h) & (df1h["ts"] <= hi1h)].reset_index(drop=True)
    dfm = _read_binance("1m")
    dfm = dfm[(dfm["ts"] >= lof) & (dfm["ts"] <= hif)].reset_index(drop=True)
    for tf, df, (lo, hi) in (("15m", df15, (lo15, hi15)),
                             ("1h", df1h, (lo1h, hi1h)),
                             ("1m", dfm, (lof, hif))):
        expect = (hi - lo) // STEP_SECONDS[tf] + 1
        if lo % STEP_SECONDS[tf] or len(df) != expect:
            raise ValueError(
                f"binance {scope}/{tf}: bounds off-grid or slice mismatch "
                f"(lo={lo} mod={lo % STEP_SECONDS[tf]} got={len(df)} expect={expect})")
    c15, f15 = _candles(df15)
    c1h, f1h = _candles(df1h)
    fine, _ = _candles(dfm)
    if not c15 or not c1h:
        raise ValueError(f"binance {scope}: empty slice")
    vol = [float(c.get("volume") or 0.0) for c in c1h]
    if not vol or min(vol) <= 0.0:
        raise ValueError(f"binance {scope}: 1h volume missing/zero - ZC unusable")
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    sw20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    print(f"  [binance/{scope}] 15m={len(c15)} 1h={len(c1h)} fine={len(fine)} "
          f"window {pd.to_datetime(lo15 - IST_OFFSET_SEC, unit='s', utc=True):%Y-%m-%d %H:%M}"
          f" -> {pd.to_datetime(hi15 - IST_OFFSET_SEC, unit='s', utc=True):%Y-%m-%d %H:%M} "
          f"fine_cov {'FULL' if fine and fine[0]['ts'] <= lof + 3600 else 'LATE-START'}",
          flush=True)
    return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
            "sw15": sw15, "sw10": sw10, "sw20": sw20, "fine": fine}


def build_contexts(data):
    arr = build_arrays(data["c1h"])
    conf = []
    for s in data["sw10"]:
        ci = s.get("confirmed_at_idx")
        if ci is None or not (0 <= ci < arr["n"]):
            continue
        dur = max(0, (s["seg"]["end_idx"] - s["seg"]["start_idx"]))
        conf.append((arr["ts"][ci], s["dir"], float(dur)))
    conf.sort(key=lambda x: x[0])
    from exp_regime_structure_autopsy import _chop_series_1h
    chop = _chop_series_1h(data["c1h"], lb=14)
    ctx0 = {"arr": arr, "chop": chop,
            "conf_ts": [x[0] for x in conf],
            "conf_dir": [x[1] for x in conf],
            "conf_dur": [x[2] for x in conf]}
    fine_ts = [int(c["ts"]) for c in data["fine"]]
    breaks = flatten_breaks(data["sw10"])
    raw = build_windows(data, 3.0, 16)
    windows = {lane: window_rows(rows, data["fine"], fine_ts, lane)
               for lane, rows in raw.items()}
    for lane in windows:
        enrich_windows(windows[lane], data["c1h"], breaks)
    return ctx0, windows


def run(sim, data, params):
    out = sim(
        data["c1h"], data["sw10"], data["c15"], data["sw15"],
        fine_ltf=data["fine"], **params,
    )
    return out["ltf_trades"] if isinstance(out, dict) else out


def apply_arm(trades, fam_keys, fams, mode):
    out = []
    for t in trades:
        k = (int(t["entry_ts"]), int(t["exit_ts"]))
        cnt = sum(1 for f in fams if k in fam_keys[f])
        t2 = dict(t)
        if cnt:
            mult = SIZE if mode == "union" else SIZE ** cnt
            t2["r_multiple"] = round(float(t["r_multiple"]) * mult, 6)
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades], "key sequence changed"
    return out


def flag_keys(trades, data, ctx0, windows):
    rows = trade_rows(trades, data)
    k_m2 = {(int(r["entry_ts"]), int(r["exit_ts"])) for r in rows
            if (r.get("cur_mag_atr") or 0) >= M2_MIN_ATR}
    feats = [compute_features(t, ctx0) for t in trades]
    k_zc = {(int(t["entry_ts"]), int(t["exit_ts"]))
            for t, f in zip(trades, feats)
            if f.get("vol7_prev7") is not None
            and f["vol7_prev7"] <= VOL7PREV_Q1}
    k_x = flagged_keys(trades, windows, "risk_pct", -1e9, 1.0)
    return {"M2": k_m2, "ZC": k_zc, "X": k_x}


def run_arms(trades, fam_keys, yrs):
    m_flat = equity_quality(trades, yrs)
    arms_out = {}
    print(f"    {'arm':<7} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
          f"{'sort':>7} {'calmar':>7} {'streak':>6} {'PF':>6} {'dNet':>8} curve",
          flush=True)
    for arm, fams, mode in ARMS:
        if arm == "base":
            book, n_aff = trades, 0
        else:
            book = apply_arm(trades, fam_keys, fams, mode)
            n_aff = sum(1 for t in trades
                        if any((int(t["entry_ts"]), int(t["exit_ts"])) in fam_keys[f]
                               for f in fams))
        m = equity_quality(book, yrs)
        d = arm_scores(m, m_flat)
        cb = curve_better(d)
        small = " SMALL-N" if 0 < n_aff < 20 else ""
        print(f"    {arm:<7} {m['n']:>4} {m.get('net', 0):>+8.1f} "
              f"{m.get('max_dd', 0):>6.1f} {m.get('ulcer', 0):>7.2f} "
              f"{m.get('sortino', 0):>7.2f} {m.get('calmar', 0):>7.3f} "
              f"{m.get('max_streak', 0):>6} {m.get('pf', 0):>6.2f} "
              f"{d.get('d_net', 0):>+8.1f} {cb}{small}", flush=True)
        arms_out[arm] = {"n_affected": n_aff, "metric": m, "delta": d,
                         "curve_better": cb}
    return m_flat, arms_out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE CROSS-INSTRUMENT - Binance BTCUSDT perp transfer "
          "(frozen champion params + sizing flags)", flush=True)
    print("=" * 100, flush=True)

    ref = json.loads(COMBO_REF.read_text(encoding="utf-8"))

    sim = build_module()
    payload = {
        "instrument_test": "BINANCE_FAPI_BTCUSDT_PERP (data/btc-fut, backfilled 2020-12-31..2026-09-13, 0 gaps, 1h volume present)",
        "instrument_control": "BTCUSDT_BYBIT (established loaders)",
        "stage": "cross_instrument_transfer",
        "cost_model": "Bybit BTC fee/funding applied to both venues (equity_quality convention, cross-asset precedent)",
        "frozen_no_retune": True,
        "arms": ARM_DESC,
        "years": YEARS, "scopes": {},
        "pre_registered": ("TRANSFER lane PASS = binance base net>0 AND n>=%d in BOTH eras; "
                           "FLAG arm PASS = dNet>0 AND curve_better in ALL 6 cells; "
                           "bybit controls abort on mismatch" % TRANSFER_MIN_N),
        "baseline_reference": "champion 500/+325.8 IS, 279/+70.2 OOS; utcsat 454/+358.9, 253/+60.2; age10 130/+435.7, 76/+43.2 (asserted, bybit only)",
        "fine_parity_note": "bybit OOS fine starts 5h late (legacy unseen layout); binance OOS fine covers full window",
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        yrs = YEARS[scope]
        by_data = load_bybit(scope, sim)
        bounds = bybit_bounds(by_data, scope)
        bn_data = load_binance(scope, bounds)
        by_ctx = build_contexts(by_data)
        bn_ctx = build_contexts(bn_data)

        sc = {}
        for venue, data, ctx in (("bybit", by_data, by_ctx),
                                 ("binance", bn_data, bn_ctx)):
            sc[venue] = {}
            ctx0, windows = ctx
            for name, key in LANES:
                cfg = EXPERIMENTS[key]
                params = {**BP, **cfg["params"]}
                params.setdefault("exp_partial_r", 0.0)
                trades = run(sim, data, params)
                m_flat, arms_out = run_arms(trades, fam_keys := flag_keys(
                    trades, data, ctx0, windows), yrs)
                print(f"  [{venue}] {name} n={m_flat['n']} net={m_flat['net']:+.1f} "
                      f"flags M2={len(fam_keys['M2'])} ZC={len(fam_keys['ZC'])} "
                      f"X={len(fam_keys['X'])}", flush=True)
                if venue == "bybit":
                    exp_n, exp_net = EXPECT_FLAT[name][scope]
                    assert m_flat["n"] == exp_n, (
                        f"flat ledger n mismatch {name}/{scope}: "
                        f"{m_flat['n']} != {exp_n} - not the flat reference book")
                    assert abs(m_flat["net"] - exp_net) < 0.5, (
                        f"flat ledger net mismatch {name}/{scope}: "
                        f"{m_flat['net']} != {exp_net}")
                    print(f"  [ledger-ok] {name}/{scope}: n={m_flat['n']} "
                          f"net={m_flat['net']:+.1f}", flush=True)
                sc[venue][name] = {
                    "n": m_flat["n"], "net": m_flat["net"],
                    "max_dd": m_flat.get("max_dd"),
                    "flag_counts": {"M2": len(fam_keys["M2"]),
                                    "ZC": len(fam_keys["ZC"]),
                                    "X": len(fam_keys["X"])},
                    "arms": arms_out, "identity_ok": venue == "bybit",
                }
        # side-by-side base comparison
        for name, _ in LANES:
            b = sc["bybit"][name]
            n_ = sc["binance"][name]
            print(f"  [base {scope}] {name:<10} bybit {b['n']:>4}t "
                  f"{b['net']:+7.1f} (DD {b['max_dd']:.1f}) | binance "
                  f"{n_['n']:>4}t {n_['net']:+7.1f} (DD {n_['max_dd']:.1f}) "
                  f"| dn {n_['n'] - b['n']:+d} dnet {n_['net'] - b['net']:+.1f} "
                  f"ratio {n_['net'] / b['net'] if b['net'] else 0:.2f}", flush=True)
        payload["scopes"][scope] = sc

    # --- controls: bybit M2/uMZX dNet vs 24.79 combo reference ---
    print("\n=== CONTROLS (bybit vs _sizing_combo_results.json) ===", flush=True)
    controls_ok = True
    for scope in ("is", "oos"):
        for name, _ in LANES:
            for arm in ("M2", "uMZX"):
                got = payload["scopes"][scope]["bybit"][name]["arms"][arm]["delta"]["d_net"]
                want = ref["scopes"][scope][name]["arms"][arm]["delta"]["d_net"]
                ok = abs(got - want) < 0.01
                controls_ok &= ok
                print(f"  {'OK ' if ok else 'FAIL'} {arm:<5} {name:<10} {scope:<3} "
                      f"dNet {got:+.2f} vs ref {want:+.2f}", flush=True)
    payload["controls_ok"] = controls_ok
    if not controls_ok:
        raise SystemExit("CONTROL FAILED - bybit flag machinery drifted from 24.79")

    # --- transfer verdict (binance base) ---
    print("\n=== TRANSFER (binance base edge) ===", flush=True)
    transfer = {}
    for name, _ in LANES:
        b_is = payload["scopes"]["is"]["binance"][name]["arms"]["base"]["metric"]
        b_oos = payload["scopes"]["oos"]["binance"][name]["arms"]["base"]["metric"]
        v = {"net_is": b_is.get("net"), "net_oos": b_oos.get("net"),
             "n_is": b_is["n"], "n_oos": b_oos["n"]}
        v["lane_pass"] = (v["net_is"] or 0) > 0 and (v["net_oos"] or 0) > 0 \
            and v["n_is"] >= TRANSFER_MIN_N and v["n_oos"] >= TRANSFER_MIN_N
        transfer[name] = v
        print(f"  {name:<10} IS {v['n_is']:>4}t {v['net_is']:+7.1f} | "
              f"OOS {v['n_oos']:>4}t {v['net_oos']:+7.1f} | "
              f"PASS={v['lane_pass']}", flush=True)
    payload["transfer"] = transfer
    payload["transfer_all_3"] = all(v["lane_pass"] for v in transfer.values())

    # --- flag verdicts (per venue, 6-cell rule) ---
    print("\n=== FLAG VERDICTS (per arm, 6 cells) ===", flush=True)
    flag_pass = {}
    for venue in ("bybit", "binance"):
        flag_pass[venue] = {}
        for arm, _f, _m in ARMS:
            if arm == "base":
                continue
            cells = {}
            for name, _ in LANES:
                a_is = payload["scopes"]["is"][venue][name]["arms"][arm]
                a_oos = payload["scopes"]["oos"][venue][name]["arms"][arm]
                d_is, d_oos = a_is["delta"], a_oos["delta"]
                cell = (d_is.get("d_net") or 0) > 0 and (d_oos.get("d_net") or 0) > 0 \
                    and a_is["curve_better"] and a_oos["curve_better"]
                cells[name] = cell
                print(f"  [{venue}] {arm:<5} {name:<10} "
                      f"dNet {d_is.get('d_net'):+7.1f}/{d_oos.get('d_net'):+7.1f} "
                      f"curve {int(a_is['curve_better'])}/{int(a_oos['curve_better'])} "
                      f"cell={cell}", flush=True)
            flag_pass[venue][arm] = {"cells": cells, "pass_all_6": all(cells.values())}
    payload["flag_pass"] = flag_pass

    print("\n=== SUMMARY ===", flush=True)
    print(f"  controls_ok: {controls_ok}", flush=True)
    print(f"  transfer_all_3 (binance base): {payload['transfer_all_3']}", flush=True)
    for venue in ("bybit", "binance"):
        for arm in flag_pass[venue]:
            print(f"  PASS 6/6 {venue}/{arm}: {flag_pass[venue][arm]['pass_all_6']}",
                  flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()

"""GRAY path-true test of the mechanism found by exp_range_mechanism.py.

THE MECHANISM (measured, not assumed - see _range_mechanism.json)
===============================================================
Peak-position (top-quartile range location) trades split sharply on RANGE
WIDTH, and they split the SAME way in both eras:

  3d window, PEAK trades only, net R:
              tight(w0)   normal(w1)   wide(w2)
    IS/champ    +49.5        +17.9        +15.6
    OOS/champ    -1.3         -3.9        +57.3     <- OOS wide is the only
    OOS/utcsat   -0.2         -4.0        +65.2        cell that carries OOS

But the MFE tells the real story, and it is NOT a hit-rate story:
  OOS/champ peak:  MFE 1.45 (tight) / 2.30 (normal) / 6.04 (wide)
  cont(MFE>MAE) OOS:  4/12 / 20/38 / 11/28
MAE is flat everywhere (~1.2R) - the risk is identical. Only the FAVOURABLE
excursion differs, and it differs 4x. So the peak entries in a NON-expanded
range are not "wrong more often", they are right and then go nowhere: the
move has no room to run. In an EXPANDED range the same peak location has
room, so the trail does its job and the tail (the book's whole profit
structure, Rule 13) actually gets built.

That makes the falsifiable prediction for a gate:
  gray PEAK-position trades in NON-EXPANDED ranges
  = keep PEAK trades when the range is EXPANDED (width tercile 2).
Prediction if the mechanism is right: the grayed cohort is net-NEGATIVE in
both eras, so suppressing its P&L should ADD R in both.

GRAY, NOT SKIP (Rule 18, a3ca96b design)
========================================
The trade runs to completion. Only its P&L is suppressed to r=0. The slot is
still held, the loss streak still advances (exp_gray_streak=True) and the
cooldown still starts. That makes the run path-TRUE and cascade-free BY
CONSTRUCTION: the trade sequence must be byte-identical to the reference, and
the invariant d_net == -raw_r_grayed must hold. A plain skip would free the
slot, admit a replacement trade, and buy its result with someone else's P&L
(wick gate: skip -39.0R vs gray +28.1R in IS - a ~67R swing from the slot
alone). Both are reported so the tax is visible rather than assumed.

PREDICATE (frozen, single source, entry-time only)
================================================
cutoff = entry_ts + 900; j = last 1h bar with ts <= cutoff - 3600; over the
last 72 CLOSED 1h bars (3d): pos = (close-low)/(high-low)*100, width =
(high-low)/ATR14(j)*100. Gray iff pos >= 75 AND width <= w2_cut, where
w2_cut is the IS-champion width tercile-2 lower edge, read at runtime from
the same terciles the mechanism run used. The SAME python predicate drives
the engine injection and every offline control.

STATUS: experimental. Nothing here is adopted, no production file is touched.
"""
from __future__ import annotations

import bisect
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_range_gray.json"
TMP = ROOT / "backtest/tests/_v18_gray_range_tmp.py"
WINDOW = 72            # 3d
POS_MIN = 75.0         # top quartile = "peak"
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
# Reference ledgers from exp_gray_wick1h.py BYBIT_BASE (control: must match)
BYBIT_BASE = {
    "is/champion": (500, 325.8), "is/utcsat": (454, 358.9),
    "is/age10": (130, 435.7),
    "oos/champion": (279, 70.1), "oos/utcsat": (253, 60.2),
    "oos/age10": (76, 43.2),
}
YEARS = {"is": 3.67, "oos": 2.0}

# --------------------------------------------------------------- gray patch
# Same injection points as the proven exp_sl_width_gate.py harness. The anchor
# sits right after the engine has entry/sl/risk, so the predicate reads only
# entry-time values. BOTH indent levels are patched: the 8-space main entry
# path and the 12-space retest path, or retest trades escape the gate.
_GRAY_STREAK = (
    '        _rgts=int(candles_ltf[i]["ts"])\n'
    '        _rgp=_rp_pos.get(_rgts,50.0) or 50.0\n'
    '        _rgw=_rp_wid.get(_rgts,0.0) or 0.0\n'
    '        _isgray = _rp_on and _rgp >= 75.0 and _rgw <= _rp_w2\n'
    '        sl0=sl; sl_cur=sl; best=entry\n'
)
_GRAY_STREAK_RET = (
    '            _rgts=int(candles_ltf[i]["ts"])\n'
    '            _rgp=_rp_pos.get(_rgts,50.0) or 50.0\n'
    '            _rgw=_rp_wid.get(_rgts,0.0) or 0.0\n'
    '            _isgray = _rp_on and _rgp >= 75.0 and _rgw <= _rp_w2\n'
    '            sl0=sl; sl_cur=sl; best=entry\n'
)
_STREAK_ANCHOR = '        if max_consecutive_losses > 0:\n'
_STREAK_PATCH = (
    '        if max_consecutive_losses > 0 and not (_isgray and not exp_gray_streak):\n'
)
_COOL_ANCHOR = '        if cooldown_bars > 0 and r_multiple < 0:\n'
_BOOK_ANCHOR = '            "r_multiple": round(float(r_multiple),3),\n'
_BOOK_PATCH = (
    '            "r_multiple": round(0.0 if _isgray else float(r_multiple),3),\n'
    '            "is_gray": bool(_isgray),\n'
    '            "rp_pos": round(_rgp,1),\n'
    '            "rp_wid": round(_rgw,1),\n'
    '            "r_multiple_raw": round(float(r_multiple),3),\n'
)

def _load_module(text, name):
    p = TMP
    p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, p


def build_gray_module():
    """Super-set engine source + the gray patch on top. Defaults OFF => the
    patched engine is byte-identical in behaviour to the shipped one."""
    import test_experiments_craze as tc
    cap = {}
    orig = tc._load_module

    def spy(text, name):
        cap["text"] = text
        return orig(text, name)

    tc._load_module = spy
    try:
        tc.build_module()
    finally:
        tc._load_module = orig
    s = cap["text"]

    t1 = "    *,\n"
    assert s.count(t1) == 1, "sig star"
    s = s.replace(t1, t1 + "    exp_gray_streak=True,\n")

    # Globals the injected predicate reads. Seeded empty and OFF-safe.
    s = s.replace(t1, t1, 1)
    s = s.replace("    *,\n", "    *,\n", 1)
    assert "def simulate_htf_ltf_streak_halt" in s
    s = s.replace("def simulate_htf_ltf_streak_halt",
                  "_rp_pos = {}\n_rp_wid = {}\n_rp_w2 = 0.0\n"
                  "_rp_on = False\n\n\n"
                  "def simulate_htf_ltf_streak_halt", 1)

    def _replace_at_line(s, indent, new_block):
        old = "\n" + " " * indent + "sl0=sl; sl_cur=sl; best=entry\n"
        assert s.count(old) == 1, f"indent {indent}: {s.count(old)}"
        return s.replace(old, "\n" + new_block)

    s = _replace_at_line(s, 12, _GRAY_STREAK_RET)
    s = _replace_at_line(s, 8, _GRAY_STREAK)
    for nm, a in (("streak", _STREAK_ANCHOR), ("cooldown", _COOL_ANCHOR),
                  ("book", _BOOK_ANCHOR)):
        c = s.count(a)
        print(f"  {nm} anchor count = {c}")
        assert c >= 1, f"{nm} anchor missing"
    s = s.replace(_STREAK_ANCHOR, _STREAK_PATCH)
    s = s.replace(_COOL_ANCHOR, _COOL_ANCHOR)          # cooldown untouched
    s = s.replace(_BOOK_ANCHOR, _BOOK_PATCH)
    m, _p = _load_module(s, "v18_gray_range")
    return m


def build_maps(c1h, c15):
    """{entry_ts: (range_pos, range_width)} for every 15m entry timestamp.

    Causality: j = last 1h bar with ts <= entry_ts + 900 - 3600, i.e. only
    1h bars CLOSED before the entry decision. Cached per j because j only
    changes once an hour.
    """
    c1h_ts = [int(c["ts"]) for c in c1h]
    hi = [float(c["high"]) for c in c1h]
    lo = [float(c["low"]) for c in c1h]
    cl = [float(c["close"]) for c in c1h]
    tr = [0.0] * len(c1h)
    for k in range(len(c1h)):
        tr[k] = (hi[k] - lo[k] if k == 0 else
                 max(hi[k] - lo[k], abs(hi[k] - cl[k - 1]),
                     abs(lo[k] - cl[k - 1])))
    cache = {}
    pos_m, wid_m = {}, {}
    for c in c15:
        ts = int(c["ts"])
        if ts in pos_m:
            continue
        j = bisect.bisect_right(c1h_ts, ts + 900 - 3600) - 1
        if j < 14 or j - WINDOW + 1 < 0:
            pos_m[ts] = wid_m[ts] = None
            continue
        if j not in cache:
            a = sum(tr[j - 13:j + 1]) / 14.0
            l0 = min(lo[j - WINDOW + 1:j + 1])
            h0 = max(hi[j - WINDOW + 1:j + 1])
            p = 100.0 * (cl[j] - l0) / (h0 - l0) if h0 > l0 else 50.0
            cache[j] = (round(p, 1), round(100.0 * (h0 - l0) / a, 1) if a
                        else 0.0)
        pos_m[ts], wid_m[ts] = cache[j]
    return pos_m, wid_m

def metrics(trades, years):
    """Full metric set on NET R (costs + funding included), matching the
    repo's reference ledgers.

    Grayed trades stay in the book with r_multiple=0, so the trade count is
    unchanged by design and only the P&L columns move. net_r subtracts costs
    in BOTH the reference and the gray arm, so the cascade invariant
    d_net == -raw_r_grayed holds exactly.
    """
    from run_experiment import net_r
    rs = [net_r([t]) for t in trades]
    n = len(rs)
    if not n:
        return {"n": 0}
    wins = [x for x in rs if x > 0]
    gp = sum(wins)
    gl = -sum(x for x in rs if x < 0)
    eq = peak = dd = 0.0
    for x in rs:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    net = sum(rs)
    top3 = sum(sorted(rs, reverse=True)[:3])
    top5 = sum(sorted(rs, reverse=True)[:5])
    k = max(1, n // 10)
    return {
        "n": n, "net": round(net, 1),
        "wr_pct": round(100.0 * len(wins) / n, 1),
        "pf": round(gp / gl, 2) if gl > 0 else None,
        "median": round(statistics.median(rs), 3),
        "trimmed": round(statistics.mean(sorted(rs)[k:n - k] or rs), 3),
        "max_dd": round(dd, 1),
        "net_per_year": round(net / years, 1) if years else None,
        "top3_share_pct": round(100.0 * top3 / net, 1) if net else None,
        "top5_share_pct": round(100.0 * top5 / net, 1) if net else None,
        "ex_best3_net": round(net - top3, 1),
        "ex_best5_net": round(net - top5, 1),
    }

def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  RANGE PEAK x NARROW-WIDTH GATE - GRAY mode, path-true", flush=True)
    print("=" * 100, flush=True)
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_5m_confirm import load_book

    mod = build_gray_module()
    sim = mod.simulate_htf_ltf_streak_halt
    payload = {"stage": "range_gray", "cells": {}, "errors": []}
    ref_trades = {}
    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        pos_m, wid_m = build_maps(data["c1h"], data["c15"])
        mod._rp_pos.clear()
        mod._rp_pos.update({k: v for k, v in pos_m.items() if v is not None})
        mod._rp_wid.clear()
        mod._rp_wid.update({k: v for k, v in wid_m.items() if v is not None})
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            mod._rp_on = False
            ref = sim_fn(sim, data, params)
            ref_trades[(scope, name)] = (data, ref)
            m_ref = metrics(ref, YEARS[scope])
            exp_n, exp_net = BYBIT_BASE[f"{scope}/{name}"]
            got_n = m_ref["n"]
            got_net = m_ref["net"]
            ok = got_n == exp_n and abs(got_net - exp_net) < 0.6
            print(f"  REF {scope}/{name}: {got_n}t {got_net:+.1f}R "
                  f"(expect {exp_n}t {exp_net:+.1f}) "
                  f"{'OK' if ok else 'MISMATCH'}", flush=True)
            if not ok:
                payload["errors"].append(f"ref mismatch {scope}/{name}")

    if payload["errors"]:
        print("\nABORT: reference ledgers did not reproduce.", flush=True)
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return
    # Width cutoff from the IS champion reference ledger, whose maps were
    # already built for IS. (Re-running on a freshly loaded IS book would look
    # the widths up in the OOS map still held in the module and get all 0.0.)
    is_ref = ref_trades[("is", "champion")][1]
    ref_w = [float(t["rp_wid"]) for t in is_ref
             if t.get("rp_wid") is not None]
    assert ref_w, "no rp_wid on the IS reference ledger"
    w2 = sorted(ref_w)[int(2 * len(ref_w) / 3)]
    mod._rp_w2 = float(w2)
    print(f"\n  width cutoff w2 (IS champion 2/3 quantile) = {w2:.1f}\n",
          flush=True)
    payload["width_cutoff"] = w2
    report_arms(mod, sim, sim_fn, BP, EXPERIMENTS, ref_trades, payload, w2)
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")

def report_arms(mod, sim, sim_fn, BP, EXPERIMENTS, ref_trades, payload,
                w2):
    for scope in ("is", "oos"):
        for name, key in LANES:
            data, ref = ref_trades[(scope, name)]
            # Re-seed the feature maps for THIS scope. The main loop built
            # them per scope but left the last scope's maps in the module, so
            # without this the IS arms would look IS trades up in the OOS
            # table and flag nothing (gray 0 IS, nonzero OOS). Same
            # wrong-cohort bug this repo has hit repeatedly.
            pos_m, wid_m = build_maps(data["c1h"], data["c15"])
            mod._rp_pos.clear()
            mod._rp_pos.update({k: v for k, v in pos_m.items()
                                if v is not None})
            mod._rp_wid.clear()
            mod._rp_wid.update({k: v for k, v in wid_m.items()
                                if v is not None})
            mod._rp_w2 = float(w2)
            params = {**BP, **EXPERIMENTS[key]["params"]}
            m_ref = metrics(ref, YEARS[scope])
            mod._rp_on = True
            for streak in (True, False):
                arm = sim_fn(sim, data, params, exp_gray_streak=streak)
                m_arm = metrics(arm, YEARS[scope])
                grays = [t for t in arm if t.get("is_gray")]
                raw = sum(float(t.get("r_multiple_raw") or 0.0) for t in grays)
                # The cohort's TRUE net R must be read off the REFERENCE
                # ledger, where r_multiple is intact. On the gray arm
                # r_multiple is already 0, so net_r([t]) there returns only
                # the costs - it is NOT the cohort's P&L and would badly
                # understate it. Trades are matched by (entry_ts, exit_ts);
                # seqID is asserted true for the streakON arm, so the match
                # is exact rather than approximate.
                from run_experiment import net_r
                ref_by_key = {(t["entry_ts"], t["exit_ts"]): t for t in ref}
                grayed_net = sum(
                    net_r([ref_by_key[(t["entry_ts"], t["exit_ts"])]])
                    for t in grays
                    if (t["entry_ts"], t["exit_ts"]) in ref_by_key)
                seq_ref = [(t["entry_ts"], t["exit_ts"]) for t in ref]
                seq_arm = [(t["entry_ts"], t["exit_ts"]) for t in arm]
                casc = (m_arm["net"] - m_ref["net"]) + raw
                cell = {
                    "ref": m_ref, "arm": m_arm, "n_gray": len(grays),
                    "kept_pct": round(100.0 * (m_arm["n"] - len(grays))
                                      / m_ref["n"], 2),
                    "d_net": round(m_arm["net"] - m_ref["net"], 1),
                    "d_dd": round(m_ref["max_dd"] - m_arm["max_dd"], 1),
                    "raw_r_grayed": round(raw, 1),
                    "grayed_net_r": round(grayed_net, 1),
                    "cascade_term": round(casc, 2),
                    "seq_identical": seq_ref == seq_arm,
                    "gray_streak": streak,
                    "grayed_wr_pct": round(100.0 * sum(
                        1 for t in grays
                        if float(t.get("r_multiple_raw") or 0) > 0)
                        / len(grays), 1) if grays else None,
                }
                k = f"{scope}/{name}/{'streakON' if streak else 'streakOFF'}"
                payload["cells"][k] = cell
                r, a = m_ref, m_arm
                print(f"  {k}", flush=True)
                print(f"    trades {r['n']} -> {a['n']}  (gray {len(grays)}, "
                      f"kept {cell['kept_pct']}%)", flush=True)
                print(f"    net    {r['net']:+8.1f} -> {a['net']:+8.1f}  "
                      f"({cell['d_net']:+.1f})", flush=True)
                print(f"    WR     {r['wr_pct']:>5.1f}% -> {a['wr_pct']:>5.1f}%"
                      f"   PF {r['pf']} -> {a['pf']}   maxDD "
                      f"{r['max_dd']} -> {a['max_dd']} ({cell['d_dd']:+.1f})",
                      flush=True)
                print(f"    median {r['median']:>+6.2f} -> {a['median']:>+6.2f}"
                      f"   trim {r['trimmed']:>+6.2f} -> "
                      f"{a['trimmed']:>+6.2f}", flush=True)
                print(f"    net/yr  {r['net_per_year']} -> {a['net_per_year']} R"
                      f"   ex-best3 {r['ex_best3_net']:+.1f} -> "
                      f"{a['ex_best3_net']:+.1f}   "
                      f"ex-best5 {r['ex_best5_net']:+.1f} -> "
                      f"{a['ex_best5_net']:+.1f}", flush=True)
                print(f"    GRAYED COHORT: n{len(grays)} grossR {raw:+.1f} "
                      f"TRUE netR {grayed_net:+.1f} "
                      f"WR {cell['grayed_wr_pct']}% vs book "
                      f"{r['wr_pct']}%  -> cohort "
                      f"{'PROFITABLE, gate DESTROYS R' if grayed_net > 0 else 'losing'}",  # noqa: E501
                      flush=True)
                print(f"    cascade={casc:+.2f} "
                      f"seqID={cell['seq_identical']}", flush=True)


if __name__ == "__main__":
    main()




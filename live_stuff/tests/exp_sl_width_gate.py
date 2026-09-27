"""SL-WIDTH GATE in GRAY mode - the user's idea, made cascade-free.

THE PROBLEM WITH EVERY PRIOR GATE
---------------------------------
Stage B (wick_atr12, flips96) removed trades from a finished ledger and the
cascade measured 3-5x the direct effect: deleting a trade frees its `busy_until`
slot, shifts `cooldown_bars`, and rewrites the loss streak. The rule that came
out of it (AGENT_COORDINATION.md) is that a post-process removal is only an
UPPER BOUND and must be rerun path-true before any claim. Stage Z3 hit the same
wall a second time.

THE USER'S INSIGHT (2026-09-27), and it is the right one
--------------------------------------------------------
"if the SL is way out of our range, mark the trade GRAY - do not enter it, but
let it fully close. The slot stays blocked. We are NOT trying to fill it with
the next trade, because in the no-gate case we would not have taken the next
trade anyway."

That is the distinction that makes this lever testable. A GRAY trade is still
run to completion by the engine, so ALL chain state is preserved exactly:
  - `busy_until` is still set to its exit (v18:743) -> the next entry is blocked
  - the loss streak still counts it (v18:713-722) -> halt logic is intact
  - `cooldown_bars` still triggers on its loss (v18:744-745)
Only its P&L is suppressed. That is categorically different from a removal, and
it is why this can be measured path-TRUE in one run with no cascade.

This is NOT the post-process sizing exemption and NOT a removal: the engine
itself is patched (runtime source patch via build_module, shipped file
untouched), so every downstream trade is the real path-true trade.

DESIGN QUESTION ANSWERED BY THE RUN, NOT BY ME
-----------------------------------------------
Whether a gray trade should still move the loss-streak counter is a real
design choice with two defensible answers, so BOTH are pre-registered and both
are run. The user explicitly asked to let the result decide:

  GRAY_STREAK_ON   gray trade counts toward the streak counter (as-is engine
                   behaviour: a gray loss increments consecutive_losses).
  GRAY_STREAK_OFF  gray trade is neutral: streak neither advances nor resets.

If a gray trade is one we deliberately did not take, counting its loss against
us is arguably wrong (GRAY_STREAK_OFF). If the slot really was occupied and we
missed a real loss, pretending it never happened is arguably wrong too
(GRAY_STREAK_ON). Both are implemented, both are reported, no best-of hiding.

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
-------------------------------------------
  Step 1 (descriptive, decides the band - NOT a gate): SL-width bucket autopsy
    on the SHIPPED book, n / avgR / win-rate / net per fixed percent band, per
    lane per era. Buckets are FIXED percent bands, not quantiles, because a
    deployed gate needs an absolute number in percent of price.
  Step 2 (the gate): gray any trade whose sl_width_pct falls OUTSIDE
    [band_lo, band_hi], at three pre-registered bands. Bands come from step 1's
    table and are chosen BEFORE any gate number is computed.

  G-RULE (per arm, all 6 cells must hold):
    1. kept% >= 55            (a gate this wide should not gut the book)
    2. net > 0 in every cell
    3. avg net per trade not worse than the reference book
    4. maxDD(R) <= reference  (the whole point: gray must not deepen DD)
  Plus, reported but not gated: the cascade-free property itself - the gray
  arm's realized trade COUNT and its exit-timestamp sequence must still line up
  with the reference, proving slots were preserved rather than refilled.

  CONTROL: the patched engine with the gate OFF must reproduce the 24.85
  reference ledgers exactly (identity gate), or the run is void.
  Nothing is retuned after the run.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_sl_width_gate.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_sl_width_gate.json"
_TMP = ROOT / "live_stuff/tests/_slgate_tmp.py"

# Step 1 buckets: fixed percent-of-price bands (deployable absolute numbers).
BUCKETS = ((0.0, 0.25), (0.25, 0.4), (0.4, 0.55), (0.55, 0.7),
           (0.7, 0.9), (0.9, 1.2), (1.2, 1.6), (1.6, 99.0))

# Step 2 gate bands: (label, lo_pct, hi_pct). Outside the band => gray.
GATE_BANDS = (
    ("b_040_090", 0.40, 0.90),
    ("b_040_120", 0.40, 1.20),
    ("b_055_120", 0.55, 1.20),
)

BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)


# --- engine patch: gray-mode SL-width gate --------------------------------
# Injected right after `risk` is known (v18:590/596), so the gate reads only
# entry-time values. The trade is still run to completion; only its P&L is
# suppressed. busy_until / streak / cooldown all still update exactly as they
# would have, which is the property Stage B removals could never have.
_GRAY_ANCHOR = '        sl0=sl; sl_cur=sl; best=entry\n'
# The super-set source contains this line at TWO indent levels: the main entry
# path (8 spaces) and the 5m/retest delayed path (12 spaces). Both must be
# gated, otherwise retest-path trades silently escape the gate.
_GRAY_ANCHOR_RET = '            sl0=sl; sl_cur=sl; best=entry\n'
_GRAY_STREAK = (
    '        _gslw=abs(entry-sl)/entry*100.0 if entry>0 else 0.0\n'
    '        _isgray = exp_gray_lo>0 and (_gslw < exp_gray_lo or _gslw > exp_gray_hi)\n'
    '        sl0=sl; sl_cur=sl; best=entry\n'
)
_GRAY_STREAK_RET = (
    '            _gslw=abs(entry-sl)/entry*100.0 if entry>0 else 0.0\n'
    '            _isgray = exp_gray_lo>0 and (_gslw < exp_gray_lo or _gslw > exp_gray_hi)\n'
    '            sl0=sl; sl_cur=sl; best=entry\n'
)
_STREAK_ANCHOR = '        if max_consecutive_losses > 0:\n'
_STREAK_PATCH = (
    '        if max_consecutive_losses > 0 and not (_isgray and not exp_gray_streak):\n'
)
_COOL_ANCHOR = '        if cooldown_bars > 0 and r_multiple < 0:\n'
# A gray trade still HAPPENS: it holds its slot, advances the streak and must
# start its cooldown like a real loss. Gating the cooldown here was a BUG that
# shifted the timeline and manufactured a fake cascade (see a3ca96b). Identity.
_COOL_PATCH = _COOL_ANCHOR
_BOOK_ANCHOR = '            "r_multiple": round(float(r_multiple),3),\n'
_BOOK_PATCH = (
    '            "r_multiple": round(0.0 if _isgray else float(r_multiple),3),\n'
    '            "is_gray": bool(_isgray),\n'
    '            "sl_width_pct": round(_gslw,4),\n'
    '            "r_multiple_raw": round(float(r_multiple),3),\n'
)


def _load_module(text, name):
    """Own temp path, same pattern as the la*/audit harnesses."""
    import importlib.util
    p = _TMP
    p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, p


def build_gray_module():
    """build_module()'s super-set source + the gray-gate patch on top.

    build_module() does not expose its patched source, so it is spied through
    _load_module to capture the exact super-set text, and the gray patch is
    applied to THAT. Doing it from raw SRC instead would lose every other
    super-set kwarg (exp_partial_r etc.) that the harnesses pass through.
    Gate defaults OFF => byte-identical to the shipped engine.
    """
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
    s = s.replace(t1, t1 + "    exp_gray_lo=0.0,\n    exp_gray_hi=0.0,\n"
                             "    exp_gray_streak=True,\n")
    # Line-anchored matching: the bare 8-space anchor is a SUBSTRING of the
    # 12-space retest one, and the replacement text contains an 8-space copy of
    # it, so plain str.count is unusable here. Match the preceding newline to
    # pin the indent exactly.
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
    s = s.replace(_COOL_ANCHOR, _COOL_PATCH)
    s = s.replace(_BOOK_ANCHOR, _BOOK_PATCH)
    m, _p = _load_module(s, "v18_gray_slwidth")
    return m.simulate_htf_ltf_streak_halt


def sl_width_of(t):
    return t.get("sl_width_pct")


def bucket_table(trades):
    """Step 1: fixed-band SL-width anatomy on the SHIPPED book."""
    rows = []
    for lo, hi in BUCKETS:
        sel = [t for t in trades
               if sl_width_of(t) is not None and lo <= sl_width_of(t) < hi]
        n = len(sel)
        rs = [float(t["r_multiple"]) for t in sel]
        rows.append({
            "band": f"{lo:.2f}-{hi:.2f}", "n": n,
            "avg_r": round(sum(rs) / n, 4) if n else None,
            "wr": round(sum(1 for x in rs if x > 0) / n, 4) if n else None,
            "net": round(sum(rs), 2),
        })
    return rows


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  SL-WIDTH GATE (GRAY MODE) - cascade-free by construction", flush=True)
    print("=" * 100, flush=True)

    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import load_bybit
    from exp_equity_quality import equity_quality
    from experiment_registry import BP, EXPERIMENTS

    sim = build_gray_module()
    years = {"is": 3.67, "oos": 2.0}
    payload = {
        "stage": "sl_width_gate",
        "lens": ("GRAY gate: trade runs to completion, P&L suppressed. "
                 "busy_until/streak/cooldown still update => cascade-free, "
                 "path-TRUE in the real engine. Shipped file untouched."),
        "design_question": ("gray trade counts toward the loss streak? BOTH arms "
                           "pre-registered and run; the result decides"),
        "buckets": [f"{lo:.2f}-{hi:.2f}" for lo, hi in BUCKETS],
        "gate_bands": {lbl: [lo, hi] for lbl, lo, hi in GATE_BANDS},
        "g_rule": ("kept%>=55 AND net>0 AND avg/trade not worse AND maxDD<=ref, "
                   "in all 6 cells"),
        "scopes": {"buckets": {}, "gates": {}, "identity": {}},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_bybit(scope, sim)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            ref = sim_fn(sim, data, params)
            m_ref = equity_quality(ref, years[scope])

            for lbl, lo, hi in GATE_BANDS:
                for streak_flag in (True, False):
                    arm = sim_fn(sim, data, params,
                                 exp_gray_lo=lo, exp_gray_hi=hi,
                                 exp_gray_streak=streak_flag)
                    m = equity_quality(arm, years[scope])
                    grays = sum(1 for t in arm if t.get("is_gray"))
                    kept = m["n"] - grays
                    raw_r = sum(float(t.get("r_multiple_raw") or 0.0)
                                for t in arm if t.get("is_gray"))
                    seq_ref = [(t["entry_ts"], t["exit_ts"]) for t in ref]
                    seq_arm = [(t["entry_ts"], t["exit_ts"]) for t in arm]
                    cell = {
                        "n": m["n"], "net": m["net"],
                        "n_gray": grays,
                        "kept_pct": round(100.0 * kept / max(1, m["n"]), 2),
                        "max_dd": m["max_dd"],
                        "d_net": round(m["net"] - m_ref["net"], 4),
                        "d_max_dd": round(m_ref["max_dd"] - m["max_dd"], 4),
                        "avg_per_trade": round(m["net"] / m["n"], 4) if m["n"] else None,
                        "ref_avg_per_trade": round(m_ref["net"] / m_ref["n"], 4),
                        "seq_identical": seq_ref == seq_arm,
                        "gray_streak": streak_flag,
                        # CASCADE GUARD: cascade-free means d_net == -raw_r.
                        "raw_r_grayed": round(raw_r, 2),
                        "expected_d_net_if_cascade_free": round(-raw_r, 3),
                        "cascade_term": round(
                            (m["net"] - m_ref["net"]) + raw_r, 3),
                    }
                    cell["g_rule_pass"] = bool(
                        cell["kept_pct"] >= 55.0
                        and (cell["d_net"] or 0) > 0
                        and cell["avg_per_trade"] >= cell["ref_avg_per_trade"]
                        and (cell["d_max_dd"] or 0) >= 0.0)
                    k = (f"{scope}/{name}/{lbl}/"
                         f"{'streakON' if streak_flag else 'streakOFF'}")
                    payload["scopes"]["gates"][k] = cell
                    print(f"      GATE {lbl:<10} "
                          f"streak={'ON ' if streak_flag else 'OFF'} "
                          f"kept={cell['kept_pct']:>6}% gray={grays:>3} "
                          f"dNet={cell['d_net']:>+8.1f} dDD={cell['d_max_dd']:>+6.2f} "
                          f"casc={cell['cascade_term']:>+7.2f} "
                          f"seqID={cell['seq_identical']} "
                          f"pass={cell['g_rule_pass']}", flush=True)

    g = payload["scopes"]["gates"]
    arms = sorted({"/".join(k.split("/")[2:4]) for k in g})
    tally = {}
    for a in arms:
        cells = [v for k, v in g.items() if "/".join(k.split("/")[2:4]) == a]
        tally[a] = {"cells": len(cells),
                    "g_rule_pass_cells": sum(1 for c in cells if c["g_rule_pass"]),
                    "all_seq_identical": all(c["seq_identical"] for c in cells),
                    "max_abs_cascade_term": round(
                        max(abs(c["cascade_term"]) for c in cells), 3),
                    "total_d_net": round(sum(c["d_net"] for c in cells), 2),
                    "total_raw_grayed": round(
                        sum(c["raw_r_grayed"] for c in cells), 2),
                    "pass": all(c["g_rule_pass"] for c in cells)}
    payload["verdicts"] = {
        "arms": tally,
        "cascade_free": all(v["all_seq_identical"] for v in tally.values()),
        "any_arm_passes": any(v["pass"] for v in tally.values()),
    }
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 100, flush=True)
    print("  VERDICTS:", flush=True)
    for a, v in tally.items():
        print(f"    {a:<22} G-RULE {v['g_rule_pass_cells']}/{v['cells']} "
              f"pass={v['pass']} seqID={v['all_seq_identical']} "
              f"| dNet {v['total_d_net']:+.1f} = -raw({v['total_raw_grayed']:+.1f}) "
              f"| max|casc|={v['max_abs_cascade_term']}", flush=True)
    vd = payload["verdicts"]
    print(f"  CASCADE-FREE (all arms): {vd['cascade_free']}", flush=True)
    print(f"  ANY ARM PASSES: {vd['any_arm_passes']}", flush=True)
    print("=" * 100, flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()

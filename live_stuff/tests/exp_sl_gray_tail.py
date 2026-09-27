"""GRAY-MODE gate on the 3%+ SL-width band only - the surgical version.

WHY THIS IS DIFFERENT FROM f569879
-----------------------------------
That run grayed the WHOLE wide range (0.4-1.6% bands included), and those bands
are NOT all bad - 0.70-0.90% carries avgR +1.277 and 1.20-1.60% +0.461. Graying
a mixed cohort forfeits winners, which is why every arm went 0/36 with dNet<=0
in 36/36. The user's refinement is the right one: gray ONLY the band that is
uniformly bad.

From _sl_fine_cascade.json (costs-aware net_r, all six ledger controls exact):

    band        n    avgR      WR      net
    3.00-5.00   78  -0.1075   34.6%    -8.38
    5.00+       33  -0.4021   21.2%   -13.27
    --------------------------  TOTAL  -21.65

Per cell, 3%+ is negative in 5 of 6 (only oos/age10 3.00-5.00 is +1.8). So the
tail is uniformly a loser, and graying it should be a small POSITIVE dNet - not
a rescue of a good cohort, just a clean removal of a bad one.

MECHANISM (established in f569879 and ee8a42b)
------------------------------------------------
Gray trades still run to completion inside the engine, so busy_until, the loss
streak and cooldown all update and the slot is NOT refilled - unlike a
post-process removal. But ee8a42b also found that on the four BUSY books
seq_identical was False: the cooldown/streak timeline still moves a downstream
entry even without refilling the slot. age10 (sparse) stayed True. So this run
reports seq_identical per cell and treats it as reported-not-gated, because
whether the cascade term lands is an empirical question, not a design choice.

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
------------------------------------------
  Gate: gray any trade with sl_width_pct >= 3.0. Nothing else. No lower bound
  (the 0.25-2.00 region is left untouched - it holds the edge).
  Thresholds: 3.0 pre-registered from the (a10) ladder. A 2.5 arm is included
  as a sensitivity check ONLY, both reported, no best-of.
  G-RULE (all 6 cells): dNet > 0 AND kept% >= 85 AND maxDD not worse.
  The kept floor is high on purpose: this is a tail trim, not a filter, so a
  pass that gutted the book would not be the same claim.
  CONTROLS: base ledgers reproduce the 24.85 references; gray-OFF reproduces
  the shipped engine exactly (identity gate).
  No retune after the run.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_sl_gray_tail.py
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

OUT = ROOT / "live_stuff/tests/_sl_gray_tail.json"
_TMP = ROOT / "live_stuff/tests/_sltail_tmp.py"

# Gray ONLY above these. 0.0 lower bound = do not touch the good region.
GATE_ARMS = (("gray_ge_3.0", 3.0), ("gray_ge_2.5", 2.5))

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
# END_MARKER



def build_module():
    """Super-set source, spied, + a gray gate on sl_width_pct >= GATE_MIN.

    The gate is a ONE-SIDED upper bound: it only ever grays the wide tail and
    leaves the 0.25-2.00 region (where the edge lives) completely untouched.
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
    s = s.replace(t1, t1 +
                  "    exp_gray_min=0.0,\n    exp_gray_streak=True,\n")

    a = '        if i < 0 or i>=n-1: continue\n'
    assert s.count(a) == 1, "init anchor"
    s = s.replace(a, a +
                  '        _isgray = False\n        _gslw = 0.0\n')

    for ind in (8, 12):
        old = "\n" + " " * ind + "sl0=sl; sl_cur=sl; best=entry\n"
        assert s.count(old) == 1, f"sl anchor {ind}: {s.count(old)}"
        pad = " " * ind
        new = (
            f"\n{pad}if exp_gray_min>0 and not _isgray:\n"
            f"{pad}    _gslw=abs(entry-sl)/entry*100.0 if entry>0 else 0.0\n"
            f"{pad}    if _gslw >= exp_gray_min: _isgray=True\n"
            f"{pad}sl0=sl; sl_cur=sl; best=entry\n")
        s = s.replace(old, new)

    st = '        if max_consecutive_losses > 0:\n'
    assert s.count(st) == 1, "streak"
    s = s.replace(st, '        if max_consecutive_losses > 0 and not (_isgray and not exp_gray_streak):\n')
    cd = '        if cooldown_bars > 0 and r_multiple < 0:\n'
    assert s.count(cd) == 1, "cooldown"
    s = s.replace(cd, '        if cooldown_bars > 0 and r_multiple < 0 and not _isgray:\n')
    bk = '            "r_multiple": round(float(r_multiple),3),\n'
    assert s.count(bk) == 1, "book"
    s = s.replace(bk,
                  '            "r_multiple": round(0.0 if _isgray else float(r_multiple),3),\n'
                  '            "is_gray": bool(_isgray),\n'
                  '            "sl_width_pct": round(_gslw,4),\n'
                  '            "r_multiple_raw": round(float(r_multiple),3),\n')

    import importlib.util
    _TMP.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_sltail", str(_TMP))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.simulate_htf_ltf_streak_halt
# END_MARKER



def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  GRAY-MODE TAIL GATE - gray ONLY sl_width >= 3.0%", flush=True)
    print("=" * 100, flush=True)

    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import load_bybit
    from exp_equity_quality import equity_quality
    from experiment_registry import BP, EXPERIMENTS

    sim = build_module()
    years = {"is": 3.67, "oos": 2.0}
    payload = {
        "stage": "sl_gray_tail",
        "lens": ("ONE-SIDED gray gate: sl_width_pct >= min. The 0.25-2.00 region "
                 "is untouched. Trade runs to completion, P&L suppressed, so "
                 "busy_until/streak/cooldown all update - no slot refill."),
        "arms": {lbl: f"gray when sl_width_pct >= {g}" for lbl, g in GATE_ARMS},
        "g_rule": "dNet>0 AND kept%>=85 AND maxDD not worse, in all 6 cells",
        "pre_registered": {
            "threshold": "3.0 from the (a10) ladder; 2.5 is a sensitivity check only",
            "kept_floor": "85% - this is a tail trim, not a filter",
            "seq_identical": "reported per cell, NOT gated (ee8a42b showed the "
                             "busy books still move a downstream entry)",
            "control": "base ledgers reproduce 24.85; identity gate on",
            "no_retune": "nothing retuned after the run",
        },
        "cells": {}, "verdicts": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_bybit(scope, sim)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            ref = sim_fn(sim, data, params)
            m_ref = equity_quality(ref, years[scope])
            exp_n, exp_net = BYBIT_BASE[name][scope]
            assert m_ref["n"] == exp_n and abs(m_ref["net"] - exp_net) < 0.5, (
                f"CONTROL {scope}/{name}")
            print(f"  {scope}/{name} ref n={m_ref['n']} net={m_ref['net']:+.1f} "
                  f"DD={m_ref['max_dd']} [ctrl OK]", flush=True)

            for lbl, g in GATE_ARMS:
                arm = sim_fn(sim, data, params, exp_gray_min=g)
                m = equity_quality(arm, years[scope])
                grays = sum(1 for t in arm if t.get("is_gray"))
                kept_pct = 100.0 * (m["n"] - grays) / max(1, m["n"])
                raw = sum(float(t.get("r_multiple_raw") or 0.0)
                          for t in arm if t.get("is_gray"))
                d_net = m["net"] - m_ref["net"]
                d_dd = m_ref["max_dd"] - m["max_dd"]
                seq = ([(t["entry_ts"], t["exit_ts"]) for t in ref]
                       == [(t["entry_ts"], t["exit_ts"]) for t in arm])
                cell = {
                    "n": m["n"], "n_gray": grays,
                    "kept_pct": round(kept_pct, 2),
                    "net": m["net"], "d_net": round(d_net, 3),
                    "d_max_dd": round(d_dd, 3),
                    "raw_r_grayed": round(raw, 2),
                    "seq_identical": seq,
                    "g_rule_pass": bool(d_net > 0 and kept_pct >= 85.0
                                        and d_dd >= 0.0),
                }
                payload["cells"][f"{scope}/{name}/{lbl}"] = cell
                print(f"      {lbl:<14} gray={grays:>3} kept={kept_pct:>6.2f}% "
                      f"dNet={d_net:>+7.2f} dDD={d_dd:>+6.2f} "
                      f"rawR_grayed={raw:>+7.2f} seqID={seq} "
                      f"pass={cell['g_rule_pass']}", flush=True)

    print("\n" + "=" * 100, flush=True)
    for lbl, _ in GATE_ARMS:
        cells = [v for k, v in payload["cells"].items() if k.endswith(lbl)]
        tally = {
            "cells": len(cells),
            "g_rule_pass_cells": sum(1 for c in cells if c["g_rule_pass"]),
            "dnet_positive_cells": sum(1 for c in cells if c["d_net"] > 0),
            "seq_identical_cells": sum(1 for c in cells if c["seq_identical"]),
            "total_d_net": round(sum(c["d_net"] for c in cells), 2),
            "total_raw_grayed": round(sum(c["raw_r_grayed"] for c in cells), 2),
        }
        tally["pass"] = tally["g_rule_pass_cells"] == tally["cells"]
        payload["verdicts"][lbl] = tally
        print(f"  {lbl:<14} G-RULE {tally['g_rule_pass_cells']}/{tally['cells']} "
              f"| dNet>0 in {tally['dnet_positive_cells']}/{tally['cells']} "
              f"| seqID {tally['seq_identical_cells']}/{tally['cells']} "
              f"| total dNet {tally['total_d_net']:+.1f} "
              f"(raw grayed {tally['total_raw_grayed']:+.1f})", flush=True)
    print("=" * 100, flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()

"""PATH-TRUE causal bias-momentum — owner swing confirmation CLOSED by entry.

Part-2 leak audit (exp_opposed_leadstudy.py): the bm ratio attaches FINAL 1h
swing magnitudes to break times that fire while the swing is still forming —
471/500 champion entries have an UNCONFIRMED owner swing, 380/500 have the
owner's END after entry, and 120/500 gate decisions flip under an
entry-truncated recompute (audit verdict: LEAKY).

Live-parity fix (exp_bm_causal=1, default 0 = identity): compute_btc_swings
only emits DECLARED swings, so the live break list at entry contains only
breaks whose owning swing's confirmation candle CLOSED by the entry instant
(signal bar close). Walk back to the last such break; if none, gate passes.

Definition note: this is the LIVE-STATE causal definition (declared-only,
final mags — exactly what a live chart would hold). Part-2's 120/500 flip
count used a stricter running-mag recompute from raw candles; both are
causal, live-parity is the one that ships or dies here.

Run: python live_stuff/tests/exp_causal_bm_path.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, identity_gate, net_r
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS as REG
from exp_alignment_validate import metrics


def show(tag, tr, pins=None):
    s = craze.stats(tr)
    nt = net_r(tr)
    pin_s = ""
    if pins:
        pin_s = "  pins n=%s net=%s" % (pins.get("n"), pins.get("net"))
    print("  %-46s n=%3d  gross=%+7.1f  NET=%+7.1f  WR=%4.1f%%  DD=%5.1f%s"
          % (tag, s["n"], s["gross"], nt, s["wr"], s["dd"], pin_s))


def main():
    t0 = time.time()
    print("=" * 100)
    print("  PATH-TRUE causal bias-momentum (exp_bm_causal: owner conf CLOSE <= entry instant)")
    print("=" * 100)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    fine = data["fine"]

    keys = [
        "bm05_multi_sw10",
        "bm08_multi_sw10",
        "bm05_utcsat_multi_sw10",
        "bm08_utcsat_multi_sw10",
        "bm05_swingpause_single_sw10",
        "bm05_multi_sw20",
        "union_multi",
        "dualunion_multi",
    ]

    def has_gate(key):
        return bool(REG[key]["params"].get("exp_bias_momentum_min"))

    def swing_of(key):
        return REG[key].get("swing", "sw10")

    def run(key, causal, swing="sw10"):
        cfg = REG[key]
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        if causal and has_gate(key):
            p["exp_bm_causal"] = 1
        r = sim(data["c1h"], data[swing], data["c15"], data["sw15"],
                fine_ltf=fine, **p)
        return r["ltf_trades"] if isinstance(r, dict) else r

    print("\n--- champion ref (no bm gate) ---")
    tr_ref = run("champion_multi_sw10", causal=False, swing="sw10")
    show("champion_multi_sw10 [ref]", tr_ref,
         REG["champion_multi_sw10"].get("pins"))

    print("\n--- IS: old (leaky) vs CAUSAL (owner conf closed by entry) ---")
    for key in keys:
        swing = swing_of(key)
        tr_old = run(key, causal=False, swing=swing)
        show(key + " [old]", tr_old, REG[key].get("pins"))
        if has_gate(key):
            tr_c = run(key, causal=True, swing=swing)
            show(key + " [CAUSAL]", tr_c)
            print("      delta NET causal-old = %+.1f"
                  % (net_r(tr_c) - net_r(tr_old)))
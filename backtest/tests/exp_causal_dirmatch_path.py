"""PATH-TRUE causal dirmatch — confirmed_at_idx <= entry bar.

Uses craze exp_dir_causal=1 (patched into the selector). Default 0 = identity.

Run: python backtest/tests/exp_causal_dirmatch_path.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
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
    print("  PATH-TRUE causal dir-match (exp_dir_causal: confirmed_at_idx <= entry)")
    print("=" * 100)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    fine = data["fine"]

    keys = [
        "champion_multi_sw10",
        "dirmatch_multi_sw10",
        "age25_dirmatch_multi_sw10",
        "age10_dirmatch_multi_sw10",
        "dirmatch_swingpause_single_sw10",
        "age10_dirmatch_swingpause_single_sw10",
        "age10_dirmatch_multi_sw10",
    ]
    # dedupe
    keys = list(dict.fromkeys(keys))

    def has_gate(key):
        p = REG[key]["params"]
        return bool(p.get("exp_require_dir_match") or p.get("exp_max_swing_age"))

    def run(key, causal, swing_key="sw10"):
        cfg = REG[key]
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        if causal and has_gate(key):
            p["exp_dir_causal"] = 1
        sw = data[swing_key]
        r = sim(data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=fine, **p)
        return r["ltf_trades"] if isinstance(r, dict) else r

    print("\n--- IS sw10: old vs causal (confirmed_at<=i) ---")
    is_old, is_cas = {}, {}
    for key in keys:
        tr_old = run(key, causal=False)
        is_old[key] = tr_old
        show(key + " [old]", tr_old, REG[key].get("pins"))
        if has_gate(key):
            tr_c = run(key, causal=True)
            is_cas[key] = tr_c
            show(key + " [CAUSAL]", tr_c)
            print("      delta NET causal-old = %+.1f" % (net_r(tr_c) - net_r(tr_old)))

    # Sanity: causal flag OFF must equal old for dirmatch (selector unchanged)
    tr_off = run("dirmatch_multi_sw10", causal=False)
    print("\n  sanity dirmatch causal-off still matches pin:", REG["dirmatch_multi_sw10"].get("pins"),
          "got n=%d net=%.1f" % (len(tr_off), net_r(tr_off)))

    print("\n--- TRUE OOS 2021-2022 sw10 ---")
    from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
    from engine.v18_params import SWING
    from src.btc.btc_routes import _compute_swings

    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])

    def run_oos(key, causal):
        cfg = REG[key]
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        if causal and has_gate(key):
            p["exp_dir_causal"] = 1
        r = sim(c1ho, sw10o, c15o, sw15o, fine_ltf=fineo, **p)
        return r["ltf_trades"] if isinstance(r, dict) else r

    for key in keys:
        tr_old = run_oos(key, causal=False)
        m0 = metrics(tr_old)
        print("  %-46s [old]  n=%3d NET=%+7.1f WR=%4.1f%%" % (key, m0["n"], m0["net"], m0["wr"]))
        if has_gate(key):
            tr_c = run_oos(key, causal=True)
            m1 = metrics(tr_c)
            print("  %-46s [CAUS] n=%3d NET=%+7.1f WR=%4.1f%%  dNET=%+.1f"
                  % (key, m1["n"], m1["net"], m1["wr"], m1["net"] - m0["net"]))

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()

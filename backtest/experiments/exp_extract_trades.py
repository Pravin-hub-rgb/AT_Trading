"""Extract per-trade (timestamp, net R) series for every book, both eras.

PBO and DSR both need the actual return SERIES, not summary statistics. The
whole point of CSCV is to re-partition time and see whether the winner in one
sample survives in another, and that is impossible from a table of headline
numbers.

Caching matters here: rebuilding this requires re-running the engine for 13
books across 2 eras, which takes minutes. The trade series it produces is
deterministic, so it is written once and every later statistic reads the cache.

Output: trades_series.json, shaped {book: {"is": [[ts, r], ...], "oos": [...]}}
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
sys.path.insert(0, os.path.join(HERE, "..", "tests"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

NM = {
    "fsent_champ_long_mcloff_htf15": "107",
    "fsent_champ_long_htf15_tskip6": "110",
    "fsent_champ_long_htffs": "106",
    "fsent_champ_long_htf15_htffs": "109",
    "fsent_champ_long_htfesmcl4": "108",
    "fsent_sig_multi_acc": "acc",
    "fsent_champ_long_htf15": "htf15",
    "fsent_champ_long_mcloff": "mcloff",
    "fsent_champ_long_causalfloor": "cfloor",
    "fsent_champ_long_mode_chop": "mchop",
    "fsent_champ_long_biasmom05": "bmom",
    "fsent_sig_multi_htffs": "sigm_h",
    "fsent_sig_multi": "sigm",
}

OUT = os.path.join(HERE, "trades_series.json")


def main():
    print("loading eras ...", flush=True)
    era = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    t0 = 0.0
    import time as _t
    _s = _t.time()
    for name, code in NM.items():
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {"code": code}
        for e in ("is", "oos"):
            o = sim(era[e]["c1h"], get_swings(era[e], swing), era[e]["c15"],
                    era[e]["sw15"], fine_ltf=era[e]["fine"],
                    **{**BP, **(cfg.get("params") or {})})
            tr = sorted([t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
                         if t.get("outcome") != "open"],
                        key=lambda t: int(t["entry_ts"]))
            res[name][e] = [[int(t["entry_ts"]), round(net_r([t]), 6)] for t in tr]
        n = len(res[name]["is"]) + len(res[name]["oos"])
        print("  %-6s %4d is + %4d oos = %5d trades  (%.0fs)"
              % (code, len(res[name]["is"]), len(res[name]["oos"]), n,
                 _t.time() - _s), flush=True)

    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh)
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
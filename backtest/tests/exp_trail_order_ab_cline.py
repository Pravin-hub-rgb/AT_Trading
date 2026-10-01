"""A/B: trail-event ordering. Patch: apply pending trail event BEFORE SL check,
never drop it (stop is at cand the moment its activation ts passes). Quantifies
the 'event consumed without applying' optimism on anchor + champion."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

import importlib.util
from run_experiment import get_data, BP, EXPERIMENTS, fund
from src.btc.btc_routes import _trade_costs
from engine.v18_params import get_v18_params as gvp

G = gvp("BTCUSDT_BYBIT")
ENGINE = ROOT / "backend/src/btc/engines/htf_ltf/v18_streak_halt.py"
SRC = ENGINE.read_text(encoding="utf-8")


def build(patched: bool):
    s = SRC
    if patched:
        a_long = "                        if sl_cur_f < cand < lo:\n                            sl_cur_f=cand\n"
        a_short = "                        if hi < cand < sl_cur_f:\n                            sl_cur_f=cand\n"
        assert s.count(a_long) == 1 and s.count(a_short) == 1, "patch anchors not unique"
        s = s.replace(a_long, "                        if sl_cur_f < cand:\n                            sl_cur_f=cand\n")
        s = s.replace(a_short, "                        if cand < sl_cur_f:\n                            sl_cur_f=cand\n")
    p = Path(ROOT / "backtest/tests/_trail_ab_tmp.py")
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_trail_ab", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    try:
        p.unlink()
    except OSError:
        pass
    return m.simulate_htf_ltf_streak_halt


def report(tag, tr):
    rs = [float(t["r_multiple"]) for t in tr]
    pk = cm = dd = 0.0
    for x in rs:
        cm += x; pk = max(pk, cm); dd = max(dd, pk - cm)
    c2, _ = _trade_costs(tr, G["fee_pct"], 0.0, G["entry_slip_pct"], G["exit_slip_pct"])
    net = sum(rs) - c2 - fund(tr)
    wr = 100.0 * len([x for x in rs if x > 0]) / max(len(tr), 1)
    print("  %-34s n=%d gross=%+.1f NET=%+.1f DD=%.1f WR=%.1f%%" % (tag, len(tr), sum(rs), net, dd, wr))
    return rs


def main():
    data = get_data()
    import test_experiments_craze as craze
    sim_a = build(False)          # shipped-order engine (anchor A/B)
    sim_b = build(True)           # causal-stop engine  (anchor A/B)
    # champion: patcher's superset module, with/without the causal-stop patch
    champ_a = craze.build_module()
    orig_loader = craze._load_module

    def causal_loader(text, name):
        a_long = "                        if sl_cur_f < cand < lo:\n                            sl_cur_f=cand\n"
        a_short = "                        if hi < cand < sl_cur_f:\n                            sl_cur_f=cand\n"
        assert text.count(a_long) == 1 and text.count(a_short) == 1, "champ patch anchors"
        return orig_loader(text.replace(a_long, "                        if sl_cur_f < cand:\n                            sl_cur_f=cand\n")
                                .replace(a_short, "                        if cand < sl_cur_f:\n                            sl_cur_f=cand\n"), name)

    craze._load_module = causal_loader
    try:
        champ_b = craze.build_module()
    finally:
        craze._load_module = orig_loader

    print("=== ANCHOR (BP, fine, mb50/sw20) — trail ordering A/B ===")
    ra = report("as-shipped (SL check first, may drop event)",
                sim_a(data["c1h"], data["sw20"], data["c15"], data["sw15"], fine_ltf=data["fine"], **dict(BP))["ltf_trades"])
    rb = report("causal-stop (event applied before SL check)",
                sim_b(data["c1h"], data["sw20"], data["c15"], data["sw15"], fine_ltf=data["fine"], **dict(BP))["ltf_trades"])
    print("  anchor optimism delta (gross): %+.1fR over %d vs %d trades" % (sum(ra) - sum(rb), len(ra), len(rb)))
    print("=== CHAMPION multi sw10 — trail ordering A/B ===")
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    ca = report("as-shipped", champ_a(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **params)["ltf_trades"])
    cb = report("causal-stop", champ_b(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **params)["ltf_trades"])
    print("  champion optimism delta (gross): %+.1fR over %d vs %d trades" % (sum(ca) - sum(cb), len(ca), len(cb)))


if __name__ == "__main__":
    main()

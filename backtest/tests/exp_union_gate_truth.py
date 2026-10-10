"""Instrument the engine so a trade records the window that ACTUALLY gated it.

The slack audit found 15 trades whose recorded window_start points at a window
whose 1h candle closes after the decision instant. That is arithmetically
impossible for a trade that passed `_s + 2700 < bar_ts + 900 < _e`, so either the
gate and the report disagree, or those trades came through a different door. The
reconstruction in exp_union_window_label.py says a causal gate window does exist
for each of them and the report simply names the wrong one - but it cannot prove
which window the gate used, because it only sees the trade record.

This patches the engine source so every filtered signal carries the bar_ts the
gate actually evaluated, and every booked trade records it. Then the question
"did the trade use a window that had already closed?" is answerable directly
instead of by reconstruction.

Same technique as build_family_module: capture the source text, patch it, load it.
The shipped engine is used unpatched otherwise - no floor, bar-secs or plane
overrides - so this measures the code that actually runs.
"""
import sys

sys.path.insert(0, ".")

import test_experiments_craze as tc          # noqa: E402

# (old, new, expected occurrences)
PATCHES = [
    # 1. carry the gate's bar_ts out of the filtering loop. Two append sites and
    # they differ in spacing - the union branch writes it tight, the shared path
    # writes it spaced. Match both rather than normalising, so a drift in either
    # one shows up as an anchor failure instead of silently patching neither.
    ("filtered.append((sig,use,win_start,win_end))",
     "filtered.append((sig,use,win_start,win_end,bar_ts))", 1),
    ("filtered.append((sig, use, win_start, win_end))",
     "filtered.append((sig, use, win_start, win_end, bar_ts))", 1),
    # 2. unpack it
    ("for sig, use, win_start, win_end in filtered:",
     "for sig, use, win_start, win_end, gate_bar_ts in filtered:", 1),
    # 3. record it on the trade, next to the window it was taken in
    ('            "window_start": int(win_start),',
     '            "window_start": int(win_start),\n'
     '            "gate_bar_ts": int(gate_bar_ts),', 1),
]


def build():
    cap = {}
    orig = tc._load_module

    def spy(text, name):
        cap["text"] = text
        cap["name"] = name
        return orig(text, name)

    tc._load_module = spy
    try:
        tc.build_module()
    finally:
        tc._load_module = orig

    s = cap["text"]
    for old, new, n in PATCHES:
        got = s.count(old)
        assert got == n, "anchor %r: expected %d, found %d" % (old[:44], n, got)
        s = s.replace(old, new)
    # _load_module returns (module, temp_path); build_module returns the engine
    # entry point off it, so take the same thing rather than the module.
    return tc._load_module(s, cap.get("name", "instrumented_unified"))[0]\
        .simulate_htf_ltf_streak_halt


def main():
    from run_experiment import get_swings                 # noqa: E402
    from exp_signal_metrics import load_era               # noqa: E402
    from experiment_registry import EXPERIMENTS           # noqa: E402

    sim = build()
    base = dict(EXPERIMENTS["fsent_champ_long"]["params"])
    LTF_CLOSE, HTF_CLOSE = 900, 3600

    print("=" * 92)
    print("INSTRUMENTED RUN - what the gate saw vs what the trade recorded")
    print("=" * 92)

    for book in ("fsent_champ_long", "fsent_champ_long_mode_union"):
        params = {**base, **(EXPERIMENTS[book].get("params") or {})}
        d = load_era("oos")
        out = sim(d["c1h"], get_swings(d, "sw10"), d["c15"], d["sw15"],
                  fine_ltf=d["fine"], **params)
        n = miss = bad_gate = bad_label = 0
        flagged_rows = []
        flagged_rows = []
        worst = None
        for t in out["ltf_trades"]:
            if t.get("outcome") == "open":
                continue
            n += 1
            if "gate_bar_ts" not in t:
                miss += 1
                continue
            gb = int(t["gate_bar_ts"])
            ws = int(t["window_start"])
            # THE decisive check. win_start rode along with this signal and
            # gate_bar_ts is the bar the gate actually evaluated, so if the trade
            # came through the window gate then
            #     win_start + 2700 < gate_bar_ts + 900 < win_end
            # must hold. If it does not, the recorded window is not the window
            # this signal was gated on.
            # the window gate as written admits slack > -900. If the recorded
            # window is the gating window this must hold for every trade.
            gated_ok = (ws + 2700 < gb + LTF_CLOSE) and (gb + LTF_CLOSE
                                                          < int(t["window_end"]))
            if not gated_ok:
                bad_gate += 1
                if len(flagged_rows) < 8:
                    flagged_rows.append((
                        t["trade_no"], t.get("htf_regime"), gb, ws,
                        int(t["window_end"]), (gb + LTF_CLOSE) - (ws + HTF_CLOSE)))
            if abs(gb - int(t["entry_ts"])) > 0:
                bad_label += 1
            gate_slack = (gb + HTF_CLOSE) - (ws + HTF_CLOSE)
            if gate_slack > (worst or -10**9):
                worst = gate_slack
        print("\n  %s" % book)
        print("    trades=%d   missing gate_bar_ts=%d" % (n, miss))
        print("    gate bar_ts != booked entry_ts              : %d" % bad_label)
        print("    recorded window satisfies the gate          : %d of %d"
              % (n - bad_gate, n))
        if worst is not None:
            print("    max (gate_bar_ts - window_start)            : %+d s" % worst)
        for r in flagged_rows:
            print("      #%-4d regime=%-8s gate_bar_ts=%d window=[%d,%d] slack=%+d"
                  % r)

    print()
    print("  If gate_bar_ts == entry_ts on every trade, the two lookups agree and")
    print("  the recorded window_start is the gating window. If they differ, the")
    print("  filtering loop and the booking loop are reading different bars.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
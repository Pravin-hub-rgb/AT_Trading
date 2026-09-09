"""DEEP DIVE: marks of swing N firing while swing N-1's FS/chop confirmation
has NOT arrived yet (the 'prev swing unconfirmed' state).

The user's live-doubt, pushed to its hardest case:
  - prev swing's FS comes LATE (or its marks are still printing)
  - meanwhile the CURRENT swing's B1/B2/FLIP already fired
  - can you really trade those? what SL? what happened historically?

Quantified over the FULL 4-year dataset, both TFs:
  1h chain (HTF, flip stream) and 15m chain (LTF, decisive stream),
  plus join with the actual v18 LTF trades -> R outcomes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.btc_engine import _collect_signals
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle


def load(tf):
    df = load_btc_df(tf)
    c, f = [], []
    for row in df.itertuples():
        date = str(row.timestamp)
        c.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                  "high": float(row.high), "low": float(row.low),
                  "close": float(row.close)})
        f.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                            low=float(row.low), close=float(row.close)))
    return c, f


def analyze(candles, swings, label):
    print(f"\n{'='*76}\n{label}  ({len(swings)} swings, {len(candles)} bars)\n{'='*76}")
    n_marks = n_pre_prev_conf = n_pre_prev_fs = 0
    n_never_confirmed_prev = 0
    examples = []
    for i, s in enumerate(swings):
        if i == 0:
            continue
        prev = swings[i - 1]
        pconf = int(prev.get("confirmed_at_idx", -1))
        pfs = int(prev.get("fs_at_idx", -1))
        for b in sorted(s["breaks"], key=lambda x: int(x["idx"])):
            bi = int(b["idx"])
            n_marks += 1
            prev_unconf = (pconf < 0) or (bi < pconf)
            before_fs = (pfs < 0) or (bi < pfs)
            if prev_unconf:
                n_pre_prev_conf += 1
                if pconf < 0:
                    n_never_confirmed_prev += 1
                if before_fs:
                    n_pre_prev_fs += 1
                if len(examples) < 8 and bi < len(candles):
                    examples.append((i, b, pconf, pfs, candles[bi]["date"]))
    print(f"marks total                       : {n_marks}")
    print(f"marks fired while PREV unconfirmed: {n_pre_prev_conf}"
          f"  ({100*n_pre_prev_conf/max(1,n_marks):.1f}%)")
    print(f"  ...of which also BEFORE prev FS : {n_pre_prev_fs}")
    print(f"  ...prev swing never confirmed   : {n_never_confirmed_prev}")
    print("first examples:")
    for i, b, pconf, pfs, d in examples:
        pd = candles[pconf]["date"] if 0 <= pconf < len(candles) else "NEVER"
        print(f"   sw{i} {b['kind']:<4} {b['dir']:<4} @ {d}  "
              f"(prev confirm @ {pd}, px={b['px']:.2f})")
    return n_marks, n_pre_prev_conf


# ---------------- 1h chain ----------------
c1h, f1h = load("1h")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
analyze(c1h, sw1h, "HTF 1h chain")

sigs1h = _collect_signals(sw1h, "flip", skip_first=True, selection="stream", candles=c1h)
conf1 = {s["swing_index"]: int(s.get("confirmed_at_idx", -1)) for s in sw1h}
pre = [sg for sg in sigs1h
       if sg["swing_no"] >= 1
       and (conf1.get(sg["swing_no"] - 1, -1) < 0
            or sg["bar"] < conf1.get(sg["swing_no"] - 1))]
print(f"\nHTF flip signals total {len(sigs1h)}; fired while PREV swing unconfirmed: {len(pre)}"
      f"  ({100*len(pre)/max(1,len(sigs1h)):.1f}%)")
for sg in pre[:6]:
    print(f"   {c1h[sg['bar']]['date']}  {sg['kind']:<4} {'long' if sg['dir']==1 else 'short':<5}"
          f" sw{sg['swing_no']}  SLpx={sg['swing_start_px']:.2f}")

# ---------------- 15m chain ----------------
c15, f15 = load("15m")
sw15 = _compute_swings(f15, "continuous", min_bars=50)
analyze(c15, sw15, "LTF 15m chain")

sigs15 = _collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)
conf15 = {s["swing_index"]: int(s.get("confirmed_at_idx", -1)) for s in sw15}
pre15 = [sg for sg in sigs15
         if sg["swing_no"] >= 1
         and (conf15.get(sg["swing_no"] - 1, -1) < 0
              or sg["bar"] < conf15.get(sg["swing_no"] - 1))]
print(f"\nLTF decisive signals total {len(sigs15)}; fired while PREV swing unconfirmed: {len(pre15)}"
      f"  ({100*len(pre15)/max(1,len(sigs15)):.1f}%)")
pre_keys = {(sg["swing_no"], sg["bar"], sg["dir"]) for sg in pre15}

# ---------------- join with actual v18 trades ----------------
t0 = min(c1h[0]["ts"], c15[0]["ts"]); t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)
res = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)
tr = [t for t in res["ltf_trades"] if t["outcome"] != "open"]
in_state = []
for t in tr:
    d = 1 if t["dir"] == "long" else -1
    if (t["swing_no"], t["entry_idx"], d) in pre_keys:
        in_state.append(t)
rg = sum(t["r_multiple"] for t in tr)
ri = sum(t["r_multiple"] for t in in_state)
wins_i = sum(1 for t in in_state if t["r_multiple"] > 0)
print(f"\n=== v18 LTF trades: {len(tr)} total, gross {rg:+.1f}R ===")
print(f"trades whose entry mark fired while PREV swing unconfirmed: {len(in_state)}"
      f"  ({100*len(in_state)/max(1,len(tr)):.1f}% of trades), gross {ri:+.1f}R"
      f"  ({100*ri/max(1e-9,rg):.1f}% of gross), win {wins_i}/{len(in_state)}")
print("sample:")
for t in in_state[:10]:
    print(f"   #{t['trade_no']} {t['dir']:<5} {t['break_kind']:<4} sw{t['swing_no']}"
          f" entry {t['entry_date']}  {t['r_multiple']:+.3f}R ({t['outcome']})")

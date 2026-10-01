"""CAUSAL SWING-STATE REPLAY — what did live know at each entry bar?

The batch swings_ltf only contains DECLARED swings with FINAL dir/start_idx
(FLIP can rewrite both before chop/sustain). Autopsy used that final state =
lookahead.

This replays SwingEngine bar-by-bar and snapshots (dir, start_idx, declared)
at every bar, then re-buckets champion trades by the LIVE state at entry.

Run: python backtest/tests/exp_alignment_live_state_audit.py
"""
import sys
import bisect
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS
import test_experiments_craze as craze
from src.firstswing import SwingEngine
from src.btc.btc_swing import compute_btc_swings  # noqa: F401  (parity check)


def replay_live_state(flow, min_bars):
    """Per-bar live knowledge: last DECLARED swing (final-at-declare) + forming engine.

    Mirrors compute_btc_swings stitch, but never lets a later engine overwrite
    an already-declared confirmation snapshot. Forming (undeclared) bars for the
    active engine are written forward only.
    """
    opts = {"minBars": max(2, int(min_bars)), "sustainBars": 7, "b2GapBars": 1,
            "timeCap": "00:00"}
    cap = max(1, len(flow) // 2)
    state = [{"dir": None, "start_idx": -1, "declared": False, "swing_index": -1,
              "confirmed_at": -1}
             for _ in range(len(flow))]
    last_declared = {"dir": None, "start_idx": -1, "swing_index": -1, "confirmed_at": -1}
    swing_index = 0
    next_start_pos = 0
    while swing_index < cap:
        eng = SwingEngine(dict(opts))
        if swing_index > 0:
            eng.defer_same_bar_arm = True
        found = False
        form_start = next_start_pos
        for pos in range(next_start_pos, len(flow)):
            c = flow[pos]
            eng.process_bar(c, pos)
            if eng.declared:
                # confirmation is known AT this bar — snapshot without overwrite
                state[pos] = {
                    "dir": eng.dir,
                    "start_idx": eng.start_idx,
                    "declared": True,
                    "swing_index": swing_index,
                    "confirmed_at": int(eng.confirmed_at_idx),
                }
                last_declared = {
                    "dir": eng.dir,
                    "start_idx": eng.start_idx,
                    "swing_index": swing_index,
                    "confirmed_at": int(eng.confirmed_at_idx),
                }
                # Fill forming bars this engine owned (form_start..pos-1) if still empty
                # or only forming placeholders — use this engine's pre-declare state.
                # For bars before declare, live had forming dir/start (may be None early).
                for bp in range(form_start, pos):
                    if state[bp]["declared"]:
                        continue  # never clobber a prior confirmation
                    # approximate forming state at bp with engine state at declare
                    # only where still unset/None — better: snapshot was overwritten;
                    # re-run is expensive, so keep last_declared for later bars.
                    if state[bp]["dir"] is None and eng.dir is not None:
                        # don't backfill with post-entry knowledge — leave forming as-is
                        pass
                end_abs = eng.end_idx
                end_pos = end_abs if 0 <= end_abs < len(flow) else pos
                next_start_pos = end_pos + 1
                found = True
                swing_index += 1
                break
            # forming bar — live knows engine dir/start if set (causal at end of bar)
            # Only write if not already a confirmation from a previous swing that
            # somehow overlaps (should not happen with sequential stitch).
            if not state[pos]["declared"]:
                state[pos] = {
                    "dir": eng.dir,
                    "start_idx": eng.start_idx,
                    "declared": False,
                    "swing_index": swing_index,
                    "confirmed_at": -1,
                    "last_declared_dir": last_declared["dir"],
                    "last_declared_start": last_declared["start_idx"],
                }
        if not found:
            break
    # Bars never touched: inherit last_declared
    for i, s in enumerate(state):
        if s["dir"] is None and s["start_idx"] < 0 and not s["declared"]:
            if last_declared["dir"] is not None:
                s["dir"] = last_declared["dir"]
                s["start_idx"] = last_declared["start_idx"]
                s["swing_index"] = last_declared["swing_index"]
    return state


def bucket_print(title, rows, key_fn, bins):
    print(f"\n--- {title} ---")
    for b in bins:
        lst = [r for r in rows if key_fn(r) == b]
        if not lst:
            print(f"  {b:<16} n=0")
            continue
        n = len(lst)
        rs = [r["r"] for r in lst]
        wr = 100.0 * sum(1 for x in rs if x > 0) / n
        print(f"  {b:<16} n={n:4d}  R={sum(rs):+8.1f}  avg={sum(rs)/n:+6.3f}  WR={wr:5.1f}%")


def age_band(a):
    if a < 0:
        return "z:no_start"
    if a <= 10:
        return "a:0-10"
    if a <= 25:
        return "b:11-25"
    if a <= 50:
        return "c:26-50"
    return "d:51+"


def main():
    data = get_data()
    f15 = data["f15"]
    mb15 = getattr(craze, "MB15", 50)
    print(f"replaying live 15m swing state (min_bars={mb15}, n={len(f15)}) ...")
    live = replay_live_state(f15, mb15)
    print(f"  replayed {len(live)} bars")

    # Parity: declared count vs batch
    batch_sw = data["sw15"]
    n_decl_live = sum(1 for s in live if s["declared"])
    # last bar of each declared swing counts once — count unique swing_index declared
    decl_idx = {s["swing_index"] for s in live if s["declared"] and s["swing_index"] >= 0}
    print(f"  batch swings: {len(batch_sw)}  live declared unique: {len(decl_idx)}")

    sim = craze.build_module()
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    batch = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)["ltf_trades"]
    print(f"champion trades: {len(batch)}")

    ts15 = [int(c["ts"]) for c in data["c15"]]
    sw15 = data["sw15"]
    by_index = {int(s.get("swing_index", i)): s for i, s in enumerate(sw15)}

    rows = []
    no_state = 0
    for t in batch:
        E = int(t["entry_ts"])
        e_idx = bisect.bisect_left(ts15, E)
        r = float(t["r_multiple"])
        d = 1 if t["dir"] == "long" else -1

        st = live[e_idx] if 0 <= e_idx < len(live) else None
        if st is None or (st["dir"] is None and st["start_idx"] < 0):
            no_state += 1
            continue

        live_dir = 0
        if st["dir"] == "up":
            live_dir = 1
        elif st["dir"] == "down":
            live_dir = -1
        live_start = int(st["start_idx"])
        live_age = e_idx - live_start if live_start >= 0 else -1
        live_match = (live_dir != 0 and live_dir == d)

        # final batch selector (old autopsy)
        raw = None
        for s in sw15:
            gsi = int((s.get("seg") or {}).get("start_idx", -1))
            if 0 <= gsi <= e_idx:
                raw = s
        raw_dir = 0
        raw_start = -1
        if raw is not None:
            raw_dir = 1 if raw.get("dir") == "up" else -1
            raw_start = int((raw.get("seg") or {}).get("start_idx", -1))
        raw_age = e_idx - raw_start if raw_start >= 0 else -1
        raw_match = (raw_dir != 0 and raw_dir == d)

        sno = t.get("swing_no")
        sn = by_index.get(int(sno)) if sno is not None else None
        sn_dir = 0
        if sn is not None:
            sn_dir = 1 if sn.get("dir") == "up" else -1

        rows.append({
            "r": r, "d": d, "e_idx": e_idx,
            "live_dir": live_dir, "live_start": live_start, "live_age": live_age,
            "live_match": live_match, "live_declared": bool(st["declared"]),
            "raw_dir": raw_dir, "raw_age": raw_age, "raw_match": raw_match,
            "sn_dir": sn_dir,
            "dir_flip": (live_dir != 0 and raw_dir != 0 and live_dir != raw_dir),
        })

    n = len(rows)
    print(f"\n=== LIVE STATE AT ENTRY (n={n}, no_state={no_state}) ===")
    print(f"  forming swing undeclared at entry: {sum(1 for r in rows if not r['live_declared'])} "
          f"({100.0*sum(1 for r in rows if not r['live_declared'])/max(n,1):.1f}%)")
    print(f"  live dir != final batch dir (FLIP after entry or selector drift): "
          f"{sum(1 for r in rows if r['dir_flip'])} "
          f"({100.0*sum(1 for r in rows if r['dir_flip'])/max(n,1):.1f}%)")
    print(f"  raw match label changes vs live: "
          f"{sum(1 for r in rows if r['raw_match'] != r['live_match'])}")

    bucket_print("LIVE dir-match vs trade", rows,
                 lambda r: ("MATCH" if r["live_match"] else
                            ("OPPOSED" if r["live_dir"] != 0 else "NO_DIR")),
                 ["MATCH", "OPPOSED", "NO_DIR"])
    bucket_print("LIVE dir-match — only undeclared (forming)", 
                 [r for r in rows if not r["live_declared"]],
                 lambda r: ("MATCH" if r["live_match"] else
                            ("OPPOSED" if r["live_dir"] != 0 else "NO_DIR")),
                 ["MATCH", "OPPOSED", "NO_DIR"])
    bucket_print("LIVE dir-match — only declared (confirmed)", 
                 [r for r in rows if r["live_declared"]],
                 lambda r: ("MATCH" if r["live_match"] else
                            ("OPPOSED" if r["live_dir"] != 0 else "NO_DIR")),
                 ["MATCH", "OPPOSED", "NO_DIR"])

    bucket_print("LIVE age at entry", rows,
                 lambda r: age_band(r["live_age"]),
                 ["a:0-10", "b:11-25", "c:26-50", "d:51+", "z:no_start"])
    bucket_print("RAW (batch final) age — for contrast", rows,
                 lambda r: age_band(r["raw_age"]),
                 ["a:0-10", "b:11-25", "c:26-50", "d:51+", "z:no_start"])

    # Trade-list preview of causal gates on LIVE state
    print("\n=== TRADE-LIST PREVIEW (LIVE state gates; not path-true) ===")
    base_r = sum(r["r"] for r in rows)
    gates = [
        ("base", rows),
        ("live dirmatch", [r for r in rows if r["live_dir"] == 0 or r["live_match"]]),
        ("live dirmatch strict (no NO_DIR)", [r for r in rows if r["live_match"]]),
        ("live dirmatch+age25", [r for r in rows if (r["live_dir"] == 0 or r["live_match"]) and (r["live_age"] < 0 or r["live_age"] <= 25)]),
        ("live dirmatch+age10", [r for r in rows if (r["live_dir"] == 0 or r["live_match"]) and (r["live_age"] >= 0 and r["live_age"] <= 10)]),
        ("live age10 only", [r for r in rows if r["live_age"] >= 0 and r["live_age"] <= 10]),
        ("raw dirmatch (old)", [r for r in rows if r["raw_dir"] == 0 or r["raw_match"]]),
    ]
    for tag, ks in gates:
        rs = [r["r"] for r in ks]
        wr = 100.0 * sum(1 for x in rs if x > 0) / max(len(rs), 1)
        print(f"  {tag:<40} n={len(ks):>3}  R={sum(rs):+8.1f}  WR={wr:5.1f}%  dR={sum(rs)-base_r:+.1f}")

    # Why raw opposed was 0% WR: inspect those 125 under live labels
    raw_opp = [r for r in rows if not r["raw_match"] and r["raw_dir"] != 0]
    print(f"\n=== RAW OPPOSED deep dive (n={len(raw_opp)}) ===")
    if raw_opp:
        print(f"  under LIVE labels: match={sum(1 for r in raw_opp if r['live_match'])} "
              f"opposed={sum(1 for r in raw_opp if r['live_dir'] != 0 and not r['live_match'])} "
              f"no_dir={sum(1 for r in raw_opp if r['live_dir'] == 0)}")
        print(f"  live age bands:", end=" ")
        ab = defaultdict(int)
        for r in raw_opp:
            ab[age_band(r["live_age"])] += 1
        print(dict(ab))
        # How many raw-opp were selecting a FUTURE swing (raw_start from unconfirmed)?
        # raw selector takes last start<=i from FULL list including not-yet-declared
        # At entry, if live undeclared, batch may still have a LATER swing that started
        # Actually raw takes last start<=i — often the forming one with FINAL dir.
        flip_after = sum(1 for r in raw_opp if r["dir_flip"])
        print(f"  dir_flip vs live (final != live at entry): {flip_after}")

    print("\ndone")


if __name__ == "__main__":
    main()

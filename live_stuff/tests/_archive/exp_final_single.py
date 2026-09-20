"""EXP FINAL: Full metrics for single-position champion.
No mltf, no persist — single position only, as user requested."""
import sys, time, json, importlib.util
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

ENGINE = ROOT / "backend/src/btc/engines/htf_ltf/v18_streak_halt.py"
SRC = ENGINE.read_text(encoding="utf-8")

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _trade_costs, _load_fine_1m, _compute_swings

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)
BASE = {k: _P[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                            "atr_low_thresh", "atr_high_thresh", "mode",
                            "cooldown_bars", "max_consecutive_losses",
                            "htf_rr", "window_end"] if k in _P}
MB15 = SWING["min_bars_15m"]

# SINGLE-POSITION configs
SINGLE_CHAMPION = {**BASE, "mode": "atr_high", "exp_partial_r": 7.5,
                   "cooldown_bars": 8, "ext_stop_r": 3.0}
SINGLE_PREV = {**BASE, "mode": "atr_high", "exp_partial_r": 5.0,
               "cooldown_bars": 10}
ANCHOR = dict(BASE)
ANCHOR_PARTIAL = {**BASE, "exp_partial_r": 5.0}


def _load_module(text, name):
    p = Path(ROOT / "live_stuff/tests/_final_tmp.py")
    p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, p


def _build_full(s):
    t1 = "    *,\n"
    assert s.count(t1) == 1
    s = s.replace(t1, t1 +
                  '    swings_trail=None,\n    exp_momentum=False,\n    b3_k=0,\n    b3_mode="close",\n'
                  '    exp18_arm=None,\n    exp22_conv=False,\n    exp_persist=0,\n    exp_mltf=False,\n'
                  '    exp27_mode=None,\n    exp31_lb=0,\n    exp_wage_h=0,\n'
                  '    exp_curfew_a=0.0,\n    exp_curfew_b=0.0,\n    exp_partial_r=0.0,\n')
    s = s.replace("    import bisect as bs\n", "    import bisect as bs\n    if swings_trail is None: swings_trail=swings_ltf\n")
    s = s.replace("        for s in swings_ltf:\n", "        for s in swings_trail:\n")
    t4 = 'candle_ts_htf=[int(c["ts"]) for c in candles_htf]\n'
    s = s.replace(t4, t4+'    candle_ts_htf_close=[t+3600 for t in candle_ts_htf]\n    closes_htf=[float(c["close"]) for c in candles_htf]\n')
    t5 = '    if sig["dir"] != d: continue\n'
    s = s.replace(t5, t5+'        if exp_momentum:\n            _j=bs.bisect_right(candle_ts_htf_close, bar_ts+900)-1\n            if _j>=2:\n                _ma=(closes_htf[_j-2]+closes_htf[_j-1]+closes_htf[_j])/3.0\n                if sig["dir"]==1 and closes_htf[_j]<_ma: continue\n                if sig["dir"]==-1 and closes_htf[_j]>_ma: continue\n')
    t6c = '        ev_idx=-1\n'
    s = s.replace(t6c, t6c+'        opp_events=[]\n        if exp27_mode:\n            for _s9 in swings_ltf:\n                for _b9 in _s9.get("breaks",[]):\n                    if _b9.get("time") and (1 if _b9["dir"]=="up" else -1)==-direction:\n                        opp_events.append((int(_b9["idx"]), _b9.get("kind","")))\n            opp_events.sort(key=lambda z: z[0])\n            opp_ev_idx=-1\n            while opp_ev_idx+1 < len(opp_events) and opp_events[opp_ev_idx+1][0] <= i:\n                opp_ev_idx += 1\n')
    t6d = ('        for j in range(i+1, n if not fine_ltf else i+1):\n'
           '            c=candles_ltf[j]\n'
           '            hi=float(c["high"]); lo=float(c["low"])\n')
    s = s.replace(t6d, t6d+
        '            if exp27_mode and opp_ev_idx+1 < len(opp_events) and opp_events[opp_ev_idx+1][0] <= j:\n'
        '                opp_ev_idx += 1\n'
        '                _eok = True\n'
        '                if exp27_mode in ("loss", "fliploss"):\n'
        '                    _cl = float(c["close"])\n'
        '                    _cr = ((_cl - entry) / risk) if direction == 1 else ((entry - _cl) / risk)\n'
        '                    if _cr >= 0.0: _eok = False\n'
        '                if exp27_mode == "fliploss" and opp_events[opp_ev_idx][1] != "FLIP": _eok = False\n'
        '                if _eok:\n'
        '                    exit_idx, exit_px, outcome = j, float(c["close"]), "accel27"\n'
        '                    break\n')
    t6e = '    chop=_chop_series_1h(candles_htf, lb=14)\n'
    s = s.replace(t6e, '    chop=_chop_series_1h(candles_htf, lb=(exp31_lb or 14))\n')
    t10 = '        if busy_until and bar_time <= busy_until: continue\n'
    s = s.replace(t10, '        if (not exp_mltf) and busy_until and bar_time <= busy_until: continue\n')
    t6 = '        sl_pivot=sig["swing_start_px"]\n'
    s = s.replace(t6, t6+
                  '        if b3_k>0:\n            _lv=float(candles_ltf[i]["high"]) if direction==1 else float(candles_ltf[i]["low"])\n'
                  '            _jj=None\n            for _k in range(i+1, min(i+1+b3_k, n-1)):\n'
                  '                _hi=float(candles_ltf[_k]["high"]); _lo=float(candles_ltf[_k]["low"])\n'
                  '                if direction==1 and _lo<=sl_pivot: break\n                if direction==-1 and _hi>=sl_pivot: break\n'
                  '                _cl=float(candles_ltf[_k]["close"])\n                if b3_mode=="wick":\n'
                  '                    _hit=(_hi>_lv) if direction==1 else (_lo<_lv)\n                else:\n'
                  '                    _hit=(_cl>_lv) if direction==1 else (_cl<_lv)\n                if _hit:\n'
                  '                    _jj=_k; break\n            if _jj is None: continue\n'
                  '            i=_jj\n            bar_time=candles_ltf[i]["date"]\n'
                  '            entry=float(candles_ltf[i]["close"])\n'
                  '            if (not exp_mltf) and busy_until and bar_time<=busy_until: continue\n'
                  '            if cooldown_bars>0 and i-last_loss_bar<cooldown_bars: continue\n')
    t_pe_init = '        exit_idx=None; exit_px=None; outcome="open"; exit_ts=None; exit_date=None\n'
    s = s.replace(t_pe_init, t_pe_init+'        _partial_taken=False; _partial_r=0.0\n')
    t_pe_coarse = ('            if direction==1:\n                if hi>best: best=hi\n'
                   '            else:\n                if lo<best: best=lo\n')
    s = s.replace(t_pe_coarse, t_pe_coarse+
        '            if exp_partial_r>0 and not _partial_taken and risk>0:\n                _cur_r=(best-entry)*direction/risk\n                if _cur_r>=exp_partial_r:\n                    _partial_taken=True; _partial_r=exp_partial_r\n')
    t_pe_fine = ('                if direction==1:\n                    if hi>best_f: best_f=hi\n'
                 '                else:\n                    if lo<best_f: best_f=lo\n')
    s = s.replace(t_pe_fine, t_pe_fine+
        '                if exp_partial_r>0 and not _partial_taken and risk>0:\n                    _cur_rf=(best_f-entry)*direction/risk\n                    if _cur_rf>=exp_partial_r:\n                        _partial_taken=True; _partial_r=exp_partial_r\n')
    t_r = ('        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
            '        r_multiple=move/risk if risk>0 else 0\n')
    s = s.replace(t_r,
        '        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
        '        _partial_exit_price=0.0\n'
        '        if _partial_taken and risk>0:\n'
        '            _partial_exit_price=entry+direction*_partial_r*risk\n'
        '            _rem_move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
        '            r_multiple=_partial_r+(_rem_move/risk)*0.5\n'
        '        else:\n'
        '            r_multiple=move/risk if risk>0 else 0\n')

    # E) Add partial_exit_price to trade dict
    t_dict = '            "bars_held": exit_idx - i,\n        })'
    s = s.replace(t_dict,
        '            "bars_held": exit_idx - i,\n'
        '            "partial_exit_price": round(_partial_exit_price, 2) if _partial_exit_price > 0 else 0.0,\n'
        '        })')

    return s


def build_module():
    s = _build_full(SRC)
    m, p = _load_module(s, "final")
    try: p.unlink()
    except OSError: pass
    return m.simulate_htf_ltf_streak_halt


def _net(tr, g):
    """NET R with correct partial-exit cost accounting."""
    rs = [float(t["r_multiple"]) for t in tr]
    fee_rate = g["fee_pct"] / 100.0
    entry_slip = g["entry_slip_pct"] / 100.0
    exit_slip = g["exit_slip_pct"] / 100.0
    FUND_RATE = 0.0001  # 0.01% per 8h, hardcoded to match original engine
    total_cost = 0.0
    for t in tr:
        risk = abs(float(t["entry_price"]) - float(t["sl"]))
        if risk <= 0: continue
        epx = float(t["entry_price"])
        xpx = float(t.get("exit_price", epx))
        ppx = float(t.get("partial_exit_price", 0))
        bars = int(t.get("bars_held") or 0)
        # Entry fee + slippage (full lot)
        entry_cost = (epx * fee_rate + epx * entry_slip) / risk
        # Exit fee + slippage: split if partial
        if ppx > 0:
            exit_cost = (0.5 * ppx * (fee_rate + exit_slip) + 0.5 * xpx * (fee_rate + exit_slip)) / risk
        else:
            exit_cost = (xpx * fee_rate + xpx * exit_slip) / risk
        # Funding (0.01% per 8h = 0.25/8.0 bars per interval)
        fund_r = (bars * 0.25 / 8.0) * FUND_RATE * (epx / risk)
        total_cost += entry_cost + exit_cost + fund_r
    return sum(rs) - total_cost


def full_metrics(tr, label, cfg, g):
    rs = [float(t["r_multiple"]) for t in tr]
    gross = sum(rs)
    net = _net(tr, g)
    n = len(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    flats = [x for x in rs if x == 0]
    wr = 100.0 * len(wins) / max(n, 1)
    avg_win = sum(wins) / max(len(wins), 1)
    avg_loss = sum(losses) / max(len(losses), 1)
    avg_r = gross / max(n, 1)
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)

    # Max drawdown
    peak = 0.0; cum = 0.0; dd = 0.0; cur = 0; mx_loss_streak = 0
    in_dd = False; dd_start = 0; max_dd_bars = 0; dd_bars = 0
    for x in rs:
        cum += x; peak = max(peak, cum)
        d = peak - cum; dd = max(dd, d)
        if x < 0: cur += 1; mx_loss_streak = max(mx_loss_streak, cur)
        else: cur = 0

    # Per-year
    py = defaultdict(lambda: {"net": 0, "n": 0, "wins": 0, "losses": 0, "rs": []})
    for t in tr:
        d = t.get("exit_date") or t.get("entry_date") or ""
        yr = d[:4]
        r = float(t["r_multiple"])
        py[yr]["net"] += r; py[yr]["n"] += 1; py[yr]["rs"].append(r)
        if r > 0: py[yr]["wins"] += 1
        elif r < 0: py[yr]["losses"] += 1

    # Monsters
    big = sorted([x for x in rs if x >= 10.0], reverse=True)

    print("\n" + "=" * 70)
    print("  %s" % label)
    print("=" * 70)
    print("  Config:", json.dumps({k: v for k, v in cfg.items() if k not in BASE or v != BASE.get(k)}, indent=4))
    print("")
    print("  Trades:        %d" % n)
    print("  Gross:         %+.1fR" % gross)
    print("  Costs:         -%.1fR" % (gross - net))
    print("  NET:           %+.1fR" % net)
    print("")
    print("  Win rate:      %.1f%% (%d wins / %d losses / %d flats)" % (
        wr, len(wins), len(losses), len(flats)))
    print("  Avg win:       %+.2fR" % avg_win)
    print("  Avg loss:      %.2fR" % avg_loss)
    print("  Avg R/trade:   %+.2fR" % avg_r)
    print("  Profit factor: %.2f" % pf)
    print("")
    print("  Max drawdown:  %.1fR" % dd)
    print("  Max loss streak: %d consecutive" % mx_loss_streak)
    print("  Monsters (>10R): %d  R=%s" % (
        len(big), "+".join("%.1f" % x for x in big[:10])[:60]))
    print("")
    print("  Per-year breakdown:")
    print("    Year   Trades   NET        WR       PF")
    for yr in sorted(py.keys()):
        y = py[yr]
        yr_wr = 100.0 * y["wins"] / max(y["n"], 1)
        yr_w = [x for x in y["rs"] if x > 0]
        yr_l = [x for x in y["rs"] if x < 0]
        yr_pf = sum(yr_w) / max(abs(sum(yr_l)), 1e-9)
        print("    %s   %4d    %+8.1fR   %5.1f%%   %.2f" % (
            yr, y["n"], y["net"], yr_wr, yr_pf))
    h1 = py.get("2023", {}).get("net", 0) + py.get("2024", {}).get("net", 0)
    h2 = py.get("2025", {}).get("net", 0) + py.get("2026", {}).get("net", 0)
    print("    H1 (2023-24): %+.1fR" % h1)
    print("    H2 (2025-26): %+.1fR" % h2)
    print("=" * 70)
    return {"n": n, "gross": round(gross, 1), "net": round(net, 1),
            "wr": round(wr, 1), "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2), "pf": round(pf, 2),
            "dd": round(dd, 1), "mx_loss_streak": mx_loss_streak,
            "monsters": len(big)}


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    print("data ready (%0.0fs)" % (time.time() - t0))

    sim0 = build_module()

    # 1) Shipped baseline (no CRAZE, no partials)
    from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt as ship_fn
    r_ship = ship_fn(c1h, sw1h, c15, sw15, fine_ltf=fine, **BASE)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    full_metrics(t_ship, "SHIPPED BASELINE (no partials)", BASE, _P)

    # 2) Anchor + partials
    r_ap = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **ANCHOR_PARTIAL)
    t_ap = r_ap["ltf_trades"] if isinstance(r_ap, dict) else r_ap
    full_metrics(t_ap, "ANCHOR + partR=5.0 (single position)", ANCHOR_PARTIAL, _P)

    # 3) atr_high + partR=5.0 (single position)
    r_ah = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **SINGLE_PREV)
    t_ah = r_ah["ltf_trades"] if isinstance(r_ah, dict) else r_ah
    full_metrics(t_ah, "ATR_HIGH + partR=5.0 (single position)", SINGLE_PREV, _P)

    # 4) FINAL CHAMPION (single position)
    r_fc = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **SINGLE_CHAMPION)
    t_fc = r_fc["ltf_trades"] if isinstance(r_fc, dict) else r_fc
    m_fc = full_metrics(t_fc, "FINAL CHAMPION (single position)", SINGLE_CHAMPION, _P)

    # 5) Cost impact comparison: old vs new cost model
    print("\n" + "=" * 70)
    print("  COST MODEL COMPARISON (Final Champion)")
    print("=" * 70)

    def _net_old(tr, g):
        from src.btc.btc_routes import _trade_costs
        rs = [float(t["r_multiple"]) for t in tr]
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
        f = 0.0
        for t in tr:
            e, sl = float(t["entry_price"]), float(t["sl"]); rk = abs(e - sl)
            if rk > 0 and e > 0:
                f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
        return sum(rs) - c2 - f

    net_old = _net_old(t_fc, _P)
    net_new = _net(t_fc, _P)
    gross = sum(float(t["r_multiple"]) for t in t_fc)

    # Count partial trades
    partial_trades = [t for t in t_fc if float(t.get("partial_exit_price", 0)) > 0]
    non_partial = [t for t in t_fc if float(t.get("partial_exit_price", 0)) == 0]

    print("  Partial trades: %d / %d (%.1f%%)" % (len(partial_trades), len(t_fc), 100*len(partial_trades)/max(len(t_fc),1)))
    print("  Non-partial:    %d" % len(non_partial))
    print("")
    print("  Old cost model NET:  %+.1fR" % net_old)
    print("  New cost model NET:  %+.1fR" % net_new)
    print("  Difference:          %+.1fR" % (net_new - net_old))
    print("")

    # Show sample partial trade cost breakdown
    if partial_trades:
        t0 = partial_trades[0]
        risk = abs(float(t0["entry_price"]) - float(t0["sl"]))
        epx = float(t0["entry_price"])
        xpx = float(t0["exit_price"])
        ppx = float(t0["partial_exit_price"])
        bars = int(t0.get("bars_held") or 0)
        fee_rate = _P["fee_pct"] / 100.0
        entry_slip = _P["entry_slip_pct"] / 100.0
        exit_slip = _P["exit_slip_pct"] / 100.0

        print("  Sample partial trade #%s:" % t0.get("trade_no"))
        print("    Entry: $%.2f  SL: $%.2f  Risk: $%.2f" % (epx, float(t0["sl"]), risk))
        print("    Partial exit: $%.2f  Final exit: $%.2f" % (ppx, xpx))
        print("    Bars held: %d  R multiple: %+.3f" % (bars, float(t0["r_multiple"])))

        # OLD model (1 exit)
        old_entry = (epx * fee_rate + epx * entry_slip) / risk
        old_exit = (xpx * fee_rate + xpx * exit_slip) / risk
        old_fund = (bars * 0.25 / 8.0) * 0.0001 * (epx / risk)
        old_total = old_entry + old_exit + old_fund

        # NEW model (2 exits)
        new_entry = (epx * fee_rate + epx * entry_slip) / risk
        new_exit = (0.5 * ppx * (fee_rate + exit_slip) + 0.5 * xpx * (fee_rate + exit_slip)) / risk
        new_fund = (bars * 0.25 / 8.0) * 0.0001 * (epx / risk)
        new_total = new_entry + new_exit + new_fund

        print("")
        print("    Cost breakdown (in R):")
        print("      %-20s  OLD: %.4f  NEW: %.4f" % ("Entry fee+slip", old_entry, new_entry))
        print("      %-20s  OLD: %.4f  NEW: %.4f" % ("Exit fee+slip", old_exit, new_exit))
        print("      %-20s  OLD: %.4f  NEW: %.4f" % ("Funding", old_fund, new_fund))
        print("      %-20s  OLD: %.4f  NEW: %.4f" % ("TOTAL cost", old_total, new_total))
        print("      %-20s  OLD: %.4f  NEW: %.4f" % ("Cost delta", 0.0, new_total - old_total))

    print("=" * 70)

    print("\n\n=== PROGRESSION SUMMARY (corrected costs) ===")
    print("  Shipped baseline:  NET +182.3R  (gross +251.6R)")
    print("  + partial exits:   NET +246.2R  (+63.9R)")
    print("  + atr_high mode:   NET +223.8R  (atr_high trades more, costs more)")
    print("  + ext=3.0 cd=8:    NET +278.0R  (+95.7R over baseline)")
    print("\n(la-final done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()

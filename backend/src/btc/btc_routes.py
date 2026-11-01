"""BTC API routes â€” chart swings + position-engine backtest (24/7 continuous).

Mounted from server.py via a single app.include_router() call.
BTC-only: no Nifty imports, no session logic, no Upstox dependency.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.btc.btc_config import (
    BTC_FORWARD_DATA_DIR,
    BTC_TFS,
    SYMBOLS,
    btc_csv_path,
    load_btc_df,
    load_btc_df_with_forward,
)
from src.btc.btc_engine import simulate_btc_trades, trade_stats, _walk_relabel
from src.btc.btc_fetch import refresh_tf, refresh_all, last_ts as btc_last_ts, EXCHANGES
from src.btc.btc_swing import compute_btc_flow, compute_btc_swings
from src.walker import FlowCandle

# Versioned engines â€” each isolated, v1 is the default (above)
try:
    from src.btc.engines.v2_chandelier import simulate_btc_trades_v2
except Exception:
    simulate_btc_trades_v2 = None  # type: ignore
try:
    from src.btc.engines.v3_htf_trail import simulate_btc_trades_v3
except Exception:
    simulate_btc_trades_v3 = None  # type: ignore
try:
    from src.btc.engines.v4_partial import simulate_btc_trades_v4
except Exception:
    simulate_btc_trades_v4 = None  # type: ignore
try:
    from src.btc.engines.v5_be1 import simulate_btc_trades_v5
except Exception:
    simulate_btc_trades_v5 = None  # type: ignore
try:
    from src.btc.engines.v6_adx import simulate_btc_trades_v6
except Exception:
    simulate_btc_trades_v6 = None  # type: ignore
try:
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
except Exception:
    simulate_btc_trades_v7 = None  # type: ignore
try:
    from src.btc.engines.v8_break_entry import simulate_btc_trades_v8
except Exception:
    simulate_btc_trades_v8 = None  # type: ignore
try:
    from src.btc.engines.v9_conditional_cap import simulate_btc_trades_v9
except Exception:
    simulate_btc_trades_v9 = None  # type: ignore
try:
    from src.btc.engines.v10_strength import simulate_btc_trades_v10
except Exception:
    simulate_btc_trades_v10 = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
except Exception:
    simulate_htf_ltf_15m = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v3_ext_stop import simulate_htf_ltf_ext_stop
except Exception:
    simulate_htf_ltf_ext_stop = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v5_sl_buffer import simulate_htf_ltf_sl_buffer
except Exception:
    simulate_htf_ltf_sl_buffer = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v6_sl_hhll import simulate_htf_ltf_sl_hhll
except Exception:
    simulate_htf_ltf_sl_hhll = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v11_conditional_htf import simulate_htf_ltf_conditional
except Exception:
    simulate_htf_ltf_conditional = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v13_cooldown import simulate_htf_ltf_cooldown
except Exception:
    simulate_htf_ltf_cooldown = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v15_recover_1r import simulate_htf_ltf_recover_1r
except Exception:
    simulate_htf_ltf_recover_1r = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v16_entry_dist import simulate_htf_ltf_entry_dist
except Exception:
    simulate_htf_ltf_entry_dist = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v17_atr_filter import simulate_htf_ltf_atr_filter
except Exception:
    simulate_htf_ltf_atr_filter = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
except Exception:
    simulate_htf_ltf_streak_halt = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v11_conditional_htf import simulate_htf_ltf_conditional
except Exception:
    simulate_htf_ltf_conditional = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.unified import simulate_htf_ltf_streak_halt as simulate_unified
    simulate_htf_ltf_v19_champion = simulate_unified
    # v19_champion.py is archived under engines/htf_ltf/_archive. unified.py is
    # byte-identical to it on all three pivot rules, verified trade for trade,
    # so the v19_* version keys below resolve to the same engine.
except Exception:
    simulate_htf_ltf_v19_champion = None  # type: ignore
    simulate_unified = None  # type: ignore
    simulate_unified = None  # type: ignore

# v11, v13, v15, v16, v17 and v18 were removed from this list. They were
# never dispatched - the elif chain below has branches for v1, v3, v5 and v6
# only - so selecting one silently returned the same fallback book as the
# others. Eight version keys were serving one trade list while each name
# claimed a different filter, and the registry pins quoted numbers for
# them. A key that cannot do what its name says should not be selectable.
# The engine modules still exist under engines/htf_ltf/ if any of those
# books is wanted again; it needs a branch here first.
BTC_VERSIONS = ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10", "v12", "v19", "v19_champion", "v19_causal", "v19_c16", "unified", "entry_minus_1", "utcsat_causal", "utcsat_entry_minus_1", "fsent_champ_long", "fsent_champ_long_atr_low", "fsent_sig_full", "fsent_sig_trail_delay1", "fsent_champ_short", "fsent_champ_long_htfesmcl4", "fsent_champ_long_mcloff", "fsent_sig_multi", "fsent_sig_multi_htffs", "fsent_champ_long_htffs", "fsent_champ_long_mcloff_htf15",
                # Added 2026-10-16. These six were on the frontend dropdown from
                # the start and had pins, monthly breakdowns and scorecard rows,
                # but no entry here - so selecting one returned 400. The list
                # and the dispatch had drifted apart and nothing joined them.
                # exp_dropdown_check.py is that join; it now runs in CI.
                 "fsent_champ_long_htf15_htffs", "fsent_champ_long_htf15_tskip6",
                 "fsent_sig_sw20_short", "fsent_sig_wk_pause_short", "fsent_sig_fs_mom",
                 "fsent_champ_long_mcloff_htf15_retro",
                 # 2026-11-01. The b3/flipb entry experiment (backtest/tests/
                 # exp_b3_flipb_entry.py): Book 107 with the 15m trigger moved to
                 # the global-walk flipb mark (112) or b3 mark (113), so the owner
                 # can see the late trigger on the chart. HTF pools unchanged -
                 # opening the 1h windows on 1h b3/flipb shorts both eras' nets
                 # (corrected-walk htf arm: IS -50.8, OOS -55.8 net) and is
                 # deliberately NOT offered.
                  "fsent_flipb_htf15", "fsent_b3_htf15"]

# Versions that ARE a complete HTF-LTF engine and must not also run through the
# nested htf_ltf path. Kept as a named set next to BTC_VERSIONS rather than an
# inline tuple at the use site: "unified" was added to BTC_VERSIONS and given its
# own dispatch branch but missed the inline exclusion tuple, so selecting it with
# htf_ltf="15m" would have run both paths. A set defined next to the version list
# cannot fall behind it the way a hand-written tuple did.
#   v19_champion - origin SL pivot (lookahead)
#   v19_causal   - exp_causal_sl=1 on the pre-C16 rule; a DIFFERENT book, 494t
#   v19_c16      - pivot_rule="leg"
#   unified      - the pinned shipping book, champion_multi_sw10_leg, 499t
#   fsent_champ_long        - DIRECTIONAL FS entry, long side only, atr_high
#   fsent_champ_long_atr_low - the same book with the regime sign flipped
STANDALONE_HTF_LTF_VERSIONS = {"v19_champion", "v19_causal", "v19_c16", "unified",
                                "entry_minus_1", "fsent_champ_long",
                                "fsent_champ_long_mcloff_htf15_retro",
                               "fsent_champ_long_atr_low", "fsent_sig_full",
                              "fsent_sig_trail_delay1", "fsent_champ_short",
"fsent_champ_long_htfesmcl4",
                               "fsent_champ_long_mcloff",
                               # top contenders from the rolling-weighted ranking
                               # (exp_startup_yearly.py, 35 books). The top five by
                               # that score were all sig-family and three of them
                               # were not reachable from the dropdown at all, which
                               # made them unjudgeable. Added 2026-10-10.
"fsent_sig_multi", "fsent_sig_multi_htffs",
                                "fsent_champ_long_htffs",
                                "fsent_champ_long_mcloff_htf15",
                                "fsent_b3_htf15",
                                "fsent_flipb_htf15",
                                # 2026-10-16: the six that were selectable on the
                                # page but unroutable here. All six are complete
                                # HTF+LTF books, so all six belong in this set -
                                # running one of them through the nested htf_ltf
                                # path as well is the bug the set exists to
                                # prevent, the same way "unified" was missed once.
                                "fsent_champ_long_htf15_htffs",
                                "fsent_champ_long_htf15_tskip6",
                                "fsent_sig_sw20_short",
                                "fsent_sig_wk_pause_short",
                                "fsent_sig_fs_mom"}
_HTF_CLOSE_OFFSET = 3600   # a 1h candle's open -> its close

VERSION_LABELS = {
    "v1": "v1 Honest (touchable + one-swing-one-trade) â€” cap 16d for 1h Flip",
    "v2": "v2 Chandelier ATR k=3.0",
    "v3": "v3 HTF 1h Trail",
    "v4": "v4 Partial 50/50",
    "v5": "v5 BE1 (breakeven 1R)",
    "v6": "v6 ADX>25",
    "v7": "v7 TimeCap 16d (1h Flip)",
    "v8": "v8 Break High/Low + Opposite Cancel",
    "v9": "v9 Conditional Cap 2Râ†’30d",
    "v10": "v10 Flip Strength Body/ATR",
    "v11": "v11 Conditional HTF (chop-aware entry)",
    "v12": "v12 Cooldown 20 bars (cd20) â€” FROZEN BASELINE",
    "v13": "v13 Cooldown 30 bars",
    "v15": "v15 Recover 1R mode",
    "v16": "v16 Entry distance <=30% (rejected)",
    "v17": "v17 ATR<0.5% filter (rejected)",
        "utcsat_causal": "CHAMPION CAUSAL + skip UTC Saturday (453t / +279.5R)",
        "utcsat_entry_minus_1": "CHAMPION ENTRY-1 + skip UTC Saturday (454t / +358.9R)",
    "unified": "UNIFIED shipping book - champion_multi_sw10_leg on unified.py "
                "(IS 499t / +239.12R, OOS 280 / +72.8R)",
    "fsent_champ_long": "FSENT CHAMP LONG - FS entry on longs only, atr_high. "
                        "IS 528t / +533.37R / DD 13.42R, OOS 311t / +239.59R / DD 11.88R",
    "fsent_champ_long_mcloff_htf15_retro": "RETRO 107 - Originally the buggy twin of "
                                            "fsent_champ_long_mcloff_htf15 (3 bugs). Fixed step-by-step: "
                                            "(1) cooldown look-ahead (529→687), (2) filter_pre_fs regression "
                                            "in CAUSAL corrected — now applied in BOTH per theory §9, "
                                            "(3) SL pivot extended leg extreme (prev_end+1 to break bar, "
                                            "687→782). Both versions now trade-for-trade identical.",
    "fsent_champ_long_atr_low": "FSENT CHAMP LONG + atr_low (regime sign flipped). "
                        "IS 641t / +721.30R / DD 28.90R, OOS 315t / +280.70R / DD 14.60R",
    "fsent_sig_full": "FSENT SIG FULL - serial one-position book, FS entry on the SHORT "
                      "side. IS 234t / +295.83R / DD 10.78R, OOS 152t / +194.44R / DD 6.96R",
    "fsent_sig_trail_delay1": "FSENT SIG TRAIL DELAY1 - sig_full + half profit + trail "
                              "delayed to +1R. IS 199t / +418.51R / DD 13.34R, "
                              "OOS 123t / +182.01R / DD 7.54R",
    "fsent_champ_short": "FSENT CHAMP SHORT - the champ_long MIRROR: shorts enter at "
                         "the FS print. IS 533t / +600.60R / DD 17.60R, OOS 312t / "
                         "+239.53R / DD 23.87R",
    "fsent_sig_multi": "SIG MULTI - fsent_sig_full with ONE field changed: max_positions 1 -> 0, so positions OVERLAP instead of running strictly one after another. Ranked #1 of 35 on the rolling-weighted score (exp_startup_yearly.py). Every rolling 50-trade window in the sample is profitable - the worst 50-trade stretch is still +10.0R. Zero negative half-years across all eleven, zero negative financial years, and zero startup drawdown: it has never once gone below where it started. From ANY start date its median one-year drawdown is 8.95% and its bad-luck tail (p10) is 6.95%, against 12.48% and 10.65% for fsent_champ_long. THE CAVEAT IS REAL AND IT IS HERE: paired permutation p 0.9283 in sample and 0.9138 out of sample. This is a candidate on BEHAVIOUR; there is no edge in it distinguishable from reshuffling the parent.",
    "fsent_sig_multi_htffs": "SIG MULTI + HTF-FS - fsent_sig_multi with ONE parameter added, exp_htf_fs_entry='flip', so the HTF flip-bucket window opens on the swing's FS print instead of on the break while decisive and b2 keep their breaks. The newest arm in the family and the most holdable object in it: zero negative half-years, zero negative years, every rolling 50 and rolling 100 window profitable, zero startup drawdown, and one of only five books in the family that survives deleting its best 10% of trades (+85.3R, best in the family by a wide margin). From any start date the worst one-year drawdown is 17.82% but the 10th percentile is 6.85%, the shallowest bad-luck tail among the large books. Causality is clean and measured, not asserted: the gap between window_start and its own FS print is 0.0h at min, median and max, and zero entries precede their window_start. CAVEAT: p 0.5091 / 0.9708 - excellent behaviour, no distinguishable edge.",
    "fsent_champ_long_htffs": "FSENT CHAMP LONG HTF-FS - fsent_champ_long with exp_htf_fs_entry='flip'. The strongest single arm in the family on RETURN TO DRAWDOWN: 45.4 net per unit of drawdown against mcloff's 37.4 and sig_full's 27.4, at the same five-parameter complexity. All eight in-sample half-years positive, which is exactly what htf_fs='all' could not manage. TWO REASONS NOT TO READ THE NET AS A VERDICT: it recovers its own worst drawdown (19.78R, Rs 98,909 at 1% risk on Rs 5 lakh) in TWO TRADES - a very sharp shallow dip, not a deep slow one; and out-of-sample permutation is 0.5956 with tail dependence that DEGRADES out of sample, the top 10% of trades contributing 116.9% there, the worst in the family, leaving -50.7R when they are deleted. IS 770t / +897.94R / dd19.8, OOS 415t / +300.43R / dd14.4.",
    "fsent_champ_long_mcloff_htf15": "MCL-OFF + HTF15 - fsent_champ_long with TWO differences: max_consecutive_losses 3 -> 0 (the three-loss halt stops cutting the recovery trade that follows every streak), and the HTF plane swings at min_bars=15 instead of 10, so the hour-chart windows are fewer and longer. Ranked #9 of 35 on the rolling-weighted score. Zero negative half-years, zero negative years, median one-year drawdown from any start date 13.14%. Of every book here with zero negative half-years this has the strongest in-sample permutation at 0.0115, and the best out-of-sample figure any zero-negative-half-year book has on the far side at 0.1445 - still short of 0.05, so it is the book to WATCH rather than the book to adopt.",
    "fsent_b3_htf15": "SEQ B3 ENTRY (112/113 family) - Book 107 with the 15m "
                      "trigger moved to the b3 mark of the global walk (3rd+ "
                      "same-direction break). IS 411t / -63.7R net, OOS 259t / "
                      "+25.2R net / DD 26.6 with BOTH halves positive (H1 +5.0, "
                      "H2 +20.2) (measured 2026-11-01 on the corrected walk, "
                      "net after costs, exp_b3_flipb_entry.py). The OOS-robust "
                      "arm under the corrected rules.",
    "fsent_flipb_htf15": "SEQ FLIPB ENTRY (112/113 family) - Book 107 with the "
                      "15m trigger moved to the flipb mark: the first B2 on the "
                      "FLIP'S SIDE (same dir as the FLIP, opposite the swing's "
                      "B1 - owner rule). IS 445t / +110.3R net / DD 46.7 with "
                      "BOTH halves positive, OOS 255t / -27.8R net / DD 41.9 "
                      "with both halves down (measured 2026-11-01 on the "
                      "corrected walk, net after costs, exp_b3_flipb_entry.py). "
                      "In-sample star, out-of-sample reverse - not a candidate.",
    "fsent_champ_long_mcloff": "FSENT CHAMP LONG MCL-OFF - the base book with ONE integer "
                                "changed: max_consecutive_losses 3 -> 0, so the loss-run "
                                "halt stops cutting the recovery trade that follows every "
                                "streak. IS 573t / +566.20R / DD 15.13R, OOS 334t / "
                                "+274.36R / DD 14.16R. Zero negative half-years. THE ONLY "
                                "BOOK HERE THAT CLEARS A NULL IN BOTH ERAS - paired "
                                "permutation p = 0.0312 IS and p = 0.0117 OOS - and the "
                                "only one whose period control is powered in both, b = "
                                "+1.21 at t = 3.37 and b = +1.86 at t = 3.97. Earns LESS "
                                "than the base in sample by design and MORE out of "
                                "sample. Its 2021-22 era is reused old data, not a "
                                "holdout. See method/NULL_AUDIT_P5.md.",
    "fsent_champ_long_htfesmcl4": "FSENT CHAMP LONG HTF-FS + MCL4 - the HTF side enters "
                                  "on its FS print instead of the break, and the loss-run "
                                  "cutoff is 4 not 3. IS 793t / +917.80R / DD 27.74R, OOS "
                                  "437t / +326.22R / DD 14.20R. Highest net in the set, "
                                  "and 1.47x the trades of the book it came from.",
}

router = APIRouter(prefix="/api/btc")

# Top-level index fields that need window-offsetting in daily mode.
# seg.start_idx/seg.end_idx are nested inside `seg` and offset separately.
_IDX_FIELDS = ("confirmed_at_idx", "fs_at_idx")

# Funding cannot be switched off. A perp position pays it whether or not a UI
# offers a toggle, and run_experiment.net_r has always subtracted it. 0.01 is
# the standard BTC perp rate per 8h. See the floor in btc_backtest().
MIN_FUNDING_PCT = 0.01


def _load_window(tf: str, limit: int | None, symbol: str = "BTCUSDT", include_forward: bool = False):
    """Validated load of one timeframe window. Returns (candles, flow) or
    (None, JSONResponse-error)."""
    try:
        if include_forward and symbol == "BTCUSDT_BYBIT" and tf in ("15m", "1h", "1m"):
            df = load_btc_df_with_forward(tf, symbol)
        else:
            df = load_btc_df(tf, symbol)
    except FileNotFoundError:
        return None, JSONResponse(
            status_code=404,
            content={"detail": f"{symbol} {tf} data missing â€” copy the CSV first."},
        )
    except ValueError as e:
        return None, JSONResponse(status_code=400, content={"detail": str(e)})
    if limit and limit > 0:
        df = df.tail(int(limit)).reset_index(drop=True)

    candles: list[dict] = []
    flow: list[FlowCandle] = []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        o, h, lo, c = float(row.open), float(row.high), float(row.low), float(row.close)
        candles.append(
            {
                "date": date,
                "ts": int(row.ts),
                "open": o,
                "high": h,
                "low": lo,
                "close": c,
                # BTC CSV has no volume/oi â€” zero-filled for frontend shape compat
                "volume": 0,
                "oi": 0,
            }
        )
        flow.append(FlowCandle(date=date, open=o, high=h, low=lo, close=c))
    return (candles, flow), None


def _compute_swings(flow: list[FlowCandle], mode: str, min_bars: int = 14) -> list[dict]:
    """Swing chain for a window.

    continuous: ONE 24/7 chain, swing_index never resets
    daily:      per-calendar-day chains (NSE-style); slice idx values are
                offset back to window positions
    min_bars:   SwingEngine minBars (sweep winner: 20 > 14 > 7 on BTC)

    There is one swing engine and one chain. The B1 arming comparison build is gone:
    the fix lives in firstswing.py, both sides produced the same 7975-mark chain, and
    keeping a second chain builder only served stale results - it was still returning
    the pre-fix 7975 marks while the normal route returned 7993.
    """
    opts = {"minBars": max(2, int(min_bars))}
    cap = max(1, len(flow) // 2)  # no 1000-swing cap â€” full chain like the sweep
    if mode == "continuous":
        return compute_btc_swings(flow, opts=opts, max_swings=cap)

    swings: list[dict] = []
    slice_start = 0
    n = len(flow)
    for i in range(1, n + 1):
        if i == n or flow[i].date[:10] != flow[slice_start].date[:10]:
            chunk = flow[slice_start:i]
            day_swings = compute_btc_swings(
                chunk, opts={"minBars": max(2, int(min_bars))}, max_swings=max(1, len(chunk) // 2)
            )
            for s in day_swings:
                for f in _IDX_FIELDS:
                    if s.get(f, -1) >= 0:
                        s[f] += slice_start
                # seg.start_idx/end_idx are nested â€” offset them the same way
                # so the zigzag draws at the correct window positions.
                seg = s.get("seg") or {}
                if seg.get("start_idx", -1) >= 0:
                    seg["start_idx"] += slice_start
                if seg.get("end_idx", -1) >= 0:
                    seg["end_idx"] += slice_start
                for b in s["breaks"]:
                    b["idx"] += slice_start
            swings.extend(day_swings)
            slice_start = i
    return swings


def _validate_tf_mode(tf: str, mode: str):
    if tf not in BTC_TFS:
        return JSONResponse(
            status_code=400,
            content={"detail": f"tf must be one of {sorted(BTC_TFS)}"},
        )
    if mode not in ("continuous", "daily"):
        return JSONResponse(status_code=400, content={"detail": "mode must be continuous | daily"})
    return None


def _trade_costs(trades: list[dict], fee_pct: float, slip_pts: float,
                 entry_slip_pct: float = 0.0, exit_slip_pct: float = 0.0,
                 funding_rate_pct: float = 0.0) -> tuple[float, float]:
    """Per-trade cost (in R) of round-trip fees + slippage, and total.

    fee_pct: taker fee % per side (e.g. 0.055 = Bybit taker).
    slip_pts: flat adverse price points (fallback when entry/exit_slip_pct == 0).
    entry_slip_pct: % slippage on entry (e.g. 0.001 = 1bp). If > 0, overrides slip_pts for entry.
    exit_slip_pct: % slippage on exit (e.g. 0.003 = 3bp). If > 0, overrides slip_pts for exit.
    funding_rate_pct: funding rate % per 8h interval (e.g. 0.01 = 0.01% per 8h). 0 = off.

    Peer model: entry is orderly (signal candle close), exit is adverse (trailing SL during fast move).
    Fee model: (entry * fee% + exit * fee%) / risk  +  slippage_in_R  +  funding_in_R.
    """
    total = 0.0
    total_funding = 0.0
    count = 0
    fee_rate = max(0.0, float(fee_pct)) / 100.0
    funding_per_bar = funding_rate_pct / 100.0 / 32.0  # 8h = 32 bars of 15m
    for t in trades:
        risk = abs(float(t["entry_price"]) - float(t["sl"]))
        if risk <= 0:
            continue
        entry_px = abs(float(t["entry_price"]))
        exit_px = abs(float(t.get("exit_price", t["entry_price"])))
        # Fee cost
        fee_r = (entry_px * fee_rate + exit_px * fee_rate) / risk
        # Slippage cost (peer model: % of price, asymmetric)
        if entry_slip_pct > 0 or exit_slip_pct > 0:
            slip_r = (entry_px * entry_slip_pct / 100.0
                      + exit_px * exit_slip_pct / 100.0) / risk
        else:
            slip_r = max(0.0, float(slip_pts)) / risk
        # Funding cost: notional * rate_per_bar * bars_held / risk
        bars = int(t.get("bars_held", 0))
        notional = entry_px  # qty cancels: (qty*entry*rate*bars) / (qty*risk) = entry*rate*bars/risk
        fund_r = (notional * funding_per_bar * bars) / risk if funding_rate_pct > 0 else 0.0
        cost_r = fee_r + slip_r + fund_r
        t["cost_r"] = round(cost_r, 4)
        t["fee_r"] = round(fee_r, 4)
        t["slip_r"] = round(slip_r, 4)
        t["funding_r"] = round(fund_r, 4)
        total += cost_r
        total_funding += fund_r
        count += 1
    return round(total, 4), count


def _net_stats(stats: dict, trades: list[dict]) -> dict:
    """Extend a stats dict with cost-adjusted net-R aggregates."""
    out = dict(stats)
    closed = [t for t in trades if t["outcome"] != "open"]
    net_r = 0.0
    for t in closed:
        cost = float(t.get("cost_r", 0.0))
        net_r += float(t["r_multiple"]) - cost
    out["net_total_r"] = round(net_r, 2)
    out["net_avg_r"] = round(net_r / len(closed), 3) if closed else 0.0
    out["total_costs_r"] = round(sum(float(t.get("cost_r", 0.0)) for t in closed), 2)
    out["total_funding_r"] = round(sum(float(t.get("funding_r", 0.0)) for t in closed), 2)
    return out


# Master presets â€” ONE SWING ONE TRADE + 11:30 fix 2026-09-06 via _rerun_master_sweep.py
# Fix: one swing one trade (first B2/FLIP per swing only) + opposite-dir touchable SL (max high since prev_end).
# 14 Jan 21:30 FLIP from same swing as 17:30 B2 now ignored; 11:30 SL 95465 not 95281; 20:00 SL 91780.
# Method: stream incl churn + touchable + one-trade-per-swing + 1m fills + 0.05%+2pt FULL window, OWN TF, net desc.
_MASTER_PRESETS: list[dict] = [
    {"key": "flip1h20", "bestTf": "1h",
     "label": "#1 Flip Fixed 3R (1h)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "off", "breakeven_r": 0.0,
     "min_bars": 20, "bias": "off", "regime": "off"},
    {"key": "flip1h30", "bestTf": "1h",
     "label": "#2 Flip Trail 30 (1h)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 30, "bias": "off", "regime": "off"},
    {"key": "decisive1h30", "bestTf": "1h",
     "label": "#3 Decisive Trail 30 (1h)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 30, "bias": "off", "regime": "off"},
    {"key": "flip1h20t", "bestTf": "1h",
     "label": "#4 Flip Trail 20 (1h)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 20, "bias": "off", "regime": "off"},
    {"key": "flip50", "bestTf": "15m",
     "label": "#5 Flip Trail 50 (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 50, "bias": "off", "regime": "off"},
    {"key": "decisive50", "bestTf": "15m",
     "label": "#6 Decisive Trail 50 (15m)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 50, "bias": "off", "regime": "off"},
    {"key": "sniper", "bestTf": "15m",
     "label": "#7 Sniper 3R (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "off", "breakeven_r": 1.0,
     "min_bars": 20, "bias": "15m", "regime": "streak_311"},
    {"key": "decisive30", "bestTf": "15m",
     "label": "#8 Decisive Trail 30 (15m)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 30, "bias": "off", "regime": "off"},
    {"key": "flip30", "bestTf": "15m",
     "label": "#9 Flip Trail 30 (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 30, "bias": "off", "regime": "off"},
    {"key": "baseline", "bestTf": "15m",
     "label": "#10 Baseline (ship) (15m)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "off", "breakeven_r": 1.0,
     "min_bars": 14, "bias": "off", "regime": "off"},
    {"key": "trail_max_r", "bestTf": "15m",
     "label": "#11 Trailing Max R (15m)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 1.0,
     "min_bars": 20, "bias": "off", "regime": "off"},
    {"key": "flip_bias", "bestTf": "15m",
     "label": "#12 FLIP + 15m Bias (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "off", "breakeven_r": 1.0,
     "min_bars": 14, "bias": "15m", "regime": "off"},
    {"key": "flip_quality", "bestTf": "15m",
     "label": "#13 FLIP Quality (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 1.0,
     "min_bars": 14, "bias": "off", "regime": "off"},
]


def _run_preset(candles: list[dict], swings: list[dict], p: dict,
                fee_pct: float, slip_pts: float,
                bias_timeline=None, day_gate=None, fine=None,
                entry_selection: str = "stream", version: str = "v1",
                entry_slip_pct: float = 0.005, exit_slip_pct: float = 0.010,
                funding_rate_pct: float = 0.0) -> dict:
    """Run one master preset and return a summary row. Versioned â€” v1 default never disturbed."""
    # v1 flip1h20 is now cap 16d default (old cap 0 removed) â€” use v7 engine for this preset when version v1
    if p.get("key") == "flip1h20" and version == "v1" and simulate_btc_trades_v7 is not None:
        tr = simulate_btc_trades_v7(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
            cap_days=16,
        )
        closed = [t for t in tr if t["outcome"] != "open"]
        base = sum(t["r_multiple"] for t in closed)
        wins = sum(1 for t in closed if t["r_multiple"] > 0)
        _trade_costs(tr, fee_pct, slip_pts, entry_slip_pct, exit_slip_pct, funding_rate_pct)
        costs = sum(float(t.get("cost_r", 0.0)) for t in closed)
        return {
            "key": p["key"], "label": p["label"],
            "entry_break": p["entry_break"], "min_bars": p["min_bars"],
            "trailing": p["trailing"], "breakeven_r": p["breakeven_r"],
            "bias": p["bias"], "regime": p["regime"],
            "trades": len(closed),
            "win_rate": round(100.0 * wins / max(1, len(closed)), 1),
            "base_r": round(base, 2),
            "net_r": round(base - costs, 2),
            "costs_r": round(costs, 2),
        }
    # version dispatch
    if version == "v2" and simulate_btc_trades_v2 is not None:
        tr = simulate_btc_trades_v2(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
        # for v2 we ignore p trailing and force chandelier if needed â€” but keep as is
    elif version == "v3" and simulate_btc_trades_v3 is not None:
        # v3 needs HTF swings â€” caller should have built them; fallback to v1
        tr = simulate_btc_trades(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
    elif version == "v4" and simulate_btc_trades_v4 is not None:
        tr = simulate_btc_trades_v4(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
    elif version == "v5" and simulate_btc_trades_v5 is not None:
        tr = simulate_btc_trades_v5(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
    elif version == "v6" and simulate_btc_trades_v6 is not None:
        tr = simulate_btc_trades_v6(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
    else:
        tr = simulate_btc_trades(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
        sl_pct=0.5, rr_target=float(p["rr_target"]),
        trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
        bias_timeline=bias_timeline, day_gate=day_gate,
        fine=fine, entry_selection=entry_selection,
    )
    closed = [t for t in tr if t["outcome"] != "open"]
    base = sum(t["r_multiple"] for t in closed)
    wins = sum(1 for t in closed if t["r_multiple"] > 0)
    _trade_costs(tr, fee_pct, slip_pts, entry_slip_pct, exit_slip_pct, funding_rate_pct)
    costs = sum(float(t.get("cost_r", 0.0)) for t in closed)
    return {
        "key": p["key"], "label": p["label"],
        "entry_break": p["entry_break"], "min_bars": p["min_bars"],
        "trailing": p["trailing"], "breakeven_r": p["breakeven_r"],
        "bias": p["bias"], "regime": p["regime"],
        "trades": len(closed),
        "win_rate": round(100.0 * wins / max(1, len(closed)), 1),
        "base_r": round(base, 2),
        "net_r": round(base - costs, 2),
        "costs_r": round(costs, 2),
    }


def _load_fine_1m(t0: int, t1: int, symbol: str = "BTCUSDT", include_forward: bool = False) -> list[dict]:
    """1m candles for [t0, t1] from the 1m CSV — for 1m-precise exit fills.

    Returns [] when the 1m CSV is missing. Filters the frame BEFORE building
    dicts so a full-window backtest still only materialises the needed rows.
    When include_forward=True and symbol is BTCUSDT_BYBIT, forward 1m data
    is appended (used for exit fills in the forward window).
    """
    try:
        if include_forward and symbol == "BTCUSDT_BYBIT":
            df = load_btc_df_with_forward("1m", symbol)
        else:
            df = load_btc_df("1m", symbol)
    except FileNotFoundError:
        return []
    df = df[(df["ts"] >= t0) & (df["ts"] <= t1)]
    out: list[dict] = []
    for row in df.itertuples():
        out.append(
            {
                "date": row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "ts": int(row.ts),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
            }
        )
    return out


def _streak_regime_gate(candles: list[dict]) -> dict[str, Optional[str]]:
    """3-1-1 daily-color streak regime gate (fix/btc_sweep2.py D4 winner).

    Trade the regime; on a color-break day keep the old regime; the NEXT day
    is a PAUSE (no trades) and the regime flips to the pause day's color.
    Returns {date: "long"|"short"|None} â€” None = pause day.
    """
    per_day: dict[str, list[dict]] = {}
    for c in candles:
        per_day.setdefault(c["date"][:10], []).append(c)

    days = sorted(per_day)
    gate: dict[str, Optional[str]] = {}
    if not days:
        return gate

    def _color(day: str) -> str:
        cs = per_day[day]
        return "long" if float(cs[-1]["close"]) >= float(cs[0]["open"]) else "short"

    regime = _color(days[0])
    pause = False
    for day in days:
        col = _color(day)
        if pause:
            gate[day] = None
            regime = col
            pause = False
            continue
        gate[day] = regime
        if col != regime:
            pause = True
    return gate


@router.get("/status")
def btc_status(symbol: str = "BTCUSDT"):
    """Data presence per timeframe (rows + coverage)."""
    out: dict = {}
    for tf in BTC_TFS:
        path = btc_csv_path(tf, symbol)
        if not path.exists():
            out[tf] = {"exists": False, "rows": 0, "first_ts": None, "last_ts": None}
            continue
        try:
            df = load_btc_df(tf, symbol)
        except Exception:  # malformed CSV etc.
            out[tf] = {"exists": False, "rows": 0, "first_ts": None, "last_ts": None}
            continue
        out[tf] = {
            "exists": True,
            "rows": int(len(df)),
            "first_ts": df["timestamp"].iloc[0].strftime("%Y-%m-%d %H:%M:%S"),
            "last_ts": df["timestamp"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S"),
        }
    return {"tfs": out, "symbol": symbol}


@router.get("/symbols")
def btc_symbols():
    """List available symbols for the chart dropdown."""
    result = []
    for sym, cfg in SYMBOLS.items():
        # Check if data exists for this symbol (15m is the default tf)
        try:
            path = btc_csv_path("15m", sym)
            exists = path.exists()
            if exists:
                df = load_btc_df("15m", sym)
                rows = len(df)
                first = df["timestamp"].iloc[0].strftime("%Y-%m-%d %H:%M:%S")
                last = df["timestamp"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")
            else:
                rows, first, last = 0, None, None
        except Exception:
            rows, first, last = 0, None, None
        result.append({
            "symbol": sym,
            "label": cfg["label"],
            "exists": exists,
            "rows": rows,
            "first_ts": first,
            "last_ts": last,
        })
    return {"symbols": result}


@router.get("/chart")
def btc_chart(
    tf: str = "5m",
    mode: str = "continuous",
    limit: int | None = None,
    min_bars: int = 14,
    symbol: str = "BTCUSDT",
    version: str = "",
    include_forward: bool = False,
):
    """Candles + REAL swing chain (B1/B2/FLIP/FS-SUS) for ONE window.

    Swings are computed on exactly the candle window returned - the chart's
    OWN timeframe (15m chart -> 15m swings; never a lower-TF projection) -
    so swing idx values equal array positions in `candles`.

    """
    err = _validate_tf_mode(tf, mode)
    if err:
        return err
    if symbol not in SYMBOLS:
        return JSONResponse(
            status_code=400,
            content={"detail": f"symbol must be one of {sorted(SYMBOLS)}"},
        )
    # This endpoint used to take no version check at all, so a bookmarked
    # ?version=fsent_champ_long_B1PATCH link kept returning 200 with ordinary
    # candles after that id was removed from BTC_VERSIONS. It looked alive. Now an
    # unknown version is a 400 like the other two endpoints, so a retired id fails
    # visibly instead of quietly serving something else.
    if version and version not in BTC_VERSIONS:
        return JSONResponse(
            status_code=400,
            content={"detail": f"version must be one of {BTC_VERSIONS}"},
        )
    win, err = _load_window(tf, limit, symbol, include_forward=include_forward)
    if err:
        return err
    candles, flow = win

    # Same walk the books run: promoted marks (B2 -> B3/flipb) must carry the
    # sequence name on the chart and keep kind0 as the original, or a chart
    # reader sees a book enter "on the B2" when the mark had already joined
    # the walk as a flipb. skip_first=True mirrors every _collect_signals
    # call site.
    swings = _compute_swings(flow, mode, min_bars=min_bars)
    _walk_relabel(swings, True)

    return {
        "tf": tf,
        "mode": mode,
        "symbol": symbol,
        "version": version,
        "include_forward": include_forward,
        "forward_available": BTC_FORWARD_DATA_DIR.exists(),
        "count": len(candles),
        "first_ts": candles[0]["date"] if candles else None,
        "last_ts": candles[-1]["date"] if candles else None,
        "candles": candles,
        "swings": swings,
        "flow": compute_btc_flow(flow, mode),
    }


@router.get("/backtest")
def btc_backtest(
    tf: str = "5m",
    mode: str = "continuous",
    limit: int | None = None,
    fee_pct: float = 0.0,
    slippage_pts: float = 0.0,
    entry_slip_pct: float = 0.005,
    exit_slip_pct: float = 0.010,
    funding_rate_pct: float = 0.01,
    entry_break: str = "decisive",
    sl_mode: str = "swing",
    sl_pct: float = 0.5,
    rr_target: float = 3.0,
    trailing: str = "off",
    trail_distance_r: float = 1.0,
    breakeven_r: float = 1.0,
    skip_first: bool = True,
    bias: str = "off",
    min_bars: int = 14,
    htf_min_bars: int = 10,
    htf_tf: str = "1h",
    regime: str = "off",
    fill_tf: str = "1m",
    entry_selection: str = "stream",
    version: str = "v1",
    htf_ltf: str = "off",
    htf_ltf_ver: str = "v1",
    cooldown_bars: int = 0,
    symbol: str = "BTCUSDT",
    include_forward: bool = False,
):
    """Position engine over the swing chain: entries on swing breaks,
    swing/pct SL, fixed R target, breakeven-R and trailing.

    Args:
        entry_break: decisive (default: the swing's B2/FLIP flip break) | b2 | flip
        sl_mode:     swing (broken pivot extreme) | pct (sl_pct% beyond entry)
        rr_target:   fixed R target â€” used when trailing=off
        trailing:    off | r (trail trail_distance_r behind favorable extreme)
                     | swing (trail to confirmed swing pivots)
        breakeven_r: SL moves to entry after breakeven_r * risk traveled (0 = off)
        skip_first:  first swing of the chain establishes structure only (FS/bias
                     role) â€” entries start from swing #2 onward (default true)
        bias:        off | 15m â€” gate entries by the last CONFIRMED 15m swing
                     direction (longs need "up", shorts need "down"). The BTC
                     analog of Nifty's pre-open bias. Ignored when tf=15m
                     (no higher TF available).
        min_bars:    SwingEngine minBars (sweep winner: 20 > 14 > 7 on BTC).
        regime:      off | streak_311 â€” daily-color streak regime gate
                     (trade regime, fade the break day, pause, flip).

    Returns:
        {params, stats, trades: [...]} â€” trades carry entry/exit ts + date so
        the frontend draws PositionPrimitive boxes and a trade table.
    """
    err = _validate_tf_mode(tf, mode)
    if err:
        return err
    if entry_break not in ("decisive", "b2", "flip"):
        return JSONResponse(status_code=400, content={"detail": "entry_break must be decisive | b2 | flip"})
    if sl_mode not in ("swing", "pct"):
        return JSONResponse(status_code=400, content={"detail": "sl_mode must be swing | pct"})
    if trailing not in ("off", "r", "swing"):
        return JSONResponse(status_code=400, content={"detail": "trailing must be off | r | swing"})
    if bias not in ("off", "15m"):
        return JSONResponse(status_code=400, content={"detail": "bias must be off | 15m"})
    if regime not in ("off", "streak_311"):
        return JSONResponse(status_code=400, content={"detail": "regime must be off | streak_311"})
    if not (2 <= int(min_bars) <= 200):
        return JSONResponse(status_code=400, content={"detail": "min_bars must be 2..200"})
    if not (2 <= int(htf_min_bars) <= 200):
        return JSONResponse(status_code=400, content={"detail": "htf_min_bars must be 2..200"})
    if htf_tf not in ("15m", "1h", "4h"):
        return JSONResponse(status_code=400, content={"detail": "htf_tf must be 15m | 1h | 4h"})
    if not (0 <= float(fee_pct) <= 0.5):
        return JSONResponse(status_code=400, content={"detail": "fee_pct must be 0..0.5 (% per side)"})
    if not (0 <= float(slippage_pts) <= 1000):
        return JSONResponse(status_code=400, content={"detail": "slippage_pts must be 0..1000"})
    if fill_tf not in ("signal", "1m"):
        return JSONResponse(status_code=400, content={"detail": "fill_tf must be signal | 1m"})
    if entry_selection not in ("stream", "final"):
        return JSONResponse(status_code=400, content={"detail": "entry_selection must be stream | final"})
    if version not in BTC_VERSIONS:
        return JSONResponse(status_code=400, content={"detail": f"version must be one of {BTC_VERSIONS}"})
    if htf_ltf not in ("off", "5m", "15m"):
        return JSONResponse(status_code=400, content={"detail": "htf_ltf must be off | 5m | 15m"})
    if htf_ltf_ver not in ("v1", "v3", "v5", "v6", "v11", "v12", "v13", "v15", "v16", "v17", "v18", "v19"):
        return JSONResponse(status_code=400, content={"detail": "htf_ltf_ver must be v1 | v3 | v5 | v6 | v11 | v12 | v13 | v15 | v16 | v17"})

    win, err = _load_window(tf, limit, symbol, include_forward=include_forward)
    if err:
        return err
    candles, flow = win
    swings = _compute_swings(flow, mode, min_bars=min_bars)

    # HTF leg is genuinely a different timeframe. It used to be fed the SAME
    # candles and swings as the LTF leg, so the 1h window gate was deciding on
    # 15m structure and min_bars for the two could never differ. The champion
    # harness does not do this: it passes sw10 (1h, min_bars=10) and sw15
    # (15m, min_bars=50) as separate arguments. Each book now carries both.
    candles_htf: list = candles
    swings_htf: list = swings
    if htf_tf != tf:
        hwin, herr = _load_window(htf_tf, limit, symbol, include_forward=include_forward)
        if herr is not None:
            return herr
        candles_htf, hflow = hwin
        swings_htf = _compute_swings(hflow, mode, min_bars=htf_min_bars)

    # 1m-precise exit fills: walk 1m candles for SL/target/trail/BE instead of
    # the signal TF's bars (no hidden intrabar stops). tf=1m already exact.
    fine: Optional[list[dict]] = None
    if fill_tf == "1m" and tf != "1m":
        fine = _load_fine_1m(candles[0]["ts"], candles[-1]["ts"], symbol, include_forward=include_forward)
        if not fine:
            return JSONResponse(
                status_code=400,
                content={"detail": "fill_tf=1m needs data/btc/BTCUSDT_1m.csv — missing or empty for this window."},
            )

    # Daily-color streak regime gate (3-1-1) over the trade window's days.
    day_gate: dict[str, Optional[str]] | None = None
    if regime == "streak_311":
        day_gate = _streak_regime_gate(candles)

    # Higher-TF bias timeline (15m swings over the FULL 15m series so the
    # gate is warm even at the very start of the trade window).
    bias_applied = False
    bias_timeline: list[tuple[int, str]] | None = None
    if bias == "15m" and tf in ("1m", "5m"):
        htf, htf_err = _load_window("15m", None, symbol, include_forward=include_forward)
        if htf_err is None:
            htf_candles, htf_flow = htf
            # Patched like every other chain in this request. A bias timeline
            # built from the SHIPPED chain while the LTF chain below it is
            # patched gates entries on a chain the comparison never showed.
            htf_swings = _compute_swings(htf_flow, mode)
            bias_timeline = sorted(
                (
                    int(htf_candles[s["confirmed_at_idx"]]["ts"]),
                    s["dir"],
                )
                for s in htf_swings
                if 0 <= int(s.get("confirmed_at_idx", -1)) < len(htf_candles)
            )
            bias_applied = True

    # Funding is a real, unavoidable cost of a perp position and these books hold
    # for ~117 bars. It is floored here rather than merely defaulted, so no
    # caller - the UI, a curl, a stale bookmark - can switch it off and report a
    # net R the harness would not agree with. run_experiment.net_r has always
    # charged it unconditionally; this closes the last way the two could differ.
    funding_rate_pct = max(float(funding_rate_pct), MIN_FUNDING_PCT)

    params = {
        "tf": tf,
        "mode": mode,
        "limit": limit,
        "fee_pct": float(fee_pct),
        "slippage_pts": float(slippage_pts),
        "entry_slip_pct": float(entry_slip_pct),
        "exit_slip_pct": float(exit_slip_pct),
        "funding_rate_pct": float(funding_rate_pct),
        "entry_break": entry_break,
        "sl_mode": sl_mode,
        "sl_pct": float(sl_pct),
        "rr_target": float(rr_target),
        "trailing": trailing,
        "trail_distance_r": float(trail_distance_r),
        "breakeven_r": float(breakeven_r),
        "skip_first": bool(skip_first),
        "bias": bias,
        "bias_applied": bias_applied,
        "min_bars": int(min_bars),
        "regime": regime,
        "fill_tf": fill_tf if tf != "1m" else "signal",
        "entry_selection": entry_selection,
        "version": version,
        "htf_ltf": htf_ltf,
        "htf_ltf_ver": htf_ltf_ver,
        "cooldown_bars": cooldown_bars,
    }
    # HTF-LTF nested execution: 1h Flip cap16 + 15m/5m Decisive inside HTF window
    # Skip HTF-LTF for standalone versions (v19_champion, v19_causal, v19_c16)
    if htf_ltf != "off" and simulate_htf_ltf_15m is not None and version not in STANDALONE_HTF_LTF_VERSIONS:
        # HTF is always 1h Flip cap16, LTF is htf_ltf (15m or 5m) Decisive
        htf_tf = "1h"
        ltf_tf = htf_ltf
        # Load HTF window (full)
        htf_win, htf_err = _load_window(htf_tf, None, symbol, include_forward=include_forward)
        ltf_win, ltf_err = _load_window(ltf_tf, limit, symbol, include_forward=include_forward)  # use same limit as chart window for LTF
        if htf_err is None and ltf_err is None and htf_win is not None and ltf_win is not None:
            htf_candles, htf_flow = htf_win  # type: ignore
            ltf_candles, ltf_flow = ltf_win  # type: ignore
            # HTF swings
            htf_swings = _compute_swings(htf_flow, mode, min_bars=20)
            # LTF swings
            ltf_min = 50 if ltf_tf == "15m" else 14
            ltf_swings = _compute_swings(ltf_flow, mode, min_bars=ltf_min)
            # HTF fine for 1h
            htf_fine = _load_fine_1m(htf_candles[0]["ts"], htf_candles[-1]["ts"], symbol, include_forward=include_forward)
            ltf_fine = _load_fine_1m(ltf_candles[0]["ts"], ltf_candles[-1]["ts"], symbol, include_forward=include_forward)
            # Use HTF-LTF engine
            if htf_ltf_ver == "v3" and simulate_htf_ltf_ext_stop is not None:
                # v3 Extension Stop: block fresh same-dir LTF entries once the
                # 1h leg is beyond 1.5R unrealized (see v3_ext_stop docstring).
                nested = simulate_htf_ltf_ext_stop(
                    htf_candles, htf_swings, ltf_candles, ltf_swings, ltf_fine,
                    htf_entry_break="flip", ltf_entry_break="decisive",
                    sl_mode=sl_mode, rr_target=rr_target, ltf_trailing="swing",
                    htf_breakeven=0.0, ltf_breakeven=0.0, htf_cap_days=16,
                    ext_stop_r=1.5, cooldown_bars=cooldown_bars,
                )
                params["ext_stop_r"] = 1.5
            elif htf_ltf_ver == "v5" and simulate_htf_ltf_sl_buffer is not None:
                # v5 = v3 ext-stop + SL = pivot + 0.25 ATR(14) buffer.
                nested = simulate_htf_ltf_sl_buffer(
                    htf_candles, htf_swings, ltf_candles, ltf_swings, ltf_fine,
                    htf_entry_break="flip", ltf_entry_break="decisive",
                    sl_mode=sl_mode, rr_target=rr_target, ltf_trailing="swing",
                    htf_breakeven=0.0, ltf_breakeven=0.0, htf_cap_days=16,
                    ext_stop_r=1.5, sl_buf_atr=0.25, cooldown_bars=cooldown_bars,
                )
                params["ext_stop_r"] = 1.5
                params["sl_buf_atr"] = 0.25
            elif htf_ltf_ver == "v6" and simulate_htf_ltf_sl_hhll is not None:
                # v6 = v3 ext-stop + SL = highest-high/lowest-low of 30 bars.
                nested = simulate_htf_ltf_sl_hhll(
                    htf_candles, htf_swings, ltf_candles, ltf_swings, ltf_fine,
                    htf_entry_break="flip", ltf_entry_break="decisive",
                    sl_mode=sl_mode, rr_target=rr_target, ltf_trailing="swing",
                    htf_breakeven=0.0, ltf_breakeven=0.0, htf_cap_days=16,
                    ext_stop_r=1.5, sl_hhll_n=30, cooldown_bars=cooldown_bars,
                )
                params["ext_stop_r"] = 1.5
                params["sl_hhll_n"] = 30
            elif htf_ltf_ver == "v11" and simulate_htf_ltf_conditional is not None:
                # v11 BEST all-positive 539 +172.5 chop_or_atr_low HIGH chop>61.8 OR LOW vol atr%<0.35 -> decisive else Flip â€” beats v5 +4.4R total +28.6R 2023
                nested = simulate_htf_ltf_conditional(
                    htf_candles, htf_swings, ltf_candles, ltf_swings, ltf_fine,
                    sl_buf_atr=0.25, ext_stop_r=1.5, chop_thresh=61.8, atr_low_thresh=0.35,
                    mode="chop_or_atr_low", cooldown_bars=cooldown_bars,
                )
                params["ext_stop_r"] = 1.5
                params["sl_buf_atr"] = 0.25
                params["htf_conditional"] = "chop_or_atr_low"
            elif htf_ltf_ver == "v12" and simulate_htf_ltf_conditional is not None:
                # v12 = v11 (conditional HTF) + cooldown 20 bars.
                # FROZEN BASELINE: 414 trades, +265.30R gross, all 4 years positive.
                # Do not modify â€” this is the reference version.
                nested = simulate_htf_ltf_conditional(
                    htf_candles, htf_swings, ltf_candles, ltf_swings, ltf_fine,
                    sl_buf_atr=0.25, ext_stop_r=1.5, chop_thresh=61.8, atr_low_thresh=0.35,
                    mode="b2_vs_flip_chop", cooldown_bars=20,
                )
                params["ext_stop_r"] = 1.5
                params["sl_buf_atr"] = 0.25
                params["cooldown_bars"] = 20
                params["htf_conditional"] = "b2_vs_flip_chop"
            elif htf_ltf_ver == "v13" and simulate_htf_ltf_cooldown is not None:
                # v13 = v5 (ext-stop + ATR buffer) + loss cooldown: after a
                # losing LTF trade, skip LTF signals for cooldown_bars
                # (20 x 15m = 5h). Live-safe, sequential, no lookahead.
                nested = simulate_htf_ltf_cooldown(
                    htf_candles, htf_swings, ltf_candles, ltf_swings, ltf_fine,
                    htf_entry_break="flip", ltf_entry_break="decisive",
                    sl_mode=sl_mode, rr_target=rr_target, ltf_trailing="swing",
                    htf_breakeven=0.0, ltf_breakeven=0.0, htf_cap_days=16,
                    ext_stop_r=1.5, sl_buf_atr=0.25, cooldown_bars=20,
                )
                params["ext_stop_r"] = 1.5
                params["sl_buf_atr"] = 0.25
                params["cooldown_bars"] = 20
            elif htf_ltf_ver == "v15" and simulate_htf_ltf_recover_1r is not None:
                # v15 = v12 (b2_vs_flip + ext-stop + ATR buf) + cooldown
                # + post-loss 1R secure: after a loss, the next trade exits
                # immediately at +1R (no trail) to lock in the recovery
                # profit. After a win, trails normally.
                nested = simulate_htf_ltf_recover_1r(
                    candles_htf=htf_candles,
                    swings_htf=htf_swings,
                    candles_ltf=ltf_candles,
                    swings_ltf=ltf_swings,
                    fine_ltf=ltf_fine,
                    sl_buf_atr=0.25,
                    ext_stop_r=1.5,
                    chop_thresh=61.8,
                    mode="b2_vs_flip_chop",
                    cooldown_bars=20,
                    recover_1r=True,
                )
                params["ext_stop_r"] = 1.5
                params["sl_buf_atr"] = 0.25
                params["cooldown_bars"] = 20
                params["recover_1r"] = True
            elif htf_ltf_ver == "v16" and simulate_htf_ltf_entry_dist is not None:
                # v16 = v12+cd20 + entry distance gate: skip LTF entries
                # that are >30% into the 15m swing (research: 0-30% bucket
                # = +220R net, >30% buckets = only +45R combined).
                nested = simulate_htf_ltf_entry_dist(
                    candles_htf=candles_htf,
                    swings_htf=swings_htf,
                    candles_ltf=ltf_candles,
                    swings_ltf=ltf_swings,
                    fine_ltf=ltf_fine,
                    sl_buf_atr=0.25,
                    ext_stop_r=1.5,
                    chop_thresh=61.8,
                    mode="b2_vs_flip_chop",
                    cooldown_bars=20,
                    recover_1r=False,
                    entry_dist_max=0.3,
                )
                params["ext_stop_r"] = 1.5
                params["sl_buf_atr"] = 0.25
                params["cooldown_bars"] = 20
                params["entry_dist_max"] = 0.3
            elif htf_ltf_ver == "v17" and simulate_htf_ltf_atr_filter is not None:
                # v17 = v12+cd20 + ATR<0.5% filter: skip LTF entries where
                # ATR% at entry > 0.5%. Research: low-vol bucket IS +0.449,
                # OOS +0.961 (2.14x better). Hypothesis: low vol = tighter SL
                # = more room for runners to develop.
                nested = simulate_htf_ltf_atr_filter(
                    candles_htf=candles_htf,
                    swings_htf=swings_htf,
                    candles_ltf=ltf_candles,
                    swings_ltf=ltf_swings,
                    fine_ltf=ltf_fine,
                    sl_buf_atr=0.25,
                    ext_stop_r=1.5,
                    chop_thresh=61.8,
                    mode="b2_vs_flip_chop",
                    cooldown_bars=20,
                    recover_1r=False,
                    atr_max_pct=0.5,
                )
                params["ext_stop_r"] = 1.5
                params["sl_buf_atr"] = 0.25
                params["cooldown_bars"] = 20
                params["atr_max_pct"] = 0.5
            elif htf_ltf_ver == "v18" and simulate_htf_ltf_streak_halt is not None:
                # v18 = v12+cd20 + streak halt at 5L: halt trading after 5
                # consecutive losses, resume on next winner. Research: +322R net
                # vs +265R without halt (streak analysis test_streak_analysis.py).
                #
                # Per-instrument tuning (2026-09-17, corrected streak + cd sweep):
                #   BTC Spot:     chop=61.8 cd=20 slbuf=0.25 halt=5 â†’ +331.1R  DD 9.7R
                #   Binance Perp: chop=61.8 cd=5  slbuf=0.15 halt=5 â†’ +311.7R  DD 11.6R
                # Bybit Perp:   chop=58.0 cd=10 slbuf=0.01 halt=3 â†’ +365.7R  DD 17.9R
                if symbol == "BTCUSDT_BYBIT":
                    _chop = 58.0
                    _cd = 10
                    _slbuf = 0.01
                    _halt = 3
                elif symbol == "BTCUSDT_PERP":
                    _chop = 61.8
                    _cd = 5
                    _slbuf = 0.15
                    _halt = 5
                else:
                    _chop = 61.8
                    _cd = 20
                    _slbuf = 0.25
                    _halt = 5
                nested = simulate_htf_ltf_streak_halt(
                    candles_htf=htf_candles,
                    swings_htf=htf_swings,
                    candles_ltf=ltf_candles,
                    swings_ltf=ltf_swings,
                    fine_ltf=ltf_fine,
                    sl_buf_atr=_slbuf,
                    ext_stop_r=1.5,
                    mode="b2_vs_flip_chop",
                    chop_thresh=_chop,
                    cooldown_bars=_cd,
                    max_consecutive_losses=_halt,
                )
                params["ext_stop_r"] = 1.5
                params["sl_buf_atr"] = _slbuf
                params["cooldown_bars"] = _cd
                params["max_consecutive_losses"] = _halt
            elif htf_ltf_ver == "v19" and simulate_htf_ltf_streak_halt is not None:
                # v19 = v18 with HTF window ending at first touch of 1.5R (r_touch)
                # instead of the HTF trade's exit. Research 2026-09-08 (fix/research_v19.md):
                # 242t +200.6R DD8.5 PF2.51 vs v18 330t +331.1R DD9.7 â€” REJECTED as default
                # (removed 88 trades avg +1.48R = pullback winners), kept for comparison.
                if symbol == "BTCUSDT_BYBIT":
                    _chop = 58.0
                    _cd = 0
                    _slbuf = 0.20
                elif symbol == "BTCUSDT_PERP":
                    _chop = 61.8
                    _cd = 5
                    _slbuf = 0.15
                else:
                    _chop = 61.8
                    _cd = 20
                    _slbuf = 0.25
                nested = simulate_htf_ltf_streak_halt(
                    candles_htf=htf_candles,
                    swings_htf=htf_swings,
                    candles_ltf=ltf_candles,
                    swings_ltf=ltf_swings,
                    fine_ltf=ltf_fine,
                    sl_buf_atr=_slbuf,
                    ext_stop_r=1.5,
                    mode="b2_vs_flip_chop",
                    chop_thresh=_chop,
                    cooldown_bars=_cd,
                    max_consecutive_losses=5,
                    window_end="r_touch",
                )
                params["ext_stop_r"] = 1.5
                params["sl_buf_atr"] = _slbuf
                params["cooldown_bars"] = _cd
                params["max_consecutive_losses"] = 5
                params["window_end"] = "r_touch"
            else:
                nested = simulate_htf_ltf_15m(
                    htf_candles, htf_swings, ltf_candles, ltf_swings, ltf_fine,
                    htf_entry_break="flip", ltf_entry_break="decisive",
                    sl_mode=sl_mode, rr_target=rr_target, ltf_trailing="swing",
                    htf_breakeven=0.0, ltf_breakeven=0.0, htf_cap_days=16,
                )
            # For chart, we show LTF trades (inside HTF) as main trades, plus HTF trades as context
            # Combine for stats: LTF trades are the execution, HTF trades are regime
            ltf_trades = nested.get("ltf_trades", [])
            htf_trades = nested.get("htf_trades", [])
            # Merged intervals from v18: union of flip + b2 + decisive.
            # These are the actual windows the engine trades in â€” used for chart tinting.
            merged_intervals = nested.get("intervals", [])
            # Use LTF trades for main chart, but also include HTF for stats
            # For now, return LTF trades as primary, with HTF count in params
            _trade_costs(ltf_trades, fee_pct, slippage_pts, entry_slip_pct, exit_slip_pct, funding_rate_pct)
            _trade_costs(htf_trades, fee_pct, slippage_pts, entry_slip_pct, exit_slip_pct, funding_rate_pct)
            stats_ltf = trade_stats(ltf_trades)
            stats_ltf = _net_stats(stats_ltf, ltf_trades)
            # Also compute HTF stats for reference
            stats_htf = trade_stats(htf_trades)
            stats_htf = _net_stats(stats_htf, htf_trades)
            # Combined net
            combined_net = float(stats_ltf.get("net_total_r", 0)) + float(stats_htf.get("net_total_r", 0))
            # Combined merged-equity drawdown: both books interleaved by exit
            # time (the honest risk number for running 1h + 15m on one account)
            _merged = sorted(
                [(int(t["exit_ts"]), float(t["r_multiple"]) - float(t.get("cost_r", 0.0)))
                 for t in htf_trades if t["outcome"] != "open"]
                + [(int(t["exit_ts"]), float(t["r_multiple"]) - float(t.get("cost_r", 0.0)))
                   for t in ltf_trades if t["outcome"] != "open"]
            )
            _cum = _peak = 0.0
            combined_maxdd = 0.0
            for _ts, _r in _merged:
                _cum += _r
                if _peak - _cum > combined_maxdd:
                    combined_maxdd = _peak - _cum
                if _cum > _peak:
                    _peak = _cum
            params["combined_maxdd"] = round(combined_maxdd, 2)
            # Return LTF trades as main, but include htf info in params
            params["htf_trades"] = len(htf_trades)
            params["htf_net"] = stats_htf.get("net_total_r")
            params["ltf_trades"] = len(ltf_trades)
            # Build htf_windows from parent intervals â€” each LTF trade's parent
            # HTF interval (flip or b2). Non-overlapping, covers every trade.
            htf_windows = []
            for iv in merged_intervals:
                s, e, d = int(iv[0]), int(iv[1]), int(iv[2])
                htf_windows.append({
                    "entry_ts": s,
                    "exit_ts": e,
                    "dir": "long" if d == 1 else "short",
                    "entry_price": float(iv[3]) if len(iv) > 3 else 0,
                    "sl": float(iv[4]) if len(iv) > 4 else 0,
                    "trade_no": len(htf_windows) + 1,
                    "swing_no": 0, "break_kind": "interval",
                    "entry_idx": 0, "entry_date": "",
                    "exit_idx": 0, "exit_date": "",
                    "exit_price": 0, "outcome": "window",
                    "r_multiple": 0, "bars_held": 0,
                })
            return {
                "params": params,
                "count": len(ltf_candles) if ltf_candles else len(candles),
                "swings_used": len(ltf_swings) if ltf_swings else len(swings),
                "trades": ltf_trades,
                "stats": stats_ltf,
                "htf_trades": htf_windows,
                "htf_stats": stats_htf,
                "combined_net": combined_net,
            }
    # versioned dispatch â€” v1 is default honest baseline, v2..v7 are isolated crazy ideas
    # v1 flip1h20 is now cap 16d default (old cap 0 removed) â€” use v7 engine for that preset
    if version == "v1" and tf == "1h" and entry_break == "flip" and int(min_bars) == 20 and trailing == "off" and float(breakeven_r) == 0.0 and simulate_btc_trades_v7 is not None:
        trades = simulate_btc_trades_v7(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
        )
    elif version == "v1":
        trades = simulate_btc_trades(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            trail_distance_r=float(trail_distance_r),
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v2":
        if simulate_btc_trades_v2 is None:
            return JSONResponse(status_code=500, content={"detail": "v2 engine not loaded"})
        trades = simulate_btc_trades_v2(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            trail_k=3.0,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v3":
        if simulate_btc_trades_v3 is None:
            return JSONResponse(status_code=500, content={"detail": "v3 engine not loaded"})
        # load HTF 1h swings for HTF trail
        htf_swings = None
        htf_ts = None
        try:
            htf_win, htf_err = _load_window("1h", None, symbol, include_forward=include_forward)
            if htf_err is None and htf_win is not None:
                htf_candles, htf_flow = htf_win  # type: ignore
                htf_swings = _compute_swings(htf_flow, mode, min_bars=min_bars)
                htf_ts = [int(c["ts"]) for c in htf_candles]
        except Exception:
            htf_swings = None
            htf_ts = None
        trades = simulate_btc_trades_v3(
            candles,
            swings,
            swings_htf=htf_swings,
            candle_ts_htf=htf_ts,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v4":
        if simulate_btc_trades_v4 is None:
            return JSONResponse(status_code=500, content={"detail": "v4 engine not loaded"})
        trades = simulate_btc_trades_v4(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v5":
        if simulate_btc_trades_v5 is None:
            return JSONResponse(status_code=500, content={"detail": "v5 engine not loaded"})
        # v5 forces BE1
        trades = simulate_btc_trades_v5(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=1.0,
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v6":
        if simulate_btc_trades_v6 is None:
            return JSONResponse(status_code=500, content={"detail": "v6 engine not loaded"})
        trades = simulate_btc_trades_v6(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v7":
        if simulate_btc_trades_v7 is None:
            return JSONResponse(status_code=500, content={"detail": "v7 engine not loaded"})
        trades = simulate_btc_trades_v7(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
        )
    elif version == "v8":
        if simulate_btc_trades_v8 is None:
            return JSONResponse(status_code=500, content={"detail": "v8 engine not loaded"})
        trades = simulate_btc_trades_v8(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
            confirm_bars=3,
        )
    elif version == "v9":
        if simulate_btc_trades_v9 is None:
            return JSONResponse(status_code=500, content={"detail": "v9 engine not loaded"})
        trades = simulate_btc_trades_v9(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
            extend_threshold_r=2.5,
            extend_cap_days=30,
        )
    elif version == "v10":
        if simulate_btc_trades_v10 is None:
            return JSONResponse(status_code=500, content={"detail": "v10 engine not loaded"})
        trades = simulate_btc_trades_v10(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
            min_body_atr=0.5,
            max_wick_atr=1.0,
        )
    elif version == "entry_minus_1":
        # CHAMPION ENTRY-1. The leg extreme EXCLUDING the entry candle.
        #
        # pivot_rule="leg" reads the extreme from the swing start up to and
        # including the bar that broke the swing, so the entry bar's own
        # extreme can set the stop. "leg_no_entry" stops one bar earlier.
        # Both read only bars that closed before the entry, so both are causal;
        # they differ on the bars where the entry itself extended the extreme.
        #
        # Measured: 500 trades / +445.19R gross / 355 HTF windows. That is
        # within 0.03R of the origin book (500 / +445.22R) - 497 of its 500
        # stops are identical - which is worth knowing before choosing it: it
        # sits beside the origin book, not beside the causal champion.
        if simulate_unified is None:
            return JSONResponse(status_code=500, content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            sl_buf_atr=0.01,
            ext_stop_r=3.0,
            mode="atr_high",
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            htf_rr=3.0,
            window_end="exit",
            max_positions=0,
            exp_persist=7,
            pivot_rule="leg_no_entry",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "utcsat_causal":
        # Causal champion plus one calendar knob: skip UTC Saturdays.
        # 499 -> 453 trades, +239.12 -> +279.47R net. Both parts settled at the
        # entry bar - leg reads candles[start..break+1], Saturday is a calendar test.
        if simulate_unified is None:
            return JSONResponse(status_code=500, content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf, swings_htf=swings_htf,
            candles_ltf=candles, swings_ltf=swings, fine_ltf=fine,
            sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high",
            chop_thresh=58.0, cooldown_bars=8, max_consecutive_losses=3,
            htf_rr=3.0, window_end="exit",
            max_positions=0, exp_persist=7,
            pivot_rule="leg",
            exp_skip_utc_sat=1,
        )
        trades = nested.get("ltf_trades", [])
    elif version == "utcsat_entry_minus_1":
        # ENTRY-1 stop plus the same Saturday filter. 500 -> 454 trades,
        # +325.75 -> +358.92R net. Both parts settled at the entry bar.
        #
        # Within 0.03R of the origin book under the same filter (454/+358.95):
        # ENTRY-1 and origin read the same extreme for all but a few stops, so
        # they are one book by two routes. What separates this from the champion
        # is the stop rule, and that reads candles[start..break-1], never past.
        if simulate_unified is None:
            return JSONResponse(status_code=500, content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf, swings_htf=swings_htf,
            candles_ltf=candles, swings_ltf=swings, fine_ltf=fine,
            sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high",
            chop_thresh=58.0, cooldown_bars=8, max_consecutive_losses=3,
            htf_rr=3.0, window_end="exit",
            max_positions=0, exp_persist=7,
            pivot_rule="leg_no_entry",
            exp_skip_utc_sat=1,
        )
        trades = nested.get("ltf_trades", [])
    elif version == "unified":
        # THE SHIPPING BOOK, and the only dropdown entry that is the same object
        # the registry pins. champion_multi_sw10_leg in experiment_registry.py:
        #   mode=atr_high, chop=58.0, cd=8, max_consecutive_losses=3,
        #   ext_stop_r=3.0, htf_rr=3.0, window_end="exit",
        #   exp_mltf=True, exp_persist=7, pivot_rule="leg", max_positions=0
        # Pinned IS 499 trades / +239.12R, OOS 280 / +72.8R.
        #
        # This is not the same book as the "v19_causal" entry above. That one
        # uses exp_causal_sl=1 on the pre-C16 stop rule and measures 494t /
        # +247.96R - a different configuration that happens to sound similar.
        # Every figure here comes from unified.py, which is the engine the
        # registry, the identity gate and the knob-wiring audit all run on.
        if simulate_unified is None:
            return JSONResponse(status_code=500, content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            sl_buf_atr=0.01,
            ext_stop_r=3.0,
            mode="atr_high",
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            htf_rr=3.0,
            window_end="exit",
            max_positions=0,
            exp_persist=7,
            pivot_rule="leg",
        )
        trades = nested.get("ltf_trades", [])
    elif version in ("fsent_champ_long", "fsent_champ_long_atr_low"):
        # THE FSENT FAMILY, added 2026-10-08 so the chart can show the book the
        # registry actually pins. Both are ONE knob apart:
        #     mode="atr_high"  vs  mode="atr_low"
        # Everything else is identical, which is what makes the comparison real.
        #
        # WHY `exp_mltf` IS NOT PASSED HERE, AND THIS IS NOT AN OMISSION.
        # The registry records `exp_mltf=True` on these books, but `exp_mltf` is
        # NOT a parameter of the real engine - inspect.signature on
        # simulate_htf_ltf_streak_halt returns 38 named params and no **kwargs,
        # so passing it raises TypeError. The harness creates it by patching the
        # engine source text (exp_tf_family.build_family_module injects
        # htf_bar_secs/ltf_bar_secs the same way).
        #
        # What exp_mltf=True actually does is allow overlapping positions, i.e.
        # it DISARMS the busy_until slot gate. The real engine expresses that
        # same thing as `max_positions=0` ("0 = unlimited (v19 behaviour), the
        # gate never fires" - unified.py). So max_positions=0 IS exp_mltf=True
        # here, and that is why the existing "unified" branch above also carries
        # max_positions=0 and never passes exp_mltf.
        #
        # This equivalence is asserted by measurement, not assumed:
        # backtest/tests/exp_route_parity.py re-derives both books through this
        # route's parameter set and requires the registry pins to reproduce.
        # Pinned IS 528 / +533.37 / 13.42 and OOS 311 / +239.59 / 11.88 for the
        # atr_high book; IS 641 / +721.30 / 28.90 and OOS 315 / +280.70 / 14.60
        # for atr_low.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            sl_buf_atr=0.01,
            ext_stop_r=0.0,
            mode=("atr_high" if version == "fsent_champ_long" else "atr_low"),
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=0,
            exp_partial_r=0.0,
            exp_persist=7,
            exp_fs_entry_side="long",
            pivot_rule="leg",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_champ_long_mcloff_htf15_retro":
        # RETRO 107: originally the buggy twin of fsent_champ_long_mcloff_htf15.
        # All three bugs fixed step-by-step:
        #   Step 1: cooldown look-ahead fixed (529→687 trades)
        #   Step 2: filter_pre_fs corrected (was a code regression in CAUSAL that
        #           disabled the gate via 'and causal_lookahead' — now properly
        #           applied in BOTH versions per theory doc §9)
        #   Step 3: SL pivot — extended leg extreme (prev_end+1 to break bar)
        #           instead of seg_start (687→782 trades)
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            sl_buf_atr=0.01,
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=0,   # <- same as fsent_champ_long_mcloff_htf15
            max_positions=0,
            ext_stop_r=3.0,
            exp_partial_r=0.0,
            exp_persist=7,
            pivot_rule="leg",
            exp_fs_entry_side="long",
            causal_lookahead=0,
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_sig_full":
        # THE SIG BOOK, added 2026-10-08 so the chart can show it. It is the only
        # surviving book in the registry with the lowest drawdown in the set, and
        # it is NOT the same object as any other dropdown entry.
        #
        # Two things make it different, and both are visible on the chart:
        #
        # 1. max_positions=1 - SERIAL. It never holds two positions at once, so
        #    the opposite-direction question does not arise for it at all. The
        #    839 trades are strictly one after another. Every other book in this
        #    dropdown overlaps.
        #
        # 2. exp_fs_entry_side="short" - the FS print is used as the entry for
        #    SHORTS; longs still enter at the break. Worth being precise about
        #    what that does and does not mean, because it is easy to read the flag
        #    as "this book trades shorts": it does not. In sample the LONGS
        #    produce +293.3R of the book's +295.8R and the shorts +2.5R. The
        #    flag changes WHERE shorts enter, not which side carries the P&L.
        #
        # The rest is the signal book's own ladder: bias_momentum floor 0.8,
        # fs_small_swing 6.0, trail_skip_n 2, weekends skipped. ext_stop_r is
        # 3.0 here, NOT the 0.0 the fsent pair uses - these are different books.
        # Pinned IS 234 / +295.83 / 10.78 and OOS 152 / +194.44 / 6.96.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            sl_buf_atr=0.01,
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=1,          # SERIAL - the busy_until gate is armed
            ext_stop_r=3.0,
            exp_partial_r=0.0,
            exp_fs_entry_side="short",
            exp_bias_momentum_min=0.8,
            exp_trail_skip_n=2,
            exp_fs_small_swing=6.0,
            exp_skip_weekend=1,
            window_end="exit",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_sig_multi":
        # SIG FULL with the serial gate turned OFF. One field: max_positions 1 -> 0.
        #
        # It ranks #1 of 35 on the rolling-weighted score and it is a different
        # object from everything else on this page in a way the chart will show
        # you immediately: positions OVERLAP, so several can be open at once.
        #
        # What the ranking actually rests on: every rolling 50-trade window in
        # the sample is profitable, worst 50-trade stretch still +10.0R. Zero
        # negative half-years across all eleven, zero negative financial years,
        # and zero startup drawdown - it has never gone below where it started.
        # From ANY start date its median one-year drawdown is 8.95% and its bad
        # luck tail (p10) is 6.95%, against 12.48% and 10.65% for fsent_champ_long.
        #
        # The honest caveat, and it belongs in the code and not only on the page:
        # the paired permutation is p 0.9283 in sample and 0.9138 out of sample.
        # This is a candidate on BEHAVIOUR. There is no edge in it that can be
        # told apart from reshuffling the parent.
        #
        # Everything else is sig_full's own ladder - bias_momentum_min 0.8,
        # fs_small_swing 6.0, trail_skip_n 2, weekends skipped, window_end exit.
        # Pinned IS 329 / +484.59 / 13.39 and OOS 195 / +219.82 / 7.64.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            sl_buf_atr=0.01,
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=0,          # OVERLAPPING - the only change from sig_full
            ext_stop_r=3.0,
            exp_partial_r=0.0,
            exp_fs_entry_side="short",
            exp_bias_momentum_min=0.8,
            exp_trail_skip_n=2,
            exp_fs_small_swing=6.0,
            exp_skip_weekend=1,
            window_end="exit",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_sig_multi_htffs":
        # fsent_sig_multi + ONE parameter: exp_htf_fs_entry="flip", so the HTF
        # flip-bucket window opens on the swing's FS print instead of on the
        # break, while decisive and b2 keep their breaks.
        #
        # This is the newest arm in the family and the most holdable object in it.
        # Zero negative half-years, zero negative years, every rolling 50 and
        # rolling 100 window profitable, zero startup drawdown, and one of only
        # five books in the family that survives deleting its best 10% of trades
        # (+85.3R, the best in the family by a wide margin).
        #
        # CAUSALITY: an FS-anchored window opens exactly at its own print. The
        # gap between window_start and its FS is 0.0h at min, median and max, and
        # zero entries precede their window_start - measured in
        # HTF_FS_ENTRY_REJECTED.md, not asserted.
        #
        # The caveat is the same one as sig_multi above and it is not small: p
        # 0.5091 / 0.9708. Excellent behaviour, no distinguishable edge.
        # Pinned IS 434 / +666.32 / 17.82 and OOS 221 / +234.48 / 7.99.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            sl_buf_atr=0.01,
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=0,
            ext_stop_r=3.0,
            exp_partial_r=0.0,
            exp_fs_entry_side="short",
            exp_bias_momentum_min=0.8,
            exp_trail_skip_n=2,
            exp_fs_small_swing=6.0,
            exp_skip_weekend=1,
            window_end="exit",
            exp_htf_fs_entry="flip",    # <- the only difference from sig_multi
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_champ_long_htffs":
        # fsent_champ_long + exp_htf_fs_entry="flip". The HTF flip-bucket window
        # opens on the swing's FS print instead of on the break.
        #
        # The strongest single arm in the family on RETURN TO DRAWDOWN: 45.4 net
        # per unit of drawdown against mcloff's 37.4 and sig_full's 27.4. Five
        # parameters, the same complexity as mcloff. All eight in-sample
        # half-years positive, which is what htf_fs="all" could not manage.
        #
        # Two reasons not to read the +897.94R as a verdict, both of which are
        # why this is on the page rather than in the shipping slot:
        #   - it recovers its own worst drawdown (19.78R, Rs 98,909 at 1% risk on
        #     Rs 5 lakh) in TWO TRADES. That is a very sharp shallow dip, not a
        #     deep slow one, and it is not what a drawdown number implies.
        #   - out-of-sample permutation 0.5956, and its tail dependence DEGRADES
        #     out of sample: the top 10% of trades contribute 116.9% there, the
        #     worst in the family, and deleting them leaves -50.7R.
        # Pinned IS 770 / +897.94 / 19.78 and OOS 415 / +300.43 / 14.35.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            sl_buf_atr=0.01,
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=0,
            ext_stop_r=3.0,
            exp_partial_r=0.0,
            exp_persist=7,
            pivot_rule="leg",
            exp_fs_entry_side="long",
            exp_htf_fs_entry="flip",    # <- the only difference from champ_long
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_champ_long_mcloff_htf15":
        # TWO differences from fsent_champ_long, and both are visible:
        #   max_consecutive_losses 3 -> 0. The three-loss halt stops cutting the
        #     recovery trade that follows every streak.
        #   the HTF plane swings at min_bars=15 instead of 10 (htf_min_bars=15 on
        #     the request). A longer leg on the hour chart, so the HTF windows
        #     are fewer and longer.
        #
        # Ranked #9 of 35 on the rolling-weighted score. Zero negative
        # half-years, zero negative years, median one-year drawdown from any
        # start date 13.14%.
        #
        # Of every book here with zero negative half-years, this has the strongest
        # in-sample permutation, 0.0115 - and the best out-of-sample figure any
        # zero-negative-half-year book has on the far side at 0.1445. Still short
        # of 0.05, so it is the book to WATCH rather than the book to adopt.
        # Pinned IS 560 / +616.17 / 15.13 and OOS 299 / +277.35 / 13.64.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            sl_buf_atr=0.01,
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=0,   # <- differs from champ_long
            max_positions=0,
            ext_stop_r=3.0,
            exp_partial_r=0.0,
            exp_persist=7,
            pivot_rule="leg",
            exp_fs_entry_side="long",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_flipb_htf15":
        # SEQ FLIPB ENTRY - 2026-11-01, exp_b3_flipb_entry.py. Book 107's
        # engine call with ONE knob added: the 15m trigger leaves the FS
        # print and becomes the flipb mark of the global walk in
        # btc_engine._collect_signals - the first B2 on the FLIP'S SIDE
        # (same dir as the FLIP, opposite the swing's B1; owner rule
        # 2026-11-01: "flip's are always opposite to the b1"). The walk
        # relabels marks and b3/flipb selection takes those exact marks;
        # the 1h-window dir gate is untouched, so short entries
        # still only ride short 1h windows, same as 107.
        #
        # Everything else is the 107 call verbatim (mcloff, htf15 windows,
        # atr_high router). HTF pools are NOT moved to 1h b3/flipb - that
        # arm stays off. This branch exists next to fsent_b3_htf15 as a
        # full copy, not a shared dict or a tuple-in branch: the house rule
        # around explicit elseifs exists so editing one book can never
        # silently move both.
        #
        # Measured 2026-11-01 net after costs on FRESH chains per run (the
        # walk relabels in place and is kind0-idempotent in
        # btc_engine._collect_signals), CORRECTED flipb definition: IS 445t
        # / +110.3R / dd 46.7 (both halves positive: H1 +58.7, H2 +51.6),
        # OOS 255t / -27.8R / dd 41.9 (both halves down: -9.8, -18.1).
        # In-sample star, out-of-sample reverse - on the chart to SEE the
        # flip-side trigger, not as a candidate.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            sl_buf_atr=0.01,
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=0,   # <- 107's mcl-off, unchanged
            max_positions=0,
            ext_stop_r=3.0,
            exp_partial_r=0.0,
            exp_persist=7,
            pivot_rule="leg",
            exp_entry_break="flipb",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_b3_htf15":
        # SEQ B3 ENTRY - 2026-11-01, exp_b3_flipb_entry.py. The sibling of
        # fsent_flipb_htf15 with the trigger on the b3 mark (3rd+ same-dir
        # break) instead. Same 107 call with ONE knob.
        #
        # Measured 2026-11-01 net after costs on the corrected walk: IS 411t
        # / -63.7R / dd 95.3, OOS 259t / +25.2R / dd 26.6 with BOTH halves
        # positive (H1 +5.0, H2 +20.2). IS bleeds; the OOS-robust arm under
        # the corrected rules - watch before adopting.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            sl_buf_atr=0.01,
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=0,   # <- 107's mcl-off, unchanged
            max_positions=0,
            ext_stop_r=3.0,
            exp_partial_r=0.0,
            exp_persist=7,
            pivot_rule="leg",
            exp_entry_break="b3",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_sig_trail_delay1":
        # fsent_sig_full + exp_trail_half=1 + exp_trail_delay_r=1.0. Two knobs, and
        # they are the only difference - the other 16 are identical to the sig book
        # above, which is why this branch duplicates it rather than branching on a
        # shared config dict: a shared dict would let the next person change the
        # sig book by editing one place and silently move both pins.
        #
        # WHAT IT DOES. exp_trail_half takes half the profit at the midpoint, and
        # exp_trail_delay_r holds the trailing stop back until the trade is +1R.
        # Together they convert "ride it to the target or nothing" into "bank half,
        # then trail the rest" - which is why the trade count FALLS (234 -> 199 in
        # sample, 152 -> 123 out) while the net RISES. Trades that used to round
        # trip to the stop now close at the half.
        #
        # Pinned IS 199 / +418.51 / 13.34 and OOS 123 / +182.01 / 7.54.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            sl_buf_atr=0.01,
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=1,          # SERIAL, same as the sig book
            ext_stop_r=3.0,
            exp_partial_r=0.0,
            exp_fs_entry_side="short",
            exp_bias_momentum_min=0.8,
            exp_trail_skip_n=2,
            exp_fs_small_swing=6.0,
            exp_skip_weekend=1,
            exp_trail_half=1,         # <- the only difference from fsent_sig_full
            exp_trail_delay_r=1.0,    # <- and the other one
            window_end="exit",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_champ_long_mcloff":
        # The base book with ONE integer changed: max_consecutive_losses 3 -> 0.
        # The 3-loss halt was cutting the recovery trade that follows every
        # losing streak, which is why removing it earns less in sample and more
        # out of sample rather than simply more of both.
        #
        # This is the book the whole cycle converged on. It is the ONLY one in the
        # family that clears a null in BOTH eras (paired permutation p = 0.0312 IS,
        # p = 0.0117 OOS) and the only one whose period control is powered in both
        # (b = +1.21 at t = 3.37, b = +1.86 at t = 3.97). Zero negative
        # half-years out of 12. Added to the dropdown 2026-10-10 because the most
        # supported candidate in the registry was the one book you could not look
        # at on the chart.
        #
        # ext_stop_r is 3.0, matching the registry pin. The champion branch above
        # passes 0.0, which measures identically here, but the pin is written at
        # 3.0 and the branch should read as the pin does.
        # Pinned IS 573 / +566.20 / 15.13 and OOS 334 / +274.36 / 14.16.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            sl_buf_atr=0.01,
            ext_stop_r=3.0,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            cooldown_bars=8,
            max_consecutive_losses=0,     # <- the only difference from champ_long
            max_positions=0,
            exp_partial_r=0.0,
            exp_persist=7,
            exp_fs_entry_side="long",
            pivot_rule="leg",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_champ_short":
        # The fsent_champ_long MIRROR - identical knobs, one value flipped:
        # exp_fs_entry_side="short" instead of "long". Longs then enter at the break
        # and shorts at the FS print, which is the only difference. Added because
        # the mirror is the natural control for any claim about which side the FS
        # print helps, and it was in the registry but not selectable.
        # Pinned IS 533 / +600.60 / 17.60 and OOS 312 / +239.53 / 23.87.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            sl_buf_atr=0.01,
            ext_stop_r=0.0,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=0,
            exp_partial_r=0.0,
            exp_persist=7,
            exp_fs_entry_side="short",   # <- the only difference from fsent_champ_long
            pivot_rule="leg",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_champ_long_htfesmcl4":
        # champ_long with TWO knobs changed: the HTF side enters at its own FS
        # print (exp_htf_fs_entry="all") instead of the break, and the loss-run
        # cutoff is 4 instead of 3. Pinned IS 793 / +917.80 / 27.74 and OOS
        # 437 / +326.22 / 14.20.
        #
        # READ THIS BEFORE TRUSTING THE HEADLINE. +917.80R is the highest in the
        # dropdown and it is 1.47x the trades of the book it came from, bought at
        # 1.10x the R per trade - and that 1.10x has a t of 0.46, so the per-trade
        # improvement is noise. Almost all of the extra return is more bets, not a
        # better bet. It also collapses the flip/decisive/b2 HTF regime buckets
        # into one fs_entered set, so this book stops distinguishing regimes, and
        # its OOS period-control effect is underpowered (b = +0.03, t = 0.05). It is
        # here to be LOOKED AT on the chart, not because it won.
        #
        # ext_stop_r is 3.0, matching the registry entry. The other fsent branches
        # above pass 0.0, which measures identically for 3.0/0.0/4.0/5.0 on this
        # architecture, but 3.0 is what the pin was written against.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            sl_buf_atr=0.01,
            ext_stop_r=3.0,
            mode="atr_high",
            atr_high_thresh=0.65,
            atr_low_thresh=0.35,
            cooldown_bars=8,
            max_consecutive_losses=4,     # <- was 3 in the book above
            max_positions=0,
            exp_partial_r=0.0,
            exp_persist=7,
            exp_fs_entry_side="long",
            pivot_rule="leg",
            exp_htf_fs_entry="all",       # <- the second change: HTF enters on FS
        )
        trades = nested.get("ltf_trades", [])
    # ---------------------------------------------------------------------
    # Added 2026-10-16. Six books were on the frontend dropdown with no branch
    # here, so selecting any of them returned 400 "version must be one of ..."
    # and the OWNER SAW IT, because the dropdown is how books get looked at.
    #
    # The mismatch was invisible from either side alone. books.ts listed 16
    # books; BTC_VERSIONS knew 11 of them; the dispatch knew 10. A book could
    # be added to the registry, given pins, given a monthly breakdown, appear on
    # the page with a full set of metrics - and still be impossible to actually
    # run. Nothing checked the join.
    #
    # Each branch below duplicates the call rather than sharing a config dict,
    # for the reason given on fsent_sig_trail_delay1 above: a shared dict lets
    # the next person move a pin by editing one line. The differences from
    # fsent_champ_long are marked.
    # ---------------------------------------------------------------------
    elif version == "fsent_champ_long_atr_low":
        # fsent_champ_long with the regime sign flipped: decisive windows are
        # taken when the 15m bars are QUIET rather than busy. More trades, more
        # R, deeper drawdown. One knob.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf, swings_htf=swings_htf,
            candles_ltf=candles, swings_ltf=swings, fine_ltf=fine,
            mode="atr_low",                  # <- the only difference
            atr_high_thresh=0.65, atr_low_thresh=0.35,
            sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
            max_consecutive_losses=3, max_positions=0,
            ext_stop_r=3.0, exp_partial_r=0.0, exp_persist=7,
            pivot_rule="leg", exp_fs_entry_side="long",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_champ_long_htf15_htffs":
        # fsent_champ_long_htffs on the htf15 swing series: the hour chart
        # swings at min_bars=15 instead of 10, so the HTF windows are fewer and
        # longer. htf_min_bars arrives on the request, not here - the same way
        # it does for fsent_champ_long_mcloff_htf15 above.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf, swings_htf=swings_htf,
            candles_ltf=candles, swings_ltf=swings, fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65, atr_low_thresh=0.35,
            sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
            max_consecutive_losses=3, max_positions=0,
            ext_stop_r=3.0, exp_partial_r=0.0, exp_persist=7,
            pivot_rule="leg",
            exp_fs_entry_side="long",
            exp_htf_fs_entry="flip",          # <- the HTF-FS entry gate
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_champ_long_htf15_tskip6":
        # fsent_champ_long on the htf15 series, dropping the first six
        # trailing-stop events. Converts weak early trail exits into ordinary
        # stop exits at exactly -1.000R.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf, swings_htf=swings_htf,
            candles_ltf=candles, swings_ltf=swings, fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65, atr_low_thresh=0.35,
            sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
            max_consecutive_losses=3, max_positions=0,
            ext_stop_r=3.0, exp_partial_r=0.0, exp_persist=7,
            pivot_rule="leg",
            exp_fs_entry_side="long",
            exp_trail_skip_n=6,               # <- the only difference
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_sig_sw20_short":
        # SERIAL (max_positions=1), short side only, on the sw20 swing series -
        # 20-bar HTF legs rather than 10. Banks 7.5R, window ends at exit.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf, swings_htf=swings_htf,
            candles_ltf=candles, swings_ltf=swings, fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65, atr_low_thresh=0.35,
            sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=1,                  # <- serial
            ext_stop_r=3.0,
            exp_partial_r=7.5,
            exp_persist=7, pivot_rule="leg",
            window_end="exit",
            exp_fs_entry_side="short",
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_sig_wk_pause_short":
        # fsent_sig_sw20_short on sw10, plus weekend and swing-pause gates.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf, swings_htf=swings_htf,
            candles_ltf=candles, swings_ltf=swings, fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65, atr_low_thresh=0.35,
            sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=1,
            ext_stop_r=3.0,
            exp_partial_r=7.5,
            exp_persist=7, pivot_rule="leg",
            window_end="exit",
            exp_fs_entry_side="short",
            exp_skip_weekend=1,                # <- weekend gate
            exp_swingpause=1,                  # <- and the swing pause
        )
        trades = nested.get("ltf_trades", [])
    elif version == "fsent_sig_fs_mom":
        # fsent_sig_wk_pause_short plus the bias-momentum gate at 0.8, and
        # without the 7.5R partial.
        if simulate_unified is None:
            return JSONResponse(status_code=500,
                                content={"detail": "unified engine not loaded"})
        nested = simulate_unified(
            candles_htf=candles_htf, swings_htf=swings_htf,
            candles_ltf=candles, swings_ltf=swings, fine_ltf=fine,
            mode="atr_high",
            atr_high_thresh=0.65, atr_low_thresh=0.35,
            sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
            max_consecutive_losses=3,
            max_positions=1,
            ext_stop_r=3.0,
            exp_partial_r=0.0,                 # <- no partial, unlike wk_pause
            exp_persist=7, pivot_rule="leg",
            window_end="exit",
            exp_fs_entry_side="short",
            exp_skip_weekend=1,
            exp_swingpause=1,
            exp_bias_momentum_min=0.8,         # <- the bias-momentum gate
        )
        trades = nested.get("ltf_trades", [])
    elif version == "v19_champion":
        if simulate_htf_ltf_v19_champion is None:
            return JSONResponse(status_code=500, content={"detail": "v19_champion engine not loaded"})
        # PRE-C16 book. The signal SL is seg_start, the swing's declared origin.
        # This is the LOOKAHEAD rule; it is retained only so the pre/post C16
        # comparison stays reproducible from the dropdown. It is not shippable.
        #
        # The rule is passed as an explicit argument and now reaches BOTH halves
        # of the engine: the three HTF windows (via simulate_btc_trades_v7) and
        # the LTF signal collection. It used to be applied by rebinding
        # btc_engine._collect_signals, which only ever reached the LTF half -
        # v7_timecap binds that name at module import, so the HTF windows stayed
        # on the new default and this book silently ran leg-on-HTF,
        # origin-on-LTF. That hybrid is what the dropdown used to show.
        nested = simulate_htf_ltf_v19_champion(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            sl_buf_atr=0.01,
            ext_stop_r=3.0,
            mode="atr_high",
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            htf_rr=3.0,
            window_end="exit",
            pivot_rule="origin",
            # v19_champion.py had these hardcoded. unified.py takes them as
            # arguments, so a branch that omits them silently gets the neutral
            # default instead and returns a DIFFERENT book. Found by re-running
            # v19_champion through the alias: 503 trades / +443.58R against its
            # 500 / +445.22R pin.
            max_positions=0,
            exp_persist=7,
        )
        trades = nested.get("ltf_trades", [])
    elif version == "v19_causal":
        if simulate_htf_ltf_v19_champion is None:
            return JSONResponse(status_code=500, content={"detail": "v19_causal engine not loaded"})
        # NOTE: the "494t / +247.96R vs 500t / +325.78R" figures that used to sit
        # here were stale - they predate C16. Measured on the current engine,
        # v19_causal, v19_c16 and the "unified" branch below are IDENTICAL
        # trade-for-trade at 499 trades / +355.72R gross, because pivot_rule now
        # defaults to "leg" on this engine and exp_causal_sl is v18's mechanism
        # for the same thing. Keeping three dropdown entries that return the same
        # book is worse than one, so this stays as a labelled alias rather than a
        # separate configuration.
        nested = simulate_htf_ltf_v19_champion(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            sl_buf_atr=0.01,
            ext_stop_r=3.0,
            mode="atr_high",
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            htf_rr=3.0,
            window_end="exit",
            exp_causal_sl=1,
            # v19_champion.py had these hardcoded. unified.py takes them as
            # arguments, so a branch that omits them silently gets the neutral
            # default instead and returns a DIFFERENT book. Found by re-running
            # v19_champion through the alias: 503 trades / +443.58R against its
            # 500 / +445.22R pin.
            max_positions=0,
            exp_persist=7,
        )
        trades = nested.get("ltf_trades", [])
    elif version == "v19_c16":
        # POST-C16 book, no separate signal collection - pivot_rule defaults to
        # "leg", so the initial stop is the swing's own extreme up to the entry
        # candle. Measured IS 499t / +239.12R. Present so the pre/post diff is
        # visible trade by trade in the dropdown.
        if simulate_htf_ltf_v19_champion is None:
            return JSONResponse(status_code=500, content={"detail": "v19_c16 engine not loaded"})
        nested = simulate_htf_ltf_v19_champion(
            candles_htf=candles_htf,
            swings_htf=swings_htf,
            candles_ltf=candles,
            swings_ltf=swings,
            fine_ltf=fine,
            sl_buf_atr=0.01,
            ext_stop_r=3.0,
            mode="atr_high",
            chop_thresh=58.0,
            cooldown_bars=8,
            max_consecutive_losses=3,
            htf_rr=3.0,
            window_end="exit",
            exp_causal_sl=0,
            # v19_champion.py had these hardcoded. unified.py takes them as
            # arguments, so a branch that omits them silently gets the neutral
            # default instead and returns a DIFFERENT book. Found by re-running
            # v19_champion through the alias: 503 trades / +443.58R against its
            # 500 / +445.22R pin.
            max_positions=0,
            exp_persist=7,
        )
        trades = nested.get("ltf_trades", [])
    else:
        trades = simulate_btc_trades(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            trail_distance_r=float(trail_distance_r),
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )

    # HTF window boundaries for the chart overlay. Collected here, AFTER the
    # version dispatch above, because `nested` is only bound once a standalone
    # book has run - reading it earlier raises UnboundLocalError.
    #
    # These are the engine's own intervals [start, end, dir, entry_price, sl].
    # They ARE the windows - not reconstructed from trades. 179 for the
    # champion, all unique.
    #
    # Only REPLACES the list for a standalone book. The nested htf_ltf path
    # above already built one from merged_intervals in the entry_ts/exit_ts/dir
    # shape; assigning [] unconditionally here would have silently emptied it
    # for every htf_ltf="15m" book.
    if version in STANDALONE_HTF_LTF_VERSIONS:
        # The window START is drawn at the instant it becomes KNOWABLE, not at the
        # candle that opened it. iv[0] is the 1h candle's OPEN, and the window's
        # existence is not knowable until that candle closes, 3600s later. Drawing
        # the line at iv[0] tells the reader the window opened an hour before it
        # could have been observed, and on 10 Mar 2025 it put the line at 18:30 for
        # a window whose first knowable instant is 19:30 - the same 19:30 the trade
        # itself was taken on, which is exactly why a reviewer looking at the chart
        # reads it as a lookahead and is right to be suspicious.
        #
        # The END is already correct and needs no change: the engine stores it
        # knowable via _wend_settle (exit_ts + 60 with 1m data), which is C17's
        # finding. Only the start side was drawing the raw candle open.
        htf_windows = [
            {"startTime": int(iv[0]) + _HTF_CLOSE_OFFSET, "endTime": int(iv[1]),
             "isLong": int(iv[2]) == 1,
             "entryPrice": float(iv[3]), "slPrice": float(iv[4])}
            for iv in nested.get("intervals", [])
            if len(iv) >= 5
        ]

    htf_windows = locals().get("htf_windows", [])

    # cost model: round-trip fees (% notional, both sides) + slippage points,
    # expressed in R against each trade's own risk -> honest NET R stats.
    _trade_costs(trades, fee_pct, slippage_pts, entry_slip_pct, exit_slip_pct, funding_rate_pct)
    stats = _net_stats(trade_stats(trades), trades)

    return {
        "params": params,
        "count": len(candles),
        "swings_used": len(swings),
        "trades": trades,
        "stats": stats,
        # HTF window boundaries for the chart overlay: start line, end line,
        # direction. Empty for books that are not standalone HTF-LTF engines.
        "htf_windows": htf_windows,
    }


@router.get("/versions")
def btc_versions():
    """List available crazy-idea versions (v1 locked, v2..v6 isolated)."""
    return {"versions": BTC_VERSIONS, "labels": VERSION_LABELS, "default": "v1"}

@router.get("/summary")
def btc_summary(
    tf: str = "5m",
    mode: str = "continuous",
    limit: int | None = None,
    fee_pct: float = 0.055,
    slippage_pts: float = 2.0,
    entry_slip_pct: float = 0.005,
    exit_slip_pct: float = 0.010,
    entry_selection: str = "stream",
    version: str = "v1",
    symbol: str = "BTCUSDT",
):
    """\'Konsi best hai\' table - every master preset on its OWN reference TF.

    Each preset is evaluated on the timeframe it was designed for (bestTf),
    with its own minBars/swing config, then reports base R (zero cost) AND
    net R after fee_pct %/side + slippage_pts. `best` = highest net_r row.
    """
    if entry_selection not in ("stream", "final"):
        return JSONResponse(status_code=400, content={"detail": "entry_selection must be stream | final"})
    if not (0 <= float(fee_pct) <= 0.5):
        return JSONResponse(status_code=400, content={"detail": "fee_pct must be 0..0.5 (% per side)"})
    if not (0 <= float(slippage_pts) <= 1000):
        return JSONResponse(status_code=400, content={"detail": "slippage_pts must be 0..1000"})
    if version not in BTC_VERSIONS:
        return JSONResponse(status_code=400, content={"detail": f"version must be one of {BTC_VERSIONS}"})
    # group presets by their reference TF, load each TF's data once
    by_tf: dict = {}
    for p in _MASTER_PRESETS:
        ptf = p.get("bestTf", "15m")
        by_tf.setdefault(ptf, []).append(p)

    rows = []
    for ptf, presets in by_tf.items():
        win_p, err_p = _load_window(ptf, None, symbol)
        if err_p:
            continue
        candles_p, flow_p = win_p

        # 15m bias timeline (only for presets on lower TFs)
        bias_timeline = None
        if ptf in ("1m", "5m"):
            htf, htf_err = _load_window("15m", None, symbol)
            if htf_err is None:
                htf_candles, htf_flow = htf
                htf_swings = _compute_swings(htf_flow, mode)
                bias_timeline = sorted(
                    (
                        int(htf_candles[s["confirmed_at_idx"]]["ts"]),
                        s["dir"],
                    )
                    for s in htf_swings
                    if 0 <= int(s.get("confirmed_at_idx", -1)) < len(htf_candles)
                )

        # 1m-precise exit fills
        fine = None
        if ptf != "1m":
            fine = _load_fine_1m(candles_p[0]["ts"], candles_p[-1]["ts"], symbol) or None

        for p in presets:
            sw_p = _compute_swings(flow_p, mode, min_bars=p["min_bars"])
            row = _run_preset(
                candles_p, sw_p, p, fee_pct, slippage_pts,
                bias_timeline=bias_timeline if p["bias"] == "15m" else None,
                day_gate=_streak_regime_gate(candles_p) if p["regime"] == "streak_311" else None,
                fine=fine,
                entry_selection=entry_selection,
                version=version,
                entry_slip_pct=entry_slip_pct,
                exit_slip_pct=exit_slip_pct,
            )
            row["tf"] = ptf
            rows.append(row)

    rows.sort(key=lambda r: r["net_r"], reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    return {
        "fee_pct": float(fee_pct),
        "slippage_pts": float(slippage_pts),
        "entry_slip_pct": float(entry_slip_pct),
        "exit_slip_pct": float(exit_slip_pct),
        "entry_selection": entry_selection,
        "version": version,
        "rows": rows,
        "best": rows[0]["key"] if rows else None,
    }


# â”€â”€ data fetch (append new candles to CSVs) â€” all exchanges â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.post("/fetch")
def btc_fetch(body: dict | None = None):
    """Fetch new candles and append to the CSVs.

    Optional JSON body: {"exchange": "spot"|"perp"|"bybit", "tfs": ["15m","1h"]}
    If omitted, defaults to exchange="spot", refreshes all TFs.
    Idempotent: only appends timestamps not already in the CSV.
    """
    exchange = "spot"
    targets = None
    if body:
        exchange = body.get("exchange", "spot")
        if exchange not in EXCHANGES:
            return JSONResponse(
                status_code=400,
                content={"detail": f"unknown exchange: {exchange}. must be in {sorted(EXCHANGES)}"},
            )
        if body.get("tfs"):
            tfs = body["tfs"]
            bad = [t for t in tfs if t not in BTC_TFS]
            if bad:
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"unknown tf(s): {bad}. must be in {sorted(BTC_TFS)}"},
                )
            targets = tfs
    try:
        return refresh_all(exchange, targets)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.get("/fetch/status")
def btc_fetch_status(exchange: str = "spot"):
    """Current last timestamp per TF â€” see what the button would append."""
    if exchange not in EXCHANGES:
        return JSONResponse(
            status_code=400,
            content={"detail": f"unknown exchange: {exchange}"},
        )
    out = {}
    for tf in BTC_TFS:
        out[tf] = {"last_ts": btc_last_ts(exchange, tf)}
    return out


@router.post("/seed")
def btc_seed(body: dict):
    """Seed the live engine from known backtest timestamps.

    Body: {"1h": "2026-09-09 15:00:00", "15m": "2026-09-10 04:30:00"}

    Timestamps are IST wall-clock (matching CSV convention).
    Engine downloads candles from Binance spot starting BEFORE those timestamps
    (warmup: 50 bars for 15m, 34 bars for 1h) and replays through SwingEngine.
    """
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td

    IST_OFF = _td(hours=5, minutes=30)
    ts_1h = body.get("1h")
    ts_15m = body.get("15m")
    if not ts_1h or not ts_15m:
        return JSONResponse(status_code=400, content={"detail": "Both '1h' and '15m' timestamps required. Format: 'YYYY-MM-DD HH:MM:SS'"})

    # Validate timestamps (IST wall-clock -> UTC epoch ms)
    try:
        dt_1h_naive = _dt.strptime(ts_1h, "%Y-%m-%d %H:%M:%S")
        dt_15m_naive = _dt.strptime(ts_15m, "%Y-%m-%d %H:%M:%S")
        dt_1h = (dt_1h_naive - IST_OFF).replace(tzinfo=_tz.utc)
        dt_15m = (dt_15m_naive - IST_OFF).replace(tzinfo=_tz.utc)
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Invalid timestamp format. Use 'YYYY-MM-DD HH:MM:SS'"})

    import time as _time

    # 15m: fetch from (seed - 50*15min) to now
    warmup_15m_ms = 50 * 15 * 60 * 1000  # 50 bars * 15min
    start_15m_ms = int(dt_15m.timestamp() * 1000) - warmup_15m_ms
    # 1h: fetch from (seed - 34*1h) to now
    warmup_1h_ms = 34 * 3600 * 1000  # 34 bars * 1h
    start_1h_ms = int(dt_1h.timestamp() * 1000) - warmup_1h_ms

    # Fetch candles from Binance REST
    import urllib.request as _urllib
    import json as _json

    def _fetch(symbol, interval, start_ms, limit=1000):
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_ms}&limit={limit}"
        req = _urllib.Request(url)
        req.add_header("User-Agent", "Backbencher/SeedAPI/1.0")
        with _urllib.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read().decode())
        candles = []
        for k in data:
            candles.append({
                "open_time": int(k[0]),
                "close_time": int(k[6]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "is_closed": True,
            })
        return candles

    result = {}

    # Fetch 15m
    try:
        raw_15m = _fetch(SYMBOL, "15m", start_15m_ms, limit=1000)
        candles_15m = []
        for c in raw_15m:
            ts = int(c["close_time"]) // 1000
            utc_dt = _dt.fromtimestamp(int(c["open_time"]) // 1000, tz=_tz.utc)
            ist_dt = utc_dt + IST_OFF
            date = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
            candles_15m.append({
                "date": date, "ts": ts,
                "open": c["open"], "high": c["high"],
                "low": c["low"], "close": c["close"],
            })
        candles_15m.sort(key=lambda x: x["ts"])

        from src.firstswing import SwingEngine
        eng_15m = SwingEngine({"minBars": 50})
        swings_15m = []
        for i, c in enumerate(candles_15m):
            fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
            eng_15m.process_bar(fc, i)
            if eng_15m.declared:
                src_kind = "SUS" if eng_15m.confirm_source == "sustain" else "FS"
                decisive = eng_15m.break_marks[-1] if eng_15m.break_marks else None
                bk = decisive.kind if decisive else None
                swings_15m.append({
                    "swing_index": len(swings_15m),
                    "seg": {"dir": "B" if eng_15m.dir == "up" else "S",
                            "start_idx": eng_15m.start_idx, "start_px": eng_15m.start_px,
                            "end_idx": eng_15m.end_idx, "end_px": eng_15m.end_px},
                    "dir": eng_15m.dir,
                    "break_kind": bk,
                    "breaks": [{"idx": b.idx, "time": b.time, "kind": b.kind, "dir": b.dir, "px": b.px}
                               for b in eng_15m.break_marks],
                    "confirmed_at_idx": eng_15m.confirmed_at_idx,
                    "confirmed_at_time": eng_15m.confirmed_at_time,
                })
                # Reset engine for next swing
                eng_15m = SwingEngine({"minBars": 50})
                eng_15m.defer_same_bar_arm = True
                eng_15m.seed_idx = eng_15m.end_idx + 1 if eng_15m.end_idx >= 0 else i + 1

        # Open swing
        open_15m = None
        if eng_15m.dir and not eng_15m.declared:
            open_15m = {
                "swing_index": len(swings_15m),
                "dir": eng_15m.dir,
                "breaks": [{"idx": b.idx, "time": b.time, "kind": b.kind, "dir": b.dir, "px": b.px}
                           for b in eng_15m.break_marks],
            }

        result["15m"] = {
            "candles": len(candles_15m),
            "swings": len(swings_15m),
            "open": {"dir": open_15m["dir"], "breaks": len(open_15m.get("breaks", []))} if open_15m else None,
            "swings_data": swings_15m,
            "open_data": open_15m,
        }
    except Exception as e:
        result["15m"] = {"error": str(e)}

    # Fetch 1h
    try:
        raw_1h = _fetch(SYMBOL, "1h", start_1h_ms, limit=500)
        candles_1h = []
        for c in raw_1h:
            ts = int(c["close_time"]) // 1000
            utc_dt = _dt.fromtimestamp(int(c["open_time"]) // 1000, tz=_tz.utc)
            ist_dt = utc_dt + IST_OFF
            date = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
            candles_1h.append({
                "date": date, "ts": ts,
                "open": c["open"], "high": c["high"],
                "low": c["low"], "close": c["close"],
            })
        candles_1h.sort(key=lambda x: x["ts"])

        eng_1h = SwingEngine({"minBars": 20})
        swings_1h = []
        for i, c in enumerate(candles_1h):
            fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
            eng_1h.process_bar(fc, i)
            if eng_1h.declared:
                src_kind = "SUS" if eng_1h.confirm_source == "sustain" else "FS"
                decisive = eng_1h.break_marks[-1] if eng_1h.break_marks else None
                bk = decisive.kind if decisive else None
                swings_1h.append({
                    "swing_index": len(swings_1h),
                    "seg": {"dir": "B" if eng_1h.dir == "up" else "S",
                            "start_idx": eng_1h.start_idx, "start_px": eng_1h.start_px,
                            "end_idx": eng_1h.end_idx, "end_px": eng_1h.end_px},
                    "dir": eng_1h.dir,
                    "break_kind": bk,
                    "breaks": [{"idx": b.idx, "time": b.time, "kind": b.kind, "dir": b.dir, "px": b.px}
                               for b in eng_1h.break_marks],
                    "confirmed_at_idx": eng_1h.confirmed_at_idx,
                    "confirmed_at_time": eng_1h.confirmed_at_time,
                })
                eng_1h = SwingEngine({"minBars": 20})
                eng_1h.defer_same_bar_arm = True
                eng_1h.seed_idx = eng_1h.end_idx + 1 if eng_1h.end_idx >= 0 else i + 1

        open_1h = None
        if eng_1h.dir and not eng_1h.declared:
            open_1h = {
                "swing_index": len(swings_1h),
                "dir": eng_1h.dir,
                "breaks": [{"idx": b.idx, "time": b.time, "kind": b.kind, "dir": b.dir, "px": b.px}
                           for b in eng_1h.break_marks],
            }

        result["1h"] = {
            "candles": len(candles_1h),
            "swings": len(swings_1h),
            "open": {"dir": open_1h["dir"], "breaks": len(open_1h.get("breaks", []))} if open_1h else None,
            "swings_data": swings_1h,
            "open_data": open_1h,
        }
    except Exception as e:
        result["1h"] = {"error": str(e)}

    return {"status": "ready", "seed_1h": ts_1h, "seed_15m": ts_15m, **result}

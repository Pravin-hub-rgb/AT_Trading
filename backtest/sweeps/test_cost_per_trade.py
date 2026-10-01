"""Per-trade cost sensitivity analysis — Bybit Perp (Trailing SL).

Peer model: asymmetric % slippage (entry is orderly, exit is adverse during fast move).
  Entry: 0.001% (1bp) — signal candle close
  Exit:  0.003% (3bp) — trailing SL triggers intrabar

Sensitivity table:
  Optimistic:    0.0005% / 0.001%
  Base:          0.001%  / 0.003%
  Conservative:  0.002%  / 0.005%
  Very conserv.: 0.005%  / 0.010%

Fees: Bybit taker 0.055% per side (separate from slippage).
"""
import sys
sys.path.insert(0, r"C:\Users\Pravin\Desktop\main\AT_Trading\backend")

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_engine import trade_stats
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

TAKER_FEE_PCT = 0.055

# Peer's slippage scenarios (% of price, asymmetric)
SCENARIOS = [
    ("Optimistic",       0.0005, 0.001),
    ("Base",             0.001,  0.003),
    ("Conservative",     0.002,  0.005),
    ("Very conservative", 0.005, 0.010),
]

# INR/USDT monthly averages
INR_USDT = {
    "2023-01": 81.74, "2023-02": 82.60, "2023-03": 82.27, "2023-04": 81.97,
    "2023-05": 82.30, "2023-06": 82.23, "2023-07": 82.16, "2023-08": 82.81,
    "2023-09": 83.07, "2023-10": 83.22, "2023-11": 83.27, "2023-12": 83.25,
    "2024-01": 83.11, "2024-02": 82.95, "2024-03": 83.02, "2024-04": 83.40,
    "2024-05": 83.39, "2024-06": 83.46, "2024-07": 83.59, "2024-08": 83.89,
    "2024-09": 83.79, "2024-10": 84.01, "2024-11": 84.33, "2024-12": 84.97,
    "2025-01": 86.27, "2025-02": 87.06, "2025-03": 86.52, "2025-04": 85.58,
    "2025-05": 85.25, "2025-06": 85.88, "2025-07": 86.17, "2025-08": 87.57,
    "2025-09": 88.32, "2025-10": 88.37, "2025-11": 88.84, "2025-12": 90.04,
    "2026-01": 90.90, "2026-02": 90.75, "2026-03": 92.82, "2026-04": 93.48,
    "2026-05": 95.53, "2026-06": 94.96, "2026-07": 95.86, "2026-08": 95.44,
    "2026-09": 94.90,
}

RISK_USDT = 50.0

def to_cf(df):
    c, f = [], []
    for row in df.itertuples():
        d = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        c.append({"date":d,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),
                   "low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
        f.append(FlowCandle(date=d,open=float(row.open),high=float(row.high),
                            low=float(row.low),close=float(row.close)))
    return c, f


def run_scenario(trades, name, entry_slip_pct, exit_slip_pct):
    """Run one slippage scenario on a fresh copy of trades (so cost_r doesn't stack)."""
    import copy
    t_copy = copy.deepcopy(trades)
    total_cost, n = _trade_costs(t_copy, TAKER_FEE_PCT, 0.0,
                                 entry_slip_pct=entry_slip_pct,
                                 exit_slip_pct=exit_slip_pct)
    closed = [t for t in t_copy if t["outcome"] != "open"]
    net_rs = [float(t["r_multiple"]) - float(t.get("cost_r", 0)) for t in closed]
    fee_rs = [float(t.get("fee_r", 0)) for t in closed]
    slip_rs = [float(t.get("slip_r", 0)) for t in closed]
    gross_total = sum(float(t["r_multiple"]) for t in closed)
    cost_total = sum(float(t.get("cost_r", 0)) for t in closed)
    fee_total = sum(fee_rs)
    slip_total = sum(slip_rs)
    net_total = sum(net_rs)
    wins = [r for r in net_rs if r > 0]
    losses = [r for r in net_rs if r <= 0]
    net_wr = len(wins) / len(net_rs) * 100 if net_rs else 0
    net_pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    # Max DD
    peak = max_dd = equity = 0
    for r in net_rs:
        equity += r
        if equity > peak: peak = equity
        dd = peak - equity
        if dd > max_dd: max_dd = dd
    # Avg slippage per trade in USD
    avg_slip_usdt = (slip_total / len(closed) * RISK_USDT) if closed else 0
    avg_entry = sum(abs(float(t["entry_price"])) for t in closed) / len(closed) if closed else 0
    avg_exit = sum(abs(float(t.get("exit_price", 0))) for t in closed) / len(closed) if closed else 0

    return {
        "name": name,
        "entry_pct": entry_slip_pct,
        "exit_pct": exit_slip_pct,
        "trades": len(closed),
        "gross_r": gross_total,
        "fee_r": fee_total,
        "slip_r": slip_total,
        "cost_r": cost_total,
        "net_r": net_total,
        "net_wr": net_wr,
        "net_pf": net_pf,
        "max_dd": max_dd,
        "avg_slip_usdt": avg_slip_usdt,
        "avg_entry": avg_entry,
        "avg_exit": avg_exit,
    }


def main():
    print("=" * 80)
    print("SLIPPAGE SENSITIVITY — BYBIT PERP (Trailing SL)")
    print(f"Fee: {TAKER_FEE_PCT}% taker both sides | Risk: ${RISK_USDT} USDT/trade")
    print("=" * 80)

    # Load data
    print("\n[1] Loading data...")
    df1h = load_btc_df("1h", "BTCUSDT_BYBIT")
    df15 = load_btc_df("15m", "BTCUSDT_BYBIT")
    c1h, f1h = to_cf(df1h)
    c15, f15 = to_cf(df15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol="BTCUSDT_BYBIT")
    print(f"  1h: {len(c1h)} | 15m: {len(c15)} | 1m: {len(fine)}")

    # Run v18 backtest once
    print("\n[2] Running v18 backtest...")
    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=0.20, ext_stop_r=1.5,
        mode="b2_vs_flip_chop", chop_thresh=58.0,
        cooldown_bars=0, max_consecutive_losses=5,
    )
    trades = result["ltf_trades"]
    gross_stats = trade_stats(trades)
    print(f"  Gross: {gross_stats['trades']} trades, {gross_stats['total_r']:+.1f}R, "
          f"WR {gross_stats['win_rate']:.1f}%, PF {gross_stats['profit_factor']:.2f}")

    # Run all scenarios
    print("\n[3] Running slippage sensitivity...")
    results = []
    for name, entry_pct, exit_pct in SCENARIOS:
        r = run_scenario(trades, name, entry_pct, exit_pct)
        results.append(r)

    # ── COMPARISON TABLE ──
    print(f"\n{'=' * 80}")
    print("SENSITIVITY RESULTS")
    print(f"{'=' * 80}")
    hdr = f"  {'Scenario':<20} {'Entry':>7} {'Exit':>7} | {'Gross':>8} {'Fee':>7} {'Slip':>7} {'Cost':>7} {'Net':>8} | {'PF':>5} {'WR':>5} {'DD':>6}"
    print(hdr)
    print(f"  {'-'*20}-+-{'-'*7}-+-{'-'*7}-+-{'-'*8}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*8}-+-{'-'*5}-+-{'-'*5}-+-{'-'*6}")
    for r in results:
        entry_str = f"{r['entry_pct']:.4f}%"
        exit_str = f"{r['exit_pct']:.3f}%"
        print(f"  {r['name']:<20} {entry_str:>7} {exit_str:>7} | "
              f"{r['gross_r']:>+7.1f} {r['fee_r']:>6.1f} {r['slip_r']:>6.1f} {r['cost_r']:>6.1f} {r['net_r']:>+7.1f} | "
              f"{r['net_pf']:>5.2f} {r['net_wr']:>4.1f}% {r['max_dd']:>5.1f}R")

    # ── GROSS (NO COST) ──
    print(f"\n  {'GROSS (no cost)':<20} {'---':>7} {'---':>7} | "
          f"{gross_stats['total_r']:>+7.1f} {'---':>7} {'---':>7} {'---':>7} {gross_stats['total_r']:>+7.1f} | "
          f"{gross_stats['profit_factor']:>5.2f} {gross_stats['win_rate']:>4.1f}% {'---':>5}")

    # ── FLAT $2 COMPARISON ──
    import copy
    t_flat = copy.deepcopy(trades)
    _trade_costs(t_flat, TAKER_FEE_PCT, 2.0)
    closed_flat = [t for t in t_flat if t["outcome"] != "open"]
    net_flat = sum(float(t["r_multiple"]) - float(t.get("cost_r", 0)) for t in closed_flat)
    cost_flat = sum(float(t.get("cost_r", 0)) for t in closed_flat)
    print(f"  {'Flat $2 (old)':<20} {'---':>7} {'---':>7} | "
          f"{gross_stats['total_r']:>+7.1f} {'---':>7} {'---':>7} {cost_flat:>6.1f} {net_flat:>+7.1f} | "
          f"{'---':>5} {'---':>5} {'---':>5}")

    # ── DOLLAR IMPACT ──
    print(f"\n{'=' * 80}")
    print("DOLLAR IMPACT (at $50 risk/trade)")
    print(f"{'=' * 80}")
    print(f"  {'Scenario':<20} {'Cost R':>8} {'Cost $':>10} {'Net $':>10} {'Avg slip':>10}")
    print(f"  {'-'*20}-+-{'-'*8}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")
    for r in results:
        cost_usdt = r["cost_r"] * RISK_USDT
        net_usdt = r["net_r"] * RISK_USDT
        print(f"  {r['name']:<20} {r['cost_r']:>7.2f}R {cost_usdt:>+9,.0f}$ {net_usdt:>+9,.0f}$ {r['avg_slip_usdt']:>9.2f}$")

    # ── TOP 5 COST TRADES (Base scenario) ──
    print(f"\n{'=' * 80}")
    print("TOP 5 HIGHEST COST TRADES (Base: 0.001%/0.003%)")
    print(f"{'=' * 80}")
    t_base = copy.deepcopy(trades)
    _trade_costs(t_base, TAKER_FEE_PCT, 0.0, entry_slip_pct=0.001, exit_slip_pct=0.003)
    closed_base = sorted([t for t in t_base if t["outcome"] != "open"],
                         key=lambda t: abs(float(t.get("cost_r", 0))), reverse=True)
    print(f"  {'#':>3} | {'Entry':>10} | {'Exit':>10} | {'Risk$':>7} | "
          f"{'Fee_R':>7} {'Slip_R':>7} {'Cost_R':>7} | {'Gross':>7} {'Net':>7} | {'Outcome'}")
    print(f"  {'-'*3}-+-{'-'*10}-+-{'-'*10}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*6}")
    for i, t in enumerate(closed_base[:5]):
        entry = float(t["entry_price"])
        exit_p = float(t.get("exit_price", entry))
        risk = abs(entry - float(t["sl"]))
        fee_r = float(t.get("fee_r", 0))
        slip_r = float(t.get("slip_r", 0))
        cost_r = float(t.get("cost_r", 0))
        gross_r = float(t["r_multiple"])
        net_r = gross_r - cost_r
        print(f"  {i+1:>3} | {entry:>10.0f} | {exit_p:>10.0f} | {risk:>7.0f} | "
              f"{fee_r:>7.4f} {slip_r:>7.4f} {cost_r:>7.4f} | {gross_r:>+7.2f} {net_r:>+7.2f} | {t.get('outcome','?')}")

    print(f"\n{'=' * 80}")
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()

"""v5 — minBars 50 BE1 vs BE0. Same engine as v1 but breakeven 1R."""
from src.btc.btc_engine import simulate_btc_trades as sim_v1

def simulate_btc_trades_v5(candles, swings, **kwargs):
    # v5 just forces breakeven 1.0 for decisive50 to test BE1
    kwargs["breakeven_r"] = 1.0
    return sim_v1(candles, swings, **kwargs)

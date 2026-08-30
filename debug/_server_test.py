"""Test the server's backtest API directly via HTTP."""
import urllib.request
import json

url = "http://127.0.0.1:8003/api/intraday/backtest?sl_mode=avg&execution=5min&trailing=off&gap_pct=0.27"
try:
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    s = data["stats"]
    n_traded = sum(1 for d in data["days"] if d.get("trades"))
    print(f"=== SERVER avg mode ===")
    print(f"  trades={s['trades']}  win_rate={s['win_rate']}%  total_r={s['total_r']}  avg_r={s['avg_r']}")
    print(f"  days_traded={n_traded}/{len(data['days'])}")
    print(f"  longs={s.get('longs', 0)} shorts={s.get('shorts', 0)}")
    print(f"  outcomes={s.get('outcomes', {})}")
    print(f"\n  first 5 traded days:")
    shown = 0
    for d in data["days"]:
        if d.get("trades"):
            outcomes = [t.get("outcome") for t in d["trades"]]
            print(f"    {d['date']} n={len(d['trades'])} outcomes={outcomes}")
            shown += 1
            if shown >= 5:
                break
except Exception as e:
    print(f"Error: {e}")
    print("Is the server running? Try: python -m uvicorn backend.server:app --reload")

"""Fetch all historical funding rates for BTCUSDT from Bybit."""
import requests, json, time, os

url = "https://api.bybit.com/v5/market/funding/history"
all_data = []
end_time = None
cutoff = 1672531200000  # 2023-01-01 UTC ms
batch = 0

while True:
    batch += 1
    params = {"category": "linear", "symbol": "BTCUSDT", "limit": 200}
    if end_time:
        params["endTime"] = end_time

    r = requests.get(url, params=params, timeout=15)
    d = r.json()

    if d["retCode"] != 0:
        print("Error:", d)
        break

    items = d["result"]["list"]
    if not items:
        break

    all_data.extend(items)

    oldest_ts = int(items[-1]["fundingRateTimestamp"])
    oldest_dt = time.strftime("%Y-%m-%d %H:%M", time.gmtime(oldest_ts / 1000))
    print("Batch %d: got %d records, oldest=%s (%s)" % (batch, len(items), oldest_ts, oldest_dt))

    if oldest_ts <= cutoff:
        print("Reached cutoff date")
        break

    end_time = oldest_ts - 1
    time.sleep(0.2)

print("Total: %d records" % len(all_data))

# Sort by timestamp ascending
all_data.sort(key=lambda x: int(x["fundingRateTimestamp"]))

# Filter to 2023+
all_data = [d for d in all_data if int(d["fundingRateTimestamp"]) >= cutoff]
print("After filter: %d records" % len(all_data))

# Date range
if all_data:
    first = int(all_data[0]["fundingRateTimestamp"])
    last = int(all_data[-1]["fundingRateTimestamp"])
    print("Range: %s to %s" % (
        time.strftime("%Y-%m-%d", time.gmtime(first / 1000)),
        time.strftime("%Y-%m-%d", time.gmtime(last / 1000))
    ))

# Stats
rates = [float(d["fundingRate"]) for d in all_data]
print("Funding rate stats:")
print("  min: %.4f%%" % (min(rates) * 100))
print("  max: %.4f%%" % (max(rates) * 100))
print("  avg: %.4f%%" % (sum(rates) / len(rates) * 100))
print("  >0.05%%: %d times" % sum(1 for r in rates if r > 0.0005))
print("  >0.10%%: %d times" % sum(1 for r in rates if r > 0.001))
print("  >0.15%%: %d times" % sum(1 for r in rates if r > 0.0015))
print("  >0.20%%: %d times" % sum(1 for r in rates if r > 0.002))
print("  <-0.05%%: %d times" % sum(1 for r in rates if r < -0.0005))

# Save
os.makedirs("live_stuff/data", exist_ok=True)
with open("live_stuff/data/btc_funding_history.json", "w") as f:
    json.dump(all_data, f)
print("Saved to btc_funding_history.json")

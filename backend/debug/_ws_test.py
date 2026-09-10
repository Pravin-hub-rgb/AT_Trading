import asyncio
import json
import websockets

async def test():
    # Try single stream first
    url = "wss://stream.binance.com:9443/ws/btcusdt@kline_15m"
    print(f"connecting to: {url}")
    ws = await websockets.connect(url, ping_interval=20, ping_timeout=10, open_timeout=15)
    print("connected")
    try:
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=30)
            data = json.loads(raw)
            d = data
            if d.get("e") == "kline":
                k = d["k"]
                print(f'kline: {k["i"]} closed={k["x"]} t={k["t"]}')
                if k["x"]:
                    break
    except asyncio.TimeoutError:
        print("timeout - no data in 30s")
    finally:
        await ws.close()

asyncio.run(test())

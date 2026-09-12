"""Stream Bybit ticks — prints each one."""
import asyncio, json, websockets

async def main():
    url = "wss://stream.bybit.com/v5/public/linear"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"op": "subscribe", "args": ["publicTrade.BTCUSDT"]}))
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < 10:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            if data.get("topic") == "publicTrade.BTCUSDT":
                for t in data.get("data", []):
                    print(f"  {t['p']}  {t['S']}  {t['v']}BTC  {t['T']}")

asyncio.run(main())

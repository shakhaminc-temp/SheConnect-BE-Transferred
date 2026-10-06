import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as c:
        try:
            r = await c.get('https://photon.komoot.io/api/?q=Pune&limit=5&lang=en', headers={'User-Agent': 'sheconnect-app/1.0'})
            print("Status:", r.status_code)
            print("Body:", r.text[:500])
        except Exception as e:
            print("Error:", e)

asyncio.run(test())

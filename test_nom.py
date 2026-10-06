import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as c:
        try:
            url = 'https://nominatim.openstreetmap.org/search?format=json&q=Pune+Station,+India&limit=1&addressdetails=1&featuretype=settlement&namedetails=1'
            r = await c.get(url, headers={'User-Agent': 'sheconnect/1.0'})
            print("Status:", r.status_code)
            print("Body:", r.json())
        except Exception as e:
            print("Error:", e)

asyncio.run(test())

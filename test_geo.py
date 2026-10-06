import sys
import httpx
import asyncio

async def test_photon():
    async with httpx.AsyncClient() as client:
        r = await client.get('https://photon.komoot.io/api/?q=Pune&limit=5&lang=en')
        print("Status code:", r.status_code)
        print("Content:", r.text[:200])

asyncio.run(test_photon())

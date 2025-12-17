import httpx
import asyncio

async def check():
    async with httpx.AsyncClient() as client:
        # Try to hit the endpoint that is failing
        resp = await client.get("http://localhost:8000/api/events?limit=50&start_date=2024-01-01")
        print(f"Status: {resp.status_code}")
        if resp.status_code == 422:
            print("Error Body:")
            print(resp.json())
        else:
            print("Success (unexpected based on user report)")
            # Print first item to see if schema matches
            data = resp.json()
            if data:
                print("Sample item keys:", data[0].keys())

if __name__ == "__main__":
    asyncio.run(check())

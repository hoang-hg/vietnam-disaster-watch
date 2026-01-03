import asyncio
import random
from app.settings import settings

async def test_rotation_logic():
    print("--- TESTING PROXY ROTATION LOGIC ---")
    mock_proxies = ["http://proxy1.com:8080", "http://proxy2.com:8080", "http://proxy3.com:8080"]
    
    # Simulate the logic in crawler.py
    for i in range(5):
        selected = random.choice(mock_proxies)
        print(f"Fetch {i+1}: Selected Proxy -> {selected}")
        
    print("\n--- TESTING JITTER LOGIC ---")
    for i in range(3):
        jitter = random.uniform(0.5, 2.0)
        print(f"Simulating request {i+1} with {jitter:.2f}s delay...")
        await asyncio.sleep(jitter)
        print(f"Request {i+1} sent.")

if __name__ == "__main__":
    asyncio.run(test_rotation_logic())

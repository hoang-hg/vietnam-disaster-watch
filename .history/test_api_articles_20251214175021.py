# -*- coding: utf-8 -*-
"""Test API articles endpoint with limit=200"""
import asyncio
import httpx

async def test_articles_api():
    async with httpx.AsyncClient() as client:
        # Test /api/articles/latest with limit=200
        response = await client.get(
            "http://localhost:8000/api/articles/latest?limit=200",
            follow_redirects=True
        )
        
        if response.status_code == 200:
            articles = response.json()
            print(f"✅ API Status: 200 OK")
            print(f"📊 Articles returned: {len(articles)}")
            print(f"🎯 Requested limit: 200")
            
            if articles:
                print(f"\n📋 Sample articles:")
                for i, art in enumerate(articles[:5], 1):
                    print(f"\n{i}. {art.get('title', 'No title')[:60]}")
                    print(f"   Source: {art.get('source')}")
                    print(f"   Type: {art.get('disaster_type')}")
                    print(f"   Province: {art.get('province')}")
            else:
                print("⚠️  No articles found")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")

if __name__ == "__main__":
    asyncio.run(test_articles_api())

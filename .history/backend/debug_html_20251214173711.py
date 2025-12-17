# -*- coding: utf-8 -*-
"""Debug script to check HTML structure of Vietnamese news sites."""

import asyncio
import httpx
from bs4 import BeautifulSoup

async def debug_tuoitre():
    print("Checking Tuổi Trẻ HTML structure...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get('https://tuoitre.vn/thoi-su', follow_redirects=True)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            print(f"Response status: {response.status_code}")
            print(f"Title: {soup.title.string if soup.title else 'No title'}")
            
            # Find various element types
            print("\n=== Looking for article containers ===")
            
            # Check for divs with class containing 'item' or 'article'
            items = soup.find_all(['div', 'article'], class_=lambda x: x and ('item' in x.lower() or 'article' in x.lower()), limit=3)
            print(f"Found {len(items)} items/articles with class")
            for item in items[:2]:
                print(f"  {item.name}: {item.get('class')}")
            
            # Check all links
            print("\n=== First 10 links ===")
            links = soup.find_all('a', limit=10)
            for i, link in enumerate(links):
                text = link.get_text(strip=True)[:60]
                href = link.get('href', 'NO HREF')[:60]
                if text and len(text) > 5:
                    print(f"{i}: {text}")
                    
    except Exception as e:
        print(f"Error: {e}")

async def debug_vnexpress():
    print("\n\nChecking VnExpress HTML structure...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get('https://vnexpress.net/thoi-su-trong-ngay', follow_redirects=True)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            print(f"Response status: {response.status_code}")
            
            # Check for common news item selectors
            print("\n=== Looking for article/item containers ===")
            
            items = soup.find_all(['div', 'article'], class_=lambda x: x and 'item' in str(x).lower(), limit=3)
            print(f"Found {len(items)} items")
            
            # Check all links
            print("\n=== First 10 headlines ===")
            links = soup.find_all('a', limit=10)
            for i, link in enumerate(links):
                text = link.get_text(strip=True)
                if text and len(text) > 10:
                    print(f"{i}: {text[:70]}")
                    
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(debug_tuoitre())
asyncio.run(debug_vnexpress())

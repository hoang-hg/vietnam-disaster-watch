#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import Article

db = SessionLocal()
articles = db.query(Article).limit(5).all()

for art in articles:
    print(f"\n=== Article ===")
    print(f"Title: {art.title[:100]}")
    print(f"Summary: {art.summary[:00] if art.summary else 'NONE'}")
    print(f"Extracted - Deaths: {art.deaths}, Missing: {art.missing}, Injured: {art.injured}")
    print(f"Extracted - Damage: {art.damage_billion_vnd}, Province: {art.province}, Type: {art.disaster_type}")

db.close()

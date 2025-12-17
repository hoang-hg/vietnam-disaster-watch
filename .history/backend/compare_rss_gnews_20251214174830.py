# -*- coding: utf-8 -*-
"""Compare RSS vs GNews article quality"""
from app.database import SessionLocal
from app.models import Article
from sqlalchemy import func

db = SessionLocal()

print("=== ARTICLES BY SOURCE ===\n")
result = db.query(
    Article.source,
    func.count(Article.id).label('count')
).group_by(Article.source).order_by(func.count(Article.id).desc()).all()

for source, count in result:
    print(f"{source:30s}: {count:4d} articles")

print("\n=== DISASTER-RELATED ARTICLES ===\n")
disaster_articles = db.query(
    Article.source,
    func.count(Article.id).label('count')
).filter(
    (Article.disaster_type != None) | 
    (Article.deaths != None) | 
    (Article.injured != None) | 
    (Article.missing != None) |
    (Article.damage_billion_vnd != None)
).group_by(Article.source).order_by(func.count(Article.id).desc()).all()

for source, count in disaster_articles:
    print(f"{source:30s}: {count:4d} disaster articles")

print("\n=== RSS vs GNews COMPARISON ===\n")
rss_sources = ['Thanh Niên', 'VietNamNet', 'Tuổi Trẻ', 'VnExpress']
gnews_sources = ['Dân Trí', 'Báo Tin tức (TTXVN)', 'SGGP', 'Người Lao Động', 'Lao Động', 'Quân đội Nhân dân', 'VNA Net', 'Báo Mới']

rss_count = db.query(func.count(Article.id)).filter(Article.source.in_(rss_sources)).scalar()
gnews_count = db.query(func.count(Article.id)).filter(Article.source.in_(gnews_sources)).scalar()

print(f"RSS Sources (4):   {rss_count} articles")
print(f"GNews Sources (8): {gnews_count} articles")

rss_disaster = db.query(func.count(Article.id)).filter(
    Article.source.in_(rss_sources),
    ((Article.disaster_type != None) | (Article.deaths != None) | (Article.injured != None))
).scalar()

gnews_disaster = db.query(func.count(Article.id)).filter(
    Article.source.in_(gnews_sources),
    ((Article.disaster_type != None) | (Article.deaths != None) | (Article.injured != None))
).scalar()

print(f"\nDisaster Content Quality:")
if rss_count > 0:
    print(f"RSS Sources:   {rss_disaster} ({rss_disaster*100/rss_count:.1f}% contain disaster data)")
else:
    print(f"RSS Sources:   0 articles")

if gnews_count > 0:
    print(f"GNews Sources: {gnews_disaster} ({gnews_disaster*100/gnews_count:.1f}% contain disaster data)")
else:
    print(f"GNews Sources: 0 articles")

total_articles = db.query(func.count(Article.id)).scalar()
print(f"\nTotal articles in database: {total_articles}")

# Show latest 10 articles
print("\n=== LATEST 10 ARTICLES ===\n")
latest = db.query(Article).order_by(Article.published_at.desc()).limit(10).all()
for article in latest:
    source_short = article.source[:15]
    print(f"[{source_short:15s}] {article.title[:70]}")

db.close()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare NLP accuracy between GNews RSS vs Official RSS sources.
Analyzes extracted impact data (deaths, injured, etc).
"""

from pathlib import Path
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Article
from collections import defaultdict


def analyze_nlp_quality():
    """Compare extraction quality between RSS types."""
    db: Session = SessionLocal()
    
    try:
        # Get articles from official RSS sources
        official_sources = ["Thanh Niên", "VietNamNet"]
        
        official_articles = db.query(Article).filter(
            Article.source.in_(official_sources)
        ).all()
        
        # Get articles from GNews fallback
        gnews_articles = db.query(Article).filter(
            ~Article.source.in_(official_sources)
        ).all()
        
        # Calculate stats per group
        def get_stats(articles, label):
            stats = {
                "label": label,
                "count": len(articles),
                "with_impacts": 0,
                "avg_impacts_per_article": 0,
                "with_deaths": 0,
                "with_injured": 0,
                "with_damage": 0,
                "with_province": 0,
            }
            
            total_impact_fields = 0
            
            for article in articles:
                has_impact = False
                
                if article.deaths is not None and article.deaths > 0:
                    stats["with_deaths"] += 1
                    has_impact = True
                    total_impact_fields += 1
                
                if article.injured is not None and article.injured > 0:
                    stats["with_injured"] += 1
                    has_impact = True
                    total_impact_fields += 1
                
                if article.damage_billion_vnd is not None and article.damage_billion_vnd > 0:
                    stats["with_damage"] += 1
                    has_impact = True
                    total_impact_fields += 1
                
                if article.province and article.province != "unknown":
                    stats["with_province"] += 1
                
                if has_impact:
                    stats["with_impacts"] += 1
            
            stats["avg_impacts_per_article"] = total_impact_fields / len(articles) if articles else 0
            
            return stats
        
        official_stats = get_stats(official_articles, "Official RSS (Thanh Niên + VietNamNet)")
        gnews_stats = get_stats(gnews_articles, "GNews Fallback")
        
        print("\n" + "=" * 80)
        print("📊 NLP QUALITY ANALYSIS")
        print("=" * 80)
        
        for stats in [official_stats, gnews_stats]:
            pct_with_impacts = (stats["with_impacts"] / stats["count"] * 100) if stats["count"] > 0 else 0
            pct_deaths = (stats["with_deaths"] / stats["count"] * 100) if stats["count"] > 0 else 0
            pct_injured = (stats["with_injured"] / stats["count"] * 100) if stats["count"] > 0 else 0
            pct_damage = (stats["with_damage"] / stats["count"] * 100) if stats["count"] > 0 else 0
            pct_province = (stats["with_province"] / stats["count"] * 100) if stats["count"] > 0 else 0
            
            print(f"\n📰 {stats['label']}")
            print(f"   Total articles: {stats['count']}")
            print(f"   Articles with any impact data: {stats['with_impacts']} ({pct_with_impacts:.1f}%)")
            print(f"   Avg impact fields per article: {stats['avg_impacts_per_article']:.2f}")
            print(f"   └─ Deaths found: {stats['with_deaths']} ({pct_deaths:.1f}%)")
            print(f"   └─ Injured found: {stats['with_injured']} ({pct_injured:.1f}%)")
            print(f"   └─ Damage found: {stats['with_damage']} ({pct_damage:.1f}%)")
            print(f"   └─ Province identified: {stats['with_province']} ({pct_province:.1f}%)")
        
        # Comparison
        print("\n" + "-" * 80)
        print("📈 COMPARISON (Official RSS vs GNews)")
        print("-" * 80)
        
        if official_stats["count"] > 0 and gnews_stats["count"] > 0:
            official_impact_rate = (official_stats["with_impacts"] / official_stats["count"]) * 100
            gnews_impact_rate = (gnews_stats["with_impacts"] / gnews_stats["count"]) * 100
            improvement = official_impact_rate - gnews_impact_rate
            
            print(f"Impact data extraction rate:")
            print(f"  Official RSS:  {official_impact_rate:.1f}%")
            print(f"  GNews:         {gnews_impact_rate:.1f}%")
            print(f"  Improvement:   {improvement:+.1f} percentage points")
            
            if improvement > 0:
                print(f"\n✅ Official RSS sources extract {improvement:.1f}% MORE impact data than GNews")
                print(f"   Reason: RSS includes full article summaries; GNews uses snippets")
            else:
                print(f"\n⚠️  GNews performs as well or better - check source quality")
        
        print("=" * 80 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    analyze_nlp_quality()

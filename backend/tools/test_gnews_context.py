#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify gnews_context_terms functionality
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

from app.sources import build_gnews_rss, CONFIG, DISASTER_KEYWORDS
import urllib.parse


def test_gnews_context_terms():
    """Test that gnews_context_terms are properly loaded and used"""
    
    print("=" * 70)
    print("🧪 TESTING GNEWS CONTEXT TERMS FEATURE")
    print("=" * 70)
    
    # 1. Check CONFIG loaded
    print("\n1️⃣ Checking CONFIG loaded from sources.json:")
    print(f"   ✓ CONFIG type: {type(CONFIG)}")
    print(f"   ✓ CONFIG keys: {list(CONFIG.keys())}")
    
    if not CONFIG:
        print("   ❌ ERROR: CONFIG is empty! Check sources.json loading.")
        return False
    
    # 2. Check gnews_context_terms
    print("\n2️⃣ Checking gnews_context_terms:")
    context_terms = CONFIG.get("gnews_context_terms", [])
    print(f"   ✓ Number of context terms: {len(context_terms)}")
    
    if context_terms:
        print(f"   ✓ First 5 terms: {context_terms[:5]}")
        print(f"   ✓ Last 5 terms: {context_terms[-5:]}")
    else:
        print("   ⚠️  WARNING: No context terms defined in sources.json")
    
    # 3. Test build_gnews_rss WITHOUT context terms
    print("\n3️⃣ Testing build_gnews_rss WITHOUT context terms:")
    test_domain = "thanhnien.vn"
    url_no_context = build_gnews_rss(test_domain)
    parsed_no_context = urllib.parse.urlparse(url_no_context)
    query_no_context = urllib.parse.parse_qs(parsed_no_context.query)
    q_no_context = query_no_context.get('q', [''])[0]
    
    print(f"   Domain: {test_domain}")
    print(f"   Query length: {len(q_no_context)} chars")
    print(f"   Has 'AND' clause: {'AND' in q_no_context}")
    print(f"   Sample query: {q_no_context[:150]}...")
    
    # 4. Test build_gnews_rss WITH context terms
    print("\n4️⃣ Testing build_gnews_rss WITH context terms:")
    if context_terms:
        url_with_context = build_gnews_rss(test_domain, context_terms=context_terms)
        parsed_with_context = urllib.parse.urlparse(url_with_context)
        query_with_context = urllib.parse.parse_qs(parsed_with_context.query)
        q_with_context = query_with_context.get('q', [''])[0]
        
        print(f"   Domain: {test_domain}")
        print(f"   Query length: {len(q_with_context)} chars")
        print(f"   Has 'AND' clause: {'AND' in q_with_context}")
        print(f"   Sample query: {q_with_context[:200]}...")
        
        # 5. Compare queries
        print("\n5️⃣ Comparing queries:")
        print(f"   Query length increase: {len(q_with_context) - len(q_no_context)} chars")
        print(f"   Without context: {len(q_no_context)} chars")
        print(f"   With context: {len(q_with_context)} chars")
        
        if 'AND' in q_with_context and 'AND' not in q_no_context:
            print("   ✅ PASS: Context terms properly add AND clause")
        else:
            print("   ❌ FAIL: AND clause not added correctly")
            return False
    else:
        print("   ⚠️  SKIPPED: No context terms to test")
    
    # 6. Verify query structure
    print("\n6️⃣ Verifying query structure:")
    if context_terms:
        # Check that query has both disaster keywords and context terms
        has_disaster_terms = any(term in q_with_context for term in ['bão', 'lũ', 'sạt'])
        has_context_terms = any(term in q_with_context for term in context_terms[:5])
        
        print(f"   Contains disaster keywords: {has_disaster_terms}")
        print(f"   Contains context terms: {has_context_terms}")
        
        if has_disaster_terms and has_context_terms:
            print("   ✅ PASS: Query contains both disaster and context terms")
        else:
            print("   ❌ FAIL: Query missing required terms")
            return False
    
    # 7. Display full URLs for manual inspection
    print("\n7️⃣ Full URLs for manual inspection:")
    print("\n   WITHOUT context terms:")
    print(f"   {url_no_context}\n")
    
    if context_terms:
        print("   WITH context terms:")
        print(f"   {url_with_context}\n")
    
    # 8. Test other config values
    print("\n8️⃣ Other config values:")
    print(f"   gnews_fallback: {CONFIG.get('gnews_fallback')}")
    print(f"   gnews_min_articles: {CONFIG.get('gnews_min_articles')}")
    print(f"   request_timeout: {CONFIG.get('request_timeout')}")
    print(f"   max_articles_per_source: {CONFIG.get('max_articles_per_source')}")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = test_gnews_context_terms()
    sys.exit(0 if success else 1)

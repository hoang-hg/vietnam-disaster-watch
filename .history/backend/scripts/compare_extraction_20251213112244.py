#!/usr/bin/env python
"""Compare extraction performance of summary vs full-text.

Usage:
  cd backend
  python .\scripts\compare_extraction.py --limit 30

Outputs a short summary of how many articles had impacts detected by
summary-only vs full-page extraction.
"""
import argparse
import sys
from pathlib import Path
import re

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "backend"))

import httpx
from app.database import SessionLocal
from app.models import Article
from app import nlp
from app.settings import settings


def extract_paragraphs_from_html(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        paras = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
        cleaned = [re.sub(r"\s+", " ", p).strip() for p in paras if p and p.strip()]
        if cleaned:
            cleaned.sort(key=len, reverse=True)
            return "\n\n".join(cleaned[:5])
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        paras = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.I | re.S)
        cleaned = []
        for p in paras:
            t = re.sub(r"<[^>]+>", "", p)
            t = re.sub(r"\s+", " ", t).strip()
            if t:
                cleaned.append(t)
        if cleaned:
            cleaned.sort(key=len, reverse=True)
            return "\n\n".join(cleaned[:5])
        t = re.sub(r"<[^>]+>", " ", html)
        t = re.sub(r"\s+", " ", t).strip()
        return t


def any_impacts(out: dict) -> int:
    count = 0
    for k in ("deaths", "missing", "injured", "damage_billion_vnd"):
        if out.get(k) is not None:
            count += 1
    return count


def main(limit: int = 50):
    session = SessionLocal()
    try:
        q = session.query(Article).filter(Article.url != None).order_by(Article.published_at.desc()).limit(limit)
        arts = q.all()
        if not arts:
            print("No articles found")
            return

        stats = {"total": 0, "summary_hits": 0, "fulltext_hits": 0, "both": 0}
        improved_examples = []

        timeout = getattr(settings, "request_timeout_seconds", 10)
        client = httpx.Client(timeout=timeout, headers={"User-Agent": settings.user_agent})

        for a in arts:
            stats["total"] += 1
            summary_text = "".join([s for s in [a.title or "", "\n", a.summary or ""]])
            out_summary = nlp.extract_impacts(summary_text)
            s_hits = any_impacts(out_summary)
            if s_hits:
                stats["summary_hits"] += 1

            # fetch full page
            full_hits = 0
            out_full = {}
            try:
                r = client.get(a.url)
                html = r.text
                full_text = extract_paragraphs_from_html(html)
                out_full = nlp.extract_impacts(full_text)
                full_hits = any_impacts(out_full)
                if full_hits:
                    stats["fulltext_hits"] += 1
            except Exception as e:
                # network/parsing error; continue
                print(f"fetch error for article {a.id}: {e}")

            if s_hits and full_hits:
                stats["both"] += 1
            if (not s_hits) and full_hits:
                improved_examples.append({"id": a.id, "title": a.title, "url": a.url, "summary_out": out_summary, "full_out": out_full})

        # report
        print("\n=== Summary ===")
        print(f"total articles sampled: {stats['total']}")
        print(f"summary-only detected impacts: {stats['summary_hits']}")
        print(f"full-text detected impacts: {stats['fulltext_hits']}")
        print(f"detected by both: {stats['both']}")
        print(f"improvements (full-text found but summary did not): {len(improved_examples)}")
        if improved_examples:
            print("\nExamples where full-text improved extraction:")
            for ex in improved_examples[:10]:
                print("---")
                print(f"article id: {ex['id']}")
                print(f"title: {ex['title']}")
                print(f"url: {ex['url']}")
                print(f"summary_out: {ex['summary_out']}")
                print(f"full_out: {ex['full_out']}")

    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    main(args.limit)

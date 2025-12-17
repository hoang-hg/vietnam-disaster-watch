#!/usr/bin/env python
"""Add `full_text` column to `articles` table if missing (SQLite/Postgres safe-ish).

Run from `backend`:
  python .\scripts\add_full_text_column.py
"""
from pathlib import Path
import sys
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "backend"))

from app.database import engine
import sqlalchemy as sa

inspector = sa.inspect(engine)
cols = [c['name'] for c in inspector.get_columns('articles')]
if 'full_text' in cols:
    print('Column full_text already exists')
    sys.exit(0)

with engine.connect() as conn:
    dialect = engine.dialect.name
    if dialect == 'sqlite':
        # SQLite supports simple ALTER TABLE ADD COLUMN
        conn.execute(sa.text('ALTER TABLE articles ADD COLUMN full_text TEXT'))
        print('Added full_text column (sqlite)')
    else:
        conn.execute(sa.text('ALTER TABLE articles ADD COLUMN full_text TEXT'))
        print('Added full_text column')

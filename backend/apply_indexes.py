from sqlalchemy import create_engine, text
from app.settings import settings

def apply_indexes():
    engine = create_engine(settings.app_db_url)
    
    with engine.connect() as conn:
        print("Applying performance optimization indexes...")

        # 0. Extensions
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            print("Enabled pg_trgm extension")
        except Exception: pass

        # Article Indexes
        article_indexes = [
            ("ix_article_status_type_date", "articles", "(status, disaster_type, published_at)"),
            ("ix_article_prov_type_date", "articles", "(province, disaster_type, published_at)"),
            ("ix_article_title_trgm", "articles", "USING gin (title gin_trgm_ops)")
        ]

        for idx_name, table, cols in article_indexes:
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} {cols}"))
                print(f"Created index {idx_name} on {table}")
            except Exception as e:
                print(f"Error creating index {idx_name}: {e}")

        # Event Indexes
        event_indexes = [
            ("ix_event_prov_type_date", "events", "(province, disaster_type, started_at)"),
            ("ix_event_title_trgm", "events", "USING gin (title gin_trgm_ops)")
        ]

        for idx_name, table, cols in event_indexes:
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} {cols}"))
                print(f"Created index {idx_name} on {table}")
            except Exception as e:
                print(f"Error creating index {idx_name}: {e}")

        conn.commit()
    print("Indexing process finished.")

if __name__ == "__main__":
    apply_indexes()

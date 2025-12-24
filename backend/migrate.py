from sqlalchemy import text
from app.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """
    Manually add missing columns to the existing database schema.
    Used as a lightweight migration tool when schema changes but Base.metadata.create_all
    can't update existing tables.
    """
    logger.info("Starting database migration...")
    
    # Use autocommit mode to prevent transaction blocks from failing subsequent commands
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        # 1. Add columns to articles table
        columns_to_add = [
            ("needs_verification", "INTEGER DEFAULT 0"),
            ("is_broken", "INTEGER DEFAULT 0"),
            ("full_text", "TEXT")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                logger.info(f"Adding '{col_name}' to 'articles' table...")
                conn.execute(text(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}"))
                logger.info(f"Successfully added '{col_name}' to 'articles'.")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    logger.info(f"Column '{col_name}' already exists in 'articles'. Skipping.")
                else:
                    logger.error(f"Error migrating 'articles' ({col_name}): {e}")

        # 2. Add columns to events table
        event_columns = [
            ("needs_verification", "INTEGER DEFAULT 0"),
            ("image_url", "TEXT")
        ]
        
        for col_name, col_type in event_columns:
            try:
                logger.info(f"Adding '{col_name}' to 'events' table...")
                conn.execute(text(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}"))
                logger.info(f"Successfully added '{col_name}' to 'events'.")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    logger.info(f"Column '{col_name}' already exists in 'events'. Skipping.")
                else:
                    logger.error(f"Error migrating 'events' ({col_name}): {e}")

    logger.info("Migration finished.")

if __name__ == "__main__":
    migrate()

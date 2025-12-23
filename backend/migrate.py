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
    
    with engine.connect() as conn:
        # 1. Add column to articles table
        try:
            logger.info("Checking for 'needs_verification' in 'articles' table...")
            conn.execute(text("ALTER TABLE articles ADD COLUMN needs_verification INTEGER DEFAULT 0"))
            conn.commit()
            logger.info("Successfully added 'needs_verification' to 'articles'.")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                logger.info("Column 'needs_verification' already exists in 'articles'. Skipping.")
            else:
                logger.error(f"Error migrating 'articles': {e}")

        # 2. Add column to events table
        try:
            logger.info("Checking for 'needs_verification' in 'events' table...")
            conn.execute(text("ALTER TABLE events ADD COLUMN needs_verification INTEGER DEFAULT 0"))
            conn.commit()
            logger.info("Successfully added 'needs_verification' to 'events'.")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                logger.info("Column 'needs_verification' already exists in 'events'. Skipping.")
            else:
                logger.error(f"Error migrating 'events': {e}")

    logger.info("Migration finished.")

if __name__ == "__main__":
    migrate()

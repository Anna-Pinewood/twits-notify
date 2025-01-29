"""Main script for the Reddit consumer service."""
import logging
import sys
import os
from consumer_instance import RedditConsumer
from db_manager import DatabaseManager
from consts import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB,
    POSTGRES_USER, POSTGRES_PASSWORD
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def check_database_connection():
    """Verify database connection and table existence."""
    logger.info("Checking database connection...")
    logger.info("Database parameters: host=%s, port=%s, dbname=%s, user=%s",
                POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER)

    db = DatabaseManager(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

    try:
        db.connect()
        # Test table existence
        db.cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'reddit_posts'
            );
        """)
        table_exists = db.cur.fetchone()[0]
        logger.info("Database connection test successful")
        logger.info("reddit_posts table exists: %s", table_exists)

        if table_exists:
            # Test table structure
            db.cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'reddit_posts';
            """)
            columns = db.cur.fetchall()
            logger.info("Table structure: %s", columns)

        return True
    except Exception as e:
        logger.error("Database connection test failed: %s",
                     str(e), exc_info=True)
        return False
    finally:
        db.close()


def main():
    """Main entry point for the consumer service."""
    logger.info("Starting Reddit consumer service...")
    logger.info("Environment variables:")
    for key in ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER']:
        logger.info("%s = %s", key, os.getenv(key))

    # Check database connection
    if not check_database_connection():
        logger.error("Failed to verify database connection. Exiting.")
        sys.exit(1)

    # Initialize and start consumer
    try:
        consumer = RedditConsumer()
        consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping consumer...")
        consumer.stop_consuming()
    except Exception as e:
        logger.error("Consumer failed: %s", str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

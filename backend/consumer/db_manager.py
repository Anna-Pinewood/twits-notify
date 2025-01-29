"""Database operations for storing processed Reddit posts."""
import json
import logging
import os
from typing import Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import Json
from consts_consumer import POSTGRES_HOST, POSTGRES_DB, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations for Reddit posts."""

    def __init__(
        self,
        host: str = POSTGRES_HOST,
        port: int = POSTGRES_PORT,
        dbname: str = POSTGRES_DB,
        user: str = POSTGRES_USER,
        password: str = POSTGRES_PASSWORD
    ):
        """Initialize database connection parameters."""
        # Debug environment variables
        logger.debug("Environment variables:")
        logger.debug("POSTGRES_HOST: %s", os.getenv('POSTGRES_HOST'))
        logger.debug("POSTGRES_PORT: %s", os.getenv('POSTGRES_PORT'))
        logger.debug("POSTGRES_DB: %s", os.getenv('POSTGRES_DB'))
        logger.debug("POSTGRES_USER: %s", os.getenv('POSTGRES_USER'))

        # Debug constructor parameters
        logger.debug("Constructor parameters:")
        logger.debug("host: %s", host)
        logger.debug("port: %s", port)
        logger.debug("dbname: %s", dbname)
        logger.debug("user: %s", user)

        self.conn_params = {
            'host': host,
            'port': port,
            'dbname': dbname,
            'user': user,
            'password': password
        }

        logger.info("DatabaseManager initialized with params: host=%s, port=%s, dbname=%s, user=%s",
                    host, port, dbname, user)
        self.conn = None
        self.cur = None

        # Try initial connection
        try:
            self.connect()
        except Exception as e:
            logger.error("Initial connection failed: %s",
                         str(e), exc_info=True)

    def connect(self) -> None:
        """Establish database connection."""
        try:
            conn_params_safe = {
                k: v for k, v in self.conn_params.items() if k != 'password'}
            logger.info("Connecting to PostgreSQL with params: %s",
                        conn_params_safe)

            self.conn = psycopg2.connect(**self.conn_params)
            self.cur = self.conn.cursor()

            # Test the connection
            self.cur.execute("SELECT current_database(), current_user;")
            db, user = self.cur.fetchone()
            logger.info("Connected to database: %s as user: %s", db, user)

            # Check table existence
            self.cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'reddit_posts'
                );
            """)
            table_exists = self.cur.fetchone()[0]
            logger.info("reddit_posts table exists: %s", table_exists)

        except Exception as e:
            logger.error("Database connection failed: %s",
                         str(e), exc_info=True)
            raise

    def ensure_connection(self) -> None:
        """Ensure database connection is active."""
        try:
            if not self.conn or self.conn.closed:
                logger.info("Connection lost, reconnecting...")
                self.connect()

            # Test if connection is alive
            self.cur.execute("SELECT 1")
            self.cur.fetchone()

        except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.Error) as e:
            logger.warning(
                "Lost database connection, reconnecting: %s", str(e))
            self.conn = None
            self.cur = None
            self.connect()
        except Exception as e:
            logger.error("Failed to ensure database connection: %s",
                         str(e), exc_info=True)
            raise

    def save_processed_post(
        self,
        post_data: Dict[str, Any],
        llm_results: Dict[str, Any]
    ) -> None:
        """Save processed Reddit post with LLM analysis results."""
        self.ensure_connection()
        try:
            query = """
                INSERT INTO reddit_posts (
                    post_id,
                    subreddit,
                    title,
                    content,
                    author,
                    created_utc,
                    processed_at,
                    llm_tags,
                    discussion_summary,
                    url,
                    score,
                    num_comments
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (post_id) 
                DO UPDATE SET
                    processed_at = EXCLUDED.processed_at,
                    llm_tags = EXCLUDED.llm_tags,
                    discussion_summary = EXCLUDED.discussion_summary
                RETURNING post_id;
            """

            # Extract tags and summary from LLM results
            tags = {
                "tags": llm_results.get("tags", []),
                "main_topics": llm_results.get("main_topics", [])
            }

            # Prepare values for insertion
            values = (
                post_data['post_id'],
                post_data['subreddit'],
                post_data['title'],
                post_data['text'],
                post_data['author'],
                datetime.strptime(
                    post_data['created_utc'], '%Y-%m-%d %H:%M:%S'),
                datetime.now(),
                Json(tags),
                llm_results.get('discussion_summary', ''),
                post_data['url'],
                post_data['score'],
                post_data['num_comments']
            )

            logger.info("Executing INSERT query with post_id=%s",
                        post_data['post_id'])
            self.cur.execute(query, values)
            result = self.cur.fetchone()
            logger.info("Insert result: %s", result)

            logger.info("Committing transaction...")
            self.conn.commit()
            logger.info(
                "Successfully saved/updated post %s from r/%s",
                post_data['post_id'],
                post_data['subreddit']
            )

            # Verify the insert
            self.cur.execute("""
                SELECT post_id FROM reddit_posts 
                WHERE post_id = %s
            """, (post_data['post_id'],))
            verify_result = self.cur.fetchone()
            logger.info("Verification query result: %s", verify_result)

        except Exception as e:
            logger.error("Failed to save post to database: %s",
                         str(e), exc_info=True)
            self.conn.rollback()
            raise

    def close(self) -> None:
        """Close database connection."""
        try:
            if self.cur is not None:
                self.cur.close()
            if self.conn is not None:
                self.conn.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.error("Error while closing database connection: %s", str(e))
        finally:
            self.cur = None
            self.conn = None


# Create singleton instance
db_manager_singleton = DatabaseManager()

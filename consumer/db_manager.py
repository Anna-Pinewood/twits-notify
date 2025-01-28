"""Database operations for storing processed Reddit posts."""
import json
import logging
from typing import Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import Json
from .consts import POSTGRES_HOST, POSTGRES_DB, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD

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
        """Initialize database connection parameters.
        
        Args:
            host: Database host address
            port: Database port number
            dbname: Database name
            user: Database user
            password: Database password
        """
        self.conn_params = {
            'host': host,
            'port': port,
            'dbname': dbname,
            'user': user,
            'password': password
        }
        self.conn = None
        self.cur = None

    def connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.cur = self.conn.cursor()
            logger.info("Successfully connected to PostgreSQL")
        except Exception as e:
            logger.error("Database connection failed: %s", str(e))
            raise

    def ensure_connection(self) -> None:
        """Ensure database connection is active."""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
        except Exception as e:
            logger.error("Failed to ensure database connection: %s", str(e))
            raise

    def save_processed_post(
        self,
        post_data: Dict[str, Any],
        llm_results: Dict[str, Any]
    ) -> None:
        """
        Save processed Reddit post with LLM analysis results.

        Args:
            post_data: Original post data from Reddit
            llm_results: Analysis results from LLM including tags and summary

        Raises:
            psycopg2.Error: If database operation fails
        """
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
                datetime.strptime(post_data['created_utc'], '%Y-%m-%d %H:%M:%S'),
                datetime.now(),
                Json(tags),
                llm_results.get('discussion_summary', ''),
                post_data['url'],
                post_data['score'],
                post_data['num_comments']
            )

            self.cur.execute(query, values)
            self.conn.commit()
            logger.info(
                "Successfully saved/updated post %s from r/%s",
                post_data['post_id'],
                post_data['subreddit']
            )

        except Exception as e:
            self.conn.rollback()
            logger.error("Failed to save post to database: %s", str(e))
            raise

    def get_recent_posts(self, limit: int = 100) -> list:
        """
        Retrieve recently processed posts.

        Args:
            limit: Maximum number of posts to retrieve

        Returns:
            list: Recent posts with their analysis
        """
        self.ensure_connection()
        try:
            query = """
                SELECT 
                    post_id,
                    subreddit,
                    title,
                    llm_tags,
                    discussion_summary,
                    processed_at
                FROM reddit_posts
                ORDER BY processed_at DESC
                LIMIT %s
            """
            self.cur.execute(query, (limit,))
            return self.cur.fetchall()

        except Exception as e:
            logger.error("Failed to retrieve recent posts: %s", str(e))
            raise

    def close(self) -> None:
        """Close database connection."""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Create singleton instance
db_manager_singleton = DatabaseManager()
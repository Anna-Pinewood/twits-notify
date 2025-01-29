"""Database operations for the API service."""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

from .consts import (
    POSTGRES_HOST,
    POSTGRES_DB,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations for the API service."""

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
        """Establish database connection with RealDictCursor for JSON-like results."""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
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

    def get_latest_processing_date(self) -> Optional[datetime]:
        """Get the most recent processing date from the database.
        
        Returns:
            datetime or None: The latest processing date, or None if no records exist
        """
        self.ensure_connection()
        try:
            query = """
                SELECT MAX(processed_at) as latest_date
                FROM reddit_posts
            """
            self.cur.execute(query)
            result = self.cur.fetchone()
            return result['latest_date'] if result else None

        except Exception as e:
            logger.error("Failed to get latest processing date: %s", str(e))
            raise

    def get_posts_by_date(self, date: datetime) -> List[Dict[str, Any]]:
        """Get all posts processed on a specific date.
        
        Args:
            date: The date to fetch posts for
            
        Returns:
            List of posts with their analysis data
        """
        self.ensure_connection()
        try:
            query = """
                SELECT 
                    subreddit,
                    COUNT(*) as post_count,
                    ARRAY_AGG(DISTINCT llm_tags->>'tags') as unique_tags,
                    ARRAY_AGG(
                        json_build_object(
                            'title', title,
                            'discussion_summary', discussion_summary,
                            'score', score,
                            'num_comments', num_comments
                        )
                    ) as posts
                FROM reddit_posts
                WHERE DATE(processed_at) = DATE(%s)
                GROUP BY subreddit
                ORDER BY post_count DESC
            """
            self.cur.execute(query, (date,))
            results = self.cur.fetchall()
            
            # Convert results to list of dicts
            return [dict(row) for row in results]

        except Exception as e:
            logger.error("Failed to get posts for date %s: %s", date, str(e))
            raise

    def get_subreddit_stats(self, date: datetime) -> Dict[str, Any]:
        """Get aggregated statistics for all subreddits on a specific date.
        
        Args:
            date: The date to calculate statistics for
            
        Returns:
            Dictionary with subreddit statistics
        """
        self.ensure_connection()
        try:
            query = """
                SELECT 
                    COUNT(DISTINCT subreddit) as total_subreddits,
                    COUNT(*) as total_posts,
                    AVG(score) as avg_score,
                    AVG(num_comments) as avg_comments,
                    ARRAY_AGG(DISTINCT subreddit) as subreddits
                FROM reddit_posts
                WHERE DATE(processed_at) = DATE(%s)
            """
            self.cur.execute(query, (date,))
            return dict(self.cur.fetchone())

        except Exception as e:
            logger.error("Failed to get subreddit stats for date %s: %s", date, str(e))
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
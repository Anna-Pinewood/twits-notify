import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.api.db_manager_read import DatabaseManager, db_manager_singleton


@pytest.fixture
def db_manager():
    """Create a fresh DatabaseManager instance for each test."""
    return DatabaseManager(
        host="test_host",
        port=5432,
        dbname="test_db",
        user="test_user",
        password="test_pass"
    )


@pytest.fixture
def mock_cursor():
    """Create a mock cursor with RealDictCursor-like behavior."""
    cursor = MagicMock(spec=RealDictCursor)
    return cursor


@pytest.fixture
def mock_connection(mock_cursor):
    """Create a mock database connection."""
    conn = MagicMock()
    conn.cursor.return_value = mock_cursor
    return conn


@pytest.fixture
def sample_db_response():
    """Create sample database response data."""
    return {
        'subreddit': 'testsubreddit',
        'post_count': 10,
        'unique_tags': ['python', 'coding', 'technology'],
        'posts': [
            {
                'title': 'Test Post 1',
                'discussion_summary': 'Summary 1',
                'score': 100,
                'num_comments': 50
            },
            {
                'title': 'Test Post 2',
                'discussion_summary': 'Summary 2',
                'score': 200,
                'num_comments': 75
            }
        ]
    }


class TestDatabaseManager:
    """Test suite for DatabaseManager class."""

    def test_init(self, db_manager):
        """Test DatabaseManager initialization."""
        assert db_manager.conn_params['host'] == "test_host"
        assert db_manager.conn_params['port'] == 5432
        assert db_manager.conn_params['dbname'] == "test_db"
        assert db_manager.conn_params['user'] == "test_user"
        assert db_manager.conn_params['password'] == "test_pass"
        assert db_manager.conn is None
        assert db_manager.cur is None

    def test_connect(self, db_manager):
        """Test database connection establishment."""
        with patch('psycopg2.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_connect.return_value.cursor.return_value = mock_cursor

            db_manager.connect()

            mock_connect.assert_called_once_with(**db_manager.conn_params)
            assert db_manager.conn is not None
            assert db_manager.cur is not None

    def test_connect_error(self, db_manager):
        """Test database connection error handling."""
        with patch('psycopg2.connect', side_effect=psycopg2.Error("Connection failed")):
            with pytest.raises(psycopg2.Error, match="Connection failed"):
                db_manager.connect()

            assert db_manager.conn is None
            assert db_manager.cur is None

    def test_ensure_connection(self, db_manager):
        """Test ensure_connection when no connection exists."""
        with patch('psycopg2.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_connect.return_value.cursor.return_value = mock_cursor

            db_manager.ensure_connection()

            mock_connect.assert_called_once()
            assert db_manager.conn is not None
            assert db_manager.cur is not None

    def test_get_latest_processing_date(self, db_manager, mock_connection, mock_cursor):
        """Test retrieving the latest processing date."""
        test_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_cursor.fetchone.return_value = {'latest_date': test_date}

        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            result = db_manager.get_latest_processing_date()

            mock_cursor.execute.assert_called_once()
            assert result == test_date

    def test_get_posts_by_date(self, db_manager, mock_connection, mock_cursor, sample_db_response):
        """Test retrieving posts for a specific date."""
        mock_cursor.fetchall.return_value = [sample_db_response]
        test_date = datetime(2024, 1, 1)

        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            results = db_manager.get_posts_by_date(test_date)

            mock_cursor.execute.assert_called_once()
            assert len(results) == 1
            assert results[0]['subreddit'] == 'testsubreddit'
            assert results[0]['post_count'] == 10
            assert len(results[0]['posts']) == 2

    def test_get_subreddit_stats(self, db_manager, mock_connection, mock_cursor):
        """Test retrieving subreddit statistics."""
        mock_stats = {
            'total_subreddits': 5,
            'total_posts': 100,
            'avg_score': 150.5,
            'avg_comments': 75.2,
            'subreddits': ['sub1', 'sub2', 'sub3', 'sub4', 'sub5']
        }
        mock_cursor.fetchone.return_value = mock_stats
        test_date = datetime(2024, 1, 1)

        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            stats = db_manager.get_subreddit_stats(test_date)

            mock_cursor.execute.assert_called_once()
            assert stats == mock_stats
            assert stats['total_subreddits'] == 5
            assert stats['total_posts'] == 100
            assert len(stats['subreddits']) == 5

    def test_close(self, db_manager, mock_connection, mock_cursor):
        """Test database connection closure."""
        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            db_manager.close()

            mock_cursor.close.assert_called_once()
            mock_connection.close.assert_called_once()

    def test_error_handling(self, db_manager, mock_connection, mock_cursor):
        """Test error handling in database operations."""
        mock_cursor.execute.side_effect = psycopg2.Error("Database error")
        test_date = datetime(2024, 1, 1)

        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            with pytest.raises(psycopg2.Error, match="Database error"):
                db_manager.get_posts_by_date(test_date)


def test_db_manager_singleton():
    """Test the database manager singleton instance."""
    assert isinstance(db_manager_singleton, DatabaseManager)

    # Create a new instance and verify it's different
    new_manager = DatabaseManager()
    assert db_manager_singleton is not new_manager

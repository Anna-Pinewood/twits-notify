"""Tests for the consumer's DatabaseManager class."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import json
import psycopg2
from psycopg2.extras import Json

from backend.consumer.db_manager import DatabaseManager, db_manager_singleton


@pytest.fixture
def db_manager():
    """Create a fresh DatabaseManager instance for each test."""
    with patch('backend.consumer.db_manager.DatabaseManager.connect'):
        manager = DatabaseManager(
            host="test_host",
            port=5432,
            dbname="test_db",
            user="test_user",
            password="test_pass"
        )
        # Prevent automatic connection in __init__
        manager.conn = None
        manager.cur = None
        return manager


@pytest.fixture
def mock_cursor():
    """Create a mock database cursor."""
    cursor = MagicMock()
    # Configure cursor to return expected test query results
    cursor.fetchone.return_value = ("test_db", "test_user")
    return cursor


@pytest.fixture
def mock_connection(mock_cursor):
    """Create a mock database connection."""
    conn = MagicMock()
    conn.cursor.return_value = mock_cursor
    conn.closed = False
    return conn


@pytest.fixture
def sample_post_data():
    """Create sample Reddit post data for testing."""
    return {
        'post_id': 'abc123',
        'subreddit': 'testsubreddit',
        'title': 'Test Post',
        'text': 'This is a test post',
        'author': 'testuser',
        'created_utc': '2024-01-01 12:00:00',
        'url': 'https://reddit.com/r/testsubreddit/abc123',
        'score': 100,
        'num_comments': 50
    }


@pytest.fixture
def sample_llm_results():
    """Create sample LLM analysis results for testing."""
    return {
        'tags': ['python', 'testing', 'pytest'],
        'discussion_summary': 'A discussion about Python testing practices.'
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

    def test_connect(self, db_manager, mock_connection, mock_cursor):
        """Test database connection establishment."""
        # Set up mock responses for both queries
        mock_cursor.fetchone.side_effect = [
            ("test_db", "test_user"),  # For current_database/user query
            (True,)  # For table existence check
        ]

        with patch('psycopg2.connect', return_value=mock_connection) as mock_connect:
            db_manager.connect()

            # Verify connection was established with correct parameters
            mock_connect.assert_called_once_with(**db_manager.conn_params)

            # Verify cursor was created
            mock_connection.cursor.assert_called_once()

            # Verify both queries were executed
            assert mock_cursor.execute.call_count == 2
            calls = mock_cursor.execute.call_args_list
            assert "SELECT current_database(), current_user" in calls[0][0][0]
            assert "SELECT EXISTS" in calls[1][0][0]

    def test_connect_error(self, db_manager):
        """Test database connection error handling."""
        with patch('psycopg2.connect', side_effect=psycopg2.Error("Connection failed")):
            with pytest.raises(psycopg2.Error, match="Connection failed"):
                db_manager.connect()

            assert db_manager.conn is None
            assert db_manager.cur is None

    def test_ensure_connection(self, db_manager, mock_connection, mock_cursor):
        """Test ensure_connection when no connection exists."""
        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.ensure_connection()

            assert db_manager.conn is mock_connection
            assert db_manager.cur is mock_cursor

    def test_ensure_connection_when_closed(self, db_manager, mock_connection, mock_cursor):
        """Test ensure_connection when connection is closed."""
        with patch('psycopg2.connect', return_value=mock_connection):
            # First establish connection
            db_manager.connect()

            # Then simulate closed connection
            db_manager.conn.closed = True

            # Ensure connection should reconnect
            db_manager.ensure_connection()

            assert db_manager.conn is mock_connection
            assert db_manager.cur is mock_cursor

    def test_save_processed_post_success(self, db_manager, mock_connection, mock_cursor,
                                         sample_post_data, sample_llm_results):
        """Test successful post saving with LLM results."""
        # Add more responses for all potential database queries
        mock_cursor.fetchone.side_effect = [
            ("test_db", "test_user"),  # Initial connection test
            (True,),                    # Table existence check
            None,                       # For the INSERT
            ('abc123',),               # For verification query
            None                        # Extra response for safety
        ]

        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            db_manager.save_processed_post(
                sample_post_data, sample_llm_results)

            assert mock_cursor.execute.call_count >= 4  # Verify minimum number of queries
            mock_connection.commit.assert_called_once()

    def test_save_processed_post_invalid_date(self, db_manager, mock_connection,
                                              sample_post_data, sample_llm_results):
        """Test handling of invalid date format in post data."""
        sample_post_data['created_utc'] = 'invalid_date_format'

        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            with pytest.raises(ValueError):
                db_manager.save_processed_post(
                    sample_post_data, sample_llm_results)

    def test_save_processed_post_missing_required_fields(self, db_manager, mock_connection,
                                                         sample_llm_results):
        """Test handling of missing required fields in post data."""
        invalid_post_data = {'post_id': 'abc123'}  # Missing required fields

        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            with pytest.raises(KeyError):
                db_manager.save_processed_post(
                    invalid_post_data, sample_llm_results)

    def test_close(self, db_manager, mock_connection, mock_cursor):
        """Test database connection closure."""
        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            db_manager.close()

            mock_cursor.close.assert_called_once()
            mock_connection.close.assert_called_once()

            # Verify connections were nullified
            assert db_manager.cur is None
            assert db_manager.conn is None

    def test_table_existence_check(self, db_manager, mock_connection, mock_cursor):
        """Test checking for reddit_posts table existence."""
        mock_cursor.fetchone.side_effect = [
            ("test_db", "test_user"),  # For initial connection test
            (True,)  # For table existence check
        ]

        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()

            # Verify table existence check query was executed
            table_check_call = mock_cursor.execute.call_args_list[1][0][0]
            assert 'SELECT EXISTS' in table_check_call
            assert 'reddit_posts' in table_check_call

    def test_save_processed_post_with_verification(self, db_manager, mock_connection, mock_cursor,
                                                   sample_post_data, sample_llm_results):
        """Test post saving with insert verification."""
        mock_cursor.fetchone.side_effect = [
            ("test_db", "test_user"),  # Initial connection test
            (True,),                    # Table existence check
            None,                       # For INSERT
            ('abc123',),               # Verification query result
            None,                       # Extra response for safety
            None                        # Extra response for safety
        ]

        with patch('psycopg2.connect', return_value=mock_connection):
            db_manager.connect()
            db_manager.save_processed_post(
                sample_post_data, sample_llm_results)

            execute_calls = mock_cursor.execute.call_args_list
            assert len(execute_calls) >= 4  # Verify minimum number of queries


def test_db_manager_singleton():
    """Test the database manager singleton instance."""
    # Patch connect to prevent actual database connection
    with patch('backend.consumer.db_manager.DatabaseManager.connect'):
        assert isinstance(db_manager_singleton, DatabaseManager)

        # Create a new instance and verify it's different
        new_manager = DatabaseManager()
        assert db_manager_singleton is not new_manager

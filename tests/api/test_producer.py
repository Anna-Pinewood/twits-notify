import pytest
import json
import pika
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the producer singleton and RedditPost class
from backend.api.producer import RedditProducer, producer_singleton
from backend.api.reddit import RedditPost

# Test data fixtures


@pytest.fixture
def mock_reddit_post():
    """Create a mock RedditPost for testing."""
    mock_post = MagicMock()
    mock_post.id = "test123"
    mock_post.title = "Test Post"
    mock_post.selftext = "Test Content"
    mock_post.subreddit.display_name = "testsubreddit"
    mock_post.author = "testuser"
    mock_post.score = 100
    mock_post.num_comments = 50
    mock_post.created_utc = datetime.now().timestamp()
    mock_post.url = "https://reddit.com/r/testsubreddit/test123"

    return RedditPost(mock_post)


@pytest.fixture
def producer():
    """Create a fresh RedditProducer instance for each test."""
    producer = RedditProducer()
    yield producer
    # Cleanup after tests
    if producer.connection and not producer.connection.is_closed:
        producer.close()


class TestRedditProducer:
    """Test suite for RedditProducer class."""

    def test_init(self):
        """Test producer initialization."""
        producer = RedditProducer()
        assert producer.queue_name == "reddit_posts"
        assert producer.connection is None
        assert producer.channel is None

    def test_ensure_connection(self, producer):
        """Test connection establishment."""
        with patch('pika.BlockingConnection') as mock_connection:
            mock_channel = MagicMock()
            mock_connection.return_value.channel.return_value = mock_channel

            producer.ensure_connection()

            # Verify connection was established
            mock_connection.assert_called_once()
            mock_channel.queue_declare.assert_called_once_with(
                queue=producer.queue_name,
                durable=True,
                arguments={
                    'x-message-ttl': 24 * 60 * 60 * 1000,
                    'x-max-length': 10000
                }
            )

    def test_publish_success(self, producer, mock_reddit_post):
        """Test successful message publishing."""
        with patch('pika.BlockingConnection') as mock_connection:
            mock_channel = MagicMock()
            mock_connection.return_value.channel.return_value = mock_channel

            producer.publish(mock_reddit_post)

            # Verify message was published
            mock_channel.basic_publish.assert_called_once()

            # Verify the published message format
            call_args = mock_channel.basic_publish.call_args
            assert call_args[1]['exchange'] == ''
            assert call_args[1]['routing_key'] == producer.queue_name

            # Verify message content
            published_message = json.loads(call_args[1]['body'])
            assert published_message['post_id'] == mock_reddit_post.post.id
            assert published_message['title'] == mock_reddit_post.post.title
            assert published_message['subreddit'] == mock_reddit_post.post.subreddit.display_name

    def test_publish_connection_failure(self, producer, mock_reddit_post):
        """Test handling of connection failures during publish."""
        with patch('pika.BlockingConnection', side_effect=pika.exceptions.AMQPConnectionError):
            with pytest.raises(pika.exceptions.AMQPConnectionError):
                producer.publish(mock_reddit_post)

            assert producer.connection is None
            assert producer.channel is None

    def test_publish_channel_failure(self, producer, mock_reddit_post):
        """Test handling of channel failures during publish."""
        with patch('pika.BlockingConnection') as mock_connection:
            mock_channel = MagicMock()
            mock_channel.basic_publish.side_effect = pika.exceptions.AMQPChannelError
            mock_connection.return_value.channel.return_value = mock_channel

            with pytest.raises(pika.exceptions.AMQPChannelError):
                producer.publish(mock_reddit_post)

    def test_close_connection(self, producer):
        """Test connection closure with proper setup."""
        # Create mock connection first
        mock_conn = MagicMock()
        mock_conn.is_closed = False
        producer.connection = mock_conn
        producer.channel = MagicMock()

        producer.close()

        mock_conn.close.assert_called_once()
        assert producer.connection is None
        assert producer.channel is None

    def test_clear_queue(self, producer):
        """Test queue clearing functionality."""
        with patch('pika.BlockingConnection') as mock_connection:
            mock_channel = MagicMock()
            mock_connection.return_value.channel.return_value = mock_channel

            producer.ensure_connection()
            producer.clear_queue()

            mock_channel.queue_purge.assert_called_once_with(
                queue=producer.queue_name
            )


def test_producer_singleton():
    """Test the producer singleton instance."""
    assert isinstance(producer_singleton, RedditProducer)

    # Create a new instance and verify it's different
    new_producer = RedditProducer()
    assert producer_singleton is not new_producer

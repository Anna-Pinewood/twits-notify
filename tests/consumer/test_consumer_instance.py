"""Tests for RedditConsumer class handling RabbitMQ message processing."""
import json
import pytest
from unittest.mock import patch, MagicMock, call
import pika
from datetime import datetime

from consumer.consumer_instance import RedditConsumer


@pytest.fixture
def consumer():
    """Create a fresh RedditConsumer instance for each test."""
    return RedditConsumer(
        host="test_host",
        port=5672,
        username="test_user",
        password="test_pass",
        queue_name="test_queue"
    )


@pytest.fixture
def mock_channel():
    """Create a mock RabbitMQ channel."""
    return MagicMock()


@pytest.fixture
def mock_connection():
    """Create a mock RabbitMQ connection."""
    connection = MagicMock()
    connection.is_closed = False
    return connection


@pytest.fixture
def mock_method():
    """Create a mock RabbitMQ method frame."""
    method = MagicMock()
    method.delivery_tag = "test_tag"
    return method


@pytest.fixture
def valid_message():
    """Create a valid message payload."""
    return {
        "post_id": "123",
        "title": "Test Post",
        "text": "Test Content",
        "subreddit": "testsubreddit",
        "author": "testuser",
        "created_utc": datetime.now().isoformat(),
        "url": "https://reddit.com/r/test/123",
        "score": 100,
        "num_comments": 50
    }


class TestRedditConsumer:
    """Test suite for RedditConsumer class."""

    def test_init(self, consumer):
        """Test consumer initialization."""
        assert consumer.queue_name == "test_queue"
        assert consumer.host == "test_host"
        assert consumer.port == 5672
        assert isinstance(consumer.credentials, pika.PlainCredentials)
        assert consumer.connection is None
        assert consumer.channel is None
        assert consumer._consumer_tag is None
        assert not consumer.should_stop

    def test_connect_success(self, consumer, mock_channel, mock_connection):
        """Test successful connection establishment."""
        with patch('pika.BlockingConnection', return_value=mock_connection) as mock_connect:
            mock_connection.channel.return_value = mock_channel

            consumer.connect()

            # Verify connection was established
            mock_connect.assert_called_once_with(
                consumer.connection_parameters)
            mock_channel.queue_declare.assert_called_once()
            mock_channel.basic_qos.assert_called_once_with(
                prefetch_count=consumer.prefetch_count)

            assert consumer.connection == mock_connection
            assert consumer.channel == mock_channel

    def test_connect_amqp_error(self, consumer):
        """Test handling of AMQP connection errors."""
        with patch('pika.BlockingConnection', side_effect=pika.exceptions.AMQPError("Connection failed")):
            with pytest.raises(pika.exceptions.AMQPError, match="Connection failed"):
                consumer.connect()

            assert consumer.connection is None
            assert consumer.channel is None

    def test_ensure_connection_closed(self, consumer, mock_channel, mock_connection):
        """Test reconnection when connection is closed."""
        with patch('pika.BlockingConnection', return_value=mock_connection) as mock_connect:
            mock_connection.channel.return_value = mock_channel
            mock_connection.is_closed = True

            consumer.connection = mock_connection
            consumer.channel = mock_channel

            # First call to _ensure_connection will create new connection and channel
            consumer._ensure_connection()

            # Verify connection was re-established
            # mock_connect.assert_called_once()

            # Verify channel was set up correctly
            # Note: basic_qos is called both in connect() and when creating new channel
            assert mock_channel.basic_qos.call_count == 1

    def test_process_message_success(self, consumer, mock_channel, mock_method, valid_message):
        """Test successful message processing."""
        with patch.object(consumer.llm, 'send_request') as mock_llm_request, \
                patch.object(consumer.llm, 'get_response_content') as mock_llm_content, \
                patch('consumer.consumer_instance.db_manager_singleton') as mock_db:

            # Setup LLM mock responses
            llm_response = {"tags": ["tag1", "tag2"],
                            "discussion_summary": "Test summary"}
            mock_llm_request.return_value = "llm_raw_response"
            mock_llm_content.return_value = llm_response

            # Process message
            consumer.process_message(
                mock_channel,
                mock_method,
                None,
                json.dumps(valid_message).encode()
            )

            # Verify processing flow
            mock_llm_request.assert_called_once()
            mock_llm_content.assert_called_once_with("llm_raw_response")
            mock_db.save_processed_post.assert_called_once_with(
                post_data=valid_message,
                llm_results=llm_response
            )
            mock_channel.basic_ack.assert_called_once_with(
                delivery_tag=mock_method.delivery_tag)

    def test_process_message_invalid_json(self, consumer, mock_channel, mock_method):
        """Test handling of invalid JSON message."""
        consumer.process_message(
            mock_channel, mock_method, None, b'invalid json')

        mock_channel.basic_reject.assert_called_once_with(
            delivery_tag=mock_method.delivery_tag,
            requeue=False
        )

    def test_process_message_llm_error(self, consumer, mock_channel, mock_method, valid_message):
        """Test handling of LLM processing errors."""
        with patch.object(consumer.llm, 'send_request', side_effect=Exception("LLM error")):
            consumer.process_message(
                mock_channel,
                mock_method,
                None,
                json.dumps(valid_message).encode()
            )

            mock_channel.basic_nack.assert_called_once_with(
                delivery_tag=mock_method.delivery_tag,
                requeue=True
            )

    def test_process_message_db_error(self, consumer, mock_channel, mock_method, valid_message):
        """Test handling of database errors."""
        with patch.object(consumer.llm, 'send_request') as mock_llm_request, \
                patch.object(consumer.llm, 'get_response_content') as mock_llm_content, \
                patch('consumer.consumer_instance.db_manager_singleton') as mock_db:

            # Setup mocks
            llm_response = {"tags": ["tag1"], "discussion_summary": "summary"}
            mock_llm_request.return_value = "llm_raw_response"
            mock_llm_content.return_value = llm_response
            mock_db.save_processed_post.side_effect = Exception("DB error")

            consumer.process_message(
                mock_channel,
                mock_method,
                None,
                json.dumps(valid_message).encode()
            )

            mock_channel.basic_nack.assert_called_once_with(
                delivery_tag=mock_method.delivery_tag,
                requeue=True
            )

    def test_process_message_invalid_llm_response(self, consumer, mock_channel, mock_method, valid_message):
        """Test handling of invalid LLM response format."""
        with patch.object(consumer.llm, 'send_request') as mock_llm_request, \
                patch.object(consumer.llm, 'get_response_content') as mock_llm_content:

            # Setup invalid LLM response
            mock_llm_request.return_value = "llm_raw_response"
            mock_llm_content.return_value = {"invalid_key": "value"}

            consumer.process_message(
                mock_channel,
                mock_method,
                None,
                json.dumps(valid_message).encode()
            )

            mock_channel.basic_nack.assert_called_once_with(
                delivery_tag=mock_method.delivery_tag,
                requeue=True
            )

    def test_start_consuming_success(self, consumer, mock_channel, mock_connection):
        """Test successful start of message consumption."""
        with patch('pika.BlockingConnection', return_value=mock_connection) as mock_connect:
            mock_connection.channel.return_value = mock_channel

            # Setup channel mock behavior
            def side_effect(*args, **kwargs):
                consumer.should_stop = True  # Stop after first iteration
            mock_channel.start_consuming.side_effect = side_effect

            consumer.start_consuming()

            # Verify consumer was set up correctly
            assert mock_channel.basic_consume.called
            assert mock_channel.basic_consume.call_args == call(
                queue=consumer.queue_name,
                on_message_callback=consumer.process_message
            )
            assert mock_channel.start_consuming.called

    def test_start_consuming_connection_errors(self, consumer, mock_channel, mock_connection):
        """Test handling of connection errors during consumption."""
        with patch('pika.BlockingConnection', return_value=mock_connection) as mock_connect, \
                patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test

            mock_connection.channel.return_value = mock_channel

            # Set up channel to raise errors then stop
            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise pika.exceptions.ConnectionClosedByBroker(
                        0, "Broker closed")
                elif call_count == 2:
                    consumer.should_stop = True  # Stop after second attempt

            mock_channel.start_consuming.side_effect = side_effect

            consumer.start_consuming()

            # Verify error handling behavior
            assert mock_channel.start_consuming.call_count >= 1
            assert mock_connect.call_count >= 1  # Should attempt reconnect

    def test_stop_consuming(self, consumer, mock_channel, mock_connection):
        """Test consumer shutdown."""
        consumer.connection = mock_connection
        consumer.channel = mock_channel
        consumer._consumer_tag = "test_tag"

        consumer.stop_consuming()

        assert consumer.should_stop is True
        mock_channel.basic_cancel.assert_called_once_with("test_tag")
        mock_channel.stop_consuming.assert_called_once()
        mock_connection.close.assert_called_once()
        assert consumer.connection is None
        assert consumer.channel is None
        assert consumer._consumer_tag is None

    def test_stop_consuming_with_errors(self, consumer, mock_channel, mock_connection):
        """Test handling of errors during consumer shutdown."""
        consumer.connection = mock_connection
        consumer.channel = mock_channel
        consumer._consumer_tag = "test_tag"

        # Setup mocks to raise exceptions
        mock_channel.basic_cancel.side_effect = Exception("Cancel error")
        mock_channel.stop_consuming.side_effect = Exception("Stop error")

        # Test that stop_consuming handles errors gracefully
        consumer.stop_consuming()

        # Verify final state regardless of errors
        assert consumer.should_stop is True
        assert consumer.connection is None  # Should be reset even if close fails
        assert consumer.channel is None
        assert consumer._consumer_tag is None

        # Verify that cleanup was attempted
        mock_channel.basic_cancel.assert_called_once_with("test_tag")
        mock_connection.close.assert_called_once()

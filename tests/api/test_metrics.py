"""Tests for the metrics collection module."""
import pytest
from unittest.mock import patch, MagicMock, call
import pika
from prometheus_client import generate_latest
from backend.api.metrics import (
    get_queue_size,
    metrics_endpoint,
    REQUESTS_TOTAL,
    REQUEST_DURATION,
    QUEUE_SIZE,
    REGISTRY
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean up the registry before and after each test."""
    # Clear registry before test
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)
    
    # Re-register metrics for each test
    REQUESTS_TOTAL.clear()
    REQUEST_DURATION.clear()
    QUEUE_SIZE._value.set(0)
    
    yield
    
    # Clear registry after test
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)


@pytest.fixture
def mock_pika_connection():
    """Create a mock RabbitMQ connection."""
    with patch('pika.BlockingConnection') as mock_conn:
        # Create mock objects for the connection chain
        mock_channel = MagicMock()
        mock_queue = MagicMock()
        mock_method = MagicMock()
        
        # Set up the mock chain
        mock_conn.return_value.channel.return_value = mock_channel
        mock_channel.queue_declare.return_value = mock_queue
        mock_queue.method = mock_method
        
        yield {
            'connection': mock_conn,
            'channel': mock_channel,
            'queue': mock_queue,
            'method': mock_method
        }


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    mock_req = MagicMock()
    mock_req.url.path = "/test"
    mock_req.method = "GET"
    return mock_req


class TestQueueSizeMetrics:
    """Test suite for queue size metrics collection."""

    def test_get_queue_size_success(self, mock_pika_connection):
        """Test successful queue size retrieval."""
        # Set up mock queue size
        mock_pika_connection['method'].message_count = 42

        # Call the function
        queue_size = get_queue_size()

        # Verify the connection was properly configured
        mock_pika_connection['connection'].assert_called_once()
        
        # Verify queue declaration parameters
        mock_pika_connection['channel'].queue_declare.assert_called_once_with(
            queue='reddit_posts',
            durable=True,
            arguments={
                'x-message-ttl': 24 * 60 * 60 * 1000,
                'x-max-length': 10000
            }
        )

        # Verify connection was closed
        mock_pika_connection['connection'].return_value.close.assert_called_once()

        # Verify returned size
        assert queue_size == 42

    def test_get_queue_size_connection_error(self, mock_pika_connection):
        """Test queue size retrieval with connection error."""
        # Make connection raise an error
        mock_pika_connection['connection'].side_effect = pika.exceptions.AMQPConnectionError()

        # Call function and verify it handles error gracefully
        queue_size = get_queue_size()
        assert queue_size is None

    def test_get_queue_size_declaration_error(self, mock_pika_connection):
        """Test queue size retrieval with queue declaration error."""
        # Make queue declaration raise an error
        mock_pika_connection['channel'].queue_declare.side_effect = pika.exceptions.AMQPChannelError()

        # Call function and verify it handles error gracefully
        queue_size = get_queue_size()
        assert queue_size is None

    @pytest.mark.asyncio
    async def test_metrics_endpoint_with_queue_size(self, mock_pika_connection, mock_request):
        """Test metrics endpoint with successful queue size retrieval."""
        # Set up mock queue size
        mock_pika_connection['method'].message_count = 42
        
        # Initialize the gauge with a value
        QUEUE_SIZE.set(0)
        
        # Create sample metrics output
        sample_metrics = b"""
# HELP reddit_queue_size Number of messages in RabbitMQ queue
# TYPE reddit_queue_size gauge
reddit_queue_size 42.0
"""
        # Mock generate_latest to return our sample metrics
        with patch('prometheus_client.generate_latest', return_value=sample_metrics):
            # Call the metrics endpoint
            response = await metrics_endpoint(mock_request)

            # Verify queue size metric was set
            queue_size_metric = QUEUE_SIZE._value.get()
            assert queue_size_metric == 42

            # Verify response format
            assert response.media_type == "text/plain; version=0.0.4; charset=utf-8"
            

    @pytest.mark.asyncio
    async def test_metrics_endpoint_queue_error(self, mock_pika_connection, mock_request):
        """Test metrics endpoint when queue size retrieval fails."""
        # Make connection raise an error
        mock_pika_connection['connection'].side_effect = pika.exceptions.AMQPConnectionError()

        # Call the metrics endpoint
        response = await metrics_endpoint(mock_request)

        # Verify response still succeeds despite queue error
        assert response.status_code == 200

        # Verify response format
        assert response.media_type == "text/plain; version=0.0.4; charset=utf-8"


class TestMetricsCollection:
    """Test suite for general metrics collection."""

    def test_requests_total_metric(self):
        """Test the requests_total counter metric."""
        # Record some test requests
        REQUESTS_TOTAL.labels(endpoint="/test", method="GET").inc()
        REQUESTS_TOTAL.labels(endpoint="/test", method="POST").inc()
        REQUESTS_TOTAL.labels(endpoint="/test", method="GET").inc()

        # Get current value for test endpoint GET requests
        value = REQUESTS_TOTAL.labels(endpoint="/test", method="GET")._value.get()
        assert value == 2

        # Get current value for test endpoint POST requests
        value = REQUESTS_TOTAL.labels(endpoint="/test", method="POST")._value.get()
        assert value == 1

    def test_request_duration_metric(self):
        """Test the request_duration histogram metric."""
        # Record some test durations
        REQUEST_DURATION.labels(endpoint="/test").observe(0.2)
        REQUEST_DURATION.labels(endpoint="/test").observe(0.5)

        # Get histogram value count
        value = REQUEST_DURATION.labels(endpoint="/test")._sum.get()
        assert value == 0.7  # Sum of recorded values

    def test_queue_size_gauge_metric(self):
        """Test the queue_size gauge metric."""
        # Set test values
        QUEUE_SIZE.set(10)
        assert QUEUE_SIZE._value.get() == 10

        QUEUE_SIZE.set(20)
        assert QUEUE_SIZE._value.get() == 20

        # Test increment/decrement
        QUEUE_SIZE.inc()
        assert QUEUE_SIZE._value.get() == 21

        QUEUE_SIZE.dec()
        assert QUEUE_SIZE._value.get() == 20
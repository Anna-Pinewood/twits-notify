"""Prometheus metrics configuration for the API service."""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import pika
from typing import Optional
from consts import RABBIT_HOST, RABBIT_USER, RABBIT_PASSWORD

# Create a custom registry
REGISTRY = CollectorRegistry()

# Define metrics with custom registry
REQUESTS_TOTAL = Counter(
    'reddit_api_requests_total',
    'Total number of API requests',
    ['endpoint', 'method'],
    registry=REGISTRY
)

REQUEST_DURATION = Histogram(
    'reddit_api_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
    registry=REGISTRY
)

QUEUE_SIZE = Gauge(
    'reddit_queue_size',
    'Number of messages in RabbitMQ queue',
    registry=REGISTRY
)


def get_queue_size() -> Optional[int]:
    """Get current size of RabbitMQ queue."""
    try:
        credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBIT_HOST,
            credentials=credentials
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare queue to ensure it exists (idempotent operation)
        queue = channel.queue_declare(
            queue='reddit_posts',
            durable=True,
            arguments={
                'x-message-ttl': 24 * 60 * 60 * 1000,  # 24 hours
                'x-max-length': 10000
            }
        )

        size = queue.method.message_count
        connection.close()
        return size
    except Exception:
        return None


async def metrics_endpoint(request):
    """Endpoint for exposing metrics to Prometheus."""
    # Update queue size before generating metrics
    queue_size = get_queue_size()
    if queue_size is not None:
        QUEUE_SIZE.set(queue_size)

    return Response(
        generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )

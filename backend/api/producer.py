"""RabbitMQ producer for Reddit posts."""
import json
import logging
import pika
from typing import Optional

from .reddit import RedditPost
from .consts import RABBIT_HOST, RABBIT_PORT, RABBIT_USER, RABBIT_PASSWORD, RABBIT_QUEUE

logger = logging.getLogger(__name__)


class RedditProducer:
    """Handles publishing Reddit posts to RabbitMQ queue."""

    def __init__(self):
        """Initialize producer settings."""
        self.queue_name = RABBIT_QUEUE
        self.connection = None
        self.channel = None

    def ensure_connection(self) -> None:
        """Ensure active connection and channel exist."""
        try:
            if (not self.connection or
                self.connection.is_closed or
                not self.channel or
                    self.channel.is_closed):
                self._init_connection()
                self._init_channel()
        except Exception as e:
            logger.error("Failed to ensure connection: %s", str(e))
            raise

    def _init_connection(self) -> None:
        """Set up RabbitMQ connection with credentials."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()

        credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBIT_HOST,
            credentials=credentials,
            port=RABBIT_PORT,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        self.connection = pika.BlockingConnection(parameters)

    def _init_channel(self) -> None:
        """Initialize channel and declare queue."""
        self.channel = self.connection.channel()
        self.channel.queue_declare(
            queue=self.queue_name,
            durable=True,  # Survive broker restarts
            arguments={
                'x-message-ttl': 24 * 60 * 60 * 1000,  # 24 hours in milliseconds
                'x-max-length': 10000  # Limit queue size
            }
        )

    def publish(self, post: RedditPost) -> None:
        """
        Publish single Reddit post to queue.

        Args:
            post: RedditPost instance to publish

        Raises:
            pika.exceptions.AMQPError: If publishing fails
        """
        try:
            # Ensure we have active connection
            self.ensure_connection()

            # Convert post to dict and serialize
            post_data = post.to_dict()
            message = json.dumps(post_data)

            # Publish with persistent delivery
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                )
            )
            logger.info("Published post '%s' to queue",
                        post_data.get('title', ''))

        except pika.exceptions.AMQPError as e:
            logger.error("Failed to publish post: %s", str(e))
            # Clear connection state
            self.connection = None
            self.channel = None
            raise

    def clear_queue(self):
        self.channel.queue_purge(queue=self.queue_name)
        logger.info("Queue cleared")

    def close(self) -> None:
        """Close RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            self.connection = None
            self.channel = None


# Create singleton instance
producer_singleton = RedditProducer()

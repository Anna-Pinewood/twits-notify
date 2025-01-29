"""RabbitMQ consumer for processing Reddit posts."""
import json
import logging
import pika
from typing import Optional, Callable
import time
from datetime import datetime

from llm import LLMInterface
from prompt import REDDIT_ANALYSIS_PROMPT
from consts import RABBIT_HOST, RABBIT_PORT, RABBIT_USER, RABBIT_PASSWORD, RABBIT_QUEUE
from db_manager import db_manager_singleton
logger = logging.getLogger(__name__)


class RedditConsumer:
    def __init__(
        self,
        host: str = RABBIT_HOST,
        port: int = RABBIT_PORT,
        username: str = RABBIT_USER,
        password: str = RABBIT_PASSWORD,
        queue_name: str = RABBIT_QUEUE,
        prefetch_count: int = 1
    ):
        self.queue_name = queue_name
        self.host = host
        self.port = port
        self.credentials = pika.PlainCredentials(username, password)
        self.prefetch_count = prefetch_count

        # Connection state
        self.connection = None
        self.channel = None
        self._consumer_tag = None
        self.should_stop = False  # Added missing attribute

        self.llm = LLMInterface(prompt=REDDIT_ANALYSIS_PROMPT)

        # Connection parameters with port
        self.connection_parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,  # Added port
            credentials=self.credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
            connection_attempts=3,
            retry_delay=5
        )

    def connect(self) -> None:
        """
        Establish connection to RabbitMQ and set up channel.

        Raises:
            pika.exceptions.AMQPError: If connection fails after retries
        """
        if self.connection and not self.connection.is_closed:
            return

        logger.info("Connecting to RabbitMQ at %s", self.host)
        try:
            self.connection = pika.BlockingConnection(
                self.connection_parameters)
            self.channel = self.connection.channel()

            # Declare queue (idempotent operation)
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                arguments={
                    'x-message-ttl': 24 * 60 * 60 * 1000,  # 24 hours
                    'x-max-length': 10000
                }
            )

            # Enable message acknowledgment and set QoS
            self.channel.basic_qos(prefetch_count=self.prefetch_count)

            logger.info("Successfully connected to RabbitMQ")

        except pika.exceptions.AMQPError as e:
            logger.error("Failed to connect to RabbitMQ: %s", str(e))
            self.connection = None
            self.channel = None
            raise

    def _ensure_connection(self) -> None:
        """Ensure active connection exists, reconnecting if necessary."""
        try:
            if (not self.connection or
                self.connection.is_closed or
                not self.channel or
                    self.channel.is_closed):
                self.connect()
        except Exception as e:
            logger.error("Failed to ensure connection: %s", str(e))
            raise

    def process_message(self, ch, method, properties, body: bytes) -> None:
        """
        Process a single message from the queue.

        This is a placeholder implementation that should be overridden
        by subclasses or replaced with a callback function.

        Args:
            ch: Channel object
            method: Method frame
            properties: Message properties
            body: Message body as bytes
        """
        try:
            # Parse message
            message = json.loads(body.decode('utf-8'))
            logger.info(
                "Processing post '%s' from r/%s",
                message.get('title', ''),
                message.get('subreddit', '')
            )

            # TODO: Add actual processing logic
            # time.sleep(1)  # Simulate processing
            llm_response = self.llm.send_request(
                call_params={"post_content": message.get("pretty_text")})
            llm_results = self.llm.get_response_content(llm_response)
            logger.info("LLM results:\n%s", llm_results)

            db_manager_singleton.save_processed_post(
                post_data=message, llm_results=llm_results)

            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as e:
            logger.error("Failed to decode message: %s", str(e))
            # Reject malformed messages without requeue
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error("Error processing message: %s", str(e))
            # Requeue message for retry on processing error
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start_consuming(self) -> None:
        """
        Start consuming messages from the queue.

        The consumer will automatically reconnect if the connection is lost.
        """
        while not self.should_stop:
            self._ensure_connection()
            try:
                # Register consumer
                self._consumer_tag = self.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self.process_message
                )

                logger.info("Started consuming from queue '%s'",
                            self.queue_name)
                self.channel.start_consuming()

            except pika.exceptions.ConnectionClosedByBroker:
                logger.warning("Connection closed by broker, retrying...")
                continue

            except pika.exceptions.AMQPChannelError as e:
                logger.error("Channel error: %s, retrying...", str(e))
                continue

            except Exception as e:
                logger.error("Unexpected error: %s", str(e))
                self.connection = None
                self.channel = None
                time.sleep(5)  # Wait before reconnecting
                continue

    def stop_consuming(self) -> None:
        """
        Stop consuming messages and close connection.
        """
        logger.info("Stopping consumer...")
        self.should_stop = True

        if self.channel and self._consumer_tag:
            try:
                self.channel.basic_cancel(self._consumer_tag)
                self.channel.stop_consuming()
            except Exception as e:
                logger.error("Error while stopping consumer: %s", str(e))

        if self.connection and not self.connection.is_closed:
            self.connection.close()

        self.connection = None
        self.channel = None
        self._consumer_tag = None
        logger.info("Consumer stopped")

"""Main process for the Reddit consumer service."""
import logging
import signal
import sys
from consumer.consumer_instance import RedditConsumer
from consumer.db_manager import db_manager_singleton

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s\t[%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def handle_shutdown(signum, frame, consumer):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal")
    consumer.stop_consuming()
    db_manager_singleton.close()
    sys.exit(0)


def main():
    """Main entry point for the consumer service."""
    # Initialize components
    consumer = RedditConsumer()

    # Set up signal handlers
    signal.signal(signal.SIGTERM, lambda s, f: handle_shutdown(s, f, consumer))
    signal.signal(signal.SIGINT, lambda s, f: handle_shutdown(s, f, consumer))

    try:
        logger.info("Starting consumer service...")
        consumer.start_consuming()
    except Exception as e:
        logger.error("Service error: %s", str(e))
        consumer.stop_consuming()
        db_manager_singleton.close()
        sys.exit(1)


if __name__ == "__main__":
    main()

import logging
from fastapi import APIRouter, HTTPException

from .models import UpdateRequest, UpdateResponse, SummaryResponse
from .reddit import scraper_singleton
from .producer import producer_singleton

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/update", response_model=UpdateResponse)
async def trigger_update(request: UpdateRequest) -> UpdateResponse:
    """
    Trigger Reddit posts analysis flow:
    1. Get posts from specified subreddits
    2. Send each post to RabbitMQ queue for processing
    """
    try:
        logger.info(
            "Processing update request for subreddits: %s",
            ", ".join(request.subreddits)
        )

        # Get posts from Reddit
        posts = scraper_singleton.get_posts_since(
            subreddits=request.subreddits,
        )
        logger.info("Fetched %d posts from Reddit", len(posts))

        # Send posts to queue
        queued_count = 0
        for post in posts:
            try:
                producer_singleton.publish(post)
                queued_count += 1
            except Exception as e:
                logger.error("Failed to queue post %s: %s",
                             post.post.url, str(e))

        logger.info("Successfully queued %d/%d posts",
                    queued_count, len(posts))

        return UpdateResponse(
            job_id=f"job-{'-'.join(request.subreddits)}",
            status="queued",
            queued_posts=queued_count
        )

    except Exception as e:
        logger.error("Failed to process update request: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=SummaryResponse)
async def get_summary() -> SummaryResponse:
    """
    Get summary of processed Reddit posts.
    Dummy implementation for now.
    """
    try:
        logger.info("Retrieving analysis summary")

        return SummaryResponse(
            total_processed=0,
            subreddit_stats={},
            latest_update="2024-01-28T00:00:00Z"
        )

    except Exception as e:
        logger.error("Failed to retrieve summary: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

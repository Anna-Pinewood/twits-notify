import logging
from fastapi import APIRouter, HTTPException

from .models import UpdateRequest, UpdateResponse, SummaryResponse

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/update", response_model=UpdateResponse)
async def trigger_update(request: UpdateRequest) -> UpdateResponse:
    """
    Trigger Reddit post analysis for specified subreddits.
    Dummy implementation for now.
    """
    try:
        logger.info(
            "Processing update request for subreddits: %s",
            ", ".join(request.subreddits)
        )
        
        # Dummy response for now
        return UpdateResponse(
            job_id="test-123",
            status="queued",
            queued_posts=len(request.subreddits)
        )
        
    except Exception as e:
        logger.error("Failed to process update request: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

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
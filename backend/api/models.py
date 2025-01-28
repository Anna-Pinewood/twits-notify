from typing import List, Optional
from pydantic import BaseModel, Field


class UpdateRequest(BaseModel):
    """Request model for /update endpoint."""
    subreddits: List[str] = Field(..., min_items=1, max_items=10)
    time_window: Optional[int] = Field(
        default=24, ge=1, le=168)  # Hours, 1-7 days


class UpdateResponse(BaseModel):
    """Response model for /update endpoint."""
    job_id: str
    status: str
    queued_posts: int


class SummaryResponse(BaseModel):
    """Response model for /summary endpoint."""
    total_processed: int
    subreddit_stats: dict  # Will define more specific structure later
    latest_update: str     # ISO timestamp

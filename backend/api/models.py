from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class UpdateRequest(BaseModel):
    """Request model for /update endpoint."""
    subreddits: List[str] = Field(..., min_items=1, max_items=10)


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


class PostSummary(BaseModel):
    """Summary of a single Reddit post."""
    title: str
    discussion_summary: str
    score: int
    num_comments: int


class SubredditStats(BaseModel):
    """Statistics for a single subreddit."""
    post_count: int
    unique_tags: List[str]
    posts: List[PostSummary]


class SummaryResponse(BaseModel):
    """Response model for /summary endpoint."""
    total_processed: int
    subreddit_stats: Dict[str, SubredditStats]
    latest_update: str  # ISO timestamp

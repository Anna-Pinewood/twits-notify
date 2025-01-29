import pytest
from datetime import datetime
import pytz
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.models import UpdateRequest
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_update_handler():
    with patch("backend.api.routes.scraper_singleton.get_posts_since") as mock_scraper, \
         patch("backend.api.routes.producer_singleton.publish") as mock_producer:
        mock_scraper.return_value = [MagicMock(), MagicMock()]
        response = client.post("/update", json={"subreddits": ["python", "fastapi"]})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "job_id" in data

def test_get_summary():
    with patch("backend.api.routes.db_manager_singleton.get_latest_processing_date") as mock_latest, \
         patch("backend.api.routes.db_manager_singleton.get_subreddit_stats") as mock_stats, \
         patch("backend.api.routes.db_manager_singleton.get_posts_by_date") as mock_posts:
        mock_latest.return_value = None
        response = client.get("/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 0
        assert data["subreddit_stats"] == {}
        assert data["latest_update"] == ""

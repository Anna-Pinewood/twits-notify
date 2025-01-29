import pytest
from datetime import datetime
import pytz
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.models import UpdateRequest

client = TestClient(app)

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

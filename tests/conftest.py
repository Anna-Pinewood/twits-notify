import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.api.routes import router

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

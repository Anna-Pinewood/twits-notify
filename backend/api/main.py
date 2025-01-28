import logging
from fastapi import FastAPI
from .routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(title="Reddit Analysis Service")

# Include routes
app.include_router(router)

# Add health check endpoint


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}

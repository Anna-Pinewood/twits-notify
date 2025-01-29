"""Main FastAPI application with metrics middleware."""
import time
import os
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from routes import router
from metrics import metrics_endpoint, REQUESTS_TOTAL, REQUEST_DURATION

app = FastAPI(title="Reddit Analysis Service")


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()

        # Get endpoint path for metrics
        endpoint = request.url.path

        # Update requests counter
        REQUESTS_TOTAL.labels(
            endpoint=endpoint,
            method=request.method
        ).inc()

        # Process request
        response = await call_next(request)

        # Record request duration
        duration = time.time() - start_time
        REQUEST_DURATION.labels(
            endpoint=endpoint
        ).observe(duration)

        return response


# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Add routes
app.include_router(router)

# Add metrics endpoint
app.add_route("/metrics", metrics_endpoint)


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}

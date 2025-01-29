FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create directories and set permissions
RUN mkdir -p /home/appuser/.local && \
    chown -R appuser:appuser /home/appuser

WORKDIR /home/appuser/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER appuser

# Rest remains the same
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

ENV PATH="/home/appuser/.local/bin:${PATH}"

COPY --chown=appuser:appuser . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${API_PORT}"]
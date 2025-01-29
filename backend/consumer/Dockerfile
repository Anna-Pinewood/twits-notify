FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN mkdir -p /home/appuser/.local && \
    chown -R appuser:appuser /home/appuser

WORKDIR /home/appuser/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER appuser

COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

ENV PATH="/home/appuser/.local/bin:${PATH}"

COPY --chown=appuser:appuser . .

CMD ["python", "main.py"]

FROM python:3.11-slim

WORKDIR /app

# System deps: poppler-utils for pdf2image; build-essential for any wheels
# (sentence-transformers, hdbscan) that fall back to source builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first to leverage layer cache
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline code last so dep layer is reused on code changes
COPY pipeline/ ./pipeline/

# Runtime artifact dirs (mounted as volumes in docker-compose)
RUN mkdir -p /app/parsed_documents /app/ner_results /app/graphify-out /app/.pipeline-state

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Default entrypoint launches the Typer CLI. Override with `docker run ... cli run <stage>`.
ENTRYPOINT ["python", "-m", "pipeline"]
CMD ["--help"]

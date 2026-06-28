FROM python:3.13-slim

# set work directory
WORKDIR /app

# Install system dependencies:
# - curl/ca-certificates: needed to fetch the NodeSource setup script
# - gnupg: NodeSource apt key
# - Pillow runtime libs (libjpeg, zlib) for ImageField/photo handling
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        gnupg \
        libjpeg62-turbo \
        zlib1g \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# copy project
COPY . .

# Synchronize dependencies (install all production dependencies)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Set environment to use the virtual environment
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Verify critical dependencies are installed
RUN python -c "import psycopg; print(f'✅ psycopg {psycopg.__version__} installed')" && \
    python -c "import django; print(f'✅ Django {django.__version__} installed')" && \
    python -c "import uvicorn; print(f'✅ uvicorn installed')"

# Build Vite assets
WORKDIR /app/vite/src
RUN npm ci && npm run build

# Return to app directory
WORKDIR /app

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Run uvicorn directly from virtual environment
CMD ["uvicorn", "kmm_web_backend.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

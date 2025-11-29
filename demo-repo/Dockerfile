FROM python:3.12-slim
WORKDIR /app

# Install tini for proper signal handling (SIGINT/SIGTERM)
RUN apt-get update && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files and install dependencies
COPY pyproject.toml main.py ./
RUN uv pip install --system --no-cache .

EXPOSE 8000

# Use tini as init for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "main.py"]

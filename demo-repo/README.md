# Demo App

A minimal Python FastAPI application demonstrating CI/CD with Woodpecker.

## Local Development

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv sync                              # Install dependencies
uv run uvicorn main:app --reload     # Run dev server
```

Or with pip:

```bash
pip install -e .
uvicorn main:app --reload
```

## Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check

## CI Pipeline

The `.woodpecker.yaml` defines three stages:

1. **lint** - Run ruff linter (using `uv tool run`)
2. **build** - Build Docker image (uses uv for fast installs)
3. **test-container** - Run container and verify health endpoint

## Docker

```bash
docker build -t demo-app .
docker run -p 8000:8000 demo-app
```

Then visit http://localhost:8000

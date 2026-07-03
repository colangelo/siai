# Design: Add Demo Repository

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  just demo      │────▶│ gitea_demo.py   │────▶│ Gitea API       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               │                        ▼
                               │                ┌─────────────────┐
                               │                │ Demo Repository │
                               │                │ - main.py       │
                               │                │ - Dockerfile    │
                               │                │ - .woodpecker   │
                               │                └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │ Woodpecker API  │────▶│ Pipeline Run    │
                        │ (activate repo) │     │ (build + test)  │
                        └─────────────────┘     └─────────────────┘
```

## API Flow

### 1. Repository Creation (Gitea API)

```
POST /api/v1/orgs/{org}/repos
{
  "name": "demo-app",
  "description": "Demo Python application for CI testing",
  "auto_init": false,
  "private": false
}
```

### 2. File Upload (Gitea API)

For each file in the demo template:
```
POST /api/v1/repos/{owner}/{repo}/contents/{filepath}
{
  "content": "<base64-encoded-content>",
  "message": "Initial commit: Add demo application"
}
```

Files to create:
- `main.py` - FastAPI hello-world
- `requirements.txt` - Dependencies
- `Dockerfile` - Multi-stage build
- `.woodpecker.yaml` - CI pipeline
- `README.md` - Documentation

### 3. Repository Activation (Woodpecker API)

First, get the forge_remote_id from Gitea:
```
GET /api/v1/repos/{owner}/{repo}  → response.id
```

Then activate in Woodpecker:
```
POST /api/repos?forge_remote_id={id}
Authorization: Bearer <token>
```

### 4. Issue Creation (Gitea API, optional)

```
POST /api/v1/repos/{owner}/{repo}/issues
{
  "title": "Add unit tests",
  "body": "## Description\nAdd pytest tests for the main application..."
}
```

## Demo Application Structure

```
demo-app/
├── main.py              # FastAPI application
├── requirements.txt     # fastapi, uvicorn
├── Dockerfile           # Multi-stage Python build
├── .woodpecker.yaml     # CI pipeline
└── README.md            # Documentation
```

### main.py
```python
from fastapi import FastAPI

app = FastAPI(title="Demo App")

@app.get("/")
def root():
    return {"message": "Hello from Woodpecker CI!"}

@app.get("/health")
def health():
    return {"status": "ok"}
```

### Dockerfile
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY main.py .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

### .woodpecker.yaml
```yaml
steps:
  - name: lint
    image: python:3.12-slim
    commands:
      - pip install ruff
      - ruff check .

  - name: build
    image: docker
    commands:
      - docker build -t demo-app:${CI_COMMIT_SHA:0:8} .
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  - name: test-container
    image: docker
    commands:
      - docker run --rm -d --name demo-test -p 8080:8000 demo-app:${CI_COMMIT_SHA:0:8}
      - sleep 3
      - wget -qO- http://localhost:8080/health | grep -q ok
      - docker stop demo-test
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

## Authentication Strategy

### Option A: Use Gitea Basic Auth (Current)
- Reuse existing `GITEA_ADMIN_PASSWORD` from `.env`
- Simple, no additional token management
- Works for Gitea API calls

### Option B: Woodpecker Token via Gitea OAuth
- Generate Woodpecker API token through OAuth flow
- More complex but matches production patterns
- Required for Woodpecker API calls

**Decision**: Use hybrid approach:
1. Gitea API: Basic auth (existing pattern)
2. Woodpecker API: User must first login to Woodpecker UI to authorize, then we can use their Gitea token

Actually, simpler approach: Instruct user to manually activate repo in Woodpecker UI (one click) since Woodpecker's API requires a logged-in user token that's complex to obtain programmatically.

**Revised Decision**: Create repo + files via Gitea API, provide instructions for Woodpecker activation. Add `--activate` flag that attempts Woodpecker activation if user provides a token.

## Configuration (setup.toml)

```toml
[demo]
enabled = true
repo_name = "demo-app"
repo_description = "Demo Python application for CI testing"
create_issues = true

[[demo.issues]]
title = "Add unit tests"
body = "Add pytest tests for the main application endpoints."
labels = ["enhancement"]

[[demo.issues]]
title = "Configure container registry push"
body = "Set up secrets for pushing to container registry."
labels = ["infrastructure"]
```

## Idempotency

1. Check if repository exists before creating
2. Skip file creation if file already exists with same content
3. Skip issue creation if issue with same title exists
4. Report what was created vs skipped

## Error Handling

| Error | Response |
|-------|----------|
| Repo already exists | Skip creation, continue with files |
| File already exists | Update if content differs, skip if same |
| Woodpecker not reachable | Warn, provide manual activation instructions |
| Invalid config | Exit with clear error message |

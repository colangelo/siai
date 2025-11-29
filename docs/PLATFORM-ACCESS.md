# SiAI Platform Access Guide

This document describes how AI agents can interact with the SiAI CI/CD platform (Gitea + Woodpecker CI).

## Overview

The platform provides:
- **Gitea** - Git hosting at `http://gitea.localhost`
- **Woodpecker CI** - CI/CD at `http://ci.localhost`
- **Container Registry** - Docker images at `127.0.0.1/admin/<repo>:<tag>`

## Access Methods

### 1. Gitea API (Recommended for Git Operations)

Direct HTTP API access for repository and user management.

**Authentication:**
```bash
# Create API token
curl -s -X POST "http://gitea.localhost/api/v1/users/admin/tokens" \
  -u "admin:admin123" \
  -H "Content-Type: application/json" \
  -d '{"name": "agent-token", "scopes": ["write:repository", "write:package"]}'
```

**Common Operations:**

```bash
# Get file content
curl -s "http://gitea.localhost/api/v1/repos/admin/demo-app/contents/main.py" \
  -H "Authorization: token $GITEA_TOKEN" | jq -r '.content' | base64 -d

# Update file (requires SHA of current version)
CURRENT_SHA=$(curl -s "http://gitea.localhost/api/v1/repos/admin/demo-app/contents/main.py" \
  -H "Authorization: token $GITEA_TOKEN" | jq -r '.sha')

curl -s -X PUT "http://gitea.localhost/api/v1/repos/admin/demo-app/contents/main.py" \
  -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Update main.py\",
    \"content\": \"$(cat main.py | base64 | tr -d '\n')\",
    \"sha\": \"$CURRENT_SHA\"
  }"

# Create repository
curl -s -X POST "http://gitea.localhost/api/v1/user/repos" \
  -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "new-repo", "private": false}'
```

**API Documentation:** http://gitea.localhost/api/swagger

### 2. Browser Automation (For UI-Only Operations)

Use Playwright for operations not available via API (e.g., Woodpecker settings).

**Location:** `servers/playwright/run.py`

**Commands:**
```bash
# Navigate to a URL
uv run servers/playwright/run.py navigate "http://ci.localhost/repos/admin/demo-app"

# Get accessibility snapshot (preferred for finding elements)
uv run servers/playwright/run.py snapshot

# Take screenshot (for visual verification)
uv run servers/playwright/run.py screenshot /tmp/page.png

# Click element (by text content, role, or CSS)
uv run servers/playwright/run.py click "Run pipeline"

# Type into field
uv run servers/playwright/run.py type "input[name='value']" "secret-value"

# Evaluate JavaScript (for complex element finding)
uv run servers/playwright/run.py eval "document.querySelector('button').click()"

# Wait for element
uv run servers/playwright/run.py wait ".success-message"
```

**Workflow Example - Trigger Manual Pipeline:**
```bash
# Navigate to manual pipeline page
uv run servers/playwright/run.py navigate "http://ci.localhost/repos/1/manual"

# Click the Run pipeline button
uv run servers/playwright/run.py eval "Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Run pipeline')).click()"

# Wait and verify
sleep 5
uv run servers/playwright/run.py screenshot /tmp/pipeline.png
```

**Workflow Example - Add Woodpecker Secret:**
```bash
# Navigate to secrets page
uv run servers/playwright/run.py navigate "http://ci.localhost/repos/admin/demo-app/settings/secrets"

# Take snapshot to find form elements
uv run servers/playwright/run.py snapshot

# Fill secret name and value
uv run servers/playwright/run.py type "input[placeholder='Name']" "gitea_token"
uv run servers/playwright/run.py type "input[placeholder='Value']" "$TOKEN_VALUE"

# Save
uv run servers/playwright/run.py click "button:has-text('Save')"
```

### 3. Docker Commands (For Container Operations)

**Pull and Run Images:**
```bash
# Pull from Gitea registry
docker pull 127.0.0.1/admin/demo-app:latest

# Run container
docker run --rm -p 8080:8000 127.0.0.1/admin/demo-app:latest

# Push to registry (requires login)
echo "$GITEA_TOKEN" | docker login 127.0.0.1 --username admin --password-stdin
docker push 127.0.0.1/admin/demo-app:latest
```

**Check Container Logs:**
```bash
docker compose logs -f gitea
docker compose logs -f wpk-server
docker compose logs -f wpk-agent
```

### 4. Just Commands (For Stack Management)

```bash
# Stack lifecycle
just docker-up          # Start all services
just docker-down        # Stop all services
just docker-restart     # Restart after config changes
just docker-status      # Show service status
just docker-health      # Status + endpoint URLs

# Logs
just docker-logs        # All logs
just docker-logs-server # Woodpecker server
just docker-logs-agent  # Woodpecker agent

# Setup
just quickstart         # Full automated setup
just nuclear            # Reset everything (destructive)
```

## Default Credentials

| Service | Username | Password | Notes |
|---------|----------|----------|-------|
| Gitea | admin | admin123 | From `.env` |
| Woodpecker | admin | (OAuth via Gitea) | Login through Gitea |

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Gitea Web | http://gitea.localhost | Git hosting UI |
| Gitea API | http://gitea.localhost/api/v1 | REST API |
| Woodpecker | http://ci.localhost | CI/CD UI |
| Container Registry | 127.0.0.1 (port 80) | Docker push/pull |

## Network Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Traefik        │────▶│  Gitea       │     │  Woodpecker     │
│  (*.localhost)  │     │  (port 3000) │◀───▶│  Server         │
└─────────────────┘     └──────────────┘     │  (port 8000)    │
        │                      │             └─────────────────┘
        │                      │                     │
        │               ┌──────┴───────┐             │
        │               │  PostgreSQL  │             │
        │               │  (port 5432) │             │
        │               └──────────────┘             │
        │                                            │
        │              ┌─────────────────────────────┘
        │              │
        │              ▼
        │       ┌─────────────────┐
        └──────▶│  Woodpecker     │
                │  Agent          │
                │  (Docker sock)  │
                └─────────────────┘
```

**Internal Hostnames (Docker network):**
- `gitea:3000` - Gitea from within containers
- `wpk-server:8000` - Woodpecker server
- `ci-postgres:5432` - PostgreSQL

## Pipeline Configuration

Pipelines are defined in `.woodpecker.yaml` in the repository root.

**Build and Push Example:**
```yaml
steps:
  - name: build
    image: docker:cli
    when:
      - event: [manual, tag]
    commands:
      - docker build -t 127.0.0.1/admin/demo-app:${CI_COMMIT_SHA:0:8} .
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  - name: push
    image: docker:cli
    when:
      - event: [manual, tag]
    environment:
      GITEA_TOKEN:
        from_secret: gitea_token
    commands:
      - echo "$GITEA_TOKEN" | docker login 127.0.0.1 --username admin --password-stdin
      - docker push 127.0.0.1/admin/demo-app:${CI_COMMIT_SHA:0:8}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

**Required Secrets:**
- `gitea_token` - Gitea API token with `write:package` scope

**Trust Requirements:**
For Docker builds, the repository must be marked as "Trusted" with "Volumes" enabled in Woodpecker settings.

## Troubleshooting

**Webhook not triggering pipeline:**
- Check Gitea can reach `ci.localhost` (configured via `extra_hosts`)
- Verify webhook URL in Gitea repo settings

**Docker push fails with HTTPS error:**
- Use `127.0.0.1` not `localhost` or `gitea.localhost`
- `127.0.0.1` is in Docker's default insecure registries

**Pipeline clone fails:**
- Pipeline uses `http://gitea:3000` internally (Docker network)
- Custom clone step needed if default fails

## Security Notes

- This is a development/POC setup - not hardened for production
- All services communicate over unencrypted HTTP
- Default credentials should be changed for any non-local deployment
- See ROADMAP.md v0.4.0 for authentication/HTTPS configuration plans

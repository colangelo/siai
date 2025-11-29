# Quickstart Guide

Get your local Gitea + Woodpecker CI stack running in 5 minutes.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [just](https://github.com/casey/just) command runner
- [uv](https://docs.astral.sh/uv/) Python package manager (for automation scripts)

## Quick Setup

### Option A: Fully Automated (Recommended)

```bash
just quickstart
```

This single command will:
- Initialize configuration files
- Generate required secrets
- Start all containers
- Configure Gitea and create OAuth app
- Create a demo repository

### Option B: Step-by-Step

```bash
just step1-init      # Create .env and config/setup.toml
just step2-secrets   # Generate WOODPECKER_AGENT_SECRET
just step3-start     # Start all containers
# Wait ~10 seconds for services to start
just step4-configure # Initialize Gitea + create OAuth app
just docker-restart  # Apply OAuth credentials
just step5-demo      # Create demo repository (optional)
```

## Access Your Stack

| Service    | URL                        | Default Login        |
|------------|----------------------------|----------------------|
| Gitea      | http://gitea.localhost     | `admin` / `admin123` |
| Woodpecker | http://ci.localhost        | (via Gitea OAuth)    |

## Optional: Configure Users & Organizations

Use the interactive wizard to set up users, organizations, and teams:

```bash
just wizard      # Interactive setup
just setup       # Apply configuration
```

Or edit `config/setup.toml` directly.

## Common Commands

```bash
just docker-status      # Show service status
just docker-health      # Status + endpoint URLs
just docker-logs        # Follow all logs
just docker-logs-gitea  # Follow Gitea logs only

just docker-restart     # Restart after .env changes
just docker-down        # Stop all services
just docker-up          # Start all services
```

## Troubleshooting

### Services won't start

```bash
just docker-logs        # Check for errors
just docker-status      # Check container status
```

### Can't login to Woodpecker

1. Verify OAuth credentials in `.env` match what's in Gitea
2. Check Woodpecker logs: `just docker-logs-server`
3. Ensure redirect URI is `http://ci.localhost/authorize`

### Reset everything

```bash
just nuclear     # Backup configs + full reset
just quickstart  # Start fresh with full automation
```

## Demo Repository

Create a demo repository to test the CI integration:

```bash
just demo            # Create demo-app repository
just demo-dry-run    # Preview what would be created
```

The demo includes:
- FastAPI Python application (`main.py`)
- Docker multi-stage build (`Dockerfile`)
- Woodpecker CI pipeline (`.woodpecker.yaml`)
- Documentation (`README.md`)

After running `just demo`:
1. Go to Woodpecker (http://ci.localhost)
2. Click "Add repository" → activate "demo-app"
3. The pipeline will run automatically on the next push

## Next Steps

1. Explore the demo repository in Gitea
2. Activate it in Woodpecker and trigger a build
3. Create your own repositories with `.woodpecker.yml` pipelines

See [README.md](README.md) for architecture details and advanced configuration.

# Quickstart Guide

Get your local Gitea + Woodpecker CI stack running in 5 minutes.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [just](https://github.com/casey/just) command runner
- [uv](https://docs.astral.sh/uv/) Python package manager (for automation scripts)

## Quick Setup

```bash
# 1. Initialize configuration
just init

# 2. Generate agent secret (automatically saved to .env)
just secret

# 3. Start the stack
just up

# 4. Wait ~10 seconds for services to start, then bootstrap Gitea
just bootstrap

# 5. Restart to apply OAuth config
just restart
```

The bootstrap command will:
- Initialize Gitea database
- Create admin user (default: `admin` / `admin123`)
- Create OAuth app for Woodpecker
- Automatically save OAuth credentials to `.env`

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
just status      # Show service status
just health      # Status + endpoint URLs
just logs        # Follow all logs
just logs-gitea  # Follow Gitea logs only

just restart     # Restart after .env changes
just down        # Stop all services
just up          # Start all services
```

## Troubleshooting

### Services won't start

```bash
just logs        # Check for errors
just status      # Check container status
```

### Can't login to Woodpecker

1. Verify OAuth credentials in `.env` match what's in Gitea
2. Check Woodpecker logs: `just logs-server`
3. Ensure redirect URI is `http://ci.localhost/authorize`

### Reset everything

```bash
just nuclear     # Backup configs + full reset
just init        # Start fresh
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

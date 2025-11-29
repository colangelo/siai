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

# 2. Generate agent secret and add to .env
just secret
# Copy the output and paste into .env as WOODPECKER_AGENT_SECRET=<secret>

# 3. Start the stack
just up

# 4. Wait ~10 seconds for services to start, then bootstrap Gitea
just bootstrap
```

The bootstrap command will:
- Initialize Gitea database
- Create admin user (default: `admin` / `admin123`)
- Create OAuth app for Woodpecker
- Output OAuth credentials to add to `.env`

```bash
# 5. Add OAuth credentials to .env (from bootstrap output)
# WOODPECKER_GITEA_CLIENT=<client-id>
# WOODPECKER_GITEA_SECRET=<client-secret>

# 6. Restart to apply OAuth config
just restart
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

## Next Steps

1. Create a repository in Gitea
2. Add a `.woodpecker.yml` pipeline file
3. Activate the repo in Woodpecker
4. Push and watch your pipeline run!

See [README.md](README.md) for architecture details and advanced configuration.

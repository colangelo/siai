# Justfile for Gitea + Woodpecker CI local stack

set dotenv-load := true

# Default recipe: show available commands
default:
    @just --list

# === Bootstrap ===

# Initialize .env from example (won't overwrite existing)
init:
    #!/usr/bin/env bash
    if [ -f .env ]; then
        echo ".env already exists, skipping copy"
    else
        cp .env.example .env
        echo "Created .env from .env.example"
    fi
    echo ""
    echo "Next steps:"
    echo "  1. Run 'just secret' to generate WOODPECKER_AGENT_SECRET"
    echo "  2. Run 'just up' to start the stack"
    echo "  3. Visit http://gitea.localhost to complete Gitea setup"
    echo "  4. Create OAuth app in Gitea (see 'just oauth-help')"
    echo "  5. Add OAuth credentials to .env and run 'just restart'"

# Generate a random secret for WOODPECKER_AGENT_SECRET
secret:
    @echo "Generated secret (add to .env as WOODPECKER_AGENT_SECRET):"
    @openssl rand -hex 32

# Show OAuth setup instructions
oauth-help:
    @echo "OAuth Setup for Woodpecker:"
    @echo ""
    @echo "1. Go to http://gitea.localhost"
    @echo "2. User Settings → Applications → OAuth2 Applications"
    @echo "3. Create new app:"
    @echo "   - Name: Woodpecker"
    @echo "   - Redirect URI: http://ci.localhost/authorize"
    @echo "4. Copy Client ID → WOODPECKER_GITEA_CLIENT in .env"
    @echo "5. Copy Client Secret → WOODPECKER_GITEA_SECRET in .env"
    @echo "6. Run 'just restart'"

# === Stack Management ===

# Start all services
up:
    docker compose up -d

# Stop all services
down:
    docker compose down

# Restart all services (use after .env changes)
restart:
    docker compose up -d --force-recreate

# Show service status
status:
    docker compose ps

# === Logs ===

# Follow logs for all services
logs:
    docker compose logs -f

# Follow logs for a specific service
logs-service service:
    docker compose logs -f {{ service }}

# Follow Gitea logs
logs-gitea:
    docker compose logs -f gitea

# Follow Woodpecker server logs
logs-server:
    docker compose logs -f woodpecker-server

# Follow Woodpecker agent logs
logs-agent:
    docker compose logs -f woodpecker-agent

# Follow Traefik logs
logs-traefik:
    docker compose logs -f traefik

# === Health & Debug ===

# Check if services are healthy
health:
    @echo "=== Service Status ==="
    @docker compose ps --format "table {{{{.Name}}}}\t{{{{.Status}}}}\t{{{{.Ports}}}}"
    @echo ""
    @echo "=== Endpoints ==="
    @echo "Gitea:      http://gitea.localhost"
    @echo "Woodpecker: http://ci.localhost"

# Show Woodpecker server health endpoint
health-woodpecker:
    @curl -s http://ci.localhost/healthz && echo " - Woodpecker OK" || echo "Woodpecker not responding"

# Shell into a running container
shell service:
    docker compose exec {{ service }} sh

# === Cleanup ===

# Stop and remove containers, networks
clean:
    docker compose down

# Stop, remove containers, networks, AND volumes (destructive!)
clean-all:
    @echo "This will delete all data (Gitea repos, Woodpecker DB)!"
    @read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] && docker compose down -v || echo "Aborted"

# === URLs ===

# Open Gitea in browser (macOS)
[macos]
open-gitea:
    open http://gitea.localhost

# Open Woodpecker in browser (macOS)
[macos]
open-ci:
    open http://ci.localhost

# Open Gitea in browser (Linux)
[linux]
open-gitea:
    xdg-open http://gitea.localhost

# Open Woodpecker in browser (Linux)
[linux]
open-ci:
    xdg-open http://ci.localhost

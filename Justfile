# Justfile for Gitea + Woodpecker CI local stack

# Note: Not using dotenv-load to avoid shell env overriding .env file in docker compose

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
    echo "  3. Run 'just gitea-init' to initialize Gitea and create admin"
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

# Initialize Gitea database and create admin user (run once after first 'just up')
gitea-init:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && source .env
    echo "=== Initializing Gitea database ==="
    docker exec gitea gitea migrate
    echo ""
    echo "=== Creating admin user ==="
    ADMIN_USER="${GITEA_ADMIN:-admin}"
    ADMIN_EMAIL="${GITEA_ADMIN_EMAIL:-admin@localhost}"
    ADMIN_PASS="${GITEA_ADMIN_PASSWORD:-admin123}"
    docker exec gitea gitea admin user create \
        --username "$ADMIN_USER" \
        --password "$ADMIN_PASS" \
        --email "$ADMIN_EMAIL" \
        --admin \
        --must-change-password=false
    echo ""
    echo "✓ Gitea initialized!"
    echo "  Login: http://gitea.localhost"
    echo "  User:  $ADMIN_USER"
    echo "  Pass:  $ADMIN_PASS"
    echo ""
    echo "Next: run 'just gitea-oauth' to create Woodpecker OAuth app"

# Create OAuth2 app for Woodpecker in Gitea (run after gitea-init)
gitea-oauth:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && source .env
    ADMIN_USER="${GITEA_ADMIN:-admin}"
    ADMIN_PASS="${GITEA_ADMIN_PASSWORD:-admin123}"
    REDIRECT_URI="${WOODPECKER_HOST:-http://ci.localhost}/authorize"

    echo "=== Creating OAuth2 application for Woodpecker ==="
    RESPONSE=$(curl -s -X POST "http://gitea.localhost/api/v1/user/applications/oauth2" \
      -u "$ADMIN_USER:$ADMIN_PASS" \
      -H "Content-Type: application/json" \
      -d "{\"name\": \"Woodpecker CI\", \"redirect_uris\": [\"$REDIRECT_URI\"], \"confidential_client\": true}")

    CLIENT_ID=$(echo "$RESPONSE" | grep -o '"client_id":"[^"]*"' | cut -d'"' -f4)
    CLIENT_SECRET=$(echo "$RESPONSE" | grep -o '"client_secret":"[^"]*"' | cut -d'"' -f4)

    if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
        echo "Error: Failed to create OAuth app"
        echo "$RESPONSE"
        exit 1
    fi

    echo ""
    echo "✓ OAuth2 app created!"
    echo ""
    echo "Add these to your .env file:"
    echo "  WOODPECKER_GITEA_CLIENT=$CLIENT_ID"
    echo "  WOODPECKER_GITEA_SECRET=$CLIENT_SECRET"
    echo ""
    echo "Then run: just restart"

# Full bootstrap: init + oauth + show next steps
bootstrap:
    #!/usr/bin/env bash
    set -e
    just gitea-init
    echo ""
    just gitea-oauth

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
    docker compose logs -f wpk-server

# Follow Woodpecker agent logs
logs-agent:
    docker compose logs -f wpk-agent

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

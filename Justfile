# Justfile for Gitea + Woodpecker CI local stack

# Note: Not using dotenv-load to avoid shell env overriding .env file in docker compose

# Default recipe: show available commands
default:
    @just --list

# === Bootstrap ===

# Initialize .env and config from examples (won't overwrite existing)
init:
    #!/usr/bin/env bash
    if [ -f .env ]; then
        echo ".env already exists, skipping copy"
    else
        cp .env.example .env
        echo "Created .env from .env.example"
    fi
    if [ -f config/setup.toml ]; then
        echo "config/setup.toml already exists, skipping copy"
    else
        cp config/setup.toml.example config/setup.toml
        echo "Created config/setup.toml from config/setup.toml.example"
    fi
    echo ""
    echo "Next steps:"
    echo "  1. Run 'just secret' to generate WOODPECKER_AGENT_SECRET"
    echo "  2. Edit .env with your settings"
    echo "  3. Edit config/setup.toml for users/orgs (optional)"
    echo "  4. Run 'just up' to start the stack"
    echo "  5. Run 'just bootstrap' to initialize Gitea"

# Generate and set WOODPECKER_AGENT_SECRET in .env
secret:
    #!/usr/bin/env bash
    set -e
    if [ ! -f .env ]; then
        echo "Error: .env not found. Run 'just init' first."
        exit 1
    fi
    SECRET=$(openssl rand -hex 32)
    if grep -q "^WOODPECKER_AGENT_SECRET=" .env; then
        sed -i.bak "s/^WOODPECKER_AGENT_SECRET=.*/WOODPECKER_AGENT_SECRET=$SECRET/" .env && rm -f .env.bak
    else
        echo "WOODPECKER_AGENT_SECRET=$SECRET" >> .env
    fi
    echo "✓ WOODPECKER_AGENT_SECRET set in .env"

# Interactive wizard to create config/setup.toml
wizard:
    uv run scripts/gitea_wizard.py

# Show OAuth setup instructions (manual alternative)
oauth-help:
    @echo "OAuth Setup for Woodpecker (manual method):"
    @echo ""
    @echo "1. Go to http://gitea.localhost"
    @echo "2. User Settings → Applications → OAuth2 Applications"
    @echo "3. Create new app:"
    @echo "   - Name: Woodpecker"
    @echo "   - Redirect URI: http://ci.localhost/authorize"
    @echo "4. Copy Client ID → WOODPECKER_GITEA_CLIENT in .env"
    @echo "5. Copy Client Secret → WOODPECKER_GITEA_SECRET in .env"
    @echo "6. Run 'just restart'"
    @echo ""
    @echo "Or use: just gitea-oauth (requires Python + uv)"

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

# Create OAuth2 app for Woodpecker using Python script
gitea-oauth:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && source .env
    export GITEA_ADMIN="${GITEA_ADMIN:-admin}"
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_oauth.py --config config/setup.toml

# Create OAuth2 app using bash (fallback, no Python required)
gitea-oauth-bash:
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

# Provision users, orgs, and teams from config/setup.toml
setup:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_setup.py

# Preview setup changes without applying (dry-run)
setup-dry-run:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_setup.py --dry-run

# Full bootstrap: init + oauth + show next steps
bootstrap:
    #!/usr/bin/env bash
    set -e
    just gitea-init
    echo ""
    just gitea-oauth

# Create demo repository with Python app and CI pipeline
demo:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_demo.py

# Preview demo repository creation (dry-run)
demo-dry-run:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_demo.py --dry-run

# Create demo repository with sample issues
demo-with-issues:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_demo.py --create-issues

# === Stack Management ===

# Start all services (unset env vars to ensure .env is used)
up:
    #!/usr/bin/env bash
    unset WOODPECKER_GITEA_CLIENT WOODPECKER_GITEA_SECRET WOODPECKER_AGENT_SECRET 2>/dev/null || true
    docker compose up -d

# Stop all services
down:
    docker compose down

# Restart all services (use after .env changes)
restart:
    #!/usr/bin/env bash
    unset WOODPECKER_GITEA_CLIENT WOODPECKER_GITEA_SECRET WOODPECKER_AGENT_SECRET 2>/dev/null || true
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

# ☢️  Full reset: backups only configs (.env, config/setup.toml), then removes EVERYTHING (repos, users, CI history) for fresh start
nuclear:
    #!/usr/bin/env bash
    set -e
    echo "☢️  NUCLEAR RESET - This will:"
    echo "   • Stop and remove all containers"
    echo "   • Delete all volumes (repos, databases, CI history)"
    echo "   • Backup and remove .env and config/setup.toml"
    echo ""
    read -p "Are you sure? [y/N] " confirm
    if [ "$confirm" != "y" ]; then
        echo "Aborted."
        exit 0
    fi
    echo ""
    echo "=== Backing up config files ==="
    [ -f .env ] && cp .env ".env.backup.$(date +%Y%m%d-%H%M%S)" && echo "  .env → .env.backup.*"
    [ -f config/setup.toml ] && cp config/setup.toml "config/setup.toml.backup.$(date +%Y%m%d-%H%M%S)" && echo "  config/setup.toml → config/setup.toml.backup.*"
    echo ""
    echo "=== Stopping containers and removing volumes ==="
    docker compose down -v
    echo ""
    echo "=== Removing config files ==="
    rm -f .env config/setup.toml
    echo ""
    echo "☢️  Nuclear reset complete!"
    echo ""
    echo "To start fresh, run:"
    echo "  just init        # Create .env and config/setup.toml"
    echo "  just secret      # Generate agent secret (add to .env)"
    echo "  just up          # Start stack"
    echo "  just bootstrap   # Initialize Gitea + OAuth"
    echo ""
    echo "See QUICKSTART.md for detailed instructions."

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

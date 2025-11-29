# Justfile for Gitea + Woodpecker CI local stack

# Note: Not using dotenv-load to avoid shell env overriding .env file in docker compose

# Default recipe: show available commands
default:
    @just --list

# ══════════════════════════════════════════════════════════════════════════════
# QUICKSTART - Run this for fully automated setup
# ══════════════════════════════════════════════════════════════════════════════

# 🚀 Fully automated setup: creates config, starts stack, initializes everything
quickstart:
    #!/usr/bin/env bash
    set -e
    echo "🚀 Quickstart: Automated CI/CD Stack Setup"
    echo "==========================================="
    echo ""

    # Step 1: Initialize config files
    echo "━━━ Step 1/5: Initializing configuration ━━━"
    just step1-init
    echo ""

    # Step 2: Generate secrets
    echo "━━━ Step 2/5: Generating secrets ━━━"
    just step2-secrets
    echo ""

    # Step 3: Start containers
    echo "━━━ Step 3/5: Starting containers ━━━"
    just step3-start
    echo ""

    # Wait for services to be ready
    echo "Waiting for services to start..."
    sleep 10

    # Step 4: Configure Gitea + OAuth
    echo "━━━ Step 4/5: Configuring Gitea + OAuth ━━━"
    just step4-configure
    echo ""

    # Restart to apply OAuth
    echo "Restarting to apply OAuth credentials..."
    just restart
    sleep 5
    echo ""

    # Step 5: Create demo (optional but included in quickstart)
    echo "━━━ Step 5/5: Creating demo repository ━━━"
    just step5-demo || echo "Demo creation skipped (may need manual config)"
    echo ""

    echo "==========================================="
    echo "✅ Quickstart complete!"
    echo ""
    echo "Access your stack:"
    echo "  Gitea:      http://gitea.localhost"
    echo "  Woodpecker: http://ci.localhost"
    echo ""
    echo "Default credentials:"
    echo "  User: admin"
    echo "  Pass: (check .env for GITEA_ADMIN_PASSWORD)"
    echo ""
    echo "Optional next steps:"
    echo "  just wizard       # Customize users/orgs interactively"
    echo "  just step6-apply  # Apply config/setup.toml changes"

# ══════════════════════════════════════════════════════════════════════════════
# SETUP STEPS (run in order, or use 'just quickstart')
# ══════════════════════════════════════════════════════════════════════════════

# Step 1: Initialize .env and config from examples (won't overwrite existing)
step1-init:
    #!/usr/bin/env bash
    if [ -f .env ]; then
        echo "✓ .env already exists, skipping copy"
    else
        cp .env.example .env
        echo "✓ Created .env from .env.example"
    fi
    if [ -f config/setup.toml ]; then
        echo "✓ config/setup.toml already exists, skipping copy"
    else
        cp config/setup.toml.example config/setup.toml
        echo "✓ Created config/setup.toml from config/setup.toml.example"
    fi

# Step 2: Generate required secrets (agent secret)
step2-secrets:
    #!/usr/bin/env bash
    set -e
    if [ ! -f .env ]; then
        echo "Error: .env not found. Run 'just step1-init' first."
        exit 1
    fi
    SECRET=$(openssl rand -hex 32)
    if grep -q "^WOODPECKER_AGENT_SECRET=" .env; then
        sed -i.bak "s/^WOODPECKER_AGENT_SECRET=.*/WOODPECKER_AGENT_SECRET=$SECRET/" .env && rm -f .env.bak
    else
        echo "WOODPECKER_AGENT_SECRET=$SECRET" >> .env
    fi
    echo "✓ WOODPECKER_AGENT_SECRET set in .env"

# Step 3: Start all services
step3-start:
    #!/usr/bin/env bash
    unset WOODPECKER_GITEA_CLIENT WOODPECKER_GITEA_SECRET WOODPECKER_AGENT_SECRET 2>/dev/null || true
    docker compose up -d
    echo "✓ Services started"
    echo ""
    echo "Endpoints (wait ~10s for startup):"
    echo "  Gitea:      http://gitea.localhost"
    echo "  Woodpecker: http://ci.localhost"

# Step 4: Configure Gitea (init DB + create admin + OAuth app)
step4-configure:
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
    echo "✓ Admin user created: $ADMIN_USER"
    echo ""

    echo "=== Creating OAuth app for Woodpecker ==="
    export GITEA_ADMIN="${GITEA_ADMIN:-admin}"
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_oauth.py --config config/setup.toml
    echo ""

    echo "✓ Gitea configured!"
    echo "  Login: http://gitea.localhost"
    echo "  User:  $ADMIN_USER"

# Step 5: Create demo repository (optional)
step5-demo:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_demo.py

# Step 6: Apply users/orgs/teams from config/setup.toml (optional)
step6-apply:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_setup.py

# ══════════════════════════════════════════════════════════════════════════════
# OPTIONAL TOOLS
# ══════════════════════════════════════════════════════════════════════════════

# Interactive wizard to customize config/setup.toml
wizard:
    uv run scripts/gitea_wizard.py

# Preview what step6-apply would do (dry-run)
step6-apply-dry-run:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_setup.py --dry-run

# Preview what step5-demo would create (dry-run)
step5-demo-dry-run:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_demo.py --dry-run

# Create demo repository with sample issues
step5-demo-with-issues:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-admin123}"
    uv run scripts/gitea_demo.py --create-issues

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

# ══════════════════════════════════════════════════════════════════════════════
# STACK MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

# Start all services (alias for 3-start)
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

# ══════════════════════════════════════════════════════════════════════════════
# LOGS
# ══════════════════════════════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH & DEBUG
# ══════════════════════════════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

# Stop and remove containers, networks
clean:
    docker compose down

# Stop, remove containers, networks, AND volumes (destructive!)
clean-all:
    @echo "This will delete all data (Gitea repos, Woodpecker DB)!"
    @read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] && docker compose down -v || echo "Aborted"

# ☢️  Full reset: backup configs, remove EVERYTHING, start fresh
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
    echo "  just quickstart      # Fully automated setup"
    echo ""
    echo "Or step-by-step:"
    echo "  just step1-init      # Create config files"
    echo "  just step2-secrets   # Generate secrets"
    echo "  just step3-start     # Start containers"
    echo "  just step4-configure # Initialize Gitea + OAuth"
    echo "  just step5-demo      # Create demo repo (optional)"

# ══════════════════════════════════════════════════════════════════════════════
# BROWSER SHORTCUTS
# ══════════════════════════════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════════════════════════════
# LEGACY ALIASES (for backwards compatibility)
# ══════════════════════════════════════════════════════════════════════════════

# Alias: init → step1-init
init: step1-init

# Alias: secret → step2-secrets
secret: step2-secrets

# Alias: bootstrap → step4-configure
bootstrap: step4-configure

# Alias: setup → step6-apply
setup: step6-apply

# Alias: setup-dry-run → step6-apply-dry-run
setup-dry-run: step6-apply-dry-run

# Alias: demo → step5-demo
demo: step5-demo

# Alias: demo-dry-run → step5-demo-dry-run
demo-dry-run: step5-demo-dry-run

# Alias: demo-with-issues → step5-demo-with-issues
demo-with-issues: step5-demo-with-issues

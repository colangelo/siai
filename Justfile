# Justfile for Gitea + Woodpecker CI local stack

# Note: Not using dotenv-load to avoid shell env overriding .env file in docker compose

# Default recipe: show available commands
default:
    @just --list

# ══════════════════════════════════════════════════════════════════════════════
# QUALITY GATE - lint / test / check (what CI and second-loop run)
# ══════════════════════════════════════════════════════════════════════════════

# Lint all Python (automation scripts, playwright runner, demo app)
lint:
    uv run --with ruff ruff check scripts servers demo-repo

# Run the eval suite (repo sanity checks + frozen second-loop evals in evals/)
test *args:
    uv run --with pytest --with pyyaml pytest evals/ -q "$@"

# Conformance check for the docs/ OKF bundle (exit-code truth)
docs-check:
    node ~/_sync/dev/second-loop/src/okf.ts check docs

# Regenerate docs/index.md from frontmatter. Run after adding/editing any doc.
docs-index:
    node ~/_sync/dev/second-loop/src/okf.ts index docs

# Validate every compose layering parses (client-side only, no daemon needed)
compose-check:
    docker compose -f docker-compose.yml config -q
    docker compose -f docker-compose.yml -f docker-compose.harbor.yml config -q
    docker compose -f docker-compose.yml -f docker-compose.homelab.yml config -q 2>/dev/null
    docker compose -f docker-compose.yml -f docker-compose.homelab.yml -f docker-compose.homelab.smoke.yml config -q 2>/dev/null

# The deterministic gate: lint + docs conformance + compose validation + evals
check: lint docs-check compose-check test

# Static file server over the repo (loopback, non-default port) — lets a browser
# (or the second-loop verifier) navigate the docs bundle from docs/index.md.
serve port="8378":
    python3 -m http.server {{port}} --bind 127.0.0.1

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
    just docker-restart
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
    @echo "6. Run 'just docker-restart'"

# ══════════════════════════════════════════════════════════════════════════════
# HARBOR - Optional Container Registry
# ══════════════════════════════════════════════════════════════════════════════

# Start Harbor services (requires REGISTRY_BACKEND=harbor in .env)
harbor-up:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && source .env
    if [ "${REGISTRY_BACKEND:-gitea}" != "harbor" ]; then
        echo "Warning: REGISTRY_BACKEND is not set to 'harbor' in .env"
        echo "Set REGISTRY_BACKEND=harbor to enable Harbor."
        exit 1
    fi
    unset WOODPECKER_GITEA_CLIENT WOODPECKER_GITEA_SECRET WOODPECKER_AGENT_SECRET 2>/dev/null || true

    # Check if Trivy should be enabled
    PROFILES=""
    if [ "${HARBOR_TRIVY_ENABLED:-false}" = "true" ]; then
        PROFILES="--profile trivy"
        echo "Starting Harbor with Trivy vulnerability scanner..."
    else
        echo "Starting Harbor services..."
    fi

    docker compose -f docker-compose.yml -f docker-compose.harbor.yml $PROFILES up -d
    echo ""
    echo "Harbor UI: http://registry.localhost"
    echo "Default login: admin / Harbor12345 (or HARBOR_ADMIN_PASSWORD from .env)"

# Stop Harbor services
harbor-down:
    #!/usr/bin/env bash
    echo "Stopping Harbor services..."
    docker compose -f docker-compose.yml -f docker-compose.harbor.yml --profile trivy down
    echo "Harbor services stopped. Data volumes preserved."

# Configure Harbor (create projects and robot accounts)
harbor-setup:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export HARBOR_ADMIN_PASSWORD="${HARBOR_ADMIN_PASSWORD:-Harbor12345}"
    uv run scripts/harbor_setup.py

# Preview Harbor setup changes (dry-run)
harbor-setup-dry-run:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && set -a && source .env && set +a
    export HARBOR_ADMIN_PASSWORD="${HARBOR_ADMIN_PASSWORD:-Harbor12345}"
    uv run scripts/harbor_setup.py --dry-run

# Docker login to Harbor registry
harbor-login:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] && source .env
    HARBOR_USER="${1:-admin}"
    HARBOR_PASS="${HARBOR_ADMIN_PASSWORD:-Harbor12345}"
    echo "Logging in to Harbor as $HARBOR_USER..."
    echo "$HARBOR_PASS" | docker login registry.localhost --username "$HARBOR_USER" --password-stdin
    echo "✓ Logged in to registry.localhost"

# Show active registry configuration and status
registry-status:
    #!/usr/bin/env bash
    [ -f .env ] && source .env
    echo "=== Registry Configuration ==="
    echo ""
    BACKEND="${REGISTRY_BACKEND:-gitea}"
    echo "Active backend: $BACKEND"
    echo ""

    if [ "$BACKEND" = "harbor" ]; then
        echo "Registry URL:   http://registry.localhost"
        echo "Push format:    registry.localhost/<project>/<image>:<tag>"
        echo ""
        echo "=== Harbor Service Status ==="
        docker compose -f docker-compose.yml -f docker-compose.harbor.yml ps --format "table {{{{.Name}}}}\t{{{{.Status}}}}" 2>/dev/null | grep -E "^(NAME|harbor)" || echo "Harbor services not running"
        echo ""
        echo "Trivy enabled: ${HARBOR_TRIVY_ENABLED:-false}"
        echo ""
        # Check if Harbor API is responding
        if curl -sf http://registry.localhost/api/v2.0/systeminfo > /dev/null 2>&1; then
            echo "Harbor API: ✓ responding"
            VERSION=$(curl -sf http://registry.localhost/api/v2.0/systeminfo | grep -o '"harbor_version":"[^"]*"' | cut -d'"' -f4)
            [ -n "$VERSION" ] && echo "Harbor version: $VERSION"
        else
            echo "Harbor API: ✗ not responding"
        fi
    else
        echo "Registry URL:   127.0.0.1 (via Traefik to Gitea)"
        echo "Push format:    127.0.0.1/<owner>/<repo>:<tag>"
        echo ""
        echo "Note: Gitea registry requires no additional services."
        echo "To enable Harbor, set REGISTRY_BACKEND=harbor in .env"
    fi

# ══════════════════════════════════════════════════════════════════════════════
# DOCKER - Stack Management
# ══════════════════════════════════════════════════════════════════════════════

# Start all services (includes Harbor if REGISTRY_BACKEND=harbor)
docker-up:
    #!/usr/bin/env bash
    unset WOODPECKER_GITEA_CLIENT WOODPECKER_GITEA_SECRET WOODPECKER_AGENT_SECRET 2>/dev/null || true
    [ -f .env ] && source .env

    if [ "${REGISTRY_BACKEND:-gitea}" = "harbor" ]; then
        PROFILES=""
        [ "${HARBOR_TRIVY_ENABLED:-false}" = "true" ] && PROFILES="--profile trivy"
        docker compose -f docker-compose.yml -f docker-compose.harbor.yml $PROFILES up -d
    else
        docker compose up -d
    fi

# Stop all services
docker-down:
    docker compose down

# Restart all services (use after .env changes)
docker-restart:
    #!/usr/bin/env bash
    unset WOODPECKER_GITEA_CLIENT WOODPECKER_GITEA_SECRET WOODPECKER_AGENT_SECRET 2>/dev/null || true
    [ -f .env ] && source .env

    if [ "${REGISTRY_BACKEND:-gitea}" = "harbor" ]; then
        PROFILES=""
        [ "${HARBOR_TRIVY_ENABLED:-false}" = "true" ] && PROFILES="--profile trivy"
        docker compose -f docker-compose.yml -f docker-compose.harbor.yml $PROFILES up -d --force-recreate
    else
        docker compose up -d --force-recreate
    fi

# Show service status
docker-status:
    docker compose ps

# ══════════════════════════════════════════════════════════════════════════════
# DOCKER - Logs
# ══════════════════════════════════════════════════════════════════════════════

# Follow logs for all services
docker-logs:
    docker compose logs -f

# Follow logs for a specific service
docker-logs-service service:
    docker compose logs -f {{ service }}

# Follow Gitea logs
docker-logs-gitea:
    docker compose logs -f gitea

# Follow Woodpecker server logs
docker-logs-server:
    docker compose logs -f wpk-server

# Follow Woodpecker agent logs
docker-logs-agent:
    docker compose logs -f wpk-agent

# Follow Traefik logs
docker-logs-traefik:
    docker compose logs -f traefik

# ══════════════════════════════════════════════════════════════════════════════
# DOCKER - Health & Debug
# ══════════════════════════════════════════════════════════════════════════════

# Check if services are healthy
docker-health:
    #!/usr/bin/env bash
    [ -f .env ] && source .env
    echo "=== Service Status ==="
    if [ "${REGISTRY_BACKEND:-gitea}" = "harbor" ]; then
        docker compose -f docker-compose.yml -f docker-compose.harbor.yml ps --format "table {{{{.Name}}}}\t{{{{.Status}}}}\t{{{{.Ports}}}}" 2>/dev/null || docker compose ps
    else
        docker compose ps --format "table {{{{.Name}}}}\t{{{{.Status}}}}\t{{{{.Ports}}}}" 2>/dev/null || docker compose ps
    fi
    echo ""
    echo "=== Endpoints ==="
    echo "Gitea:      http://gitea.localhost"
    echo "Woodpecker: http://ci.localhost"
    if [ "${REGISTRY_BACKEND:-gitea}" = "harbor" ]; then
        echo "Harbor:     http://registry.localhost"
    fi

# Show Woodpecker server health endpoint
docker-health-woodpecker:
    @curl -s http://ci.localhost/healthz && echo " - Woodpecker OK" || echo "Woodpecker not responding"

# Shell into a running container
docker-shell service:
    docker compose exec {{ service }} sh

# ══════════════════════════════════════════════════════════════════════════════
# DOCKER - Cleanup
# ══════════════════════════════════════════════════════════════════════════════

# Stop and remove containers, networks
docker-clean:
    docker compose down

# Stop, remove containers, networks, AND volumes (destructive!)
docker-clean-all:
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


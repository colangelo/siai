<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local OSS CI/CD stack: **Gitea + Woodpecker CI + Traefik** (Caddy alternative available). This is a POC/template for self-hosted Git + CI pipelines with Docker-based execution.

## Common Commands

```bash
# === QUICKSTART (recommended) ===
just quickstart      # 🚀 Fully automated setup (does everything)

# === STEP-BY-STEP SETUP ===
just step1-init      # Create .env and config/setup.toml from examples
just step2-secrets   # Generate WOODPECKER_AGENT_SECRET
just step3-start     # Start all services
just step4-configure # Initialize Gitea + create OAuth app
just step5-demo      # Create demo repository with CI pipeline
just step6-apply     # Provision users/orgs from config/setup.toml

# === TOOLS ===
just wizard          # Interactive setup wizard
just step5-demo-dry-run   # Preview demo creation
just step6-apply-dry-run  # Preview setup changes

# === STACK MANAGEMENT ===
just docker-up              # Start all services
just docker-down            # Stop all services
just docker-restart         # Restart after .env changes
just docker-status          # Show service status
just docker-health          # Status + endpoint URLs

# === LOGS ===
just docker-logs            # Follow all logs
just docker-logs-server     # Woodpecker server logs
just docker-logs-agent      # Woodpecker agent logs

# === CLEANUP ===
just docker-clean           # Remove containers/networks
just docker-clean-all       # Also remove volumes (destructive)
just nuclear                # Full reset with config backup
```

## Setup Flow

**Recommended:** `just quickstart` (fully automated)

**Or step-by-step:**
1. `just step1-init` - create .env and config/setup.toml
2. `just step2-secrets` - generate agent secret
3. `just step3-start` - start stack
4. `just step4-configure` - initialize Gitea + create OAuth app
5. `just docker-restart` - apply OAuth credentials
6. `just step5-demo` - create demo repository (optional)
7. `just step6-apply` - provision users/orgs from config (optional)
8. Visit `http://ci.localhost`, login via Gitea, activate repos

## Project Structure

```
siai/
├── scripts/                    # Python automation (PEP 723 + uv)
│   ├── gitea_wizard.py         # Interactive setup wizard
│   ├── gitea_setup.py          # Provision users, orgs, teams
│   ├── gitea_oauth.py          # Create OAuth2 applications
│   └── gitea_demo.py           # Create demo repository
├── demo-repo/                  # Demo repository template files
│   ├── main.py                 # FastAPI application
│   ├── pyproject.toml          # Python project config (uv)
│   ├── Dockerfile              # Docker build with uv
│   └── .woodpecker.yaml        # CI pipeline (clone, lint, test, build)
├── servers/                    # Automation tools
│   └── playwright/             # Browser automation
│       └── run.py              # Playwright CLI runner
├── config/
│   ├── init-db.sql             # PostgreSQL database init
│   ├── setup.toml.example      # User/org configuration template
│   └── Caddyfile.example       # Alternative reverse proxy config
├── docker-compose.yml
├── Justfile
└── .env.example
```

## Architecture

| Container     | Image                      | Description                                      |
|---------------|----------------------------|--------------------------------------------------|
| ci-traefik    | traefik:v3                 | Reverse proxy, routes `*.localhost` domains      |
| ci-postgres   | postgres:18                | Shared database for Gitea and Woodpecker         |
| gitea         | gitea/gitea:latest-rootless| Git server with webhook support                  |
| wpk-server    | woodpecker-server:v3       | CI coordinator (HTTP 8000, gRPC 9000)            |
| wpk-agent     | woodpecker-agent:v3        | Job runner using host Docker socket              |

All services communicate on `devnet` Docker network. PostgreSQL creates `gitea` and `woodpecker` databases on init via `config/init-db.sql`.

## Key Configuration Details

### Webhook Delivery (Gitea → Woodpecker)

Gitea must reach `ci.localhost` to deliver webhooks. This is configured via:
- `extra_hosts: ci.localhost:host-gateway` on the gitea container
- `GITEA__webhook__ALLOWED_HOST_LIST=external,loopback,private` to allow private IPs

### Pipeline Cloning (Internal Docker Network)

Pipeline containers can't resolve `gitea.localhost`. The demo pipeline uses a custom clone step:

```yaml
clone:
  - name: clone
    image: woodpeckerci/plugin-git
    settings:
      remote: http://gitea:3000/${CI_REPO}  # Docker network hostname
```

### Docker Builds (Trusted Repos)

To enable Docker socket access in pipelines:

1. Set `WOODPECKER_ADMIN=admin` in `.env` (matches Gitea username)
2. Restart Woodpecker to pick up admin setting
3. In Woodpecker UI: repo Settings → Trusted → enable **Volumes**
4. Pipeline can now mount `/var/run/docker.sock`

## Demo Pipeline (.woodpecker.yaml)

The demo repo includes a 4-step pipeline:

| Step | Image | Trigger | Description |
|------|-------|---------|-------------|
| `clone` | woodpeckerci/plugin-git | always | Clone via internal network |
| `lint` | ghcr.io/astral-sh/uv:python3.12-alpine | always | Run ruff linter |
| `test` | ghcr.io/astral-sh/uv:python3.12-alpine | always | Run tests with uv |
| `build` | docker:cli | manual/tag | Docker build (requires trusted) |

## Production Pipeline Template (.woodpecker.yml)

Multi-stage pipeline for Python projects deploying to Kubernetes:

- `lint_and_test`: Python 3.12 + uv + pytest
- `fetch_secrets_from_vault`: optional Vault integration
- `build_and_push_image`: Docker build/push
- `terraform_plan/apply`: infrastructure (push triggers plan, tags trigger apply)
- `helm_deploy`: Kubernetes deployment on tags

## Woodpecker Secrets

Configure in Woodpecker UI for pipeline:

- `registry_url`, `registry_username`, `registry_password`
- `vault_addr`, `vault_token` (if using Vault step)
- `aws_access_key_id`, `aws_secret_access_key` (for Terraform)
- `kubeconfig` (for Helm deploys)

## Caddy Alternative

Replace Traefik with Caddy using `config/Caddyfile.example`. Mount the Caddyfile in a Caddy service, expose ports 80/443. Caddy provides automatic HTTPS but doesn't use Docker labels.

## Browser Automation (Playwright)

For testing the web UIs, use the Playwright runner:

```bash
# Install browser (first time)
uv run --with playwright python -c "from playwright.__main__ import main; main()" install chromium

# Navigate and interact
uv run servers/playwright/run.py navigate "http://ci.localhost"
uv run servers/playwright/run.py snapshot    # Accessibility tree
uv run servers/playwright/run.py screenshot /tmp/test.png
uv run servers/playwright/run.py click "button"
```

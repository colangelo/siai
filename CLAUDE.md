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
just init           # Bootstrap .env from example, show setup steps
just secret         # Generate WOODPECKER_AGENT_SECRET
just oauth-help     # Show OAuth configuration instructions

just up             # Start all services
just down           # Stop all services
just restart        # Restart after .env changes
just status         # Show service status
just health         # Status + endpoint URLs

just logs           # Follow all logs
just logs-server    # Woodpecker server logs
just logs-agent     # Woodpecker agent logs

just clean          # Remove containers/networks
just clean-all      # Also remove volumes (destructive)
```

## Setup Flow

1. `just init` then `just secret` - create .env with generated agent secret
2. `just up` - start stack, visit `http://gitea.localhost` for first-time setup
3. `just oauth-help` - follow instructions to create Gitea OAuth app
4. Add OAuth credentials to `.env`, run `just restart`
5. Visit `http://ci.localhost`, login via Gitea, activate repos

## Architecture

| Container     | Image                      | Description                                      |
|---------------|----------------------------|--------------------------------------------------|
| ci-traefik    | traefik:v3                 | Reverse proxy, routes `*.localhost` domains      |
| ci-postgres   | postgres:18                | Shared database for Gitea and Woodpecker         |
| gitea         | gitea/gitea:latest-rootless| Git server with webhook support                  |
| wpk-server    | woodpecker-server:v3       | CI coordinator (HTTP 8000, gRPC 9000)            |
| wpk-agent     | woodpecker-agent:v3        | Job runner using host Docker socket              |

All services communicate on `devnet` Docker network. PostgreSQL creates `gitea` and `woodpecker` databases on init via `init-db.sql`.

## Pipeline Template (.woodpecker.yml)

Multi-stage pipeline for Python projects deploying to Kubernetes:

- `lint_and_test`: Python 3.12 + uv + pytest
- `fetch_secrets_from_vault`: optional Vault integration
- `build_and_push_image`: Docker build/push
- `terraform_plan/apply`: infrastructure (push triggers plan, tags trigger apply)
- `helm_deploy`: Kubernetes deployment on tags

Expected repo layout for pipeline:

- `app/` or `src/`: Python code with `pyproject.toml`
- `infra/terraform/`: Terraform modules
- `infra/helm/chart/`: Helm chart

## Woodpecker Secrets

Configure in Woodpecker UI for pipeline:

- `registry_url`, `registry_username`, `registry_password`
- `vault_addr`, `vault_token` (if using Vault step)
- `aws_access_key_id`, `aws_secret_access_key` (for Terraform)
- `kubeconfig` (for Helm deploys)

## Caddy Alternative

Replace Traefik with Caddy using `Caddyfile.example`. Mount the Caddyfile in a Caddy service, expose ports 80/443. Caddy provides automatic HTTPS but doesn't use Docker labels.

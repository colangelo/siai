# Project Context

## Purpose
Local OSS CI/CD stack: **Gitea + Woodpecker CI + Traefik** - a POC/template for self-hosted Git + CI pipelines with Docker-based execution.

## Tech Stack
- Docker Compose v2 (container orchestration)
- Traefik v3 (reverse proxy with Docker labels)
- Gitea (Git server, rootless image)
- Woodpecker CI v3 (CI/CD coordinator + agents)
- PostgreSQL 18 (shared database)
- Python ≥3.11 with PEP 723 scripts (automation)
- Just (task runner)

## Project Conventions

### Code Style
- Python: PEP 723 inline script metadata for standalone scripts (`uv run` compatible)
- Python: Use `httpx` for HTTP clients, `tomllib` (stdlib) for TOML
- Shell: Bash with `set -e` for error handling
- YAML: 2-space indentation for Docker Compose

### Architecture Patterns
- All services on single `devnet` Docker network
- PostgreSQL creates databases via `init-db.sql` on first boot
- Traefik routes `*.localhost` domains via Docker labels
- Sensitive values in `.env`, never committed
- Configuration templates in `config/` directory

### Testing Strategy
- Manual testing via `just health` and endpoint verification
- Scripts should support `--dry-run` mode for safe preview
- Idempotent operations (safe to run multiple times)

### Git Workflow
- Main branch: `main`
- Commit granularity: logical units of work
- Tags: semver (v0.1.0, v0.2.0, etc.)
- Changelog: CHANGELOG.md updated with each release

## Domain Context
- **Gitea**: Self-hosted Git service with GitHub-like features
- **Woodpecker CI**: Lightweight CI/CD system, Drone fork
- **OAuth2 flow**: Woodpecker authenticates users via Gitea OAuth
- **Confidential client**: OAuth apps with client secret (not PKCE-only)

## Important Constraints
- Use latest stable images only (no pinning to old versions)
- Python ≥3.11 required (for `tomllib` stdlib)
- macOS/Linux development (Docker Desktop or native Docker)
- Local development focus (`.localhost` domains)

## External Dependencies
- Docker Engine / Docker Desktop
- `uv` package manager for Python scripts
- `just` task runner
- `openssl` for secret generation

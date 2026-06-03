# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Agent context consolidated into `AGENTS.md`** — merged the split
  `CLAUDE.md` + `AGENTS.md` into a single canonical `AGENTS.md`; `CLAUDE.md` is now
  a symlink to it (git stores a real symlink, mode `120000`). omp (oh-my-pi) loads
  a repo-root `AGENTS.md` via its walk-up context-file provider but ignores a
  repo-root `CLAUDE.md`, so only the generic boilerplate `AGENTS.md` was loaded
  while the accurate `CLAUDE.md` (stack overview, commands, setup flow,
  architecture, registry, pipelines) was not. Canonical content is the former
  `CLAUDE.md`. The generic Codex "Repository Guidelines" scaffold was dropped —
  it was template boilerplate that contradicted the project's actual conventions
  (e.g. "add a Makefile" / "use venv" vs. this repo's Justfile + uv + Docker).
  Claude Code still resolves `CLAUDE.md` via the symlink.

## [0.4.5] - 2026-05-30

### Added

- **CI consumer onboarding** - formalize how a real repository gets built by the
  homelab CI/CD stack (Gitea → Woodpecker → Harbor):
  - `docs/onboard-ci-consumer.md` - end-to-end onboarding runbook: Gitea repo →
    Harbor project + `robot$siai-ci` scope (via the home-network agent relay) →
    Woodpecker activate + mark Trusted → registry secrets → tag-gated pipeline →
    trigger + verify.
  - `templates/.woodpecker.consumer.yml` - reusable pipeline template derived
    from Direction's proven pipeline (lint + test gate; tag-gated `build-push`
    to `harbor.cat-bluegill.ts.net/<project>/<image>:<tag>`; secrets via
    `from_secret`).
  - OpenSpec change `ci-consumer-onboarding` (new `ci-consumer-onboarding`
    capability). Reference consumer: `ac/direction`, CI-built through `v0.26.8`.
  - Scope: retroactive + template (documents the proven flow). Deferred: a second
    consumer and onboarding automation.

## [0.4.1] - 2026-05-28

### Added

- **Homelab deployment profile (px1)** - run the stack on a dedicated Proxmox VM,
  integrated with the homelab substrate; additive and non-breaking for the local
  `.localhost` quick-start:
  - `docker-compose.homelab.yml` - layered override: drops the bundled `postgres`
    + `traefik` (profile-gated `local-only`), points Gitea + Woodpecker at
    external **pg1** (LAN-direct `192.168.4.50`), `REGISTRY_BACKEND=harbor`,
    persistent data under `/data/siai`.
  - **Tailnet ingress + TLS** - two `tailscale/tailscale` sidecars
    (`network_mode: service:<app>`) serving `gitea.cat-bluegill.ts.net` +
    `ci.cat-bluegill.ts.net` over HTTPS (Let's Encrypt via Tailscale; tailnet-only,
    no Funnel). Gitea SSH deferred (HTTPS + PAT).
  - `config/homelab/serve-gitea.json`, `config/homelab/serve-ci.json` - Tailscale
    `serve` configs.
  - `.env.homelab.example` - template for external pg1/Harbor/tailnet wiring,
    sourced from 1Password (real `.env.homelab` gitignored).
  - **Gitea OIDC SSO** via the homelab **tsidp** identity provider; Woodpecker↔Gitea
    CI OAuth stays internal.
  - `deploy/homelab-runbook.md` - operator runbook for the live VM deploy.
  - OpenSpec change `openspec/changes/deploy-homelab-px1/` (proposal, design, spec,
    tasks) - deployed and verified live (22/26; smoke pipeline + interactive SSO
    pending).
- **Cross-repo agent relay** (`agent-relay/`) - file-based inbox for passing
  messages between repo agents (`home-network` / `siai` / `direction`); protocol
  in `agent-relay/AGENTS.md`.

### Changed

- **Gitea homelab data binding** - bind `/etc/gitea` + `/var/lib/gitea` to the
  `state` disk (not anonymous volumes) so repo data survives docker-storage
  changes on the VM.

### Documentation

- `docs/2026-05-30-forgejo-vs-gitea-migration-study.md` - deferred research record
  on a possible Forgejo migration (no transparent path from Gitea 1.26; risk audit
  + flank-then-replace plan).

## [0.4.0] - 2025-11-29

### Added

- **Harbor Container Registry** - Optional enterprise-grade registry:
  - `docker-compose.harbor.yml` - Harbor services (core, portal, registry, jobservice, redis)
  - `scripts/harbor_setup.py` - Automated project and robot account setup
  - `config/harbor/` - Configuration templates for Harbor services
  - `docs/HARBOR.md` - Comprehensive setup and usage guide
  - Trivy vulnerability scanner support (optional, via `HARBOR_TRIVY_ENABLED`)
- **Registry abstraction in pipelines**:
  - Demo pipeline now supports both Gitea and Harbor backends
  - Registry URL configurable via Woodpecker secrets
  - Backward compatible - defaults to Gitea registry
- **New Justfile commands**:
  - `just harbor-up` - Start Harbor services
  - `just harbor-down` - Stop Harbor services
  - `just harbor-setup` - Configure projects and robot accounts
  - `just harbor-login` - Docker login helper
  - `just registry-status` - Show active registry configuration
- **Environment variables** for Harbor:
  - `REGISTRY_BACKEND` - Select gitea or harbor
  - `HARBOR_ADMIN_PASSWORD` - Harbor admin credentials
  - `HARBOR_TRIVY_ENABLED` - Enable vulnerability scanning
  - `HARBOR_*_SECRET` - Internal service secrets

### Changed

- **Pipeline registry handling**:
  - Build/push steps now use `REGISTRY_URL` from secrets
  - Falls back to Gitea (`127.0.0.1`) if not configured
  - Supports both `gitea_token` and `registry_username/registry_password`
- **docker-up/restart/health** now include Harbor if `REGISTRY_BACKEND=harbor`
- **init-db.sql** creates `harbor` database alongside gitea/woodpecker

### Documentation

- Updated README with Harbor quick start
- Updated CLAUDE.md with Harbor architecture
- Updated PLATFORM-ACCESS.md with Harbor API guide

## [0.3.9] - 2025-11-29

### Added

- **Platform access documentation** (`docs/PLATFORM-ACCESS.md`):
  - Gitea API access with token authentication
  - Browser automation via Playwright for UI operations
  - Docker commands for container registry
  - Just commands for stack management
  - Network architecture and service URLs
  - Pipeline configuration examples

### Changed

- **Demo app simplified** - Removed complex signal handling workarounds:
  - Ctrl+C traceback is a known uvicorn/starlette cosmetic issue
  - App shuts down correctly, error logging is just noisy
  - See: https://github.com/Kludex/uvicorn/discussions/2368

### Documentation

- **ROADMAP.md updated**:
  - v0.4.0: Harbor Container Registry (new)
  - v0.5.0: Authentication & Access Configuration (was v0.4.0)
  - v0.5.1: Identity Provider Integration (was v0.4.1)
  - v0.6.0: Production Hardening (was v0.5.0)

## [0.3.8] - 2025-11-29

### Added

- **Container registry push** - Pipeline now pushes images to Gitea:
  - New `push` step uploads to Gitea container registry
  - Images available at `gitea.localhost/admin/-/packages`
  - Uses `gitea_token` secret for authentication
- **Traefik registry route** - Path-based routing for `/v2/*`:
  - Enables Docker push via `127.0.0.1` (HTTP insecure registry)
  - No Docker daemon configuration required

### Changed

- **Pipeline updated** with build+push workflow:
  - Build tags images as `127.0.0.1/admin/demo-app:${CI_COMMIT_SHA:0:8}`
  - Push uploads both commit SHA and `latest` tags
  - Uses Woodpecker v3 `environment.from_secret` syntax

## [0.3.7] - 2025-11-29

### Added

- **Docker build step** in demo pipeline (`.woodpecker.yaml`):
  - Optional `build` step runs on `manual` or `tag` events
  - Builds `demo-app:${CI_COMMIT_SHA:0:8}` image
  - Requires trusted repo with Volumes enabled
- **Playwright browser automation** (`servers/playwright/`):
  - `run.py` CLI for browser testing
  - Commands: navigate, snapshot, screenshot, click, type, eval
  - PEP 723 compatible, runs with `uv run`
- **WOODPECKER_ADMIN** env var in `.env.example` for admin user config

### Fixed

- **Webhook delivery** - Gitea can now reach `ci.localhost`:
  - Added `extra_hosts: ci.localhost:host-gateway` to gitea container
  - Added `private` to `GITEA__webhook__ALLOWED_HOST_LIST`
- **Pipeline cloning** - Custom clone step uses internal Docker network:
  - Clone URL: `http://gitea:3000/${CI_REPO}` (not `gitea.localhost`)
  - Pipeline containers can now fetch from Gitea

### Changed

- **Documentation updated** with:
  - Webhook configuration details
  - Internal clone URL setup
  - Docker build trust requirements
  - Playwright automation guide

## [0.3.6] - 2025-11-29

### Changed

- **Demo repository refactored** - Extracted to `demo-repo/` folder:
  - Template files now in `demo-repo/` instead of embedded in script
  - Migrated from `requirements.txt` to `pyproject.toml`
  - Uses [uv](https://docs.astral.sh/uv/) for package management
  - Dockerfile uses uv for fast dependency installation
  - CI pipeline uses `ghcr.io/astral-sh/uv` image for linting
  - Script loads files from folder with `--demo-dir` option
- **Project renamed** to SiAI, repo at `github.com/colangelo/siai`

## [0.3.5] - 2025-11-29

### Changed

- **Justfile recipe naming overhaul** - Clear, consistent naming convention:
  - Setup steps now numbered: `step1-init` through `step6-apply`
  - Added `quickstart` super-recipe for fully automated setup
  - All docker commands prefixed with `docker-`: `docker-up`, `docker-down`, `docker-restart`, `docker-logs`, `docker-status`, `docker-health`, `docker-clean`, `docker-clean-all`
  - `nuclear` kept as standalone command (full reset)
  - Removed all legacy aliases for cleaner `just --list` output
- Updated all documentation to use new command names

## [0.3.4] - 2025-11-29

### Added

- **Demo repository creation** (`just demo`) - Automated demo repository with:
  - `scripts/gitea_demo.py` - Python script for demo repository setup via Gitea API
  - FastAPI Python application (`main.py`) with `/` and `/health` endpoints
  - Multi-stage `Dockerfile` for optimized container builds
  - Woodpecker CI pipeline (`.woodpecker.yaml`) with lint, build, and test steps
  - `README.md` documentation for the demo app
- **New Justfile tasks**:
  - `just demo` - Create demo repository with CI pipeline
  - `just demo-dry-run` - Preview demo creation
  - `just demo-with-issues` - Create demo with sample issues
- **Sample issues** - Optional issue creation with `--create-issues` flag:
  - "Add unit tests" - Testing guidance
  - "Configure container registry push" - Registry integration guidance
- **Demo configuration** in `setup.toml`:
  - `[demo]` section for repo customization
  - `enabled`, `repo_name`, `repo_description` settings
  - Custom issue support via `[[demo.issues]]`
- Idempotent operation - safe to run multiple times

## [0.3.3] - 2025-11-29

### Added

- **Non-interactive wizard mode** - CLI arguments for scripted setup:
  - `--non-interactive` / `-n` flag for non-interactive mode
  - `--from-toml FILE` to load config from existing TOML backup
  - `--new-admin-username`, `--new-admin-email`, `--new-admin-password`
  - `--org-name`, `--org-description`, `--org-visibility`
  - `--team NAME:PERM:MEMBERS`, `--user NAME:EMAIL`
  - `--oauth-woodpecker`, `--oauth NAME:REDIRECT:TYPE`
  - `--overwrite` / `-y` to replace existing config without prompting

### Fixed

- **Traefik routing conflicts** - Added `docker.constraints` to only route containers from this compose project (prevents conflicts with other Traefik instances on the same Docker host)
- **OAuth credential detection** - `get_woodpecker_env()` now uses `docker inspect` instead of `printenv` (Woodpecker container is distroless with no shell)
- **Auto-restart Woodpecker** - Correctly detects stale OAuth credentials during bootstrap and restarts automatically
- **Shell env override** - Unset `WOODPECKER_GITEA_*` env vars before `docker compose` commands to ensure `.env` values are used

## [0.3.2] - 2025-11-29

### Added

- **`just nuclear`** - Full stack reset with config backups (☢️ emoji in help)
- **`QUICKSTART.md`** - Step-by-step bootstrap guide for new users
- **Safe password generator** in wizard (24-char alphanumeric, no special chars)
- Auto-save `WOODPECKER_AGENT_SECRET` to `.env` via `just secret`
- Auto-save OAuth credentials to `.env` via `just bootstrap`
- Auto-save generated admin password to `.env` via wizard
- Next steps guidance after `just bootstrap` and `just gitea-oauth`

### Changed

- Renamed `NEW_ADMIN_PASSWORD` to `NEW_GITEA_ADMIN_PASSWORD` for clarity
- Admin rename now uses correct Gitea API (`POST /admin/users/{username}/rename`)
- Setup scripts now export all env vars with `set -a`
- Wizard generates password automatically when "change password" is selected

### Fixed

- Admin rename failing silently (was using wrong API endpoint)
- Email/password update failing with 422 (missing required `login_name` field)
- Client credentials not updated after admin rename (caused 401 errors)
- Passwords with special chars causing shell escaping issues
- `just setup` not reading `NEW_GITEA_ADMIN_PASSWORD` from `.env`

## [0.3.1] - 2025-11-29

### Added

- **Interactive setup wizard** (`just wizard`) using Rich library
- Admin profile update support (rename, change email/password)
- Wizard loads defaults from `.env` file

## [0.3.0] - 2025-11-29

### Added

- **Python automation scripts** (PEP 723 compatible, run with `uv run`):
  - `scripts/gitea_setup.py` - Provision users, organizations, and teams
  - `scripts/gitea_oauth.py` - Create OAuth2 applications
- **TOML configuration** (`config/setup.toml`) for declarative Gitea setup:
  - Define users with `[[users]]` sections
  - Define organization with `[organization]` section
  - Define teams with `[[organization.teams]]` sections
- **New Justfile tasks**:
  - `just setup` - Apply configuration from setup.toml
  - `just setup-dry-run` - Preview changes without applying
  - `just gitea-oauth-bash` - Bash fallback for OAuth creation
- Dry-run mode (`--dry-run`) for safe preview of setup changes
- Idempotency - scripts skip existing resources safely

### Changed

- Reorganized project structure:
  - `init-db.sql` moved to `config/init-db.sql`
  - `Caddyfile.example` moved to `config/Caddyfile.example`
  - New `scripts/` directory for Python automation
- `just init` now also copies `config/setup.toml.example`
- `just gitea-oauth` now uses Python script (bash fallback available)
- Updated `docker-compose.yml` volume path for init-db.sql

### Deprecated

- `just gitea-oauth-bash` - Use `just gitea-oauth` (Python) instead

## [0.2.0] - 2025-11-29

### Added

- **PostgreSQL 18** as shared database for Gitea and Woodpecker
- **Automated setup** via Justfile tasks:
  - `just bootstrap` - full automated setup (init + OAuth)
  - `just gitea-init` - initialize Gitea DB and create admin user
  - `just gitea-oauth` - create OAuth2 app via Gitea API
- **Justfile** with commands for stack management, logs, health checks
- **CLAUDE.md** for AI assistant guidance
- Container naming convention: `ci-traefik`, `ci-postgres`, `wpk-server`, `wpk-agent`
- `extra_hosts` mapping for internal Gitea OAuth communication
- `GITEA__security__INSTALL_LOCK` to skip manual install wizard
- Comprehensive `.gitignore` for macOS, IDEs, secrets, Terraform, Python

### Changed

- Gitea image updated to `latest-rootless`
- Traefik updated to v3 (v3.6.2 with Docker 29 API fix)
- Woodpecker server now uses PostgreSQL instead of SQLite
- Database init via `init-db.sql` creates both `gitea` and `woodpecker` databases

### Fixed

- Traefik + Docker 29 API compatibility (requires Traefik 3.6.1+)
- Woodpecker healthcheck using built-in `ping` command
- OAuth2 app created as confidential client (fixes PKCE error)
- Shell env override issue with Justfile dotenv-load

## [0.1.0] - 2025-11-28

### Added

- Initial Docker Compose stack: Gitea + Woodpecker CI + Traefik
- `.woodpecker.yml` pipeline template for Python + K8s + Helm + Terraform
- Caddy alternative configuration (`Caddyfile.example`)
- Basic documentation in `README.md`

[0.4.5]: https://github.com/colangelo/siai/compare/v0.4.1...v0.4.5
[0.4.1]: https://github.com/colangelo/siai/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/colangelo/siai/compare/v0.3.9...v0.4.0
[0.3.9]: https://github.com/colangelo/siai/compare/v0.3.8...v0.3.9
[0.3.8]: https://github.com/colangelo/siai/compare/v0.3.7...v0.3.8
[0.3.7]: https://github.com/colangelo/siai/compare/v0.3.6...v0.3.7
[0.3.6]: https://github.com/colangelo/siai/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/colangelo/siai/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/colangelo/siai/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/colangelo/siai/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/colangelo/siai/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/colangelo/siai/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/colangelo/siai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/colangelo/siai/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/colangelo/siai/releases/tag/v0.1.0

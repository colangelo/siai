# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.3.6]: https://github.com/colangelo/siai/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/colangelo/siai/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/colangelo/siai/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/colangelo/siai/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/colangelo/siai/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/colangelo/siai/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/colangelo/siai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/colangelo/siai/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/colangelo/siai/releases/tag/v0.1.0

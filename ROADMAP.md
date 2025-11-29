# Roadmap

This document outlines the planned development phases for the CI/CD stack.

## v0.3.0 - Python Automation & Project Structure ✅

### Goals

- Automate Gitea organization and user creation via Python scripts
- Reorganize project structure for better maintainability
- Use TOML configuration file for declarative setup

### Project Structure

```txt
siai/
├── scripts/
│   ├── gitea_setup.py       # PEP 723 script: create org, users, teams
│   └── gitea_oauth.py       # PEP 723 script: create OAuth apps
├── config/
│   ├── init-db.sql          # PostgreSQL init (moved from root)
│   ├── setup.toml           # User/org configuration (see below)
│   ├── setup.toml.example   # Template for setup.toml
│   ├── gitea.env.example    # Gitea-specific env template
│   └── Caddyfile.example    # Alternative reverse proxy config
├── docker-compose.yml
├── .env.example
├── Justfile
├── CLAUDE.md
├── CHANGELOG.md
├── ROADMAP.md
└── README.md
```

### TOML Configuration Design

**File: `config/setup.toml`**

```toml
[gitea]
url = "http://gitea.localhost"

[admin]
username = "admin"
email = "admin@localhost"
# password from .env: GITEA_ADMIN_PASSWORD

[organization]
name = "myorg"
description = "Main development organization"
visibility = "public"  # or "private"

[[organization.teams]]
name = "developers"
permission = "write"  # read, write, admin
members = ["alice", "bob"]

[[organization.teams]]
name = "maintainers"
permission = "admin"
members = ["alice"]

[[users]]
username = "alice"
email = "alice@example.com"
# passwords generated or from env

[[users]]
username = "bob"
email = "bob@example.com"
```

### Python Scripts Design

**Technology choices:**

- PEP 723 inline script metadata (compatible with `uv run`)
- `httpx` for HTTP client (modern, async-capable)
- `tomllib` (stdlib since Python 3.11) for TOML parsing
- Type hints throughout
- No external Gitea SDK (direct API calls for transparency)
- Idempotency
- Fully scriptable

**Script: `scripts/gitea_setup.py`**

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
```

```txt
Features:
- Read configuration from config/setup.toml
- Create organization with configurable name/description
- Create users (non-admin) and add to organization
- Create teams within organization
- Assign users to teams with specific permissions
- Idempotent: safe to run multiple times
- Dry-run mode to preview changes
```

**Script: `scripts/gitea_oauth.py`**

```txt
Features:
- Create OAuth2 applications (confidential client)
- Output credentials in formats: env, json, shell export
- Replace current bash implementation in Justfile
```

### Justfile Updates

- Add `just setup` task calling Python scripts
- Keep bash tasks as fallbacks
- Update `just bootstrap` to use new scripts

### API Authentication Strategy

1. Initial setup uses basic auth (admin:password from .env)
2. Scripts can optionally create/use API tokens for subsequent calls
3. Tokens stored in `.env` or separate `.gitea-token` file (gitignored)

---

## v0.3.1 - Interactive Setup Wizard ✅

### Goals

- Add interactive terminal wizard for creating `config/setup.toml`
- Beautiful Rich-based UI with sensible defaults
- Lower barrier to entry for new users

### Features

- **Welcome screen** with project description
- **Guided prompts** for each configuration section:
  - Gitea URL (default: `http://gitea.localhost`)
  - Admin credentials (username, email)
  - Organization setup (optional): name, description, visibility
  - Team creation loop: name, permission level
  - User creation loop: username, email, team assignment
  - OAuth app configuration (Woodpecker defaults)
- **Summary table** before writing configuration
- **Overwrite protection** for existing `setup.toml`

### New Files

- `scripts/gitea_wizard.py` - Interactive wizard using Rich + tomli-w
- `just wizard` - Run the setup wizard

---

## v0.3.2 - Bootstrap UX & Bug Fixes ✅

### Goals

- Streamline bootstrap experience with auto-save to `.env`
- Fix admin rename and password change issues
- Add nuclear reset for fresh start testing

### Features

- **`just nuclear`** - Full stack reset with timestamped config backups
- **`QUICKSTART.md`** - Step-by-step guide for new users
- **Auto-save credentials** - Agent secret, OAuth, and generated passwords saved to `.env` automatically
- **Safe password generation** - 24-char alphanumeric passwords (no shell-problematic chars)
- **Next steps guidance** - Clear instructions after each bootstrap step

### Bug Fixes

- Admin rename now uses correct Gitea API endpoint (`POST /admin/users/{username}/rename`)
- Email/password PATCH includes required `login_name` field
- Client credentials updated after admin rename to prevent 401 errors
- Setup scripts export all env vars with `set -a`

### Breaking Changes

- `NEW_ADMIN_PASSWORD` renamed to `NEW_GITEA_ADMIN_PASSWORD`

---

## v0.3.3 - Non-Interactive Wizard & Traefik Isolation ✅

### Goals

- Enable scripted/automated setup via CLI arguments
- Fix Traefik routing conflicts in multi-project environments

### Features

- **Non-interactive wizard mode** - Full CLI argument support:
  - `--non-interactive` / `-n` for scripted setup
  - `--from-toml FILE` to load from existing TOML backup
  - All wizard options available as CLI flags
  - `--overwrite` / `-y` for automated config replacement

### Bug Fixes

- **Traefik routing conflicts** - Added `docker.constraints` to isolate routing to this compose project only
- **OAuth credential detection** - Use `docker inspect` instead of `printenv` (distroless containers)
- **Auto-restart Woodpecker** - Correctly detects and handles stale OAuth credentials
- **Shell env override** - Unset env vars before docker compose to ensure `.env` is used

---

## v0.3.4 - Demo Repository ✅

### Goals

- Provide a working demo repository after bootstrap
- Show users how Gitea and Woodpecker CI integrate
- Give new users a clear example of CI/CD pipeline structure

### Features

- **`just demo`** - Create demo repository via Gitea API:
  - FastAPI Python application (`main.py`)
  - Multi-stage Dockerfile for optimized builds
  - Woodpecker pipeline with lint, build, test steps
  - README documentation
- **`just demo-dry-run`** - Preview changes without applying
- **`just demo-with-issues`** - Also create sample issues
- **Optional issue creation** via `--create-issues` flag
- **Configurable** via `[demo]` section in setup.toml
- **Idempotent** - Safe to run multiple times

### New Files

- `scripts/gitea_demo.py` - Demo repository creation script (PEP 723)

---

## v0.3.5 - Justfile Recipe Naming Overhaul ✅

### Goals

- Improve discoverability and consistency of Justfile commands
- Make setup flow explicit with numbered steps
- Clearly separate docker commands from setup commands

### Changes

- **Numbered setup steps**: `step1-init`, `step2-secrets`, `step3-start`, `step4-configure`, `step5-demo`, `step6-apply`
- **Quickstart super-recipe**: `just quickstart` runs all setup steps automatically
- **Docker prefix**: All docker commands now start with `docker-`:
  - `docker-up`, `docker-down`, `docker-restart`
  - `docker-status`, `docker-health`
  - `docker-logs`, `docker-logs-gitea`, `docker-logs-server`, `docker-logs-agent`
  - `docker-clean`, `docker-clean-all`
- **Standalone commands**: `nuclear`, `wizard`, `oauth-help`, `open-gitea`, `open-ci`
- **No aliases**: Removed all legacy aliases for cleaner output

---

## v0.3.6 - Demo Repository Refactoring & uv Migration ✅

### Goals

- Extract demo repository templates to dedicated folder
- Migrate to uv for modern Python package management
- Improve maintainability of demo files

### Changes

- **`demo-repo/` folder** - Template files extracted from script:
  - `main.py` - FastAPI application
  - `pyproject.toml` - Project config (replaces requirements.txt)
  - `Dockerfile` - Uses uv for fast installs
  - `.woodpecker.yaml` - CI pipeline with uv image
  - `README.md` - Documentation with uv instructions
  - `issues.json` - Sample issues
- **uv integration**:
  - Dockerfile uses `ghcr.io/astral-sh/uv` for dependency installation
  - CI lint step uses `ghcr.io/astral-sh/uv:python3.12-alpine`
  - Local dev uses `uv sync` + `uv run`
- **Script updates**:
  - `gitea_demo.py` loads files from `demo-repo/` folder
  - New `--demo-dir` option to customize template location

---

## v0.4.0 - Authentication & Access Configuration

### Goals

- Add flexible authentication configuration wizard
- Support multiple security profiles (development → production)
- Enable SSO for Gitea and Woodpecker via external identity provider
- Fully idempotent, CLI-controllable scripts

### Authentication Wizard

New wizard to configure platform access with multiple security profiles:

**Security Profiles:**

| Profile | Auth | HTTPS | Use Case |
|---------|------|-------|----------|
| **local-dev** | None (current default) | No | Local development, quick testing |
| **local-secure** | Built-in Gitea auth | Self-signed TLS | Local with login required |
| **production-basic** | Built-in Gitea auth | Let's Encrypt | Simple production setup |
| **production-sso** | External IdP (OIDC) | Let's Encrypt | Enterprise SSO integration |

**CLI Interface:**

```bash
# Interactive wizard
just auth-wizard

# Non-interactive with CLI options
uv run scripts/auth_wizard.py \
  --profile production-basic \
  --domain git.example.com \
  --https \
  --cert-email admin@example.com \
  --non-interactive

# Apply existing config
uv run scripts/auth_wizard.py --from-toml config/auth.toml

# Dry-run to preview changes
uv run scripts/auth_wizard.py --profile local-secure --dry-run
```

**CLI Options:**

| Option | Description |
|--------|-------------|
| `--profile` | Security profile: `local-dev`, `local-secure`, `production-basic`, `production-sso` |
| `--domain` | Public domain (required for HTTPS profiles) |
| `--https` | Enable HTTPS (auto-selects cert method based on domain) |
| `--cert-method` | Certificate method: `letsencrypt`, `self-signed`, `custom` |
| `--cert-email` | Email for Let's Encrypt registration |
| `--idp` | Identity provider: `zitadel`, `authentik`, `keycloak` |
| `--idp-url` | External IdP URL (for existing deployments) |
| `--non-interactive` / `-n` | Run without prompts |
| `--from-toml FILE` | Load configuration from TOML file |
| `--dry-run` | Preview changes without applying |
| `--force` / `-y` | Overwrite existing configuration |

**Generated Configuration:**

- Updates `.env` with TLS and auth settings
- Creates/updates `config/auth.toml` for reproducibility
- Modifies `docker-compose.override.yml` for HTTPS labels
- Optionally provisions IdP container and configuration

**Idempotency:**

- Safe to run multiple times with same options
- Detects existing configuration and shows diff
- Backup existing config before changes
- Rollback support via timestamped backups

### New Files

- `scripts/auth_wizard.py` - Authentication configuration wizard (PEP 723)
- `config/auth.toml.example` - Authentication configuration template
- `docker-compose.override.yml.example` - HTTPS override example

### Justfile Updates

```bash
just auth-wizard           # Interactive authentication wizard
just auth-wizard-dry-run   # Preview authentication changes
just auth-apply            # Apply auth configuration from config/auth.toml
```

---

## v0.4.1 - Identity Provider Integration

### Goals

- Add external authentication provider (for `production-sso` profile)
- Integrate IdP with Gitea and Woodpecker

### Provider Options (evaluate)

| Provider | Pros | Cons |
|----------|------|------|
| **Zitadel** | Modern, K8s-native, OIDC-first | Newer, smaller community |
| **Authentik** | Feature-rich, good UI, active development | Python-based, heavier |
| **Keycloak** | Battle-tested, enterprise features | Java-based, resource-heavy |

### Implementation Plan

1. Add identity provider service to docker-compose.yml
2. Configure as OAuth2/OIDC source in Gitea
3. Configure Woodpecker to use same provider (or Gitea as proxy)
4. Update scripts to provision users/groups in IdP
5. Document SSO setup flow

### Database Considerations

- IdP may need its own database (or share PostgreSQL)
- Update `init-db.sql` to create additional database if needed

---

## v0.5.0 - Production Hardening

### Goals

- Secrets management improvements
- Backup/restore procedures
- Health monitoring

### Planned Features

- Docker secrets or external secrets manager integration
- `just backup` / `just restore` tasks for PostgreSQL
- Health monitoring and alerting hooks
- Resource limits and container hardening

---

## Future Considerations

### Potential Additions

- **Container Registry**: Harbor or Gitea's built-in registry
- **Artifact Storage**: MinIO for build artifacts and LFS
- **Monitoring**: Prometheus + Grafana stack
- **Log Aggregation**: Loki or similar

### Pipeline Enhancements

- Multi-architecture builds (ARM64 + AMD64)
- Caching strategies for faster builds
- Matrix builds for multiple Python versions

---

## Contributing

When implementing roadmap items:

1. Create feature branch from `main`
2. Update CHANGELOG.md with changes
3. Update CLAUDE.md if architecture changes
4. Tag releases following semver

---

*Last updated: 2025-11-29*

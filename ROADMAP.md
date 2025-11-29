# Roadmap

This document outlines the planned development phases for the CI/CD stack.

## v0.3.0 - Python Automation & Project Structure ✅

### Goals

- Automate Gitea organization and user creation via Python scripts
- Reorganize project structure for better maintainability
- Use TOML configuration file for declarative setup

### Project Structure

```txt
siai-sidi/
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

## v0.4.0 - Identity Provider Integration

### Goals

- Add external authentication provider
- Enable SSO for Gitea and Woodpecker

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

- TLS/HTTPS via reverse proxy + Let's Encrypt (or self-signed for local)
- Evaluate Caddy as alternative to Traefik
- Secrets management improvements
- Backup/restore procedures

### Reverse Proxy Evaluation

| Feature | Traefik | Caddy |
|---------|---------|-------|
| **Auto HTTPS** | ACME support | Built-in, simpler |
| **Config style** | Labels/API | Caddyfile |
| **Docker integration** | Native labels | Requires explicit config |
| **Performance** | High | High |
| **Complexity** | Higher | Lower |

Decision criteria:
- For Docker-native workflows: Traefik
- For simplicity and automatic HTTPS: Caddy

### Planned Features

- Reverse proxy ACME configuration for automatic certificates
- Docker secrets or external secrets manager integration
- `just backup` / `just restore` tasks for PostgreSQL
- Health monitoring and alerting hooks

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

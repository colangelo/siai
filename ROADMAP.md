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

## v0.4.0 - Harbor Container Registry

### Goals

- Add Harbor as enterprise-grade container registry
- Replace Gitea's built-in registry for production use
- Integrate with CI pipeline for image push/pull
- Vulnerability scanning and image signing

### Why Harbor?

| Feature | Gitea Registry | Harbor |
|---------|---------------|--------|
| **Vulnerability Scanning** | No | Yes (Trivy) |
| **Image Signing** | No | Yes (Notary/Cosign) |
| **Replication** | No | Yes (multi-registry) |
| **RBAC** | Basic | Fine-grained |
| **Garbage Collection** | Manual | Automated |
| **UI** | Minimal | Full-featured |
| **Helm Charts** | No | Yes |

### Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Traefik        │────▶│  Harbor      │     │  Woodpecker     │
│  registry.local │     │  (port 8080) │◀───▶│  Agent          │
└─────────────────┘     └──────────────┘     └─────────────────┘
                              │
                        ┌─────┴─────┐
                        │  Redis    │
                        │  (cache)  │
                        └───────────┘
```

### Implementation Plan

1. Add Harbor services to docker-compose.yml:
   - `harbor-core` - Main API and UI
   - `harbor-registry` - Docker registry backend
   - `harbor-db` - PostgreSQL (or share existing)
   - `harbor-redis` - Caching layer
   - `harbor-jobservice` - Async job processing
   - `harbor-trivy` - Vulnerability scanning (optional)

2. Configure Traefik routing:
   - `registry.localhost` → Harbor UI
   - `/v2/*` → Harbor registry API

3. Update pipeline to push to Harbor:
   - Replace `127.0.0.1/admin/demo-app` with `registry.localhost/library/demo-app`
   - Add Harbor robot account for CI

4. Create setup automation:
   - `scripts/harbor_setup.py` - Configure projects, users, robot accounts
   - Integration with existing wizard

### Configuration

**`config/setup.toml` additions:**

```toml
[harbor]
enabled = true
url = "http://registry.localhost"
admin_password_env = "HARBOR_ADMIN_PASSWORD"

[[harbor.projects]]
name = "library"
public = true

[[harbor.robot_accounts]]
name = "ci-pusher"
project = "library"
permissions = ["push", "pull"]
```

### Justfile Updates

```bash
just harbor-up              # Start Harbor services
just harbor-down            # Stop Harbor services
just harbor-setup           # Configure Harbor (projects, accounts)
just harbor-login           # Docker login to Harbor
```

### New Files

- `docker-compose.harbor.yml` - Harbor service definitions
- `scripts/harbor_setup.py` - Harbor automation (PEP 723)
- `config/harbor/` - Harbor configuration templates

---

## v0.5.0 - Authentication & Access Configuration

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

## v0.5.1 - Identity Provider Integration

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

## v0.6.0 - Production Hardening

### Goals

- Secrets management improvements
- Backup/restore procedures
- Health monitoring
- Automatic container updates

### Planned Features

- Docker secrets or external secrets manager integration
- `just backup` / `just restore` tasks for PostgreSQL
- Health monitoring and alerting hooks
- Resource limits and container hardening

### Watchtower Integration

Add [Watchtower](https://github.com/nicholas-fedor/watchtower) for automatic container image updates.

**Why Watchtower?**
- Automatically detects new container images in registries
- Gracefully restarts containers with updated images
- Maintains original deployment configuration
- Perfect for homelab/dev environments (our target use case)

**Implementation:**

```yaml
# docker-compose.yml addition
watchtower:
  image: ghcr.io/nicholas-fedor/watchtower:latest
  container_name: watchtower
  restart: unless-stopped
  environment:
    - WATCHTOWER_CLEANUP=true
    - WATCHTOWER_POLL_INTERVAL=86400  # Check daily
    - WATCHTOWER_INCLUDE_STOPPED=false
    - WATCHTOWER_LABEL_ENABLE=true    # Only update labeled containers
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  networks:
    - devnet
```

**Container Labeling:**

```yaml
# Enable auto-updates per container
labels:
  - "com.centurylinklabs.watchtower.enable=true"
```

**Configuration Options:**

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCHTOWER_POLL_INTERVAL` | 86400 | Check interval in seconds (daily) |
| `WATCHTOWER_CLEANUP` | true | Remove old images after update |
| `WATCHTOWER_LABEL_ENABLE` | true | Only update labeled containers |
| `WATCHTOWER_NOTIFICATIONS` | - | Slack/email/webhook notifications |
| `WATCHTOWER_SCHEDULE` | - | Cron schedule for updates |

**Justfile Commands:**

```bash
just watchtower-status    # Show update status
just watchtower-run       # Force immediate update check
just watchtower-logs      # View Watchtower logs
```

**Security Note:** Watchtower requires Docker socket access. For production, consider using Watchtower's HTTP API mode or socket proxy for additional security.

---

## v0.7.0 - Gitea CI Display Plugin for Woodpecker

### Goals

- Build a Gitea plugin to display Woodpecker CI pipelines directly in Gitea UI
- Provide unified view of code and CI status without switching tools
- Bridge the UX gap between Gitea and integrated CI providers like GitLab

### Why This Matters

Currently, users must switch between Gitea and Woodpecker UIs to see CI status. GitLab provides an integrated experience where pipelines, jobs, and logs are visible directly in the repository view. This plugin brings similar capabilities to Gitea + Woodpecker.

### Planned Features

**Phase 1: Pipeline Status Display**
- Show pipeline status badges on commit list
- Pipeline status on pull request pages
- Quick links to Woodpecker for full details

**Phase 2: Inline Pipeline View**
- Embedded pipeline visualization in Gitea UI
- Job status with expandable logs
- Re-run pipelines from Gitea interface

**Phase 3: Advanced Integration**
- Pre-step and post-step UI segments
- Problem matchers for inline error highlighting
- Annotations on code (like GitLab's inline CI feedback)

### Technical Approach

1. **Gitea Plugin API** - Use Gitea's plugin/extension mechanism
2. **Woodpecker API Integration** - Query Woodpecker API for pipeline data
3. **WebSocket for Live Updates** - Real-time status updates
4. **Shared Authentication** - Use existing OAuth for seamless access

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Gitea UI                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Repository View                                     │    │
│  │  ├── Commits (with pipeline badges)                  │    │
│  │  ├── Pull Requests (with CI status)                  │    │
│  │  └── CI/CD Tab ◄─────── NEW: Plugin adds this        │    │
│  │      ├── Pipeline History                            │    │
│  │      ├── Job Details + Logs                          │    │
│  │      └── Problem Annotations                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Woodpecker API │
                    │  (pipelines,    │
                    │   jobs, logs)   │
                    └─────────────────┘
```

### New Files

- `plugins/gitea-woodpecker/` - Plugin source code
- `plugins/gitea-woodpecker/README.md` - Plugin documentation
- `scripts/plugin_install.py` - Plugin installation automation

---

## v0.8.0 - Gitea CI UI Enhancements (Upstream Contributions)

### Goals

- Enhance Gitea's UI to display rich CI pipeline states from external CI systems
- Add missing UI features that GitLab has for displaying pipeline information
- Contribute enhancements upstream to Gitea project

### Context: Gitea Actions Limitations

Gitea Actions is still young compared to GitHub Actions or GitLab CI. Current limitations:

| Category | What's Missing |
|----------|----------------|
| **UI/UX** | Pre/post steps don't get special UI segments |
| **Annotations** | Problem matchers not supported (no inline error highlighting) |
| **Visualization** | No pipeline DAG view, limited job dependency display |
| **Logs** | Basic log rendering, no collapsible sections |
| **Artifacts** | Download only, no in-UI browser/preview |

These limitations affect **any external CI** (like Woodpecker) that reports status to Gitea, not just Gitea Actions.

### Missing UI Features (vs GitLab)

| Feature | GitLab | Gitea | Priority |
|---------|--------|-------|----------|
| **Pre/Post Steps UI** | ✓ Dedicated segments | ✗ Flat display | High |
| **Problem Matchers** | ✓ Inline annotations | ✗ Not supported | High |
| **Inline Error Highlighting** | ✓ Code annotations on diffs | ✗ Not supported | High |
| **Collapsible Log Sections** | ✓ `section_start/end` | ✗ Basic logs | Medium |
| **Job Artifacts Browser** | ✓ In-UI browsing | ✗ Download only | Medium |
| **Pipeline DAG View** | ✓ Visual graph | ✗ Linear list | Medium |
| **Environments/Deployments UI** | ✓ Dedicated view | ✗ Not supported | Low |

### Implementation Plan

**Phase 1: Annotations & Problem Matchers**

Extend Gitea's commit status API and UI to support annotations:

```go
// New annotation model for Gitea
type CommitStatusAnnotation struct {
    Path       string `json:"path"`        // File path
    Line       int    `json:"line"`        // Line number
    Column     int    `json:"column"`      // Column (optional)
    Severity   string `json:"severity"`    // error, warning, notice
    Message    string `json:"message"`     // Annotation text
    RawDetails string `json:"raw_details"` // Link to log line
}
```

- Add API endpoint: `POST /repos/{owner}/{repo}/statuses/{sha}/annotations`
- Display annotations inline on PR diff view
- Link annotations to CI log lines

**Phase 2: Enhanced Log Display**

Improve how Gitea displays CI logs (applicable to Actions and external CI):

1. **Collapsible Sections**
   - Parse `::group::name` / `::endgroup::` markers
   - Or GitLab-style `section_start` / `section_end`
   - Persist collapse state per user

2. **ANSI Color Rendering**
   - Full 256-color and truecolor support
   - Proper handling of cursor controls

3. **Pre/Post Step Visualization**
   - Visual distinction for setup, main, and teardown phases
   - Collapse/expand individual phases

**Phase 3: Pipeline Visualization**

1. **DAG View**
   - Visual graph of job dependencies
   - Real-time status updates on nodes
   - Click to navigate to job details

2. **Artifact Browser**
   - In-UI file tree for artifacts
   - Preview for text, images, HTML reports
   - Direct links to specific files

### API Extensions for External CI

To allow Woodpecker (or any CI) to provide rich data to Gitea:

```yaml
# Extended commit status payload
{
  "state": "success",
  "context": "woodpecker/build",
  "description": "Build passed",
  "target_url": "http://ci.localhost/...",

  # NEW: Rich CI data
  "annotations": [...],
  "steps": [
    {"name": "setup", "phase": "pre", "status": "success", "duration": 5},
    {"name": "build", "phase": "main", "status": "success", "duration": 120},
    {"name": "cleanup", "phase": "post", "status": "success", "duration": 2}
  ],
  "artifacts": [
    {"name": "coverage.html", "size": 12345, "url": "..."}
  ]
}
```

### Contribution Strategy

1. **Research Gitea Plugin/Extension API** - Understand current extensibility
2. **Propose RFC to Gitea** - Discuss annotation API and UI enhancements
3. **Implement as Gitea fork first** - Test with Woodpecker integration
4. **Submit upstream PRs** - Incremental, well-tested contributions
5. **Maintain compatibility layer** - Support older Gitea versions via plugin

### Related Gitea Issues to Track

- Gitea Actions feature parity with GitHub Actions
- External CI integration improvements
- Commit status API extensions
- UI/UX improvements for CI display

---

## Future Considerations

### Potential Additions

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

*Last updated: 2025-12-01*

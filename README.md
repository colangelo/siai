# OSS CI/CD Local Solution

Local POC stack: Gitea + Woodpecker CI, fronted by Traefik (or Caddy if you prefer). Use `.env.example` to create your own `.env` before starting.

## Quick Start

**Fully automated** (recommended):
```bash
just quickstart     # Does everything automatically
```

**Or step-by-step**:
```bash
just step1-init      # Create .env and config/setup.toml from examples
just step2-secrets   # Generate WOODPECKER_AGENT_SECRET
just step3-start     # Start all services
just step4-configure # Initialize Gitea + create OAuth app
just docker-restart  # Apply OAuth credentials
just step5-demo      # Create demo repository (optional)
```

Then visit:
- **Gitea**: http://gitea.localhost
- **Woodpecker**: http://ci.localhost (login via Gitea)

## Project Structure

```
siai/
├── scripts/                    # Python automation (PEP 723 + uv)
│   ├── gitea_wizard.py         # Interactive setup wizard
│   ├── gitea_setup.py          # Provision users, orgs, teams
│   ├── gitea_oauth.py          # Create OAuth2 applications
│   └── gitea_demo.py           # Create demo repository
├── config/
│   ├── init-db.sql             # PostgreSQL database init
│   ├── setup.toml.example      # User/org configuration template
│   └── Caddyfile.example       # Alternative reverse proxy config
├── docker-compose.yml
├── Justfile                    # Task runner
└── .env.example                # Environment template
```

## Interactive Setup Wizard

Use the interactive wizard to create your configuration:

```bash
just wizard             # Launch interactive setup wizard
```

The wizard guides you through:
- Gitea URL configuration
- Admin credentials
- Organization and team setup
- User creation with team assignment
- OAuth app configuration (Woodpecker)

## Declarative Setup (TOML Config)

Or manually define users, organizations, and teams in `config/setup.toml`:

```toml
[organization]
name = "myorg"
visibility = "public"

[[organization.teams]]
name = "developers"
permission = "write"
members = ["alice", "bob"]

[[users]]
username = "alice"
email = "alice@example.com"
```

Then run:
```bash
just setup              # Apply configuration
just setup-dry-run      # Preview changes without applying
```

## Commands

### Setup (run in order, or use `just quickstart`)

| Command | Description |
|---------|-------------|
| `just quickstart` | 🚀 Fully automated setup (does everything) |
| `just step1-init` | Initialize .env and config files |
| `just step2-secrets` | Generate agent secret |
| `just step3-start` | Start all services |
| `just step4-configure` | Initialize Gitea + create OAuth app |
| `just step5-demo` | Create demo repository (optional) |
| `just step6-apply` | Provision users/orgs from config/setup.toml (optional) |

### Stack Management

| Command | Description |
|---------|-------------|
| `just docker-up` | Start all services |
| `just docker-down` | Stop all services |
| `just docker-restart` | Restart after .env changes |
| `just docker-status` | Show service status |
| `just docker-health` | Status + endpoint URLs |
| `just docker-logs` | Follow all service logs |

### Tools

| Command | Description |
|---------|-------------|
| `just wizard` | Interactive setup wizard |
| `just nuclear` | Full reset with config backup |
| `just docker-clean-all` | Remove everything (destructive) |

## Caddy Alternative

Use `config/Caddyfile.example` as the reverse proxy if you prefer Caddy over Traefik. Swap the Traefik service in `docker-compose.yml` for a Caddy service that mounts that file.

## Pipeline Template

`.woodpecker.yml` contains a pipeline for Python lint/test, Docker build/push, Terraform plan/apply, and Helm deploy, with Vault and registry/K8s secrets expected as Woodpecker secrets.

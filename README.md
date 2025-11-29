# OSS CI/CD Local Solution

Local POC stack: Gitea + Woodpecker CI, fronted by Traefik (or Caddy if you prefer). Use `.env.example` to create your own `.env` before starting.

## Quick Start

```bash
just init           # Create .env and config/setup.toml from examples
just secret         # Generate WOODPECKER_AGENT_SECRET (add to .env)
just up             # Start all services
just bootstrap      # Initialize Gitea + create OAuth app
just restart        # Apply OAuth credentials
```

Then visit:
- **Gitea**: http://gitea.localhost
- **Woodpecker**: http://ci.localhost (login via Gitea)

## Project Structure

```
siai-sidi/
├── scripts/                    # Python automation (PEP 723 + uv)
│   ├── gitea_setup.py          # Provision users, orgs, teams
│   └── gitea_oauth.py          # Create OAuth2 applications
├── config/
│   ├── init-db.sql             # PostgreSQL database init
│   ├── setup.toml.example      # User/org configuration template
│   └── Caddyfile.example       # Alternative reverse proxy config
├── docker-compose.yml
├── Justfile                    # Task runner
└── .env.example                # Environment template
```

## Declarative Setup (TOML Config)

Define users, organizations, and teams in `config/setup.toml`:

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

| Command | Description |
|---------|-------------|
| `just init` | Initialize .env and config files |
| `just up` | Start all services |
| `just down` | Stop all services |
| `just restart` | Restart after .env changes |
| `just bootstrap` | Initialize Gitea + create OAuth app |
| `just setup` | Provision users/orgs from config/setup.toml |
| `just setup-dry-run` | Preview setup changes |
| `just health` | Show service status and endpoints |
| `just logs` | Follow all service logs |
| `just clean-all` | Remove everything (destructive) |

## Caddy Alternative

Use `config/Caddyfile.example` as the reverse proxy if you prefer Caddy over Traefik. Swap the Traefik service in `docker-compose.yml` for a Caddy service that mounts that file.

## Pipeline Template

`.woodpecker.yml` contains a pipeline for Python lint/test, Docker build/push, Terraform plan/apply, and Helm deploy, with Vault and registry/K8s secrets expected as Woodpecker secrets.

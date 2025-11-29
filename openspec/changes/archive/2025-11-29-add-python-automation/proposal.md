# Change: Add Python automation for Gitea setup

## Why

The current setup requires manual steps and bash scripts in Justfile for Gitea configuration (admin user creation, OAuth app setup). This is error-prone and hard to extend for multi-user/organization scenarios. A declarative TOML-based configuration with Python automation scripts will make setup reproducible, maintainable, and extensible.

## What Changes

- Add `scripts/` directory with PEP 723 Python scripts (`uv run` compatible)
- Add `config/` directory for configuration files
- Create `config/setup.toml` schema for declarative user/org/team configuration
- Implement `scripts/gitea_setup.py` for organization, user, and team provisioning
- Implement `scripts/gitea_oauth.py` for OAuth2 application management
- Move `init-db.sql` and `Caddyfile.example` to `config/` directory
- Update Justfile with new `just setup` task calling Python scripts

## Impact

- Affected specs: `gitea-automation` (new capability)
- Affected code:
  - `scripts/gitea_setup.py` (new)
  - `scripts/gitea_oauth.py` (new)
  - `config/setup.toml.example` (new)
  - `config/init-db.sql` (moved from root)
  - `config/Caddyfile.example` (moved from root)
  - `Justfile` (updated)
  - `docker-compose.yml` (path update for init-db.sql)

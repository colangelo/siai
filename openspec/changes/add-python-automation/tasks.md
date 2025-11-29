# Tasks

## 1. Project Structure
- [x] 1.1 Create `scripts/` directory
- [x] 1.2 Create `config/` directory
- [x] 1.3 Move `init-db.sql` to `config/init-db.sql`
- [x] 1.4 Move `Caddyfile.example` to `config/Caddyfile.example`
- [x] 1.5 Update `docker-compose.yml` volume path for init-db.sql

## 2. Configuration Schema
- [x] 2.1 Create `config/setup.toml.example` with full schema documentation
- [x] 2.2 Add `config/setup.toml` to `.gitignore`

## 3. Gitea Setup Script
- [x] 3.1 Implement `scripts/gitea_setup.py` with PEP 723 header
- [x] 3.2 Add TOML config parsing (tomllib)
- [x] 3.3 Implement user creation via Gitea API
- [x] 3.4 Implement organization creation via Gitea API
- [x] 3.5 Implement team creation and member assignment
- [x] 3.6 Add `--dry-run` flag for preview mode
- [x] 3.7 Add idempotency checks (skip existing resources)

## 4. OAuth Script
- [x] 4.1 Implement `scripts/gitea_oauth.py` with PEP 723 header
- [x] 4.2 Add OAuth2 app creation (confidential client)
- [x] 4.3 Support multiple output formats (env, json, shell)
- [x] 4.4 Add idempotency (check existing apps by name)

## 5. Justfile Integration
- [x] 5.1 Add `just setup` task calling gitea_setup.py
- [x] 5.2 Update `just gitea-oauth` to use gitea_oauth.py
- [x] 5.3 Update `just bootstrap` to use new scripts
- [x] 5.4 Keep bash fallbacks for environments without Python

## 6. Documentation
- [x] 6.1 Update README.md with new setup workflow
- [x] 6.2 Update CLAUDE.md with new project structure
- [x] 6.3 Update CHANGELOG.md for v0.3.0

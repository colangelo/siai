# Tasks: Add Harbor Container Registry

## 1. Infrastructure Setup

- [ ] 1.1 Update `config/init-db.sql` to create `harbor` database
- [ ] 1.2 Create `docker-compose.harbor.yml` with Harbor services:
  - harbor-core
  - harbor-registry
  - harbor-portal
  - harbor-jobservice
  - harbor-redis
  - harbor-trivy (optional, controlled by env var)
- [ ] 1.3 Add Traefik labels for `registry.localhost` routing
- [ ] 1.4 Update `.env.example` with Harbor variables:
  - `REGISTRY_BACKEND` (gitea/harbor)
  - `HARBOR_ADMIN_PASSWORD`
  - `HARBOR_DB_PASSWORD`
  - `HARBOR_TRIVY_ENABLED`
- [ ] 1.5 Create `config/harbor/` directory with configuration templates

## 2. Automation Scripts

- [ ] 2.1 Create `scripts/harbor_setup.py` (PEP 723) with:
  - Project creation
  - Robot account creation
  - Woodpecker secret configuration
- [ ] 2.2 Add `--dry-run` mode to harbor_setup.py
- [ ] 2.3 Update `config/setup.toml.example` with `[registry]` section
- [ ] 2.4 Integrate Harbor setup into existing wizard (optional path)

## 3. Pipeline Integration

- [ ] 3.1 Update `demo-repo/.woodpecker.yaml` to use registry abstraction:
  - Read `REGISTRY_URL` from secret or environment
  - Default to `127.0.0.1` (Gitea) if not set
- [ ] 3.2 Create `demo-repo/.woodpecker.harbor.yaml` example (optional)
- [ ] 3.3 Document secret configuration for both backends

## 4. Justfile Commands

- [ ] 4.1 Add `just harbor-up` - Start Harbor services
- [ ] 4.2 Add `just harbor-down` - Stop Harbor services
- [ ] 4.3 Add `just harbor-setup` - Configure Harbor (projects, accounts)
- [ ] 4.4 Add `just harbor-login` - Docker login helper
- [ ] 4.5 Add `just registry-status` - Show active registry info
- [ ] 4.6 Update `just quickstart` to handle `REGISTRY_BACKEND` variable

## 5. Documentation

- [ ] 5.1 Update `README.md` with Harbor section
- [ ] 5.2 Update `CLAUDE.md` with Harbor architecture
- [ ] 5.3 Update `docs/PLATFORM-ACCESS.md` with Harbor API access
- [ ] 5.4 Create `docs/HARBOR.md` with detailed setup guide
- [ ] 5.5 Update `CHANGELOG.md` for v0.4.0 release

## 6. Testing & Validation

- [ ] 6.1 Test `just quickstart` without Harbor (regression)
- [ ] 6.2 Test `just quickstart` with `REGISTRY_BACKEND=harbor`
- [ ] 6.3 Test demo pipeline push to Harbor
- [ ] 6.4 Test vulnerability scanning with Trivy enabled
- [ ] 6.5 Test switching between registries
- [ ] 6.6 Update `just docker-health` to include Harbor status

## Dependencies

- Task 1.1 must complete before 1.2 (database required)
- Task 2.1 depends on 1.2 (Harbor services running)
- Task 3.1 can be done in parallel with infrastructure
- Task 4.* depends on 1.2 and 2.1
- Task 5.* can be done in parallel with implementation
- Task 6.* requires all other tasks complete

## Parallelizable Work

The following can be worked on simultaneously:
- Infrastructure (1.*) and Documentation (5.*)
- Pipeline abstraction (3.1) and Justfile commands (4.*)

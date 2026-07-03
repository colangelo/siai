# Tasks: Add Harbor Container Registry

## 1. Infrastructure Setup

- [x] 1.1 Update `config/init-db.sql` to create `harbor` database
- [x] 1.2 Create `docker-compose.harbor.yml` with Harbor services:
  - harbor-core
  - harbor-registry
  - harbor-portal
  - harbor-jobservice
  - harbor-redis
  - harbor-trivy (optional, controlled by env var)
- [x] 1.3 Add Traefik labels for `registry.localhost` routing
- [x] 1.4 Update `.env.example` with Harbor variables:
  - `REGISTRY_BACKEND` (gitea/harbor)
  - `HARBOR_ADMIN_PASSWORD`
  - `HARBOR_DB_PASSWORD`
  - `HARBOR_TRIVY_ENABLED`
- [x] 1.5 Create `config/harbor/` directory with configuration templates

## 2. Automation Scripts

- [x] 2.1 Create `scripts/harbor_setup.py` (PEP 723) with:
  - Project creation
  - Robot account creation
  - Woodpecker secret configuration
- [x] 2.2 Add `--dry-run` mode to harbor_setup.py
- [x] 2.3 Update `config/setup.toml.example` with `[registry]` section
- [x] 2.4 Integrate Harbor setup into existing wizard (optional path) — DESCOPED, see notes

## 3. Pipeline Integration

- [x] 3.1 Update `demo-repo/.woodpecker.yaml` to use registry abstraction:
  - Read `REGISTRY_URL` from secret or environment
  - Default to `127.0.0.1` (Gitea) if not set
- [x] 3.2 Create `demo-repo/.woodpecker.harbor.yaml` example (optional) — DESCOPED, see notes
- [x] 3.3 Document secret configuration for both backends

## 4. Justfile Commands

- [x] 4.1 Add `just harbor-up` - Start Harbor services
- [x] 4.2 Add `just harbor-down` - Stop Harbor services
- [x] 4.3 Add `just harbor-setup` - Configure Harbor (projects, accounts)
- [x] 4.4 Add `just harbor-login` - Docker login helper
- [x] 4.5 Add `just registry-status` - Show active registry info
- [x] 4.6 Update `just quickstart` to handle `REGISTRY_BACKEND` variable

## 5. Documentation

- [x] 5.1 Update `README.md` with Harbor section
- [x] 5.2 Update `CLAUDE.md` with Harbor architecture
- [x] 5.3 Update `docs/PLATFORM-ACCESS.md` with Harbor API access
- [x] 5.4 Create `docs/HARBOR.md` with detailed setup guide
- [x] 5.5 Update `CHANGELOG.md` for v0.4.0 release

## 6. Testing & Validation

- [x] 6.1 Test `just quickstart` without Harbor (regression)
- [x] 6.2 Test `just quickstart` with `REGISTRY_BACKEND=harbor`
- [x] 6.3 Test demo pipeline push to Harbor
- [x] 6.4 Test vulnerability scanning with Trivy enabled
- [x] 6.5 Test switching between registries
- [x] 6.6 Update `just docker-health` to include Harbor status

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

## Implementation Notes

- Tasks 2.4 and 3.2 optional — DESCOPED for good (2026-07-04): the single
  registry-agnostic pipeline verified against both backends makes a separate
  Harbor pipeline example and a wizard path unnecessary
- Tasks 6.1-6.5 verified 2026-07-04 on the local stack (pipelines #3 push,
  #12 tag→Harbor incl. Trivy scan, #15 manual→Gitea registry). Verification
  surfaced and fixed real bugs: stale step4 container names, rootless-Gitea
  volume paths, Harbor v2.x auth plumbing (token cert, htpasswd, portal
  nginx, volume ownership, Traefik routing), demo pipeline YAML (colon in
  echo, tag events, hard-required secret, dollar-brace substitution)
- Task 6.6 completed as part of Justfile updates

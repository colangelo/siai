# Design: Harbor Container Registry Integration

## Context

The SiAI platform currently uses Gitea's built-in container registry, accessible at `127.0.0.1/v2/*` via Traefik routing. This works but lacks enterprise features. Harbor is the CNCF-graduated registry that provides vulnerability scanning, RBAC, replication, and more.

**Stakeholders**: DevOps engineers wanting production-ready container management
**Constraints**: Must remain optional, must not break existing Gitea registry workflow

## Goals / Non-Goals

### Goals
- Add Harbor as an optional, more powerful registry backend
- Maintain backward compatibility with Gitea registry
- Provide automated setup via Python scripts (consistent with existing patterns)
- Support vulnerability scanning via Trivy
- Enable pipeline abstraction to work with either registry

### Non-Goals
- Replace Gitea registry as default (it remains the simpler option)
- Harbor HA/clustering (single-node deployment only)
- Image replication to external registries (future consideration)
- Notary/Cosign integration (future consideration)

## Decisions

### Decision 1: Separate Compose File
**What**: Harbor services in `docker-compose.harbor.yml`, included conditionally
**Why**:
- Keeps main `docker-compose.yml` simple
- Harbor adds 5+ containers, would clutter the base file
- Compose v2 supports conditional includes via profiles or separate files

**Alternatives considered**:
- Docker Compose profiles: More complex, harder to understand
- Single monolithic file: Too large, harder to maintain

### Decision 2: Share PostgreSQL Instance
**What**: Harbor uses existing `ci-postgres` with separate database
**Why**:
- Reduces resource usage
- Consistent with existing pattern (Gitea + Woodpecker share postgres)
- Simplifies backup/restore

**Alternatives considered**:
- Separate PostgreSQL for Harbor: More isolation but double the resources
- Harbor's internal PostgreSQL: Harder to manage, backup

### Decision 3: Registry Backend Selection via Environment Variable
**What**: `REGISTRY_BACKEND=gitea|harbor` in `.env` controls which registry is active
**Why**:
- Simple, explicit configuration
- Works with existing `.env` pattern
- Easy to switch between backends

**Alternatives considered**:
- TOML configuration only: Less discoverable
- Auto-detection: Magic behavior, harder to debug

### Decision 4: Pipeline Registry Abstraction
**What**: Demo pipeline reads registry URL from Woodpecker secret or defaults to Gitea
**Why**:
- Single pipeline works with both backends
- No code duplication
- Easy migration path

**Implementation**:
```yaml
environment:
  REGISTRY_URL:
    from_secret: registry_url  # Set by harbor_setup.py or defaults to 127.0.0.1
```

### Decision 5: Harbor Services Subset
**What**: Deploy core Harbor services only, Trivy optional
**Why**:
- Full Harbor has 10+ containers (core, portal, registry, jobservice, redis, db, trivy, notary, chartmuseum, etc.)
- Start minimal, add components as needed

**Core services**:
- `harbor-core` - API and business logic
- `harbor-registry` - Docker registry backend
- `harbor-portal` - Web UI
- `harbor-jobservice` - Async jobs (GC, replication)
- `harbor-redis` - Caching (can use separate or share)

**Optional**:
- `harbor-trivy` - Vulnerability scanning

## Architecture

```
                                    ┌─────────────────────────────────┐
                                    │         Traefik                 │
                                    │    *.localhost routing          │
                                    └──────────┬──────────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
           ┌───────────────┐          ┌───────────────┐          ┌───────────────┐
           │ gitea.localhost│          │ ci.localhost  │          │registry.local │
           │    Gitea       │          │  Woodpecker   │          │   Harbor      │
           │   (port 3000)  │          │  (port 8000)  │          │  (port 8080)  │
           └───────┬───────┘          └───────────────┘          └───────┬───────┘
                   │                                                      │
                   │  ┌─────────────────────────────────────────────────┐ │
                   │  │              PostgreSQL                         │ │
                   └──►   gitea | woodpecker | harbor databases         ◄─┘
                      └─────────────────────────────────────────────────┘
                                               │
                      ┌────────────────────────┼────────────────────────┐
                      │                        │                        │
                      ▼                        ▼                        ▼
               ┌───────────┐            ┌───────────┐            ┌───────────┐
               │harbor-core│            │harbor-reg │            │harbor-job │
               │   (API)   │            │ (storage) │            │ (async)   │
               └───────────┘            └───────────┘            └───────────┘
```

## Traefik Routing

| Route | Backend | Notes |
|-------|---------|-------|
| `gitea.localhost` | Gitea:3000 | Git + Gitea registry |
| `ci.localhost` | Woodpecker:8000 | CI/CD |
| `registry.localhost` | Harbor:8080 | Harbor UI + API |
| `registry.localhost/v2/*` | Harbor registry | Docker push/pull |

**When Harbor is disabled**: `127.0.0.1/v2/*` routes to Gitea (current behavior)
**When Harbor is enabled**: `registry.localhost/v2/*` routes to Harbor

## File Structure

```
siai/
├── docker-compose.yml              # Base services (unchanged)
├── docker-compose.harbor.yml       # Harbor services (new)
├── config/
│   ├── setup.toml.example          # Add [registry] section
│   ├── init-db.sql                 # Add harbor database
│   └── harbor/                     # Harbor config templates (new)
│       └── harbor.yml.template
├── scripts/
│   └── harbor_setup.py             # Harbor automation (new)
├── demo-repo/
│   └── .woodpecker.yaml            # Registry abstraction
└── .env.example                    # Add HARBOR_* vars
```

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Harbor adds complexity | Medium | Keep it optional, document clearly |
| Resource usage increase | Medium | Document requirements, use shared PostgreSQL |
| Two registries confusing | Low | Clear documentation, status command |
| Harbor version updates | Low | Use official images, test upgrades |

## Migration Plan

### For existing users (no action required)
- Default remains Gitea registry
- Existing workflows unchanged

### To enable Harbor
1. Set `REGISTRY_BACKEND=harbor` in `.env`
2. Run `just docker-restart` (includes Harbor compose)
3. Run `just harbor-setup` (creates projects, robot accounts)
4. Update Woodpecker secret `registry_url` to `registry.localhost`

### Rollback
1. Set `REGISTRY_BACKEND=gitea` in `.env`
2. Run `just docker-restart`
3. Images in Harbor remain accessible but new pushes go to Gitea

## Open Questions

1. **Redis sharing**: Should Harbor share Redis with other services or have dedicated instance?
   - Recommendation: Dedicated Redis for Harbor (isolation)

2. **Storage backend**: Local filesystem or S3-compatible?
   - Recommendation: Local filesystem for local dev, document S3 for production

3. **Trivy database updates**: How to handle vulnerability DB updates?
   - Recommendation: Document manual update process, auto-update in future

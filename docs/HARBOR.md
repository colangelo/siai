---
type: guide
title: "Harbor container registry"
description: "Setup and operation of the optional Harbor registry backend (REGISTRY_BACKEND=harbor): architecture, projects/robot accounts, Trivy scanning, and switching between Gitea and Harbor registries."
tags: [harbor, registry, trivy]
timestamp: 2025-11-29
---

# Harbor Container Registry

Harbor is an optional enterprise-grade container registry that can replace Gitea's built-in registry. It provides vulnerability scanning, RBAC, image signing, and more.

## Quick Start

```bash
# 1. Enable Harbor in .env
sed -i 's/REGISTRY_BACKEND=gitea/REGISTRY_BACKEND=harbor/' .env

# 2. Start Harbor services
just harbor-up

# 3. Configure projects and robot accounts
just harbor-setup

# 4. Access Harbor UI
open http://registry.localhost
```

Default credentials: `admin` / `Harbor12345` (or `HARBOR_ADMIN_PASSWORD` from `.env`)

## When to Use Harbor

| Feature | Gitea Registry | Harbor |
|---------|---------------|--------|
| Basic push/pull | ✓ | ✓ |
| Web UI | Basic | Full-featured |
| Vulnerability scanning | ✗ | ✓ (Trivy) |
| Fine-grained RBAC | ✗ | ✓ |
| Robot accounts | ✗ | ✓ |
| Image replication | ✗ | ✓ |
| Garbage collection | Manual | Automated |
| Resource usage | Low | Medium-High |

**Use Gitea registry when:** You want simplicity and minimal resource usage.

**Use Harbor when:** You need vulnerability scanning, robot accounts for CI, or enterprise features.

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Enable Harbor
REGISTRY_BACKEND=harbor

# Harbor admin password
HARBOR_ADMIN_PASSWORD=Harbor12345

# Internal secrets (generate with: openssl rand -hex 16)
HARBOR_CORE_SECRET=your-secret-here
HARBOR_JOBSERVICE_SECRET=your-secret-here
HARBOR_REGISTRY_SECRET=your-secret-here

# Optional: Enable Trivy vulnerability scanner
HARBOR_TRIVY_ENABLED=true
```

### TOML Configuration

Configure projects and robot accounts in `config/setup.toml`:

```toml
[registry]
backend = "harbor"

[registry.harbor]
url = "http://registry.localhost"

# Projects (namespaces for images)
[[registry.harbor.projects]]
name = "library"
public = true

[[registry.harbor.projects]]
name = "ci"
public = false

# Robot accounts for CI automation
[[registry.harbor.robot_accounts]]
name = "ci"
projects = ["library", "ci"]
permissions = ["push", "pull"]
```

## Commands

| Command | Description |
|---------|-------------|
| `just harbor-up` | Start Harbor services |
| `just harbor-down` | Stop Harbor services (preserves data) |
| `just harbor-setup` | Configure projects and robot accounts |
| `just harbor-setup-dry-run` | Preview setup changes |
| `just harbor-login` | Docker login to Harbor |
| `just registry-status` | Show active registry info |

## Architecture

```
                         ┌─────────────────────────┐
                         │       Traefik           │
                         │  registry.localhost     │
                         └───────────┬─────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│  harbor-portal  │        │   harbor-core   │        │ harbor-registry │
│   (Web UI)      │        │   (API/Logic)   │        │   (Storage)     │
│   :8080         │        │   :8080         │        │   :5000         │
└─────────────────┘        └────────┬────────┘        └─────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │ harbor-redis │ │  PostgreSQL  │ │harbor-trivy  │
           │  (Cache)     │ │  (harbor DB) │ │ (Optional)   │
           └──────────────┘ └──────────────┘ └──────────────┘
```

## Pushing Images

### From Local Machine

```bash
# Login to Harbor
just harbor-login

# Build and push
docker build -t registry.localhost/library/myapp:v1.0 .
docker push registry.localhost/library/myapp:v1.0
```

### From CI Pipeline

Configure Woodpecker secrets:

| Secret | Value |
|--------|-------|
| `registry_url` | `registry.localhost` |
| `registry_username` | `robot$ci` (from `just harbor-setup`) |
| `registry_password` | Token from robot account creation |

The demo pipeline automatically uses these secrets when available.

## Vulnerability Scanning

When `HARBOR_TRIVY_ENABLED=true`:

1. Images are automatically scanned after push
2. View results in Harbor UI → Project → Repository → Image → Vulnerabilities
3. Configure scan policies in Project → Configuration

### Pipeline Integration (Optional)

Add a step to fail builds on critical vulnerabilities:

```yaml
- name: check-vulnerabilities
  image: curlimages/curl
  commands:
    - |
      # Wait for scan to complete
      sleep 30
      # Query Harbor API for scan results
      RESULT=$(curl -sf "http://registry.localhost/api/v2.0/projects/library/repositories/myapp/artifacts/${CI_COMMIT_SHA:0:8}?with_scan_overview=true" \
        -u "admin:${HARBOR_ADMIN_PASSWORD}")
      # Check for critical vulnerabilities
      CRITICAL=$(echo "$RESULT" | grep -o '"Critical":[0-9]*' | cut -d: -f2)
      if [ "$CRITICAL" -gt 0 ]; then
        echo "Found $CRITICAL critical vulnerabilities!"
        exit 1
      fi
```

## Troubleshooting

### Harbor won't start

```bash
# Check service status
just docker-health

# View Harbor logs
docker compose -f docker-compose.yml -f docker-compose.harbor.yml logs harbor-core

# Verify database
docker exec ci-postgres psql -U postgres -c "\l" | grep harbor
```

### Can't push images

```bash
# Check registry status
just registry-status

# Verify login works
just harbor-login

# Check Docker daemon configuration
docker info | grep -A5 "Insecure Registries"
```

### Trivy not scanning

```bash
# Verify Trivy is enabled
grep HARBOR_TRIVY_ENABLED .env

# Check Trivy container
docker logs harbor-trivy

# Trivy needs to download vulnerability DB on first run (~5 minutes)
```

## Migration

### From Gitea to Harbor

1. Pull existing images from Gitea registry
2. Enable Harbor (`REGISTRY_BACKEND=harbor`)
3. Run `just harbor-up && just harbor-setup`
4. Re-tag and push images to Harbor
5. Update Woodpecker secrets

### Rollback to Gitea

1. Set `REGISTRY_BACKEND=gitea` in `.env`
2. Run `just docker-restart`
3. Images in Harbor remain but new pushes go to Gitea

## Resource Requirements

| Component | Memory | CPU |
|-----------|--------|-----|
| harbor-core | 512MB | 0.5 |
| harbor-portal | 128MB | 0.1 |
| harbor-registry | 256MB | 0.2 |
| harbor-jobservice | 256MB | 0.2 |
| harbor-redis | 128MB | 0.1 |
| harbor-trivy | 1GB | 0.5 |

**Total:** ~1.3GB without Trivy, ~2.3GB with Trivy

## Security Considerations

1. **Change default passwords** - Update `HARBOR_ADMIN_PASSWORD` in `.env`
2. **Generate secrets** - Use `openssl rand -hex 16` for `HARBOR_*_SECRET` values
3. **Use robot accounts** - Don't use admin credentials in CI pipelines
4. **Enable HTTPS** - For production, configure TLS in Traefik

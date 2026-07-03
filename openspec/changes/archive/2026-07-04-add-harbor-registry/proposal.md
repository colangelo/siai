# Change: Add Harbor Container Registry as Optional Component

## Why

The current setup uses Gitea's built-in container registry, which works for basic workflows but lacks enterprise features like vulnerability scanning, image signing, fine-grained RBAC, and automated garbage collection. Harbor provides these capabilities while maintaining the same developer experience for push/pull operations.

Making Harbor **optional** ensures the quick-start experience remains simple (Gitea registry works out of the box), while power users can enable Harbor for production-grade container management.

## What Changes

### New Capabilities
- **Container Registry Backend Selection** - Choose between Gitea (default) or Harbor
- **Harbor Service Deployment** - Separate compose file for Harbor services
- **Harbor Automation** - Python script for project/robot account setup
- **Pipeline Registry Abstraction** - Demo pipeline supports both registry backends
- **Vulnerability Scanning** - Optional Trivy integration with Harbor

### Configuration Additions
- `[registry]` section in `config/setup.toml` for registry backend selection
- `HARBOR_*` environment variables in `.env`
- `docker-compose.harbor.yml` for Harbor services
- `config/harbor/` directory for Harbor-specific templates

### Justfile Updates
- `just registry-status` - Show active registry info
- `just harbor-up` / `just harbor-down` - Manage Harbor services
- `just harbor-setup` - Configure Harbor projects and robot accounts
- `just harbor-login` - Docker login helper

### **NOT** Breaking
- Existing Gitea registry setup continues to work unchanged
- Default behavior remains Gitea registry (zero config change required)
- Demo pipeline auto-detects registry backend

## Impact

- **Affected specs**: New `container-registry` capability, modified `ci-pipeline`
- **Affected code**:
  - `docker-compose.yml` - Add optional include for Harbor
  - `docker-compose.harbor.yml` - New file
  - `demo-repo/.woodpecker.yaml` - Registry abstraction
  - `scripts/harbor_setup.py` - New file
  - `config/setup.toml.example` - Registry section
  - `.env.example` - Harbor variables
  - `Justfile` - Harbor commands

## Success Criteria

1. `just quickstart` still works with Gitea registry (no Harbor)
2. `just quickstart` with `REGISTRY_BACKEND=harbor` deploys full Harbor stack
3. Demo pipeline pushes to correct registry based on configuration
4. Harbor UI accessible at `http://registry.localhost`
5. Vulnerability scanning works when enabled

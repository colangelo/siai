# Proposal: Add Demo Repository

## Why

After running `just bootstrap` and `just setup`, users have an empty Gitea instance with no repositories. There's no immediate way to verify the CI integration works without manually creating a repository and pipeline configuration. New users don't have a clear example of how to structure a project for Woodpecker CI.

## What Changes

- Add `scripts/gitea_demo.py` - Python script to create demo repository via Gitea API
- Demo repository includes:
  - `main.py` - FastAPI hello-world application
  - `requirements.txt` - Python dependencies
  - `Dockerfile` - Multi-stage container build
  - `.woodpecker.yaml` - CI pipeline (lint, build, test)
  - `README.md` - Usage documentation
- Add `[demo]` section to `config/setup.toml.example` for configuration
- Add Justfile tasks: `just demo`, `just demo-dry-run`
- Support optional issue creation with `--create-issues` flag

## Impact

- Affected specs: demo-repository (new capability)
- New files: `scripts/gitea_demo.py`
- Modified files: `Justfile`, `config/setup.toml.example`
- No breaking changes

## Alternatives Considered

1. **Git push-to-create**: Push pre-existing files via git CLI
   - Rejected: Requires git in path, harder to customize

2. **SQL database seeding**: Insert data directly into PostgreSQL
   - Rejected: Fragile, bypasses git, no actual repo content

3. **Pre-baked Docker volume**: Ship volume with demo data
   - Rejected: Large images, stale data, version conflicts

**Decision**: Use Gitea API for repo creation and file upload - cleanest approach using official APIs.

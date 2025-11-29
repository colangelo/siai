# Tasks: Add Demo Repository

## Overview
Create automated demo repository with Python app, Dockerfile, and Woodpecker pipeline.

## Task List

### Phase 1: Core Script

- [x] **T1: Create `scripts/gitea_demo.py` skeleton**
  - PEP 723 header with `httpx` dependency
  - Argument parser with `--dry-run`, `--config`, `--create-issues`
  - GiteaClient class (reuse pattern from gitea_setup.py)
  - Main function structure
  - **Validation**: Script runs with `--help`

- [x] **T2: Implement repository creation**
  - Check if repo exists (GET `/api/v1/repos/{owner}/{repo}`)
  - Create repo in org (POST `/api/v1/orgs/{org}/repos`) or user (POST `/api/v1/user/repos`)
  - Handle 409 Conflict (repo exists) gracefully
  - **Validation**: Running script creates empty repo in Gitea

- [x] **T3: Implement file upload**
  - Base64 encode file content
  - POST to `/api/v1/repos/{owner}/{repo}/contents/{filepath}`
  - Batch multiple files in single commit using correct API
  - Handle existing files (check SHA, update if different)
  - **Validation**: Demo files appear in repo after script runs

### Phase 2: Demo Application Files

- [x] **T4: Create demo application templates**
  - `main.py` - FastAPI hello-world with `/` and `/health` endpoints
  - `requirements.txt` - fastapi, uvicorn
  - `Dockerfile` - Multi-stage build for small image
  - `.woodpecker.yaml` - lint + build + test-container steps
  - `README.md` - Description and usage instructions
  - Store as Python string templates or files in `config/demo/`
  - **Validation**: Templates render correctly with variable substitution

- [x] **T5: Implement template rendering**
  - Support variable substitution (`{repo_name}`, `{org_name}`)
  - Load templates from embedded strings or external files
  - **Validation**: Generated files have correct content

### Phase 3: Issue Creation

- [x] **T6: Implement issue creation**
  - POST to `/api/v1/repos/{owner}/{repo}/issues`
  - Check if issue with same title exists (skip if so)
  - Support labels if available
  - Create sample issues: "Add unit tests", "Configure registry push"
  - **Validation**: Issues appear in Gitea issue tracker

### Phase 4: Configuration Integration

- [x] **T7: Add demo configuration to setup.toml**
  - `[demo]` section with `enabled`, `repo_name`, `repo_description`
  - `[[demo.issues]]` array for custom issues
  - Update `setup.toml.example` with demo section
  - **Validation**: Config loads and parses correctly

- [x] **T8: Add Justfile task**
  - `just demo` - Run demo repository creation
  - `just demo-dry-run` - Preview what would be created
  - Add to `just --list` output
  - **Validation**: `just demo` works end-to-end

### Phase 5: Documentation & Testing

- [x] **T9: Update documentation**
  - Add demo section to README.md
  - Update QUICKSTART.md with demo step
  - Add to CLAUDE.md command reference
  - **Validation**: Documentation accurate and complete

- [x] **T10: End-to-end test**
  - Run full flow: `nuclear` → `init` → `up` → `bootstrap` → `wizard` → `setup` → `demo`
  - Verify pipeline triggers in Woodpecker
  - Verify issues created in Gitea
  - **Validation**: Complete flow works for new user

### Phase 6: Release

- [x] **T11: Update CHANGELOG and ROADMAP**
  - Add v0.3.4 section with demo feature
  - Mark `add-demo-repository` as complete in OpenSpec
  - **Validation**: Documentation ready for release

## Dependencies

```
T1 ─────┬───▶ T2 ───▶ T3 ───▶ T10
        │
T4 ◀────┴───▶ T5 ───▶ T3
        │
T6 ◀────┘
        │
T7 ◀────┴───▶ T8 ───▶ T10
        │
T9 ◀────┘
```

- T1-T3 can proceed in sequence (core functionality)
- T4-T5 can be done in parallel with T1 (template work)
- T6 depends on T2 (need repo to create issues)
- T7-T8 can be done after T3 (config integration)
- T9 should happen throughout
- T10 is final validation
- T11 after T10 passes

## Estimated Complexity

| Task | Complexity | Notes |
|------|------------|-------|
| T1 | Low | Boilerplate, reuse existing patterns |
| T2 | Low | Single API call with error handling |
| T3 | Medium | Multi-file upload, SHA handling |
| T4 | Low | Simple file templates |
| T5 | Low | String formatting |
| T6 | Low | Simple API call |
| T7 | Low | TOML section addition |
| T8 | Low | Two-line Justfile recipe |
| T9 | Low | Documentation updates |
| T10 | Medium | Full integration test |
| T11 | Low | Changelog entries |

**Total**: ~3-4 hours implementation time

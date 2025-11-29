# Demo Repository Capability

## ADDED Requirements

### Requirement: System SHALL create demo repository via Gitea API

The system SHALL create a demo repository in Gitea with a working Python application and CI pipeline when `just demo` is executed.

#### Scenario: Create demo repository in organization
- **Given** Gitea is initialized and an organization exists in setup.toml
- **When** the user runs `just demo`
- **Then** a repository named "demo-app" is created in the organization
- **And** the repository contains main.py, Dockerfile, .woodpecker.yaml, README.md
- **And** the files are committed with message "Initial commit: Add demo application"

#### Scenario: Create demo repository for user (no organization)
- **Given** Gitea is initialized but no organization is configured
- **When** the user runs `just demo`
- **Then** a repository named "demo-app" is created under the admin user
- **And** the repository contains all demo files

#### Scenario: Skip existing repository
- **Given** a repository named "demo-app" already exists
- **When** the user runs `just demo`
- **Then** the script reports "Repository already exists, skipping creation"
- **And** existing files are updated only if content differs

---

### Requirement: Demo repository SHALL contain minimal Python application

The demo repository SHALL contain a minimal Python application demonstrating CI/CD integration.

#### Scenario: Demo application files
- **Given** the demo repository is created
- **Then** it contains:
  - `main.py` with FastAPI endpoints (/ and /health)
  - `requirements.txt` with fastapi and uvicorn
  - `Dockerfile` with multi-stage Python build
  - `.woodpecker.yaml` with lint, build, and test steps
  - `README.md` with usage instructions

#### Scenario: Woodpecker pipeline executes successfully
- **Given** the demo repository is created and activated in Woodpecker
- **When** Woodpecker triggers the pipeline
- **Then** the lint step passes (ruff check)
- **And** the build step creates a Docker image
- **And** the test-container step verifies the container responds on /health

---

### Requirement: System SHALL optionally create sample issues

The system SHALL optionally create sample issues in the demo repository when requested.

#### Scenario: Create sample issues
- **Given** the demo repository exists
- **And** `--create-issues` flag is provided
- **When** the user runs `just demo --create-issues`
- **Then** issues are created: "Add unit tests", "Configure container registry push"
- **And** issues have appropriate descriptions

#### Scenario: Skip existing issues
- **Given** an issue titled "Add unit tests" already exists
- **When** the user runs `just demo --create-issues`
- **Then** the existing issue is not duplicated
- **And** the script reports "Issue already exists, skipping"

---

### Requirement: Demo settings SHALL be configurable via setup.toml

The demo repository settings SHALL be configurable via the `[demo]` section in setup.toml.

#### Scenario: Configure demo repository name
- **Given** setup.toml contains `[demo]` with `repo_name = "my-demo"`
- **When** the user runs `just demo`
- **Then** the repository is created with name "my-demo"

#### Scenario: Disable demo creation
- **Given** setup.toml contains `[demo]` with `enabled = false`
- **When** the user runs `just demo`
- **Then** the script reports "Demo creation disabled in config"
- **And** no repository is created

---

### Requirement: Script SHALL support dry-run mode

The script SHALL support `--dry-run` mode to preview changes without applying them.

#### Scenario: Preview demo creation
- **Given** Gitea is initialized
- **When** the user runs `just demo-dry-run`
- **Then** the script outputs what would be created
- **And** no repository or files are actually created in Gitea

---

### Requirement: Justfile SHALL provide demo tasks

The Justfile SHALL provide tasks for demo repository management.

#### Scenario: Run just demo
- **Given** the Justfile contains the demo recipe
- **When** the user runs `just demo`
- **Then** the gitea_demo.py script is executed with proper environment

#### Scenario: Run just demo-dry-run
- **Given** the Justfile contains the demo-dry-run recipe
- **When** the user runs `just demo-dry-run`
- **Then** the gitea_demo.py script is executed with `--dry-run` flag

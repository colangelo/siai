# container-registry Specification

## Purpose

Container registry management for storing and distributing Docker images built by CI pipelines.

## ADDED Requirements

### Requirement: Registry Backend Selection
The system SHALL support multiple container registry backends selectable via configuration.

#### Scenario: Gitea registry (default)
- **WHEN** `REGISTRY_BACKEND` is not set or set to `gitea`
- **THEN** the system uses Gitea's built-in container registry
- **AND** images are pushed to `127.0.0.1/<owner>/<repo>:<tag>`
- **AND** no additional services are started

#### Scenario: Harbor registry
- **WHEN** `REGISTRY_BACKEND` is set to `harbor`
- **THEN** the system deploys Harbor services via `docker-compose.harbor.yml`
- **AND** images are pushed to `registry.localhost/<project>/<repo>:<tag>`
- **AND** Harbor UI is accessible at `http://registry.localhost`

### Requirement: Harbor Service Deployment
The system SHALL deploy Harbor as a set of Docker Compose services when enabled.

#### Scenario: Start Harbor services
- **WHEN** user runs `just harbor-up` or `just docker-up` with `REGISTRY_BACKEND=harbor`
- **THEN** the following containers are started:
  - `harbor-core` (API and business logic)
  - `harbor-registry` (Docker registry backend)
  - `harbor-portal` (Web UI)
  - `harbor-jobservice` (Async job processing)
  - `harbor-redis` (Caching)
- **AND** Harbor uses the shared PostgreSQL database (`harbor` database)

#### Scenario: Optional Trivy scanner
- **WHEN** `HARBOR_TRIVY_ENABLED=true` in `.env`
- **THEN** `harbor-trivy` container is started
- **AND** vulnerability scanning is available for pushed images

#### Scenario: Stop Harbor services
- **WHEN** user runs `just harbor-down`
- **THEN** all Harbor containers are stopped
- **AND** data volumes are preserved

### Requirement: Harbor Project Management
The system SHALL support automated creation of Harbor projects for organizing images.

#### Scenario: Create public project
- **WHEN** `harbor_setup.py` is run with project configuration in setup.toml
- **THEN** project is created via Harbor API `POST /api/v2.0/projects`
- **AND** project visibility is set according to configuration (public/private)

#### Scenario: Project already exists
- **WHEN** project with same name already exists
- **THEN** script skips creation and logs "Project {name} already exists"
- **AND** script continues with remaining configuration

### Requirement: Harbor Robot Account Management
The system SHALL support automated creation of robot accounts for CI authentication.

#### Scenario: Create robot account for CI
- **WHEN** `harbor_setup.py` is run with robot account configuration
- **THEN** robot account is created via Harbor API `POST /api/v2.0/robots`
- **AND** robot has specified permissions (push, pull)
- **AND** robot token is output for Woodpecker secret configuration

#### Scenario: Configure Woodpecker secret
- **WHEN** robot account is created successfully
- **THEN** script offers to create/update Woodpecker secret `registry_url`
- **AND** secret contains the Harbor registry URL

### Requirement: Harbor Automation Script
The system SHALL provide a PEP 723 compatible Python script for Harbor setup.

#### Scenario: Run Harbor setup
- **WHEN** user executes `uv run scripts/harbor_setup.py` or `just harbor-setup`
- **THEN** script reads configuration from `config/setup.toml` `[registry.harbor]` section
- **AND** creates projects and robot accounts as specified

#### Scenario: Dry run mode
- **WHEN** user runs `harbor_setup.py --dry-run`
- **THEN** script outputs planned actions without making API calls
- **AND** displays what projects and accounts would be created

### Requirement: Registry Status Command
The system SHALL provide a command to display the active registry configuration.

#### Scenario: Show registry status
- **WHEN** user runs `just registry-status`
- **THEN** script displays:
  - Active registry backend (gitea/harbor)
  - Registry URL for pushes
  - Whether Harbor services are running (if harbor backend)
  - Available projects/namespaces

### Requirement: Traefik Routing for Harbor
The system SHALL configure Traefik to route Harbor traffic correctly.

#### Scenario: Harbor UI routing
- **WHEN** Harbor is enabled and user navigates to `http://registry.localhost`
- **THEN** Traefik routes request to `harbor-portal:8080`
- **AND** Harbor web interface is displayed

#### Scenario: Harbor registry API routing
- **WHEN** Docker client makes request to `registry.localhost/v2/*`
- **THEN** Traefik routes to `harbor-registry:5000`
- **AND** Docker push/pull operations work correctly

### Requirement: Configuration Schema Extension
The system SHALL extend `setup.toml` with registry configuration section.

#### Scenario: Registry configuration in TOML
- **WHEN** user creates `config/setup.toml` with `[registry]` section
- **THEN** configuration supports:
  - `backend` - Registry type (gitea/harbor)
  - `[registry.harbor]` - Harbor-specific settings
  - `[[registry.harbor.projects]]` - Project definitions
  - `[[registry.harbor.robot_accounts]]` - Robot account definitions

#### Scenario: Default configuration
- **WHEN** `[registry]` section is absent from setup.toml
- **THEN** system defaults to Gitea registry backend
- **AND** no Harbor services are started

## ADDED Requirements

### Requirement: TOML Configuration Schema
The system SHALL support a TOML configuration file (`config/setup.toml`) that defines Gitea resources declaratively.

#### Scenario: Valid configuration file
- **WHEN** user creates `config/setup.toml` with gitea url, admin credentials, organization, teams, and users sections
- **THEN** the configuration is parseable by Python's `tomllib`
- **AND** all required fields are validated before API calls

#### Scenario: Missing configuration file
- **WHEN** user runs setup script without `config/setup.toml`
- **THEN** script exits with clear error message pointing to `config/setup.toml.example`

### Requirement: User Provisioning
The system SHALL create Gitea users from TOML configuration via the Gitea API.

#### Scenario: Create new user
- **WHEN** user entry exists in `[[users]]` section with username and email
- **THEN** script creates non-admin user via `POST /api/v1/admin/users`
- **AND** password is read from environment variable `{USERNAME}_PASSWORD` or generated

#### Scenario: User already exists
- **WHEN** user with same username already exists in Gitea
- **THEN** script skips creation and logs "User {username} already exists"
- **AND** script continues with remaining users

### Requirement: Organization Provisioning
The system SHALL create Gitea organizations from TOML configuration.

#### Scenario: Create organization
- **WHEN** `[organization]` section defines name, description, and visibility
- **THEN** script creates organization via `POST /api/v1/orgs`
- **AND** organization uses specified visibility (public/private)

#### Scenario: Organization already exists
- **WHEN** organization with same name already exists
- **THEN** script skips creation and logs "Organization {name} already exists"

### Requirement: Team Management
The system SHALL create teams within organizations and assign members.

#### Scenario: Create team with members
- **WHEN** `[[organization.teams]]` entry defines name, permission, and members list
- **THEN** script creates team via `POST /api/v1/orgs/{org}/teams`
- **AND** script adds each member via `PUT /api/v1/teams/{id}/members/{username}`

#### Scenario: Team member not found
- **WHEN** team member username does not exist as Gitea user
- **THEN** script logs warning "User {username} not found, skipping team assignment"
- **AND** script continues with remaining members

### Requirement: OAuth Application Management
The system SHALL create OAuth2 applications for CI integration.

#### Scenario: Create OAuth app for Woodpecker
- **WHEN** user runs oauth script with app name and redirect URI
- **THEN** script creates confidential OAuth2 client via `POST /api/v1/user/applications/oauth2`
- **AND** script outputs client_id and client_secret

#### Scenario: OAuth app already exists
- **WHEN** OAuth app with same name already exists
- **THEN** script reports existing app credentials or skips with message

### Requirement: Dry Run Mode
The system SHALL support a dry-run mode that previews changes without making API calls.

#### Scenario: Dry run execution
- **WHEN** user runs script with `--dry-run` flag
- **THEN** script outputs planned actions (create user X, create org Y, etc.)
- **AND** no API calls are made to Gitea

### Requirement: PEP 723 Script Compatibility
Scripts SHALL use PEP 723 inline metadata for dependency declaration.

#### Scenario: Run script with uv
- **WHEN** user executes `uv run scripts/gitea_setup.py`
- **THEN** uv installs dependencies from script header (httpx)
- **AND** script executes successfully

## ADDED Requirements

### Requirement: Interactive Setup Wizard
The system SHALL provide an interactive terminal wizard that guides users through creating `config/setup.toml` with sensible defaults and Rich-formatted UI.

#### Scenario: Run wizard for first-time setup
- **WHEN** user runs `uv run scripts/gitea_wizard.py` or `just wizard`
- **THEN** wizard displays welcome panel with project description
- **AND** prompts for each configuration section with defaults shown

#### Scenario: Gitea URL configuration
- **WHEN** wizard prompts for Gitea URL
- **THEN** default value `http://gitea.localhost` is shown
- **AND** user can press Enter to accept default or type custom URL

#### Scenario: Organization setup
- **WHEN** wizard asks "Do you want to create an organization?"
- **THEN** user can choose Yes/No
- **AND** if Yes, wizard prompts for name, description, and visibility

#### Scenario: Team creation loop
- **WHEN** user has created an organization
- **THEN** wizard offers to add teams
- **AND** for each team, prompts for name and permission level (read/write/admin)
- **AND** continues until user chooses "Done adding teams"

#### Scenario: User creation loop
- **WHEN** wizard reaches user section
- **THEN** wizard offers to add users
- **AND** for each user, prompts for username and email
- **AND** if organization exists, offers to assign user to teams
- **AND** continues until user chooses "Done adding users"

#### Scenario: Configuration summary
- **WHEN** all prompts are complete
- **THEN** wizard displays Rich Table summarizing all configuration
- **AND** asks for confirmation before writing file

#### Scenario: Overwrite protection
- **WHEN** `config/setup.toml` already exists
- **THEN** wizard warns user and asks for confirmation before overwriting
- **AND** user can choose to cancel and keep existing file

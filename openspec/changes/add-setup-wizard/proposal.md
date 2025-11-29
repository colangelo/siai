# Change: Add interactive setup wizard with Rich UI

## Why

Creating `config/setup.toml` manually requires reading documentation and understanding TOML syntax. An interactive wizard with sensible defaults and clear prompts will make initial setup faster and less error-prone, especially for new users.

## What Changes

- Add `scripts/gitea_wizard.py` - Interactive setup wizard using Rich library
- Wizard guides user through configuration with nice terminal UI:
  - Gitea URL (default: http://gitea.localhost)
  - Admin credentials
  - Organization setup (optional)
  - Team creation with permissions
  - User creation
  - OAuth app configuration
- Generates valid `config/setup.toml` from user input
- Add `just wizard` task to run the wizard
- Update documentation

## Impact

- Affected specs: `gitea-automation` (extends existing capability)
- Affected code:
  - `scripts/gitea_wizard.py` (new)
  - `Justfile` (add wizard task)
  - `README.md` (document wizard)

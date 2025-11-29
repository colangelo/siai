# Tasks

## 1. Setup Wizard Script
- [x] 1.1 Create `scripts/gitea_wizard.py` with PEP 723 header (rich dependency)
- [x] 1.2 Implement welcome screen with Rich Panel
- [x] 1.3 Add Gitea URL prompt with default value
- [x] 1.4 Add admin credentials section (username, email)
- [x] 1.5 Add organization setup wizard (name, description, visibility)
- [x] 1.6 Add team creation loop (name, permission, skip option)
- [x] 1.7 Add user creation loop (username, email, assign to teams)
- [x] 1.8 Add OAuth app configuration (Woodpecker defaults)
- [x] 1.9 Generate and write setup.toml with tomli-w
- [x] 1.10 Show summary with Rich Table before writing
- [x] 1.11 Add confirmation prompt before overwriting existing file

## 2. Justfile Integration
- [x] 2.1 Add `just wizard` task

## 3. Documentation
- [x] 3.1 Update README.md with wizard usage
- [x] 3.2 Update CLAUDE.md commands section

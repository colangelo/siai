# Tasks

## 1. Setup Wizard Script
- [ ] 1.1 Create `scripts/gitea_wizard.py` with PEP 723 header (rich dependency)
- [ ] 1.2 Implement welcome screen with Rich Panel
- [ ] 1.3 Add Gitea URL prompt with default value
- [ ] 1.4 Add admin credentials section (username, email)
- [ ] 1.5 Add organization setup wizard (name, description, visibility)
- [ ] 1.6 Add team creation loop (name, permission, skip option)
- [ ] 1.7 Add user creation loop (username, email, assign to teams)
- [ ] 1.8 Add OAuth app configuration (Woodpecker defaults)
- [ ] 1.9 Generate and write setup.toml with tomli-w
- [ ] 1.10 Show summary with Rich Table before writing
- [ ] 1.11 Add confirmation prompt before overwriting existing file

## 2. Justfile Integration
- [ ] 2.1 Add `just wizard` task

## 3. Documentation
- [ ] 3.1 Update README.md with wizard usage
- [ ] 3.2 Update CLAUDE.md commands section

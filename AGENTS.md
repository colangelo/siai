<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Repository Guidelines

## Project Structure & Module Organization
- Keep all executable code in `src/` with clear subpackages per domain (e.g., `src/api/`, `src/services/`, `src/lib/`).
- Place automated tests in `tests/` mirroring the `src/` layout; add fixtures under `tests/fixtures/`.
- Store CLI or maintenance helpers in `scripts/`; keep them executable and self-documented (`--help`).
- Track design docs and runbooks in `docs/`; include architecture notes and decision records.

## Build, Test, and Development Commands
- Add a Makefile early with standard targets; once present, use `make setup` (bootstrap deps), `make lint`, `make test`, and `make format`.
- Prefer local virtual envs (`python -m venv .venv && source .venv/bin/activate`) or language-specific env tooling; avoid global installs.
- For quick smoke runs during development, provide a `make dev` or `npm run dev` entry that starts the primary service with hot reload if applicable.

## Coding Style & Naming Conventions
- Use 2 or 4 space indentation consistently per language norms; avoid tabs unless required by tooling.
- Favor clear, descriptive module and file names (`user_service.py`, `queue_client.ts`) over abbreviations.
- Keep public interfaces documented with concise docstrings or comments; avoid inline comments for obvious code.
- Add formatter and linter configuration (`ruff`, `eslint`, `prettier`, or equivalents) at the repo root; run them before pushing.

## Testing Guidelines
- Mirror production entry points with integration tests; isolate core logic with fast unit tests.
- Name tests descriptively (`test_handles_empty_payload`, `test_user_creation_happy_path`); group related cases in files that match the module under test.
- Aim for meaningful coverage of critical paths rather than a numeric target; add regression tests for every bug fix.
- Provide example data in `tests/fixtures/` and keep it small to stay fast in CI.

## Commit & Pull Request Guidelines
- Write commits in imperative present tense (`Add auth middleware`, `Refactor queue client`); keep them scoped and reviewable.
- Reference related issues in PR descriptions; include a brief summary, testing notes, and any risks or rollout steps.
- Attach screenshots or logs when changes affect output or UX; note migrations or config changes explicitly.

## Security & Configuration Tips
- Keep secrets out of the repo; use `.env.example` to document required variables and load them via environment management tools.
- Validate inputs and handle error paths defensively; log sensitive data sparingly and redact by default.
- Review dependency updates for security advisories; pin versions in lockfiles and update regularly.

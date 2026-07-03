# siai — loop runbook

This repo IS the CI platform: the **Gitea + Woodpecker (+ Harbor) compose
stack**, its Python automation, and its ops docs. It is not an application
codebase — work here means editing compose files, PEP 723 scripts, Justfile
recipes, and docs. Two deployment shapes share the same base file: the local
`.localhost` POC (`docker-compose.yml`, Traefik + bundled postgres) and the
homelab px1 / VM 107 deployment (`docker-compose.homelab.yml` override —
tailnet sidecars, pg1 database, deployed by home-network's
`deploy-homelab-px1`, NOT from here).

## Docs entry point

All project knowledge is navigable from **`docs/index.md`** (an OKF bundle:
every doc carries YAML frontmatter with a required `type`; the index is
generated). Start there — do not glob the repo. `AGENTS.md` is the repo
operating manual (canonical; `CLAUDE.md` is a symlink to it).

## Conventions the gate enforces

- `just check` = `just lint` (ruff over `scripts/`, `servers/`, `demo-repo/`)
  + `just docs-check` (OKF conformance) + `just compose-check` (every compose
  layering must pass `docker compose config`) + `just test` (pytest over
  `evals/`).
- After adding or renaming a doc, regenerate the index: `just docs-index`.
- Every new/edited doc in `docs/` MUST have YAML frontmatter (`type` required).

## Conventions the gate cannot enforce (follow them anyway)

- **Never start the stack or touch live infra.** No `docker compose up`, no
  `just docker-*`/`harbor-*`/`step*` recipes, no tailnet calls
  (`*.cat-bluegill.ts.net`), no Gitea/Woodpecker API calls. The loop runs
  unattended; compose changes are validated by `just compose-check` only, and
  the homelab is deployed exclusively via home-network's `deploy-homelab-px1`.
- Python automation is **PEP 723 + uv** (`# /// script` metadata, run with
  `uv run`); every mutating script keeps `--dry-run` support.
- Secrets stay out of the repo — reference 1Password item titles (vault
  `AC-DevOps`), never values. `.env` files are gitignored; examples live in
  `.env.example` / `.env.homelab.example`.
- `docker-compose.homelab.yml` uses compose `!reset`/`!override` merge tags
  (needs compose ≥ 2.24) and MUST keep
  `WOODPECKER_FORCE_IGNORE_SERVICE_FAILURE=true` in the wpk-server env (an
  eval guards this — relay ask 2026-06-19).
- The Justfile deliberately does NOT `set dotenv-load` (shell env would
  override `.env` inside docker compose) — don't add it.
- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, scope in
  parentheses; `relay:` for agent-relay archival), granular per logical unit.

## Evals (T1)

T1 evals are plain **pytest** files using only the standard library (+
`pyyaml`, provided by the run command) — they assert on repo *files and
structure*: a compose service has an env var or volume, a doc exists and its
frontmatter parses, a script declares PEP 723 metadata, a Justfile recipe
exists. No network, no Docker daemon, no subprocesses that reach the stack.
Style example (see `evals/test_repo_sanity.py`):

```python
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent

def test_homelab_pins_gitea_sidecar_ip():
    text = (REPO / "docker-compose.homelab.yml").read_text()
    assert "gitea.cat-bluegill.ts.net" in text
```

For compose-file assertions, parse with the `!reset`/`!override`-tolerant
loader pattern from `evals/test_repo_sanity.py` rather than raw
`yaml.safe_load`.

# Onboard a repository to siai CI/CD

How to onboard a real (non-demo) repository to the homelab CI/CD stack — Gitea →
Woodpecker → Harbor on px1 (VM 107, shipped in v0.4.1). Build + push only; deploy
stays consumer-owned. Follow the steps in order; each is verifiable.

> **Reference consumer:** `ac/direction`. It is onboarded and CI-built end-to-end
> (push → lint+test gate; tag → `harbor.cat-bluegill.ts.net/direction/{api,web,mcp}`),
> shipping through tag **`v0.26.8`**. Its live `.woodpecker.yml` is the canonical
> example; this runbook is the generalization of what made it work.

## Prerequisites

- The homelab stack is up (`homelab-deployment` capability): Gitea
  `gitea.cat-bluegill.ts.net`, Woodpecker `ci.cat-bluegill.ts.net`, agent on
  VM 107, Harbor `harbor.cat-bluegill.ts.net`, `robot$siai-ci`.
- You are a Woodpecker **admin** (`WOODPECKER_ADMIN`) — required to mark repos Trusted.
- The agent can reach Harbor: `docker-compose.homelab.smoke.yml` pins Harbor's
  tailnet IP into the agent's `WOODPECKER_BACKEND_DOCKER_EXTRA_HOSTS` (tracked in
  v0.4.1). No per-consumer change needed.

## Steps

### 1. Gitea repository

The repo must live in Gitea (`gitea.cat-bluegill.ts.net`) so Woodpecker can
receive its webhooks. Push an existing repo or create one under your user/org.
Add the `gitea` remote and push:

```bash
git remote add gitea https://gitea.cat-bluegill.ts.net/<owner>/<repo>.git
git push -u gitea main
```

### 2. Harbor project + robot scope — via infra relay (home-network)

Each consumer pushes to its own Harbor **project**, and `robot$siai-ci` needs
push/pull on it. siai does **not** provision Harbor — request it from infra
through the agent relay. Drop a message in `home-network/agent-relay/inbox/`
(schema: `agent-relay/AGENTS.md`). Worked example — the `siai` project ask:

```markdown
---
date: <date -Iseconds>
from_repo: siai
from_agent: <you>
to_repo: home-network
to_agent: infra
subject: Harbor — create project `<project>` and add it to robot$siai-ci scope
status: new
---
## Action requested
1. Create a Harbor project `<project>` (private) on harbor.cat-bluegill.ts.net.
2. Add push+pull on `<project>` to the existing robot `robot$siai-ci`
   (re-scope it; do NOT mint a new robot).
## Context
Onboarding `<owner>/<repo>` to siai CI; it needs a registry push target.
## Refs
- robot: 1P `harbor - siai-ci robot` (vault AC-DevOps), user `robot$siai-ci`
```

Infra replies into `siai/agent-relay/inbox/` when done (project created, robot
re-scoped, credential unchanged). The robot token is in 1Password:
**`harbor - siai-ci robot`**, field **`credential`** (not `password`).

### 3. Activate + TRUST the repo in Woodpecker

In the Woodpecker UI (`https://ci.cat-bluegill.ts.net`):

1. **Repositories → + Add repository →** activate `<owner>/<repo>`.
2. Open the repo **Settings → mark it Trusted.**

> ⚠ **Trusted is security-relevant.** It lets pipeline steps mount the host
> Docker socket (`/var/run/docker.sock`) and run service containers. The
> `build-push` step needs it to `docker build`. Only grant it to repos you
> control. Admin-only.

### 4. Registry secrets

Add these as Woodpecker **repo secrets** (or **org secrets** to share across a
consumer's repos):

| Secret | Value |
|--------|-------|
| `registry_url` | `harbor.cat-bluegill.ts.net` |
| `registry_username` | `robot$siai-ci` |
| `registry_password` | the Harbor robot token — `op read "op://AC-DevOps/harbor - siai-ci robot/credential"` |

Secrets live in the forge, never in the repo. The template reads them via
`from_secret`.

### 5. Add the pipeline

Copy the template and fill the placeholders:

```bash
cp /path/to/siai/templates/.woodpecker.consumer.yml .woodpecker.yml
# replace <PROJECT> (Harbor project), <IMAGE>, adjust lint/test for your toolchain
git add .woodpecker.yml && git commit -m "ci: add Woodpecker pipeline" && git push gitea main
```

The template gives you a lint + test **gate** (push / PR / manual) and a
**tag-gated** `build-push` (`event: tag`, `ref: refs/tags/v*`) that pushes
`harbor.cat-bluegill.ts.net/<PROJECT>/<IMAGE>:<X.Y.Z>`.

### 6. Trigger + verify

- **Gate:** the push above should fire `lint` + `test`. Check
  `woodpecker-cli pipeline ls <owner>/<repo>` (or the UI).
- **Release / build-push:**
  ```bash
  git tag v0.0.1 && git push gitea v0.0.1
  ```
  → builds + pushes `harbor.cat-bluegill.ts.net/<PROJECT>/<IMAGE>:0.0.1`.
  Verify the artifact in the Harbor UI.
- **Triggers, re-runs, force-running build-push, and the verification chain**
  (webhook → pipeline → agent → clone) are documented in Direction's
  `direction/docs/guide-ci-triggers.md` — the live reference for everything
  beyond the production `git push` / `git tag` path.

## Notes & references

- **Clone reachability:** pipeline containers resolve the forge as `gitea` on
  `siai_devnet`; the platform-layer fix is in
  `siai/docs/2026-05-28-pipeline-clone-dns.md`. No custom clone block needed in
  consumer pipelines (unlike the local `.localhost` demo).
- **Capabilities:** this builds on the `homelab-deployment` capability
  (`openspec/specs/homelab-deployment/`). The onboarding contract itself is
  `openspec/specs/ci-consumer-onboarding/`.
- **Deferred (future changes):** onboarding automation (a `just onboard-consumer`
  script), a second consumer to empirically validate repeatability, and
  consumer-side deploy/CD.

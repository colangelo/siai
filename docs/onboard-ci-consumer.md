---
type: runbook
title: "Onboard a repository to siai CI/CD"
description: "Step-by-step onboarding of a real repo to the homelab stack (Gitea → Woodpecker → Harbor on VM 107): activate, trust, secrets, pipeline template. Canonical consumer standard lives in home-network's ci-release-standard."
tags: [onboarding, woodpecker, harbor, homelab]
timestamp: 2026-05-30
---

# Onboard a repository to siai CI/CD

How to onboard a real (non-demo) repository to the homelab CI/CD stack — Gitea →
Woodpecker → Harbor on px1 (VM 107, shipped in v0.4.1). Build + push only; deploy
stays consumer-owned. Follow the steps in order; each is verifiable.

> **Canonical consumer standard:** portable CI/release guidance lives in
> [`home-network/docs/ci-release-standard.md`](https://gitea.cat-bluegill.ts.net/ac/home-network/src/branch/main/docs/ci-release-standard.md).
> Keep shared auth, release, and debugging guidance there. This document is the
> siai-specific companion for Harbor project scope, Woodpecker trust, templates,
> and platform reachability.

> **Reference consumer:** `ac/direction`. It is onboarded and CI-built end-to-end
> (push → lint+test gate; tag → `harbor.cat-bluegill.ts.net/direction/{api,web,mcp}`),
> shipping through tag **`v0.26.8`**. Its live `.woodpecker.yml` is the proven
> image-build example for this template.

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
- **Triggers, re-runs, release webhooks, and common debugging** are covered by
  the canonical consumer standard in home-network. Direction's
  `direction/docs/guide-ci-triggers.md` remains the live reference for its own
  verification chain beyond the production `git push` / `git tag` path.

## Running an end-to-end / browser suite (services + app-under-test)

The build template (`.woodpecker.consumer.yml`) is build + push only. For a
consumer that needs a **live stack under test** — e.g. a Playwright suite hitting
a running web + API + database — use the companion template
`templates/.woodpecker.e2e-playwright.yml`. Proven by `ac/direction`'s
`.woodpecker/parity-eval.yml` (its frontend parity-eval harness).

The pattern, in three parts:

1. **Backing infra → `services:`.** A `postgres:18-alpine` (or redis, qdrant, …)
   is reachable from every step by its **service name** as hostname. Service
   containers are admin-gated: the repo must be **TRUSTED** (same gate as the
   `docker.sock` mount).
2. **App-under-test → `detach: true` steps.** The API and web tiers run as
   detached steps that stay alive for the life of the pipeline and are **also
   reachable by step name** (e.g. `http://api:8000`, `http://web:3000`), exactly
   like services. They must **bind `0.0.0.0`** (not `127.0.0.1`) so sibling
   containers can reach them. Build artifacts land in the shared workspace, so a
   non-detached `build` step and the detached `serve` step can be split.
3. **Test step polls for readiness.** `depends_on` orders *start*, not *health* —
   a detached step never "completes", and many suites' own preflight tries only
   once. Poll the full chain (web → `/api` proxy → api → db) before running.
   `node` is guaranteed inside the `mcr.microsoft.com/playwright` image, so the
   template's readiness loop uses it (no `curl`/`wget` dependency).

> **Multiple workflows need the `.woodpecker/` DIRECTORY.** A single
> `.woodpecker.yml` *file* is one workflow. To add an e2e workflow alongside an
> existing build pipeline, `git mv .woodpecker.yml .woodpecker/build.yml` first,
> then add `.woodpecker/e2e.yml`. You cannot have both the file and the dir —
> when the dir exists, the top-level file is ignored.

Pin the Playwright image to the **same version** as the repo's `@playwright/test`
(`mcr.microsoft.com/playwright:v<X.Y.Z>-noble`) so the bundled browsers match.

### Generating Linux visual baselines

`toHaveScreenshot` baselines are **OS/font-stack dependent** — pixels rendered on
macOS or Windows will not match the CI Linux agent. So canonical baselines must be
generated **in the same pinned Linux container**, never on a developer laptop.
(Structural `toMatchAriaSnapshot` baselines are OS-independent — commit those once;
only the *visual* layer is platform-pinned.)

One-shot recipe — run it where Docker is available (the homelab agent, or any
Docker host; **not** a macOS box without a Linux container):

```bash
# With the app + API + db stack already up and reachable at $BASE_URL:
docker run --rm --network host \
  -v "$PWD/e2e/playwright:/work" -w /work \
  -e BASE_URL="http://localhost:3000" \
  mcr.microsoft.com/playwright:v<X.Y.Z>-noble \
  sh -c 'npm ci && npx playwright test --update-snapshots'
# Then review + commit the new PNGs under tests/__snapshots__/ in the consumer repo.
```

Two consumer-side prerequisites for the visual layer (these live in the consumer's
`playwright.config.ts`, not here):

- **Add a `{platform}` segment to the screenshot `snapshotPathTemplate`** so per-OS
  pixels don't collide with the OS-independent structural baselines. (Direction's
  config has a comment marking exactly where this goes — task 6.2.)
- Visual baselines for **read-only** routes also need a **seeded corpus** up in the
  stack (and Qdrant if a spec exercises `mode=semantic`/`hybrid`); the write-only
  job needs neither. Until canonical baselines are committed, keep the visual layer
  **advisory** and let behavioral + structural assertions gate.

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

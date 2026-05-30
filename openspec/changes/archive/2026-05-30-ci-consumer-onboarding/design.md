## Context

siai's homelab CI/CD (v0.4.1) is live on px1 VM 107: Gitea (`gitea.cat-bluegill.ts.net`), Woodpecker (`ci.cat-bluegill.ts.net`), agent on the host Docker backend, pushing to Harbor (`harbor.cat-bluegill.ts.net`) via `robot$siai-ci`. **Direction is already onboarded and CI-built** — `ac/direction` has a `.woodpecker.yml` (lint-python · lint-web · test · tag-gated build-push) and has shipped images through `v0.26.8`. The onboarding steps that made that work are real but undocumented in siai: they're spread across `direction/docs/guide-ci-triggers.md`, a Direction design spec, the live Woodpecker repo settings (activated + trusted + secrets), and the infra relay that scoped the Harbor robot. This change writes that flow down as a siai-owned, reusable contract + template — it does not change any running system.

## Goals / Non-Goals

**Goals:**
- A single siai-owned runbook (`docs/onboard-ci-consumer.md`) a maintainer can follow to onboard a real repo end-to-end.
- A reusable `.woodpecker.yml` consumer template derived from Direction's proven pipeline.
- Capture the cross-repo touchpoint explicitly: the Harbor project + `robot$siai-ci` scope is an **infra (home-network) relay ask**, not a siai action.
- Record Direction as the reference consumer with already-met acceptance.

**Non-Goals:**
- Onboarding a second consumer (deferred — repeatability is asserted from the documented flow, not re-proven here).
- Onboarding automation (`just onboard-consumer` / a provisioning script) — deferred to a later change.
- Changing Direction's pipeline, the homelab stack, or any infra.
- Deploy/CD of consumer images (build-push only; deploy stays consumer-owned, as with Direction).

## Decisions

- **Capability = a documented process, not code.** The deliverables are a runbook + a template. *Alternative:* build automation now — rejected (scope; the manual flow must be understood and stable before automating it).
- **Template mirrors Direction's pipeline shape.** lint → test (gate, on `push`/`pull_request`/`manual`) and a **tag-gated `build-push`** (`event: tag`, `ref: refs/tags/v*`) that logs in with the registry secrets and pushes to `harbor.cat-bluegill.ts.net/<project>/<image>:<tag>`. *Alternative:* a minimal hello-world template — rejected (Direction's shape is the proven, real-world one; better to generalize from it).
- **Harbor scope via infra relay, per consumer.** Each new consumer needs its own Harbor project + `robot$siai-ci` push/pull scope, obtained by a relay to home-network (the `siai` project ask is the worked example). `robot$siai-ci` is reused and re-scoped, never replaced (Decision A from the deploy handoff). *Alternative:* a system-level robot — rejected (least-privilege).
- **Trusted repo for socket builds.** `build-push` mounts `/var/run/docker.sock`, so the consumer repo must be marked **Trusted** in Woodpecker (admin) — documented as an explicit, security-relevant step. *Alternative:* rootless/kaniko builds — out of scope; Direction uses the socket and it works.
- **Registry auth via Woodpecker secrets, not committed.** `registry_url`, `registry_username` (`robot$siai-ci`), `registry_password` (Harbor robot **`credential`** field — not `password`) are Woodpecker repo/org secrets sourced from 1Password. *Alternative:* env in the compose — rejected (secrets in the forge, not the repo).
- **Agent Harbor reachability is already solved + tracked.** Pipeline containers reach Harbor via `docker-compose.homelab.smoke.yml` (`WOODPECKER_BACKEND_DOCKER_EXTRA_HOSTS` pins Harbor's tailnet IP), committed in v0.4.1. The runbook references it; no new infra.

## Risks / Trade-offs

- **Repeatability asserted, not re-proven** (no 2nd consumer) → mitigation: the runbook is written strictly from Direction's working flow, with every cross-repo dependency made explicit; the first *next* onboarding is the real test, and the runbook is updated then.
- **Trusted-repo = host Docker socket access** → mitigation: documented as a deliberate, admin-only, security-relevant step; only trusted repos get it.
- **Harbor robot token scope creep** as consumers accumulate → mitigation: per-project scope, reviewed at each relay ask; rotate on leak.
- **Template drift from Direction's evolving pipeline** → mitigation: template is a starting point, not a sync target; note that Direction's live `.woodpecker.yml` is the living reference.

## Migration Plan

Documentation-only; nothing to deploy or roll back.
1. Write `docs/onboard-ci-consumer.md` and `templates/.woodpecker.consumer.yml`.
2. Verify the runbook against Direction's actual setup (the reference) — every step must match what made `ac/direction` work.
3. Update README/CHANGELOG/ROADMAP (v0.4.5 → Shipped, reframed).
Rollback = revert the docs; no running system is touched.

## Open Questions

- None blocking. Open follow-ons (tracked as future changes): onboarding automation; a second consumer to empirically validate repeatability; consumer-side deploy/CD.

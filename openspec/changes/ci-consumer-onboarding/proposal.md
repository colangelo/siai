# Change: Formalize CI consumer onboarding (reference: Direction)

## Why

The homelab CI/CD (Gitea + Woodpecker + Harbor on px1, shipped in v0.4.1) already builds a real production app — **Direction** has been CI-built end-to-end through `v0.26.8` (push → lint+test gate; tag → image pushed to `harbor.cat-bluegill.ts.net/direction/{api,web,mcp}` via `robot$siai-ci`). But that onboarding happened ad-hoc: the steps live scattered across Direction's own repo, the live Woodpecker UI state, and tribal memory. siai owns **no** reusable description of how to onboard the *next* real consumer — the exact gap the ROADMAP's v0.4.5 success criterion calls out ("the onboarding steps are reusable for subsequent real projects").

## What Changes

- Add a **`ci-consumer-onboarding`** capability: the repeatable, documented process for onboarding a real (non-demo) repository to the siai CI/CD stack — Gitea repo → Harbor project + robot scope (via infra relay) → Woodpecker activation/trust/secrets → a tag-gated `.woodpecker.yml`.
- Add a **siai-owned onboarding runbook** (`docs/onboard-ci-consumer.md`) capturing the end-to-end flow, including the **cross-repo relay to home-network** for the Harbor project + `robot$siai-ci` scope (the pattern proven by the `siai` project ask).
- Add a **`.woodpecker.yml` consumer template** (under `templates/`) — a parameterized starting point derived from Direction's proven pipeline (lint → test → tag-gated build-push to Harbor).
- **Retroactively document Direction** (`ac/direction`) as the reference consumer and record its acceptance as already-met (CI-built through `v0.26.8`).
- **Out of scope (explicit):** onboarding a *second* consumer; building onboarding *automation* (a `just onboard-consumer` script). Both are deferred — this change captures and templatizes what already works.

## Capabilities

### New Capabilities

- `ci-consumer-onboarding`: the documented, repeatable process and contract for onboarding a real repository to the siai CI/CD stack (forge repo, Harbor project/robot scope, Woodpecker activation/trust/secrets, tag-gated build-push to Harbor), with Direction as the reference implementation.

### Modified Capabilities

- None. `homelab-deployment` (v0.4.1) is unchanged; this is additive and documents a process layered on top of it.

## Impact

- **siai repo:** a new `docs/onboard-ci-consumer.md` runbook and a `templates/.woodpecker.consumer.yml` template; README/CHANGELOG/ROADMAP updates (v0.4.5 → Shipped, reframed to "formalize + templatize" since onboarding already happened).
- **No code/behavior change:** the live stack and Direction's pipeline are untouched — this is documentation + a reusable template that describe the existing, proven flow.
- **External dependencies (documented, not provisioned here):** Harbor project + `robot$siai-ci` scope is obtained per-consumer via the **agent relay to home-network** (infra-owned), exactly as done for the `siai` project. pg1/tailnet unaffected.
- **Reference consumer:** `ac/direction` (`.woodpecker.yml`, Harbor project `direction`), CI-built through `v0.26.8`.

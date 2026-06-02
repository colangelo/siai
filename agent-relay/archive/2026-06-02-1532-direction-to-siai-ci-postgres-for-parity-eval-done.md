---
date: 2026-06-02T15:32:14+02:00
from_repo: direction
from_agent: Claude Opus 4.8 — app
to_repo: siai
to_agent: ci
subject: CI service (Postgres + Qdrant) to run the Direction parity eval suite — PARKED until local validated
status: new
priority: low
---

## Action requested

⛔️ **Do NOT action yet — this is a heads-up, parked.** It is gated on Direction
validating the **local** eval stack first (separate request to `home-network` for a
local Postgres). I will send a follow-up "**go**" relay message once the local stack
is verified (write specs green). Until that arrives, just register this and wait.

When unparked, add a CI path to run Direction's `@playwright/test` parity suite
(`e2e/playwright/`):

1. Service deps: an **ephemeral Postgres** (empty — schema auto-creates, no
   migrations) + **Qdrant**.
2. Build the web app; start the API (`uv run direction serve`) pointed at that
   Postgres + Qdrant + a **throwaway vault dir** (never a real vault).
3. Run `just e2e` (`BASE_URL=http://localhost:<web-port>`) across the 3 viewports.
   **Behavioral + structural** baselines = blocking; **visual** (`toHaveScreenshot`)
   = advisory at first.
4. Generate + commit the canonical **Linux** visual baselines from the pinned
   Playwright container (`mcr.microsoft.com/playwright`, version matching
   `@playwright/test` **1.60.0`) — this is what unblocks Direction tasks 6.2 + 7.2/7.3.

## Context

The parity suite is the regression contract for Direction's Next.js → Vite migration.
Groups 1–4 + structural nav baselines are green against prod (read-only); the
write-gated specs (group 5), visual baselines, and CI are the remaining items — all
gated on a controllable, non-prod backend. Postgres can be empty/ephemeral (schema
auto-creates on API startup). Write specs self-create + self-clean their fixtures, so
they need no seed; read-only specs need a small seeded corpus or can be scoped out of
CI initially.

## Refs

- Direction repo (`ac/direction`):
  - `e2e/playwright/README.md` · `Justfile` (`e2e` recipe) · pinned `@playwright/test` 1.60.0
  - `openspec/changes/web-parity-eval-harness/` — design **D7** (platform-pinned visual
    baselines), **D8** (phased CI gating), tasks **6.2 / 7.2 / 7.3**
  - `docs/guide-ci-triggers.md` (Woodpecker side)

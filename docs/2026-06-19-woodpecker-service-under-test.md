---
type: learning
title: "Woodpecker: service-under-test exits 137 at teardown"
description: "A commands:-based service runs under a pipe shell as PID 1 that never forwards SIGTERM → SIGKILL → exit 137. Fix: entrypoint exec-form so the server is PID 1; WOODPECKER_FORCE_IGNORE_SERVICE_FAILURE is the server-wide green-icon override."
tags: [woodpecker, ci, services]
timestamp: 2026-06-19
---

# Woodpecker: long-lived service-under-test exits 137 at teardown

**Date:** 2026-06-19
**Context:** Direction's `parity-eval` pipeline keeps an `api` **service** alive
while Playwright drives it. The service rendered a spurious red **`exit 137`** at
teardown on every run, even though the tests passed. This captures the root cause
and the fix as a reusable pattern — it recurs in *any* pipeline that tests a
long-running server as a Woodpecker `service`. Originated as cross-repo relay
`ac/siai#1` from the direction agent (full writeup: direction
`docs/ci-woodpecker-service-under-test.md`, cross-ref direction #6).

## Symptom

A pipeline `service` that runs a long-lived server (uvicorn, a dev server, etc.)
exits **137** (128 + SIGKILL) when the pipeline tears the service down — shown as
a **failed** (red) step, even though every test step that used it passed.

## Root cause (reusable across any service-under-test pipeline)

A Woodpecker service defined with a `commands:` block runs under
`["/bin/sh","-c","echo $CI_SCRIPT | base64 -d | /bin/sh -e"]`. **PID 1 is the
outer pipe shell**, not your server. That shell does **not** forward `SIGTERM` to
the child, so at teardown:

1. Woodpecker sends `SIGTERM` to PID 1 (the pipe shell), which ignores/swallows it.
2. The stop grace period elapses; the server is still running.
3. Woodpecker sends `SIGKILL` → the server dies hard → **exit 137**.

In-container signal traps can't help — they never receive the signal. (`postgres`
and similar images render green only because their image **ENTRYPOINT is PID 1**,
so they get the SIGTERM directly and shut down cleanly.)

With Playwright specifically, keep-alive sockets the test holds open also outlast
the stop grace, compounding the dirty teardown.

## Fix

Two independent levers — use the first for correctness, the second as the global
green-icon override.

### 1. Per-pipeline: make the server PID 1 (`entrypoint:`, exec-form)

Run the server via an `entrypoint:` exec-form (**no** `commands:`) so the server
process is PID 1, receives `SIGTERM` directly, and exits **0** on a bounded
graceful shutdown:

```yaml
services:
  api:
    image: my-app:ci
    # exec-form entrypoint → the server is PID 1, gets SIGTERM, exits 0
    entrypoint: ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
    # (configure a bounded graceful-shutdown timeout in the server itself)
```

`failure: ignore` on the step is **non-blocking but still renders the step as
failed** (yellow/red, not green) — it does not fix the icon.

### 2. Server-wide: `WOODPECKER_FORCE_IGNORE_SERVICE_FAILURE`

The only lever that yields a literally-**green** icon for a service that dies at
teardown is the server-side switch (added in Woodpecker v3.14.0-rc.2, PR #6448):

```yaml
# docker-compose.homelab.yml → wpk-server environment:
- WOODPECKER_FORCE_IGNORE_SERVICE_FAILURE=true
```

This is **persisted in siai source** (`docker-compose.homelab.yml`, wpk-server env
block) so a full `deploy-homelab-px1` redeploy doesn't silently revert it. The
homelab server runs 3.15.0, which supports the flag.

## Reusable takeaway

- Prefer **entrypoint exec-form** for any service-under-test so it shuts down
  cleanly on its own — that's the correct fix and works regardless of server-side
  flags.
- `failure: ignore` ≠ green; it only stops a service failure from failing the
  pipeline.
- `WOODPECKER_FORCE_IGNORE_SERVICE_FAILURE=true` is the global override for a green
  icon and is now baked into the homelab compose for the whole stack.

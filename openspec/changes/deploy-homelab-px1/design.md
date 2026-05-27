## Context

siai runs today as a local `.localhost` POC: bundled Postgres, Gitea's built-in registry, and Traefik routing `gitea.localhost` / `ci.localhost`. The homelab (`proxmox1`/px1) already provides the substrate this stack should consume in production: **pg1** (Postgres 18 VM, one-instance-N-databases, nightly logical backup), **Harbor** (private OCI registry on VM 106), and the **tailnet** (`cat-bluegill.ts.net`) with `tailscale serve`/sidecar TLS and a hardened ACL. The Woodpecker agent runs pipeline steps and image builds via the Docker backend (`/var/run/docker.sock`). This change defines how the stack lands on px1 without disturbing the local quick-start. The infra-side contract — pinned substrate handles, 1Password item names, ACL legs, and acceptance tests — lives in home-network `docs/2026-05-27-siai-deployment-handoff.md`.

## Goals / Non-Goals

**Goals:**
- Run Gitea + Woodpecker (server + agent) + Traefik on a dedicated px1 host, on the tailnet, with TLS.
- Reuse pg1 (Gitea + Woodpecker DBs) and Harbor (image pushes) — no bundled Postgres/Harbor on the homelab.
- Keep the local `.localhost` POC fully working (additive profile).
- Be the CI substrate Direction (and others) onboard onto next.

**Non-Goals:**
- Onboarding Direction's pipeline (`.woodpecker.yaml`, repo/robot) — follow-on change.
- Multi-node Woodpecker agents / autoscaling.
- Public (Funnel) exposure — tailnet-only, consistent with the rest of the homelab.

## Decisions

- **Dedicated VM (107), not an LXC and not a tenant on VM 100.** The Woodpecker agent builds arbitrary images via the Docker daemon — a clean-VM workload (matches the Harbor VM precedent). *Alternatives:* unprivileged LXC + nesting (fiddly/foot-gunny for arbitrary `docker build`); 2nd compose tenant on VM 100 (would re-open the just-closed Phase 4 Caddy-umbrella question and couple CI build load to the app host). Debian 13 + Docker CE + Tailscale, same recipe as Harbor.
- **Databases on pg1, LAN-direct.** Create `gitea` + `woodpecker` roles + databases on pg1; point both services there; **drop the bundled `postgres`** in the homelab override. Connect **LAN-direct** to `192.168.4.50:5432` (pg1's `pg_hba` already trusts `192.168.4.0/24`) — **no tailnet ACL, no MagicDNS** (matches how VM 100 reaches pg1). *Alternatives:* bundled Postgres — rejected (defeats substrate reuse, extra backup surface); pg1 over the tailnet — rejected (needs an ACL rule, MagicDNS flaky).
- **Registry = existing Harbor.** `REGISTRY_BACKEND=harbor`; Woodpecker pushes to `harbor.cat-bluegill.ts.net/<project>` via the Harbor robot **`robot$siai-ci`**, scoped **per consumer project** (starting with `direction`; add scope per new consumer). *Alternatives:* Gitea's built-in registry — works, but the homelab standard is Harbor (scanning/RBAC, already deployed); a system-level robot — rejected (broader privilege than needed).
- **Tailnet ingress = two hostnames via two Tailscale sidecars** → `gitea.cat-bluegill.ts.net` + `ci.cat-bluegill.ts.net`. Gitea (ROOT_URL + SSH) and Woodpecker (WOODPECKER_HOST + gRPC) each want a root URL; two clean hostnames mirror the local POC (`gitea.localhost`/`ci.localhost`) and the homelab per-tenant sidecar precedent (Direction). *Alternative:* single node `siai.cat-bluegill.ts.net` + Traefik path-routing (Gitea `/`, Woodpecker subpath) — rejected: Woodpecker-under-subpath is finicky and two root apps on one host is awkward; two extra tailnet nodes is trivial in a homelab.
- **Persistent storage on the state SSD.** Gitea repo data + Woodpecker server DB-less state on a state-SSD data disk (PVE nightly backup), matching pg1/harbor. Build workspaces ephemeral on the compute disk.
- **Auth.** Woodpecker↔Gitea OAuth stays internal (`WOODPECKER_GITEA_CLIENT/SECRET`). **Gitea admin SSO via tsidp (OIDC) is in scope for this deployment:** register a tsidp client and configure a Gitea OAuth2/OpenID Connect login source so admins authenticate via the homelab IdP.
- **Gitea SSH = deferred.** Expose only HTTPS on the `gitea.` sidecar; git is HTTPS + PAT. No `:2222` TCP at bring-up — revisit if `git@…` ergonomics are wanted. *Alternative:* expose sidecar TCP `:2222` now (restrict by ACL) — deferred to keep the initial surface small.
- **VM sizing.** Start at **4 vCPU / 8 GB**; revisit if CI builds are heavy.

## Risks / Trade-offs

- **CI build load on the VM** → size adequately (≥4 vCPU / 8 GB); revisit if builds are heavy.
- **pg1 becomes a CI dependency** → if pg1 is down, CI is down. Acceptable: pg1 is core infra and now has nightly logical backups; Gitea/Woodpecker DBs are included.
- **Harbor robot token scope/rotation** → scope to the CI project, store in 1Password, rotate on leak.
- **MagicDNS flakiness from the VM** → pg1 is reached **LAN-direct** (`192.168.4.50`, no DNS); Harbor and tsidp are tailnet-only (reached by tailnet hostname, via the ACL legs below).
- **Gitea SSH over tailnet** → deferred; git is HTTPS+PAT over the `gitea.` sidecar. If SSH is added later, expose sidecar TCP `:2222` and restrict by ACL.

## Migration Plan

1. **infra (home-network):** provision VM 107 (Debian + Docker + Tailscale), MikroTik DHCP reservation (~`192.168.4.55`); create pg1 `gitea`/`woodpecker` roles+DBs (LAN-direct); create the Harbor robot `robot$siai-ci` (scoped to `direction`); register the tsidp OIDC client; add ACL legs (`ts-siai → ts-harbor:443` + `ts-siai → tag:tsidp:443`; admins already reach `tag:host:*`; **no pg1 ACL**) + push. Per the infra contract (`home-network/docs/2026-05-27-siai-deployment-handoff.md`).
2. **siai:** author the homelab compose override + `.env` (external pg1/Harbor, tailnet) + sidecar config; deploy; bring up `tailscale serve` for `gitea.` + `ci.`.
3. **verify:** Gitea + Woodpecker UIs reachable over tailnet with TLS; Woodpecker↔Gitea OAuth works; a smoke pipeline builds and pushes an image to Harbor.
4. **rollback:** tear down VM 107 (no impact on the local POC); drop the pg1 `gitea`/`woodpecker` DBs and the Harbor robot if abandoning.

## Resolved Decisions (approved 2026-05-27)

- **Ingress shape:** ✅ two Tailscale sidecars → `gitea.cat-bluegill.ts.net` + `ci.cat-bluegill.ts.net`.
- **Gitea SSH over tailnet:** ✅ deferred — HTTPS + PAT only at bring-up (no sidecar `:2222`).
- **Gitea SSO via tsidp:** ✅ in scope now — register a tsidp OIDC client and configure Gitea's OAuth2/OpenID Connect login source.
- **VM sizing:** ✅ 4 vCPU / 8 GB to start; revisit if builds are heavy.

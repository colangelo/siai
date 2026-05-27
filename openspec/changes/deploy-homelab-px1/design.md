## Context

siai runs today as a local `.localhost` POC: bundled Postgres, Gitea's built-in registry, and Traefik routing `gitea.localhost` / `ci.localhost`. The homelab (`proxmox1`/px1) already provides the substrate this stack should consume in production: **pg1** (Postgres 18 VM, one-instance-N-databases, nightly logical backup), **Harbor** (private OCI registry on VM 106), and the **tailnet** (`cat-bluegill.ts.net`) with `tailscale serve`/sidecar TLS and a hardened ACL. The Woodpecker agent runs pipeline steps and image builds via the Docker backend (`/var/run/docker.sock`). This change defines how the stack lands on px1 without disturbing the local quick-start.

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
- **Databases on pg1.** Create `gitea` + `woodpecker` roles + databases on pg1; point both services there; **drop the bundled `postgres`** in the homelab override. Connect via LAN IP / `extra_hosts` (MagicDNS is flaky on some homelab hosts). *Alternative:* bundled Postgres — rejected (defeats substrate reuse, extra backup surface).
- **Registry = existing Harbor.** `REGISTRY_BACKEND=harbor`; Woodpecker pushes to `harbor.cat-bluegill.ts.net/<project>` via a Harbor **robot account** scoped to the CI project. *Alternative:* Gitea's built-in registry — works, but the homelab standard is Harbor (scanning/RBAC, already deployed).
- **Tailnet ingress = two hostnames via two Tailscale sidecars** → `gitea.cat-bluegill.ts.net` + `ci.cat-bluegill.ts.net`. Gitea (ROOT_URL + SSH) and Woodpecker (WOODPECKER_HOST + gRPC) each want a root URL; two clean hostnames mirror the local POC (`gitea.localhost`/`ci.localhost`) and the homelab per-tenant sidecar precedent (Direction). *Alternative:* single node `siai.cat-bluegill.ts.net` + Traefik path-routing (Gitea `/`, Woodpecker subpath) — rejected: Woodpecker-under-subpath is finicky and two root apps on one host is awkward; two extra tailnet nodes is trivial in a homelab. **(Confirm at approval — see Open Questions.)**
- **Persistent storage on the state SSD.** Gitea repo data + Woodpecker server DB-less state on a state-SSD data disk (PVE nightly backup), matching pg1/harbor. Build workspaces ephemeral on the compute disk.
- **Auth.** Woodpecker↔Gitea OAuth stays internal (`WOODPECKER_GITEA_CLIENT/SECRET`). Gitea SSO via tsidp (OIDC) is optional/later.

## Risks / Trade-offs

- **CI build load on the VM** → size adequately (≥4 vCPU / 8 GB); revisit if builds are heavy.
- **pg1 becomes a CI dependency** → if pg1 is down, CI is down. Acceptable: pg1 is core infra and now has nightly logical backups; Gitea/Woodpecker DBs are included.
- **Harbor robot token scope/rotation** → scope to the CI project, store in 1Password, rotate on leak.
- **MagicDNS flakiness from the VM** → pin pg1/Harbor via LAN IP / `extra_hosts` (homelab norm).
- **Trusting Gitea SSH over tailnet** → if SSH (2222) is exposed via the sidecar, restrict by ACL; otherwise default to HTTPS+token git and defer SSH.

## Migration Plan

1. **infra (home-network):** provision VM 107 (Debian + Docker + Tailscale), MikroTik DHCP reservation; create pg1 `gitea`/`woodpecker` roles+DBs; create the Harbor robot account; add ACL rules (node → `ts-pg1:5432` + `ts-harbor:443`; admin → node) + push.
2. **siai:** author the homelab compose override + `.env` (external pg1/Harbor, tailnet) + sidecar config; deploy; bring up `tailscale serve` for `gitea.` + `ci.`.
3. **verify:** Gitea + Woodpecker UIs reachable over tailnet with TLS; Woodpecker↔Gitea OAuth works; a smoke pipeline builds and pushes an image to Harbor.
4. **rollback:** tear down VM 107 (no impact on the local POC); drop the pg1 `gitea`/`woodpecker` DBs and the Harbor robot if abandoning.

## Open Questions

- **Ingress shape:** two sidecars (`gitea.`/`ci.`, recommended) vs single node `siai.` with Traefik path-routing — confirm before implementation.
- **Gitea SSH over tailnet** (sidecar TCP `:2222`) vs HTTPS-token-only — include now or defer?
- **Gitea SSO via tsidp** — wire OIDC now or later?
- **VM sizing** for expected CI build load.

# Change: Deploy siai on the homelab (px1)

## Why

The siai stack (Gitea + Woodpecker) currently runs only as a local `.localhost` POC with bundled services. To become the homelab's real CI/CD — and the prerequisite for onboarding Direction (and other repos) to CI — it must run on the homelab host (`proxmox1`/px1), integrated with the existing homelab substrate (pg1 Postgres, Harbor registry, tailnet) instead of its local-only bundled Postgres and Gitea registry.

## What Changes

- Add a **homelab deployment profile** that runs the stack (Gitea + Woodpecker server/agent + Traefik) on a **dedicated VM on px1**, on the tailnet — additive to and **non-breaking** for the local `.localhost` quick-start.
- **Reuse pg1** (homelab Postgres VM) for the Gitea + Woodpecker databases; **drop the bundled `postgres`** service in the homelab profile.
- **Reuse the existing Harbor** (homelab VM 106) as the image registry: `REGISTRY_BACKEND=harbor`, Woodpecker pushes via a Harbor robot account scoped to the target project. The bundled/optional Harbor compose is not used on the homelab.
- **Tailnet ingress + TLS** for the Gitea and Woodpecker UIs via two Tailscale sidecars (`gitea.cat-bluegill.ts.net` + `ci.cat-bluegill.ts.net`), replacing the local Traefik `*.localhost` routing. Gitea SSH over the tailnet is **deferred** (HTTPS + PAT git at bring-up).
- **Admin SSO** to Gitea via the homelab `tsidp` OIDC provider; Woodpecker↔Gitea CI OAuth stays internal.
- Provisioning is **cross-repo**: `home-network` owns the VM, the pg1 databases/roles, the Harbor robot account, and the tailnet ACL; **siai** owns the deployment compose override + env + config for the px1 environment.
- **Out of scope (follow-on):** onboarding Direction as the first real CI consumer (`.woodpecker.yaml`, Gitea repo + robot) — tracked separately as siai's "First Real Consumer: Direction".

## Capabilities

### New Capabilities

- `homelab-deployment`: production deployment of the siai stack on the homelab (px1) — dedicated VM, external Postgres (pg1) and container registry (Harbor), tailnet ingress + ACL, and persistent storage; coexists with the local `.localhost` POC without breaking it.

### Modified Capabilities

- None. The local POC's capabilities (`gitea-automation`, etc.) are unchanged; the homelab deployment is an additive profile.

## Impact

- **siai repo:** a homelab compose override (e.g. `docker-compose.homelab.yml`) + `.env` entries for external pg1/Harbor/tailnet, config for the tailnet hostnames, and deployment docs. The local `.localhost` path (bundled Postgres + Gitea registry + Traefik) is untouched.
- **home-network repo (infra):** VM 107 on px1 (4 vCPU / 8 GB, 32 GB `state` data disk; Debian 13 + Docker CE + Tailscale, Harbor-VM pattern); pg1 `gitea` + `woodpecker` roles + databases (reached **LAN-direct** `192.168.4.50`); Harbor robot `robot$siai-ci` scoped to `direction`; a tsidp OIDC client for Gitea SSO; tailnet ACL legs (`ts-siai → ts-harbor:443` + `ts-siai → tag:tsidp:443`; **no pg1 ACL**; admins via `tag:host:*`); MikroTik DHCP reservation (~`192.168.4.55`); per-host doc + ACL push. Pinned by `home-network/docs/2026-05-27-siai-deployment-handoff.md`.
- **External dependencies:** pg1 (Postgres 18, LAN `192.168.4.50`), Harbor (VM 106), tsidp OIDC (`idp.cat-bluegill.ts.net`), tailnet `cat-bluegill.ts.net`.
- **Non-breaking:** the local quick-start experience is preserved.

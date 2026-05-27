# Tasks: Deploy siai on the homelab (px1)

> Cross-repo: groups tagged **(infra)** are home-network mutations (VM, pg1, Harbor, ACL); **(siai)** groups are this repo. Confirm the ingress decision (design.md Open Questions) before group 4.

## 1. Provision the VM (infra)

- [ ] 1.1 Create VM 107 on px1 — Debian 13 cloud-init, Docker CE, `ac` sudoer + m4m SSH key (Harbor-VM recipe)
- [ ] 1.2 MikroTik DHCP reservation (next free `.5x`); set hostname `siai`
- [ ] 1.3 Attach a state-SSD data disk (`backup=1`) mounted for Gitea repo + Woodpecker data
- [ ] 1.4 Join the tailnet: `tailscale up --advertise-tags=tag:host --hostname=siai --operator=ac --accept-routes=false --ssh=false`

## 2. Substrate wiring (infra)

- [ ] 2.1 On pg1, create `gitea` + `woodpecker` roles + databases (idempotent); store creds in 1Password (vault `AC-DevOps`)
- [ ] 2.2 In Harbor, create the CI project (if needed) + a robot account scoped to it (push+pull); store the token in 1Password
- [ ] 2.3 `tailscale/acl.hujson`: add `ts-siai` host alias + rules `ts-siai → ts-pg1:5432` and `ts-siai → ts-harbor:443`; ensure admin Macs → the node; validate + push
- [ ] 2.4 Confirm reachability from the VM: `nc -z pg1 5432` and `curl https://harbor.cat-bluegill.ts.net/v2/` → 401

## 3. Homelab compose profile (siai)

- [ ] 3.1 Author `docker-compose.homelab.yml` override: remove the bundled `postgres`; point Gitea + Woodpecker `DATABASE`/`GITEA__database__*` at pg1 via LAN IP / `extra_hosts`
- [ ] 3.2 Set `REGISTRY_BACKEND=harbor`; wire the Woodpecker registry secret to the Harbor robot + `harbor.cat-bluegill.ts.net`
- [ ] 3.3 Add `.env.homelab` (external pg1/Harbor endpoints, OAuth + agent secrets) sourced from 1Password; never commit secrets
- [ ] 3.4 Configure ingress per the approved decision: two Tailscale sidecars → `gitea.cat-bluegill.ts.net` + `ci.cat-bluegill.ts.net` (or single-node path-routing if chosen); set Gitea `ROOT_URL` + Woodpecker `WOODPECKER_HOST` accordingly

## 4. Deploy on the VM (siai)

- [ ] 4.1 Place the homelab compose + env on the VM; `docker compose -f docker-compose.yml -f docker-compose.homelab.yml up -d` (no bundled postgres)
- [ ] 4.2 Bring up tailnet ingress (sidecars/`tailscale serve`) with TLS for `gitea.` + `ci.`
- [ ] 4.3 Configure Woodpecker↔Gitea OAuth (`WOODPECKER_GITEA_CLIENT`/`SECRET`); confirm login flow

## 5. Verify (acceptance — maps to homelab-deployment spec)

- [ ] 5.1 Gitea + Woodpecker UIs reachable over the tailnet with valid TLS; a non-tailnet client cannot reach them
- [ ] 5.2 Gitea + Woodpecker tables live on pg1; no `postgres` container running in the homelab profile
- [ ] 5.3 Smoke pipeline builds + pushes an image to `harbor.cat-bluegill.ts.net/<project>` via the robot account
- [ ] 5.4 Repo data survives a VM restart and is captured by the nightly PVE backup
- [ ] 5.5 Local `.localhost` quick-start still works unchanged (bundled postgres + Gitea registry + Traefik)

## 6. Document (infra + siai)

- [ ] 6.1 (infra) Add `hosts/configs/proxmox1/siai.md` (identity, resources, storage, tailnet, ACL, daily-use); ROADMAP move "Deploy siai on px1" Next → Shipped
- [ ] 6.2 (siai) Document the homelab profile (README + CHANGELOG) + config templates
- [ ] 6.3 (siai) Update ROADMAP: deploy-on-px1 done → unblocks "First Real Consumer: Direction"

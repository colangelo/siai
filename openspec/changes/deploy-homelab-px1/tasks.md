# Tasks: Deploy siai on the homelab (px1)

> Cross-repo: groups tagged **(infra)** are home-network mutations (VM, pg1, Harbor, ACL) — pinned by the infra contract `home-network/docs/2026-05-27-siai-deployment-handoff.md`; **(siai)** groups are this repo. Ingress/SSH/SSO/sizing resolved in design.md (Resolved Decisions).

## 1. Provision the VM (infra)

- [x] 1.1 Create VM 107 on px1 (4 vCPU / 8 GB) — Debian 13 cloud-init, Docker CE, `ac` sudoer + m4m SSH key (Harbor-VM recipe)
- [x] 1.2 MikroTik DHCP reservation (~`192.168.4.55`, next free); hostname `siai`; tailnet node `siai.cat-bluegill.ts.net` (`tag:host`)
- [x] 1.3 Attach a **32 GB** state-SSD data disk (`backup=1`, ext4; grow online later) for Gitea repos + Woodpecker state; sys disk 16 GB `local-lvm`
- [x] 1.4 Join the tailnet with the one-shot auth-key (1P `siai - tailnet auth-key - cat-bluegill`): `tailscale up --advertise-tags=tag:host --hostname=siai --operator=ac --accept-routes=false --ssh=false`

## 2. Substrate wiring (infra)

- [x] 2.1 On pg1, create `gitea` + `woodpecker` roles + databases (idempotent); reached **LAN-direct** `192.168.4.50:5432`; creds in 1P (`gitea - app role @ pg1`, `woodpecker - app role @ pg1`, vault `AC-DevOps`)
- [x] 2.2 In Harbor, create robot `robot$siai-ci` (push+pull) scoped **per project, starting `direction`**; token in 1P (`harbor - siai-ci robot`)
- [x] 2.3 `tailscale/acl.hujson`: add `ts-siai` host alias + rules `ts-siai → ts-harbor:443` and **`ts-siai → tag:tsidp:443`** (Gitea's server-side OIDC token exchange — the leg that broke proxmox1 OIDC; do not omit). **No pg1 ACL** (LAN-direct); admins already reach `tag:host:*`. Validate + push
- [x] 2.4 Confirm from the VM: `nc -z 192.168.4.50 5432` (pg1 LAN), `curl https://harbor.cat-bluegill.ts.net/v2/` → 401, and `curl -sf https://idp.cat-bluegill.ts.net/.well-known/openid-configuration` (proves the tsidp ACL leg)
- [x] 2.5 Register a tsidp OIDC client for Gitea: redirect `https://gitea.cat-bluegill.ts.net/user/oauth2/tsidp/callback`, discovery `https://idp.cat-bluegill.ts.net/.well-known/openid-configuration`, scopes `openid email profile`, `username-claim email`; client ID/secret in 1P (`tsidp - gitea oidc client`)

## 3. Homelab compose profile (siai)

- [x] 3.1 Author `docker-compose.homelab.yml` override: remove the bundled `postgres`; point Gitea + Woodpecker `DATABASE`/`GITEA__database__*` at pg1 **LAN-direct `192.168.4.50:5432`** (DBs `gitea`/`woodpecker`)
- [x] 3.2 Set `REGISTRY_BACKEND=harbor`; wire the Woodpecker registry secret to `robot$siai-ci` + `harbor.cat-bluegill.ts.net`
- [x] 3.3 Add `.env.homelab` (pg1 `192.168.4.50`, Harbor, OAuth + agent secrets) sourced from the named 1P items (vault `AC-DevOps`); never commit secrets
- [x] 3.4 Configure ingress: two Tailscale sidecars → `gitea.cat-bluegill.ts.net` (HTTPS only, no `:2222`) + `ci.cat-bluegill.ts.net`; set Gitea `ROOT_URL` + Woodpecker `WOODPECKER_HOST` accordingly

## 4. Deploy on the VM (siai)

- [x] 4.1 Place the homelab compose + env on the VM; `docker compose -f docker-compose.yml -f docker-compose.homelab.yml up -d` (no bundled postgres) — VM 107 runs the 5 homelab services, no `siai-postgres`
- [x] 4.2 Bring up tailnet ingress (sidecars/`tailscale serve`) with TLS for `gitea.` + `ci.` — both nodes up (`gitea` 100.103.214.79, `ci` 100.73.148.24), valid Let's Encrypt certs
- [x] 4.3 Configure Woodpecker↔Gitea OAuth (`WOODPECKER_GITEA_CLIENT`/`SECRET`); confirm login flow — `ci/authorize` → 303 to `gitea/login/oauth/authorize` (client_id `955b402d…`)
- [x] 4.4 Configure Gitea OIDC SSO via tsidp: `gitea admin auth add-oauth --name tsidp --provider openidConnect --auto-discover-url https://idp.cat-bluegill.ts.net/.well-known/openid-configuration` (scopes `openid email profile`; key/secret from 1P `tsidp - gitea oidc client`); confirm admin SSO login — "Sign in with tsidp" present on the login page (`/user/oauth2/tsidp`)

## 5. Verify (acceptance — maps to homelab-deployment spec)

- [x] 5.1 Gitea + Woodpecker UIs reachable over the tailnet with valid TLS; a non-tailnet client cannot reach them — both serve valid LE certs over the tailnet; `serve.json` declares HTTPS only (no Funnel → tailnet-only by construction; off-tailnet negative not actively probed)
- [x] 5.2 Gitea + Woodpecker tables live on pg1; no `postgres` container running in the homelab profile — pg1 holds 112 `gitea` + 19 `woodpecker` tables; VM 107 has no postgres container
- [ ] 5.3 Smoke pipeline builds + pushes an image to `harbor.cat-bluegill.ts.net/<project>` via the robot account — **pending**: no demo repo activated / no pipeline run yet (`ci/api/repos` 401, no image under Harbor `direction`)
- [ ] 5.4 Repo data survives a VM restart and is captured by the nightly PVE backup — **pending**: won't restart the live VM; backup coverage of the `/data` state disk is infra-owned (relay ask to home-network)
- [x] 5.5 Local `.localhost` quick-start still works unchanged (bundled postgres + Gitea registry + Traefik) — base `docker-compose.yml` still resolves `postgres`+`traefik`+`gitea`+`wpk-*`; homelab override is additive
- [ ] 5.6 Admin can log into Gitea via tsidp OIDC SSO; Woodpecker↔Gitea CI OAuth still works independently — **pending**: SSO link + OAuth redirect both present (4.3/4.4), but the interactive SSO login round-trip not exercised end-to-end

## 6. Document (infra + siai)

- [ ] 6.1 (infra) Add `hosts/configs/proxmox1/siai.md` (identity, resources, storage, tailnet, ACL, daily-use); ROADMAP move "Deploy siai on px1" Next → Shipped
- [ ] 6.2 (siai) Document the homelab profile (README + CHANGELOG) + config templates
- [ ] 6.3 (siai) Update ROADMAP: deploy-on-px1 done → unblocks "First Real Consumer: Direction"

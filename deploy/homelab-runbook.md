# siai homelab deploy — operator runbook (px1 / VM 107)

> **Purpose.** Execute groups 4–5 of `openspec/changes/deploy-homelab-px1/`
> (live deploy + acceptance). Authored against the live, infra-verified
> substrate (`home-network/docs/2026-05-27-siai-deployment-handoff.md`).
> The siai-side compose + config (group 3) is committed; this is the
> "press play" sequence.
>
> Each phase below maps to one or more tasks in `tasks.md`; check them off
> as you go (or hand the result back to me and I'll mark them).

## 0. Preflight (on m4m, 60 seconds)

```bash
op signin                                                  # 1Password CLI session
ssh -o ConnectTimeout=5 ac@192.168.4.55 'hostname; docker --version; tailscale status | grep -E "\bsiai\b"'
# → siai · Docker version 29.5.x · tailnet line for siai
```

If SSH prompts for a key, the m4m SSH agent is missing the VM's key — load it
or use `ssh -i ~/.ssh/<key>`. Everything else below assumes SSH works.

---

## A. Mint two Tailscale auth-keys (task 4.2 prereq · human step)

The VM's own auth-key was one-shot and is gone. The `gitea` and `ci` sidecars
each join as their own tailnet device → each needs a fresh key. **One-shot ·
pre-approved · `tag:host` · 1-day expiry** (the homelab convention).

1. https://login.tailscale.com → Settings → Keys → **Generate auth key** ×2:
   - Reusable: **no** · Ephemeral: **no** · Pre-approved: **yes**
   - Expiry: **1 day** · Tags: `tag:host`
   - Description: `siai-gitea sidecar` / `siai-ci sidecar`
2. Save each into 1Password (vault **AC-DevOps**) with these *exact* titles
   so the `.env.homelab.example` references match:
   - `siai-gitea - tailnet auth-key - cat-bluegill`
   - `siai-ci - tailnet auth-key - cat-bluegill`
   - Put the key string in the **password** field.

---

## B. Build `.env.homelab` on m4m (task 4.1 prereq)

```bash
cd /Users/ac/_sync/ac-devops/_projects/AI/siai

cat > .env.homelab <<EOF
REGISTRY_BACKEND=harbor

# pg1 (LAN-direct) — note: \`op read\` breaks on the "@" in the item title.
GITEA_DB_PASSWORD=$(op item get "gitea - app role @ pg1"      --vault AC-DevOps --fields password --reveal)
WOODPECKER_DB_PASSWORD=$(op item get "woodpecker - app role @ pg1" --vault AC-DevOps --fields password --reveal)

# Internal Woodpecker secrets — OAuth client/secret are filled in phase E.
WOODPECKER_AGENT_SECRET=$(openssl rand -hex 32)
WOODPECKER_ADMIN=admin
WOODPECKER_GITEA_CLIENT=
WOODPECKER_GITEA_SECRET=

# Tailscale sidecars (auth-keys from phase A).
TS_AUTHKEY_GITEA=$(op read "op://AC-DevOps/siai-gitea - tailnet auth-key - cat-bluegill/password")
TS_AUTHKEY_CI=$(op read    "op://AC-DevOps/siai-ci - tailnet auth-key - cat-bluegill/password")

# Filled in phase D after first sidecar join.
GITEA_TS_IP=
CI_TS_IP=
EOF

# Sanity: every line has a value except the 4 we know are empty for now.
grep -E '^[A-Z_]+=$' .env.homelab
# → WOODPECKER_GITEA_CLIENT=  WOODPECKER_GITEA_SECRET=  GITEA_TS_IP=  CI_TS_IP=
```

---

## C. Stage the repo on the VM and prepare `/data/siai`

```bash
# Stage compose + config to /srv/siai on the VM.
ssh ac@192.168.4.55 'sudo install -d -o ac -g ac /srv/siai && sudo install -d -o 1000 -g 1000 /data/siai/gitea /data/siai/woodpecker && sudo install -d -o ac -g ac /data/siai/ts-gitea /data/siai/ts-ci'

rsync -av --delete \
  --exclude='.git/' --exclude='.venv/' --exclude='node_modules/' --exclude='__pycache__/' \
  --exclude='.env' --exclude='.env.homelab' --exclude='*.backup.*' \
  /Users/ac/_sync/ac-devops/_projects/AI/siai/ \
  ac@192.168.4.55:/srv/siai/

# Ship the secret-bearing env separately (not via rsync) and lock it down.
scp .env.homelab ac@192.168.4.55:/srv/siai/.env.homelab
ssh ac@192.168.4.55 'chmod 600 /srv/siai/.env.homelab'
```

> `/data/siai/gitea` is owned by uid 1000 (the rootless Gitea user). Sidecar
> state dirs are owned by `ac`. `/data/siai` itself is on the state SSD with
> `backup=1` (nightly PVE backup).

---

## D. First-pass `up` + fill sidecar IPs (tasks 4.1 + 4.2)

### D.1 — First pass (extra_hosts falls back to 127.0.0.1)

```bash
ssh ac@192.168.4.55 'cd /srv/siai && docker compose -f docker-compose.yml -f docker-compose.homelab.yml --env-file .env.homelab up -d'
ssh ac@192.168.4.55 'cd /srv/siai && docker compose ps'
# Expect 5 services Up: gitea, gitea-ts, wpk-server, ci-ts, wpk-agent.
# NO siai-postgres, NO siai-traefik (profile local-only is not active).
```

### D.2 — Read the sidecar tailnet IPs

```bash
GITEA_TS_IP=$(ssh ac@192.168.4.55 'docker exec siai-gitea-ts tailscale ip -4 | head -1')
CI_TS_IP=$(   ssh ac@192.168.4.55 'docker exec siai-ci-ts    tailscale ip -4 | head -1')
echo "GITEA_TS_IP=$GITEA_TS_IP · CI_TS_IP=$CI_TS_IP"
```

### D.3 — Write back to `.env.homelab` (m4m + VM) and recreate

```bash
# m4m (the canonical .env.homelab)
sed -i '' -e "s|^GITEA_TS_IP=.*|GITEA_TS_IP=$GITEA_TS_IP|" \
          -e "s|^CI_TS_IP=.*|CI_TS_IP=$CI_TS_IP|"     .env.homelab

scp .env.homelab ac@192.168.4.55:/srv/siai/.env.homelab
ssh ac@192.168.4.55 'chmod 600 /srv/siai/.env.homelab && cd /srv/siai && docker compose -f docker-compose.yml -f docker-compose.homelab.yml --env-file .env.homelab up -d --force-recreate gitea wpk-server'
```

> Recreating `gitea` / `wpk-server` also recreates the sidecars that share
> their netns (`gitea-ts`, `ci-ts`). The sidecars rejoin from their state
> volumes — the auth-keys are only used on first join.

### D.4 — Sanity: tailnet ingress is live

```bash
curl -sf https://gitea.cat-bluegill.ts.net/api/v1/version  | jq
curl -sf https://ci.cat-bluegill.ts.net/healthz             # → 200 / "OK"
# From a non-tailnet network: both should be unreachable (no Funnel).
```

---

## E. Woodpecker ↔ Gitea OAuth (task 4.3)

Done **after** Gitea is up (first admin account is created on first login,
unless you pre-seed; this run uses the SSO admin from phase F — so create the
OAuth app via Gitea's *settings* on the first SSO-logged-in admin).

Alternative (no UI): create via the Gitea API. After SSO admin exists:

```bash
# From m4m, with a PAT generated for the admin user in Gitea Settings → Applications.
GITEA_TOKEN='gtea-xxxxxxxxxxxxxxxxxxxxxxxx'

curl -sS -X POST https://gitea.cat-bluegill.ts.net/api/v1/user/applications/oauth2 \
  -H "Authorization: token $GITEA_TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "name": "woodpecker",
    "redirect_uris": ["https://ci.cat-bluegill.ts.net/authorize"],
    "confidential_client": true
  }' | tee /tmp/wpk-oauth.json

WOODPECKER_GITEA_CLIENT=$(jq -r .client_id     /tmp/wpk-oauth.json)
WOODPECKER_GITEA_SECRET=$(jq -r .client_secret /tmp/wpk-oauth.json)

# Persist (m4m + VM) and recreate wpk-server.
sed -i '' -e "s|^WOODPECKER_GITEA_CLIENT=.*|WOODPECKER_GITEA_CLIENT=$WOODPECKER_GITEA_CLIENT|" \
          -e "s|^WOODPECKER_GITEA_SECRET=.*|WOODPECKER_GITEA_SECRET=$WOODPECKER_GITEA_SECRET|" \
          .env.homelab
scp .env.homelab ac@192.168.4.55:/srv/siai/.env.homelab
ssh ac@192.168.4.55 'chmod 600 /srv/siai/.env.homelab && cd /srv/siai && docker compose -f docker-compose.yml -f docker-compose.homelab.yml --env-file .env.homelab up -d --force-recreate wpk-server'
```

> Store the resulting client_id/secret in 1Password as
> `woodpecker - gitea oauth client (siai)` (vault AC-DevOps) for the record.

---

## F. Gitea OIDC SSO via tsidp (task 4.4)

The tsidp client is already registered by infra (1P `tsidp - gitea oidc client`).

```bash
# Variable names: tsidp item stores client_id in `username`, secret in `password` (no "@" → op read works).
TSIDP_KEY=$(op read "op://AC-DevOps/tsidp - gitea oidc client/username")
TSIDP_SECRET=$(op read "op://AC-DevOps/tsidp - gitea oidc client/password")

ssh ac@192.168.4.55 "docker exec -i siai-gitea gitea admin auth add-oauth \
  --name tsidp \
  --provider openidConnect \
  --auto-discover-url https://idp.cat-bluegill.ts.net/.well-known/openid-configuration \
  --key '$TSIDP_KEY' \
  --secret '$TSIDP_SECRET' \
  --scopes 'openid email profile'"

# Verify the auth source is present
ssh ac@192.168.4.55 'docker exec siai-gitea gitea admin auth list'
```

> The auth source name **must be `tsidp`** — Gitea builds the callback as
> `/user/oauth2/tsidp/callback`, which is what infra registered with tsidp.
> Open https://gitea.cat-bluegill.ts.net → "Sign in with tsidp" → completes
> the round trip.

---

## G. Smoke: pipeline builds + pushes to Harbor (task 5.3)

The Woodpecker agent needs a reachable Harbor for pipeline `docker push` steps.
Pipeline containers run on `siai_devnet` and don't inherit MagicDNS, so pin
Harbor's tailnet IP via the agent's `WOODPECKER_BACKEND_DOCKER_EXTRA_HOSTS`.

```bash
# Get Harbor's tailnet IP (from any tailnet-connected host):
HARBOR_TS_IP=$(tailscale status | awk '/\bharbor\b/{print $1}')
echo "HARBOR_TS_IP=$HARBOR_TS_IP"

# Add to .env.homelab and a small agent override.
echo "HARBOR_TS_IP=$HARBOR_TS_IP" >> .env.homelab
```

Add the following to the agent service in `docker-compose.homelab.yml` (or
create `docker-compose.homelab.smoke.yml` if you'd rather keep it isolated):

```yaml
  wpk-agent:
    environment:
      - WOODPECKER_BACKEND_DOCKER_EXTRA_HOSTS=gitea:gitea,harbor.cat-bluegill.ts.net:${HARBOR_TS_IP}
```

Then in Woodpecker UI (`https://ci.cat-bluegill.ts.net`), add **org-level secrets**:

| Name              | Value                                                                |
|-------------------|----------------------------------------------------------------------|
| `registry_url`    | `harbor.cat-bluegill.ts.net`                                         |
| `registry_username` | `robot$siai-ci`                                                    |
| `registry_password` | `op read "op://AC-DevOps/harbor - siai-ci robot/credential"` ⚠ field is `credential`, not `password` |

Then enable the existing `demo` repo in Woodpecker, mark it **trusted**, push
a tag → `build` + `push` steps land an image at
`harbor.cat-bluegill.ts.net/direction/demo-app:<tag>`.

---

## H. Acceptance (group 5)

| Task | Check |
|------|-------|
| 5.1  | `curl -sf https://gitea.cat-bluegill.ts.net/api/v1/version` + `…/ci.cat-bluegill.ts.net/healthz` from tailnet (200); from non-tailnet (unreachable) |
| 5.2  | `ssh pg1 'psql -d gitea -c "\dt" \| head'` shows Gitea tables; `docker ps` on VM has no `siai-postgres` |
| 5.3  | Smoke pipeline pushes to `harbor.cat-bluegill.ts.net/direction/demo-app:<tag>` (phase G) |
| 5.4  | `docker compose restart` on the VM → Gitea repos still load; PVE shows the next nightly backup including `/data/siai` |
| 5.5  | On m4m (local POC): `just docker-up` → bundled postgres + Traefik come up unchanged; `gitea.localhost` works |
| 5.6  | Gitea login via tsidp succeeds; Woodpecker → Gitea OAuth login still works (independent flows) |

---

## Rollback

```bash
ssh ac@192.168.4.55 'cd /srv/siai && docker compose -f docker-compose.yml -f docker-compose.homelab.yml --env-file .env.homelab down'
# Optional: keep /data/siai for forensic / restart; remove if abandoning:
ssh ac@192.168.4.55 'sudo rm -rf /data/siai'
# Infra-side teardown (separate, in home-network): VM 107, pg1 DBs, Harbor robot, tsidp client, ACL legs.
```

VM teardown does **not** affect the local `.localhost` quick-start on m4m.

---

## Group 6 follow-ups (docs)

- (siai) Add a `just docker-up-homelab` recipe to `Justfile` and document the
  homelab profile in `README.md` + `CHANGELOG.md` (task 6.2).
- (siai) Update `ROADMAP.md`: deploy-on-px1 ✅ → unblocks "First Real Consumer:
  Direction" (task 6.3).
- (infra) `hosts/configs/proxmox1/siai.md` (task 6.1) — owned by home-network.

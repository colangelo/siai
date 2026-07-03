---
type: learning
title: "Pipeline clone DNS + tailnet reach (VM 107)"
description: "Why every pipeline clone failed on the homelab stack: Docker substitutes public DNS for the loopback resolver (no MagicDNS in pipeline containers) + a missing tailnet ACL grant to ts-siai-gitea:443. Fixed at platform layer for all repos."
tags: [woodpecker, dns, tailscale, homelab]
timestamp: 2026-05-28
---

# Pipeline clone DNS + tailnet reach (VM 107)

**Date:** 2026-05-28
**Context:** Onboarding **Direction** as the first real (non-demo) project on the
siai stack (Gitea → Woodpecker → Harbor). Repo activated, marked trusted-volumes,
Harbor robot secrets set — but every pipeline failed at the built-in **clone**
step. This documents the root cause and the two-part fix.

## Symptom

```
+ git fetch ... origin +<sha>:
fatal: unable to access 'https://gitea.cat-bluegill.ts.net/ac/direction.git/':
Could not resolve host: gitea.cat-bluegill.ts.net (DNS server returned answer with no data)
exit status 128
```

## Root cause (two stacked problems)

Woodpecker's docker backend spawns each pipeline step (including the built-in
clone) as a container on the `siai_devnet` **bridge** network. Two things broke
the clone, which uses the public URL `https://gitea.cat-bluegill.ts.net` (derived
from `WOODPECKER_GITEA_URL`):

1. **DNS.** VM 107's host `/etc/resolv.conf` is the systemd-resolved stub
   (`127.0.0.53`). Docker detects a loopback resolver and substitutes its default
   public DNS (8.8.8.8) for containers — which cannot resolve tailnet MagicDNS
   names. So `gitea.cat-bluegill.ts.net` didn't resolve inside pipeline containers.

2. **Tailnet reach + ACL.** Pipeline containers have **no tailnet interface**;
   they SNAT out through the host's `tailscale0` as the **`ts-siai`** node. Gitea
   is fronted by a `tailscale serve` sidecar on `:443`, and **serve enforces
   tailnet ACLs**. The ACL granted `ts-siai → ts-harbor:443, tag:tsidp:443` but
   **not** `ts-siai → ts-siai-gitea:443`. So even once DNS was fixed, the clone's
   TCP `:443` to Gitea would time out. (`tailscale ping gitea` succeeds — that's
   WireGuard reachability, not an ACL-gated TCP connection — which is why the gap
   was easy to miss.)

The only path that worked unconditionally was the in-stack `http://gitea:3000`
(devnet service name), but stock Woodpecker has no separate "internal clone URL",
so we fixed the public path instead.

> Aside: the agent's VM-only overlay (`docker-compose.homelab.smoke.yml`) set
> `WOODPECKER_BACKEND_DOCKER_EXTRA_HOSTS=gitea:gitea,harbor…` — `gitea:gitea` is an
> invalid `--add-host` (the "IP" is `gitea`; `docker run` rejects it). It never
> contributed to clone resolution. With the daemon-DNS fix below, the
> `EXTRA_HOSTS` override is **redundant for pipeline DNS** and can be dropped or
> corrected in a later cleanup.

## Fix

### 1. Tailnet ACL grant (home-network repo)

`tailscale/acl.hujson` — add `ts-siai-gitea:443` to the `ts-siai` grant:

```hujson
{
  "action": "accept",
  "src":    ["ts-siai"],
  "dst":    ["ts-harbor:443", "tag:tsidp:443", "ts-siai-gitea:443"],
},
```

Apply: `just ts-acl-push` (from `~/_sync/ac-devops/_projects/Infra/home-network`).
Committed in home-network as `feat(tailscale): grant ts-siai -> ts-siai-gitea:443
for Woodpecker pipeline clone`.

### 2. Docker daemon container DNS → MagicDNS (VM 107 host)

VM 107 is already a tailnet node (`siai`, 100.96.2.116) with MagicDNS. Point the
Docker daemon's container DNS at the MagicDNS resolver so spawned containers
resolve tailnet names (and still forward public queries):

`/etc/docker/daemon.json`:

```json
{
  "dns": ["100.100.100.100", "1.1.1.1"]
}
```

```bash
sudo systemctl restart docker          # bounces the stack (restart: unless-stopped brings it back)
cd /srv/siai && docker compose -f docker-compose.yml -f docker-compose.homelab.yml \
  -f docker-compose.homelab.smoke.yml --env-file .env.homelab up -d   # reconcile
```

> `100.100.100.100` answers tailnet MagicDNS and forwards public queries to the
> host's upstream resolvers; `1.1.1.1` is a fallback only used if MagicDNS is
> unreachable. This is **host-level config**, not part of the compose deploy —
> it must be reapplied if VM 107 is rebuilt.

## Verification

From a fresh pipeline-equivalent container:

```bash
docker run --rm --network siai_devnet alpine:3 sh -c '
  apk add --no-cache curl >/dev/null
  getent hosts gitea.cat-bluegill.ts.net      # -> 100.103.214.79
  curl -sk -o /dev/null -w "%{http_code}\n" https://gitea.cat-bluegill.ts.net/   # -> 200
  getent hosts github.com                     # public DNS still resolves
'
```

All three pass after the fix. A Woodpecker pipeline then clones, lints, and tests
green; image build + push to Harbor runs on `v*` tags.

## Reusable takeaway for the next onboarded repo

Clone-from-pipeline is now solved at the platform layer — no per-repo workaround
needed. Any new repo: activate in Woodpecker, mark **trusted-volumes** (for the
docker.sock build step), and add the Harbor robot secrets. The DNS + ACL plumbing
here applies to all repos on the stack.

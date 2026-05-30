# Forgejo vs Gitea — migration study (siai homelab)

> **Status: DEFERRED / for-reconsideration.** This is a point-in-time research
> record (2026-05-30), not a committed decision and not an OpenSpec change. It
> captures everything studied — findings, the flank-then-replace plan, the risk
> audit, and the open doubts — so a future session can pick it up cold and
> decide. No code, infra, or relay action has been taken.
>
> **Trigger:** "I'd like to explore replacing Gitea with Forgejo — flank it
> first, then replace; find possible problems given they're diverging."
>
> **Current state when studied:** siai deployed on px1 VM 107 (deploy-homelab-px1,
> 20/26), running **Gitea 1.26.2** rootless, pg1 Postgres (LAN-direct), Harbor
> registry, two Tailscale sidecars (`gitea.`/`ci.`), Woodpecker CI, tsidp OIDC
> SSO. Repos in Gitea: `ac/siai`, `ac/home-network`, `ac/direction` + the agent
> relay. **Effectively a fresh instance with ~no issues/PRs/2FA history.**

---

## 1. Headline finding (the thing that shapes everything)

**There is no transparent / drop-in migration from Gitea 1.26 → Forgejo.**
Official Forgejo migration support tops out at **Gitea 1.22 → Forgejo 10.x**.
We are on **1.26.2**, well past the cutoff.

Forgejo *deliberately dropped* the migration paths for Gitea ≥ 1.23 because the
two databases diverged after the 2024 hard fork and keeping the migrations
working became too costly. Quote from the Forgejo compatibility announcement:
maintaining Gitea→Forgejo compatibility was "an exceptional effort … coming to
an end as the two codebases diverge more and more."

**Implication:** a swap of `gitea/gitea:1.26` → `codeberg.org/forgejo/forgejo`
against the *same database* will **not** work. The DB schema migrations are no
longer compatible (diverged in actions indices, protected-branch priority,
admin branch protection, webhooks re-architecture, etc.).

### Migration paths that *do* exist for 1.26

| Path | What it is | Caveats |
|------|-----------|---------|
| **Per-repo API migration** | Forgejo's in-app "migrate repository" tool pulls each repo from Gitea over the API | Works only while Gitea's API stays stable; moves repo + issues/PRs/releases; **uncertain** what it drops (see doubts) |
| **Unofficial script** [`nicoverbruggen/gitea-to-forgejo`](https://github.com/nicoverbruggen/gitea-to-forgejo) | Targets Gitea **1.26 → Forgejo 15.0** specifically, via backup + Podman | **2FA & WebAuthn tokens NOT transferred** (security risk); manual verification required; needs podman/sqlite3/curl/python3/git |
| **DB version-downgrade hack** | `UPDATE version SET version=NNN WHERE id=1` then run Forgejo binary | **Unsupported, best-effort.** Exact version int for 1.26 unknown. Community reports of it half-working then failing the web UI |
| **Third-party API tool** [`visteras/gitea-to-forgejo-migrator`](https://github.com/visteras/gitea-to-forgejo-migrator) | REST-API copy of users/orgs/repos | Same class as per-repo; API-level only |

### The reframe that makes this easy *for us*

Because siai is a **fresh** instance, the only "data" is three repos that exist
as local git checkouts and are re-pushable. There are ~no issues, PRs, packages,
or 2FA enrollments worth preserving. **So we should skip data migration entirely:
stand up a clean Forgejo and re-seed by `git push`.** The painful, lossy,
unsupported part of the problem is *avoidable* — but only while the instance is
young. The cost of switching is near-zero **now** and rises monotonically as
real CI history, issues, packages, and 2FA accumulate. **If we switch, sooner is
strictly cheaper than later.**

---

## 2. Background — why Gitea and Forgejo diverged

- **2016**: Gitea forks from Gogs — lightweight self-hosted GitHub alternative.
- **Late 2022**: A group of contributors fork Gitea to create **Forgejo**, over
  governance concerns — Gitea Ltd (now **CommitGo Inc.**), a for-profit, took
  ownership of the domain/trademark; community felt development shifted away from
  community control. Forgejo lands under **Codeberg e.V.** (German non-profit).
- **2023**: Forgejo is a **soft fork** — a patch set on top of Gitea, re-synced
  regularly. Migration in either direction is trivial.
- **Early–mid 2024**: Forgejo becomes a **hard fork** (governance issue #58).
  Codebases begin to diverge; Forgejo adopts **GPL-3.0** (vs Gitea's **MIT**).
- **Dec 2024**: Forgejo announces **Gitea 1.22 is the last transparently
  upgradable version**.
- **2025–2026**: Continued divergence. Forgejo ships **federation (ActivityPub /
  ForgeFed)** — federated repo "stars" landed in 2025, with federated PRs/issues
  on the roadmap. Gitea has **no** federation work. Forgejo v15.0 released
  **April 2026**.

### What actually differs (2026)

| Dimension | Gitea | Forgejo |
|-----------|-------|---------|
| Governance | CommitGo Inc. (for-profit) | Codeberg e.V. (non-profit) |
| License | MIT (permissive) | GPL-3.0 (copyleft) |
| Federation | none | active (ActivityPub/ForgeFed, still experimental) |
| Testing | "example browser test" only; weaker E2E/upgrade tests | claims more rigorous E2E + upgrade tests |
| Open-core | small cloud-only closed portion | fully FOSS |
| CI | Gitea Actions | Forgejo Actions (shipped Actions ahead of Gitea) |

**Crucial nuance repeated across sources:** the *software itself* is "not a
dramatic difference" — UIs nearly identical, APIs compatible. The real deltas
are **governance, license, and federation**. Multiple 2026 guides call Gitea the
"safest default" and Forgejo the pick "when governance / Codeberg alignment /
privacy direction matter more than staying closest to upstream."

---

## 3. The flank-then-replace plan (as studied)

Non-destructive coexistence first, then a clean cutover. Mirrors how we built
the existing homelab profile, so the patterns are familiar.

### Phase 0 — Decide it's worth it
The diff is mostly governance/federation/license. If those don't move us, Gitea
1.26 is fine and this is cost-without-benefit. It is also a **one-way door** —
Forgejo→Gitea is equally unsupported now. Make this an explicit decision, not a
default.

### Phase 1 — Flank (Forgejo beside Gitea, nothing destructive)
- **New pg1 DB** `forgejo` (role + database). **Never share Gitea's DB.**
  → *infra dependency (home-network relay).*
- **New compose pair** in `docker-compose.forgejo.yml`:
  - `forgejo`: `codeberg.org/forgejo/forgejo:15-rootless`
  - data → `/data/siai/forgejo-data:/var/lib/gitea`
  - `forgejo-ts`: third Tailscale sidecar → **`forgejo.cat-bluegill.ts.net`**
    (`network_mode: service:forgejo`, same pattern as `gitea-ts`/`ci-ts`).
- **Infra dependencies (relay to home-network):**
  - tsidp OIDC client, redirect
    `https://forgejo.cat-bluegill.ts.net/user/oauth2/tsidp/callback`
  - ACL leg `ts-forgejo → tag:tsidp:443` (server-side OIDC back-channel — the
    exact leg that previously broke proxmox1 OIDC; do not omit)
  - one-shot tailnet auth-key for the sidecar (human mint)
  - pg1 is LAN-direct → **no** pg1 ACL.
- Gitea stays fully live and untouched. **Rollback = remove the forgejo services.**

### Phase 2 — Seed & validate
- Re-push the 3 repos: `git remote add forgejo … && git push forgejo main`
  (the relay dirs come along as tracked files).
- Validate Forgejo over the tailnet: UI, TLS, tsidp SSO login, git clone/push.
- Keep CI on Gitea for now (don't disturb Woodpecker yet).

### Phase 3 — Cutover (replace)
- Recreate the **Woodpecker OAuth app in Forgejo** (prefer a **system-wide/admin
  OAuth app** since we own both sides), then flip Woodpecker's forge config:
  `WOODPECKER_GITEA*` → **`WOODPECKER_FORGEJO` / `_URL` / `_CLIENT` / `_SECRET`**
  (separate, **experimental** driver). Recreate `wpk-server`.
- Re-activate repos in Woodpecker and **re-add secrets** (the Harbor robot push
  secret etc.) — forge user-IDs change, so activations/secrets don't carry over.
- **Hostname strategy for stable URLs:** flank under `forgejo.`, but at cutover
  stop Gitea + its sidecar and set the Forgejo sidecar's `TS_HOSTNAME=gitea` so
  existing clone URLs/bookmarks keep working. Update `ROOT_URL`; infra updates
  the tsidp redirect to the `gitea.` callback. (Alternative: adopt `forgejo.` as
  the new canonical name — cleaner, but breaks existing URLs. See doubts.)
- Smoke: clone over tailnet, SSO login, run a pipeline → push to Harbor.

### Phase 4 — Decommission
- Stop Gitea. **Keep** `/data/siai/gitea-*` and a pg1 `gitea` DB dump as a cold
  backup for N days. Drop nothing until fully confident (one-way door).

---

## 4. Technical specifics gathered (for the eventual implementation)

- **Image:** `codeberg.org/forgejo/forgejo:15-rootless` (current major v15,
  Apr 2026). Rootless data dir = `/var/lib/gitea` (rootful uses `/data`).
- **⚠ v15 rootless config-path change:** default app.ini moved from
  `/etc/gitea/app.ini` → `/var/lib/gitea/custom/conf/app.ini`, and the v8-era
  backward-compat shim was **removed** in v15. Our deployment is **env-driven**
  (`GITEA__*` env vars), which Forgejo still honors, so this largely sidesteps
  us; if an app.ini bind is needed, set `GITEA_APP_INI` explicitly. Our current
  `/etc/gitea` bind would otherwise be ignored.
- **Permissions:** rootless runs as non-root → host dirs must be chown'd to the
  container UID/GID (1000) before first start or it fails with
  `mkdir: can't create directory '/var/lib/gitea/git': Permission denied`.
- **Env prefix:** Forgejo honors the `GITEA__` prefix "for compatibility … may
  change in the future." Recommended to pass **both** `GITEA__` and `FORGEJO__`.
- **Woodpecker Forgejo forge:** built-in but **experimental**; separate driver
  from Gitea. Vars: `WOODPECKER_FORGEJO=true`, `_URL`, `_CLIENT`, `_SECRET`;
  callback `https://<host>/authorize`. Agent must reach Forgejo (same docker
  network — we have `devnet`). Prefer a **system-wide** OAuth app when you
  administer both forge and CI.

---

## 5. Problems / risks audit

| # | Problem | Bites us? | Mitigation |
|---|---------|-----------|------------|
| 1 | No transparent 1.26→Forgejo DB migration | Would be severe | Re-seed instead of migrate (data ≈ 0) |
| 2 | Lossy migration: 2FA/WebAuthn, packages, issue IDs/timestamps | Low (fresh) | N/A when re-seeding |
| 3 | Woodpecker Forgejo driver is **experimental**; forge user-IDs change | Medium | Re-activate repos, re-add secrets, expect quirks |
| 4 | Forgejo v15 rootless config-path change | Low | Env-driven config; set `GITEA_APP_INI` if needed |
| 5 | Shared-infra cross-talk (others hit it via shared Redis/DB) | Low | Separate `forgejo` pg1 DB; our stack has **no Redis** |
| 6 | tsidp SSO: new redirect + OIDC ACL back-channel leg | Medium (infra) | Relay to home-network (same pattern as deploy) |
| 7 | Env-prefix drift (`GITEA__` honored "for now") | Low / later | Set both prefixes; pin major; watch release notes |
| 8 | One-way door + ongoing divergence | Strategic | Accept consciously; Gitea features won't backport |
| 9 | GPL-3.0 vs MIT | None (self-host) | Only matters if redistributing modifications |
| 10 | Federation is experimental, not production-default | Low | Treat ActivityPub as opt-in if enabled at all |

---

## 6. Open questions & doubts (resolve before committing)

These are genuinely unresolved or assumption-laden — flagged honestly for the
reconsideration pass:

1. **Is the switch even justified?** The software is near-identical; the case
   rests entirely on governance (non-profit Codeberg vs CommitGo Inc.),
   copyleft licensing, and a federation roadmap that is still *experimental*. If
   none of these are real drivers for this homelab, the honest answer may be
   "stay on Gitea 1.26." This study does **not** assume the switch is correct.
2. **Re-seed vs migrate — confirm data really is disposable.** Need to actually
   enumerate Gitea state at decision time: any issues/PRs opened? packages
   pushed to Gitea's registry (we use Harbor, so likely none)? wiki content?
   webhooks beyond Woodpecker? user accounts beyond `ac`? If yes to any, the
   re-seed assumption weakens.
3. **What exactly does per-repo API migration drop?** Uncertain coverage of LFS,
   wiki, releases/attachments, labels/milestones, and timestamps. Untested.
4. **Hostname end-state:** land Forgejo on the `gitea.` name (stable URLs, but
   semantically odd — a node called `gitea` running Forgejo) vs adopt `forgejo.`
   as canonical (clean, but breaks every existing clone URL, Woodpecker remote,
   and bookmark, and needs a tsidp redirect change). Unresolved UX/cleanliness
   tradeoff.
5. **tsidp client:** new dedicated client for Forgejo vs reuse/repoint the
   existing Gitea one. Likely new client; not confirmed.
6. **Woodpecker forge swap blast radius:** changing the forge identity likely
   orphans existing repo activations, trusted-repo flags, and secrets. Need to
   confirm whether anything beyond re-activation + re-adding the Harbor secret is
   required (e.g., agent re-registration, webhook re-creation).
7. **v15 as the target:** is the latest major the right pin, or should we track
   the current Forgejo **LTS** for a homelab? Not decided.
8. **Source reliability:** some comparison articles cited inconsistent version
   numbers (e.g. a stray "Forgejo 1.0.0/1.3.0"); the version facts here are
   anchored to forgejo.org's own announcements/docs, but secondary blog details
   (e.g. the DB-downgrade integer) should be re-verified at implementation time.
9. **Do we actually want a one-way door now?** deploy-homelab-px1 isn't even
   fully closed (5.3/5.4/5.6 pending; infra relay outstanding). Layering a forge
   swap on top of an unfinished deploy may be premature sequencing.

---

## 7. Tentative recommendation (non-binding)

If — and only if — governance/licensing/federation are genuine drivers:
**flank a clean Forgejo 15 now and re-seed (no data migration)**, because the
switch cost is at its lifetime minimum while the instance is fresh. Otherwise,
**stay on Gitea 1.26** and revisit if/when federation or governance becomes a
concrete need. Either way, **finish deploy-homelab-px1 first** rather than
stacking a one-way migration on an unfinished deployment.

Decision: **deferred** (per request, to reconsider later).

---

## 8. Sources

- Forgejo — Gitea 1.22 is the last transparent upgrade: https://forgejo.org/2024-12-gitea-compatibility/
- Forgejo — official Gitea-migration docs: https://forgejo.org/docs/latest/admin/upgrade/from-gitea/
- Forgejo — Docker/rootless installation: https://forgejo.org/docs/latest/admin/installation/docker/
- Forgejo — v15.0 release (Apr 2026): https://forgejo.org/2026-04-release-v15-0/
- Forgejo — comparison with Gitea: https://forgejo.org/compare-to-gitea/
- Forgejo — forking forward (hard fork rationale, 2024-02): https://forgejo.org/2024-02-forking-forward/
- Forgejo governance #58 — hard-fork agreement: https://codeberg.org/forgejo/governance/issues/58
- Forgejo discussions #244 — proposal to drop ≥1.23 migration: https://codeberg.org/forgejo/discussions/issues/244
- Forgejo forgejo #7638 — Gitea 1.23 migration help: https://codeberg.org/forgejo/forgejo/issues/7638
- Unofficial script — nicoverbruggen/gitea-to-forgejo (1.26→15): https://github.com/nicoverbruggen/gitea-to-forgejo
- Third-party API tool — visteras/gitea-to-forgejo-migrator: https://github.com/visteras/gitea-to-forgejo-migrator
- Woodpecker CI — Forgejo forge docs: https://woodpecker-ci.org/docs/2.8/administration/forges/forgejo
- Migration write-up (the long way) — msfjarvis.dev: https://msfjarvis.dev/posts/migrating-from-gitea-to-forgejo-the-long-way/
- Self-hosted Git comparison 2026 — pkgpulse: https://www.pkgpulse.com/guides/gitea-vs-forgejo-vs-gogs-self-hosted-git-platforms-2026

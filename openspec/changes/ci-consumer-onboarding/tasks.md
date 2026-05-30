# Tasks: Formalize CI consumer onboarding (reference: Direction)

> Retroactive + template scope. The flow is already proven by `ac/direction`
> (CI-built through `v0.26.8`); these tasks document it and extract a reusable
> template. No second consumer, no automation. Verify each step against
> Direction's actual setup (`direction/.woodpecker.yml`,
> `direction/docs/guide-ci-triggers.md`).

## 1. Reusable pipeline template

- [ ] 1.1 Add `templates/.woodpecker.consumer.yml` derived from Direction's pipeline: lint + test gate (`event: [push, pull_request, manual]`) and a tag-gated `build-push` (`event: tag`, `ref: refs/tags/v*`) pushing to `harbor.cat-bluegill.ts.net/<project>/<image>:<tag>`
- [ ] 1.2 Parameterize the template with clear placeholders (`<project>`, `<image>`, build context/Dockerfile) and inline comments; read `registry_url`/`registry_username`/`registry_password` from secrets only — no literals
- [ ] 1.3 Note the trusted-repo + `docker.sock` requirement in a header comment of the template

## 2. Onboarding runbook

- [ ] 2.1 Write `docs/onboard-ci-consumer.md` covering the end-to-end flow: (a) Gitea repo, (b) Harbor project + `robot$siai-ci` scope via infra relay, (c) Woodpecker activate + mark **Trusted**, (d) registry secrets, (e) add `.woodpecker.yml` from the template, (f) trigger + verify
- [ ] 2.2 Document the **infra relay** step concretely (relay file to home-network for a Harbor project + robot scope) — reuse the `siai`-project ask as the worked example; reference 1P `harbor - siai-ci robot` (`credential` field)
- [ ] 2.3 Document the Woodpecker **secrets** (`registry_url`, `registry_username=robot$siai-ci`, `registry_password=`the robot credential) and the **Trusted** flag as an admin-only, security-relevant step
- [ ] 2.4 Document triggers + verification (push → gate; `git tag vX.Y.Z` → build-push; check Harbor for the image) — link Direction's `guide-ci-triggers.md` as the live trigger reference

## 3. Reference consumer + cross-links

- [ ] 3.1 Record `ac/direction` in the runbook as the reference consumer with already-met acceptance (CI-built + pushed to Harbor through `v0.26.8`)
- [ ] 3.2 Link the runbook from README; cross-reference `docker-compose.homelab.smoke.yml` (agent Harbor reachability) and the `homelab-deployment` capability

## 4. Docs + roadmap

- [ ] 4.1 Update README (point to `docs/onboard-ci-consumer.md`) and CHANGELOG (`0.4.5` entry: consumer-onboarding capability + template)
- [ ] 4.2 Update ROADMAP: mark v0.4.5 **Shipped**, reframed to "formalize + templatize CI consumer onboarding (reference: Direction)"; note deferred follow-ons (second consumer, onboarding automation)

## 5. Verify

- [ ] 5.1 Cross-check every runbook step against Direction's real setup — no step is missing or contradicts what made `ac/direction` build + push
- [ ] 5.2 `openspec validate ci-consumer-onboarding --strict` passes

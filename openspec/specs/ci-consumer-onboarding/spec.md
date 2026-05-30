# ci-consumer-onboarding Specification

## Purpose
TBD - created by archiving change ci-consumer-onboarding. Update Purpose after archive.
## Requirements
### Requirement: Documented Onboarding Runbook
The project SHALL provide a siai-owned runbook that describes, end-to-end, how to onboard a real repository to the CI/CD stack, such that a maintainer can follow it without reverse-engineering a prior consumer.

#### Scenario: Runbook covers the full flow
- **WHEN** a maintainer needs to onboard a new repository
- **THEN** the runbook documents every step: creating/locating the Gitea repository, obtaining the Harbor project + robot scope, activating and trusting the repository in Woodpecker, configuring the registry secrets, and adding the pipeline definition
- **AND** the runbook is reachable from the repository documentation (README)

#### Scenario: Runbook is grounded in a working consumer
- **WHEN** the runbook is followed
- **THEN** each step matches the configuration that makes the reference consumer (`ac/direction`) build and push successfully

### Requirement: Reusable Pipeline Template
The project SHALL provide a reusable `.woodpecker.yml` consumer template that a new repository can adopt as its CI starting point.

#### Scenario: Template gates on change and builds on tags
- **WHEN** a consumer adopts the template
- **THEN** the template defines a lint + test gate that runs on push / pull_request / manual events
- **AND** a build-push step gated to version tags (`event: tag`, `ref: refs/tags/v*`) that pushes to `harbor.cat-bluegill.ts.net/<project>/<image>:<tag>`

#### Scenario: Template references secrets, not literals
- **WHEN** the template's build-push step authenticates to the registry
- **THEN** it reads `registry_url`, `registry_username`, and `registry_password` from Woodpecker secrets
- **AND** no registry credentials are committed in the template

### Requirement: Per-Consumer Harbor Scope via Infra Relay
The onboarding process SHALL obtain each consumer's Harbor project and registry push access by requesting, via the cross-repo agent relay to home-network, a Harbor project and `robot$siai-ci` scope for that project — rather than provisioning Harbor from siai or minting a new robot.

#### Scenario: Harbor scope is requested from infra
- **WHEN** a new consumer needs a registry push target
- **THEN** the runbook directs the maintainer to relay home-network for a Harbor project and `robot$siai-ci` push/pull scope on it
- **AND** the existing robot is re-scoped (not replaced), with its token referenced from 1Password (`harbor - siai-ci robot`, `credential` field)

### Requirement: Trusted Repository for Socket Builds
The onboarding process SHALL document that a consumer whose pipeline mounts the host Docker socket MUST be marked Trusted in Woodpecker, and SHALL identify this as an administrator-only, security-relevant step.

#### Scenario: Socket-mounting pipeline requires trust
- **WHEN** a consumer's build step mounts `/var/run/docker.sock`
- **THEN** the runbook requires the repository to be marked Trusted in Woodpecker by an administrator
- **AND** the runbook flags this as granting host Docker access

### Requirement: Reference Consumer Documented
The onboarding capability SHALL document `ac/direction` as the reference consumer and record that it satisfies the onboarding acceptance.

#### Scenario: Direction is recorded as the proven reference
- **WHEN** the capability is reviewed
- **THEN** `ac/direction` is documented as the reference consumer with a real `.woodpecker.yml`
- **AND** its acceptance is recorded as already-met (CI-built and pushed to Harbor through tag `v0.26.8`)


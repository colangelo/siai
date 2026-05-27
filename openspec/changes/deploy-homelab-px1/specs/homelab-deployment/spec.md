# homelab-deployment Specification

## Purpose

Production deployment of the siai CI/CD stack (Gitea + Woodpecker) on the homelab host (`proxmox1`/px1), integrated with the homelab substrate (pg1 Postgres, Harbor registry, tailnet), as an additive profile that does not disturb the local `.localhost` POC.

## ADDED Requirements

### Requirement: Dedicated px1 Deployment Host
The homelab deployment SHALL run the siai stack (Gitea, Woodpecker server, Woodpecker agent, Traefik) on a dedicated VM on `proxmox1`, provisioned with Docker CE and Tailscale, separate from the local POC and from other application compose tenants.

#### Scenario: Stack runs on its own VM
- **WHEN** the homelab deployment is applied
- **THEN** a dedicated px1 VM runs the siai compose stack with Docker CE and Tailscale
- **AND** the stack does not share a host with other application compose tenants (e.g. VM 100)

#### Scenario: Woodpecker agent builds via the host Docker daemon
- **WHEN** a pipeline runs an image-build step
- **THEN** the Woodpecker agent executes it via the VM's Docker daemon (`/var/run/docker.sock`)
- **AND** the build does not require LXC nesting workarounds

### Requirement: External PostgreSQL on pg1
The homelab deployment SHALL use the homelab `pg1` Postgres instance for the Gitea and Woodpecker databases and SHALL NOT run a bundled `postgres` container.

#### Scenario: Gitea and Woodpecker use pg1
- **WHEN** the homelab profile starts
- **THEN** Gitea and Woodpecker connect to dedicated `gitea` and `woodpecker` databases on `pg1`
- **AND** no `postgres` service is started in the homelab profile

#### Scenario: Database address does not depend on MagicDNS
- **WHEN** a service resolves `pg1`
- **THEN** it reaches pg1 via a stable address (LAN IP or `extra_hosts`) rather than relying on MagicDNS

### Requirement: External Container Registry on Harbor
The homelab deployment SHALL push built images to the existing homelab Harbor registry using a scoped robot account, with `REGISTRY_BACKEND=harbor`.

#### Scenario: Woodpecker pushes to Harbor
- **WHEN** a tag-gated pipeline build completes
- **THEN** the image is pushed to `harbor.cat-bluegill.ts.net/<project>/<repo>:<tag>`
- **AND** authentication uses a Harbor robot account scoped to the target project

#### Scenario: No bundled registry on the homelab
- **WHEN** the homelab profile is active
- **THEN** the bundled/optional Harbor compose is not started
- **AND** Gitea's built-in registry is not used as the push target

### Requirement: Tailnet Ingress with TLS
The homelab deployment SHALL expose the Gitea and Woodpecker web UIs over the tailnet with TLS, and SHALL NOT expose them on the public internet.

#### Scenario: UIs reachable over the tailnet
- **WHEN** an authorized tailnet device opens the Gitea or Woodpecker URL
- **THEN** the service responds over HTTPS with a valid tailnet certificate

#### Scenario: Not publicly reachable
- **WHEN** a client that is not on the tailnet attempts to reach the services
- **THEN** the request does not succeed (tailnet-only; no Funnel)

### Requirement: Tailnet Access Control
The homelab deployment SHALL be governed by tailnet ACL rules that grant the deployment node access to its dependencies and grant administrators access to the node.

#### Scenario: Node reaches its dependencies
- **WHEN** the deployment node connects to `pg1:5432` or `harbor:443`
- **THEN** the ACL permits the connection

#### Scenario: Admins reach the node
- **WHEN** an administrator device connects to the deployment node's UI or SSH
- **THEN** the ACL permits the access
- **AND** non-administrative tailnet devices do not get administrative access

### Requirement: Persistent Storage and Backup
The homelab deployment SHALL persist Gitea repository data and Woodpecker state on durable storage covered by host-level backup; CI build workspaces MAY be ephemeral.

#### Scenario: Repo data persists and is backed up
- **WHEN** the VM or its containers restart
- **THEN** Gitea repositories and Woodpecker state are retained on the state-SSD data disk
- **AND** that data is included in the host's nightly PVE backup

### Requirement: Non-Breaking Local POC
The homelab deployment SHALL be additive and SHALL NOT break the local `.localhost` quick-start.

#### Scenario: Local quick-start still works
- **WHEN** a developer runs the local stack without the homelab profile
- **THEN** the bundled Postgres, Gitea built-in registry, and Traefik `*.localhost` routing operate unchanged

# ci-pipeline Specification Delta

## ADDED Requirements

### Requirement: Registry Abstraction in Pipelines
CI pipelines SHALL support pushing to different registry backends without code changes.

#### Scenario: Push to Gitea registry (default)
- **WHEN** pipeline runs and `REGISTRY_URL` secret is not set
- **THEN** pipeline uses `127.0.0.1` as registry URL
- **AND** images are pushed to Gitea's built-in registry

#### Scenario: Push to Harbor registry
- **WHEN** pipeline runs and `REGISTRY_URL` secret is set to `registry.localhost`
- **THEN** pipeline uses Harbor as registry
- **AND** images are pushed to `registry.localhost/<project>/<repo>:<tag>`

#### Scenario: Registry authentication
- **WHEN** pipeline pushes to Harbor
- **THEN** pipeline uses `HARBOR_ROBOT_TOKEN` secret for authentication
- **AND** docker login uses robot account credentials

### Requirement: Vulnerability Scan Results
CI pipelines SHALL support optional vulnerability scanning results when Harbor with Trivy is enabled.

#### Scenario: Scan after push
- **WHEN** image is pushed to Harbor with Trivy enabled
- **THEN** Harbor automatically scans the image
- **AND** scan results are visible in Harbor UI

#### Scenario: Pipeline scan step (optional)
- **WHEN** pipeline includes explicit scan step
- **THEN** pipeline can query Harbor API for scan results
- **AND** fail pipeline if critical vulnerabilities found

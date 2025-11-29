#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""
Gitea Demo Repository Script - Create demo repository with Python app and CI pipeline.

Usage:
    uv run scripts/gitea_demo.py                    # Create demo repository
    uv run scripts/gitea_demo.py --dry-run          # Preview changes
    uv run scripts/gitea_demo.py --create-issues    # Also create sample issues
    uv run scripts/gitea_demo.py --config path.toml # Custom config file
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

# Default paths
DEFAULT_CONFIG = Path("config/setup.toml")

# Demo application templates
DEMO_FILES = {
    "main.py": '''\
from fastapi import FastAPI

app = FastAPI(title="Demo App", description="Demo application for Woodpecker CI")


@app.get("/")
def root():
    """Root endpoint returning a welcome message."""
    return {"message": "Hello from Woodpecker CI!"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
''',
    "requirements.txt": """\
fastapi>=0.109.0
uvicorn>=0.27.0
""",
    "Dockerfile": """\
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY main.py .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
""",
    ".woodpecker.yaml": """\
steps:
  - name: lint
    image: python:3.12-slim
    commands:
      - pip install ruff
      - ruff check .

  - name: build
    image: docker
    commands:
      - docker build -t demo-app:${CI_COMMIT_SHA:0:8} .
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  - name: test-container
    image: docker
    commands:
      - docker run --rm -d --name demo-test -p 8080:8000 demo-app:${CI_COMMIT_SHA:0:8}
      - sleep 3
      - wget -qO- http://localhost:8080/health | grep -q ok
      - docker stop demo-test
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
""",
    "README.md": """\
# Demo App

A minimal Python FastAPI application demonstrating CI/CD with Woodpecker.

## Local Development

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check

## CI Pipeline

The `.woodpecker.yaml` defines three stages:

1. **lint** - Run ruff linter
2. **build** - Build Docker image
3. **test-container** - Run container and verify health endpoint

## Docker

```bash
docker build -t demo-app .
docker run -p 8000:8000 demo-app
```

Then visit http://localhost:8000
""",
}

# Sample issues to create
SAMPLE_ISSUES = [
    {
        "title": "Add unit tests",
        "body": """## Description

Add pytest unit tests for the main application endpoints.

## Acceptance Criteria

- [ ] Test `/` endpoint returns correct message
- [ ] Test `/health` endpoint returns status ok
- [ ] Tests run in CI pipeline

## Implementation Notes

- Use `pytest` and `httpx` for async testing
- Add `test` step to `.woodpecker.yaml`
""",
    },
    {
        "title": "Configure container registry push",
        "body": """## Description

Configure the CI pipeline to push built images to a container registry.

## Acceptance Criteria

- [ ] Add registry credentials as Woodpecker secrets
- [ ] Push image with commit SHA and `latest` tags
- [ ] Only push on main branch

## Implementation Notes

- Add `REGISTRY_URL`, `REGISTRY_USERNAME`, `REGISTRY_PASSWORD` secrets
- Update `.woodpecker.yaml` build step with push commands
""",
    },
]


@dataclass
class GiteaClient:
    """Simple Gitea API client with basic auth."""

    base_url: str
    username: str
    password: str
    dry_run: bool = False

    def _auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(self.username, self.password)

    def _api(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/api/v1{path}"

    def get(self, path: str) -> httpx.Response:
        """GET request to Gitea API."""
        return httpx.get(self._api(path), auth=self._auth(), timeout=30)

    def post(self, path: str, json: dict[str, Any]) -> httpx.Response:
        """POST request to Gitea API."""
        if self.dry_run:
            return httpx.Response(200)
        return httpx.post(self._api(path), auth=self._auth(), json=json, timeout=30)

    def put(self, path: str, json: dict[str, Any] | None = None) -> httpx.Response:
        """PUT request to Gitea API."""
        if self.dry_run:
            return httpx.Response(200)
        return httpx.put(self._api(path), auth=self._auth(), json=json, timeout=30)


def repo_exists(client: GiteaClient, owner: str, repo: str) -> bool:
    """Check if a repository exists."""
    resp = client.get(f"/repos/{owner}/{repo}")
    return resp.status_code == 200


def create_repository(
    client: GiteaClient,
    owner: str,
    repo_name: str,
    description: str,
    is_org: bool,
    dry_run: bool = False,
) -> bool:
    """Create a repository in Gitea.

    Args:
        owner: Organization name or username
        repo_name: Repository name
        description: Repository description
        is_org: True if owner is an organization, False for user
        dry_run: Preview mode
    """
    if repo_exists(client, owner, repo_name):
        print(f"  Repository '{owner}/{repo_name}' already exists, skipping creation")
        return True

    if dry_run:
        target = f"organization '{owner}'" if is_org else f"user '{owner}'"
        print(f"  [DRY-RUN] Would create repository '{repo_name}' in {target}")
        return True

    # Use different endpoints for org vs user repos
    if is_org:
        endpoint = f"/orgs/{owner}/repos"
    else:
        endpoint = "/user/repos"

    payload = {
        "name": repo_name,
        "description": description,
        "auto_init": False,
        "private": False,
    }

    resp = client.post(endpoint, payload)

    if resp.status_code in (200, 201):
        print(f"  Created repository '{owner}/{repo_name}'")
        return True
    elif resp.status_code == 409:
        print(f"  Repository '{owner}/{repo_name}' already exists")
        return True
    else:
        print(f"  Failed to create repository: {resp.status_code}")
        try:
            print(f"    {resp.json()}")
        except Exception:
            pass
        return False


def file_exists(client: GiteaClient, owner: str, repo: str, filepath: str) -> dict | None:
    """Check if a file exists in the repository. Returns file info with SHA if exists."""
    resp = client.get(f"/repos/{owner}/{repo}/contents/{filepath}")
    if resp.status_code == 200:
        return resp.json()
    return None


def create_or_update_file(
    client: GiteaClient,
    owner: str,
    repo: str,
    filepath: str,
    content: str,
    message: str,
    dry_run: bool = False,
) -> bool:
    """Create or update a file in the repository."""
    existing = file_exists(client, owner, repo, filepath)
    content_b64 = base64.b64encode(content.encode()).decode()

    if existing:
        # Check if content is the same
        existing_content = base64.b64decode(existing.get("content", "")).decode()
        if existing_content == content:
            print(f"    {filepath} - unchanged, skipping")
            return True

        if dry_run:
            print(f"    [DRY-RUN] Would update {filepath}")
            return True

        # Update existing file
        payload = {
            "content": content_b64,
            "message": f"Update {filepath}",
            "sha": existing["sha"],
        }
        resp = client.put(f"/repos/{owner}/{repo}/contents/{filepath}", payload)
    else:
        if dry_run:
            print(f"    [DRY-RUN] Would create {filepath}")
            return True

        # Create new file
        payload = {
            "content": content_b64,
            "message": message,
        }
        resp = client.post(f"/repos/{owner}/{repo}/contents/{filepath}", payload)

    if resp.status_code in (200, 201):
        action = "Updated" if existing else "Created"
        print(f"    {filepath} - {action.lower()}")
        return True
    else:
        print(f"    Failed to create {filepath}: {resp.status_code}")
        try:
            print(f"      {resp.json()}")
        except Exception:
            pass
        return False


def issue_exists(client: GiteaClient, owner: str, repo: str, title: str) -> bool:
    """Check if an issue with the given title exists."""
    resp = client.get(f"/repos/{owner}/{repo}/issues?state=all")
    if resp.status_code != 200:
        return False
    issues = resp.json()
    return any(issue.get("title") == title for issue in issues)


def create_issue(
    client: GiteaClient,
    owner: str,
    repo: str,
    title: str,
    body: str,
    dry_run: bool = False,
) -> bool:
    """Create an issue in the repository."""
    if issue_exists(client, owner, repo, title):
        print(f"    Issue '{title}' already exists, skipping")
        return True

    if dry_run:
        print(f"    [DRY-RUN] Would create issue '{title}'")
        return True

    payload = {
        "title": title,
        "body": body,
    }
    resp = client.post(f"/repos/{owner}/{repo}/issues", payload)

    if resp.status_code in (200, 201):
        print(f"    Created issue '{title}'")
        return True
    else:
        print(f"    Failed to create issue '{title}': {resp.status_code}")
        return False


def org_exists(client: GiteaClient, org_name: str) -> bool:
    """Check if an organization exists."""
    resp = client.get(f"/orgs/{org_name}")
    return resp.status_code == 200


def load_config(config_path: Path) -> dict[str, Any]:
    """Load TOML configuration."""
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        print("Run 'just wizard' to create one, or use --config to specify a path.")
        sys.exit(1)

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    return config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create demo repository with Python app and Woodpecker CI pipeline"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to TOML config file (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview changes without making API calls",
    )
    parser.add_argument(
        "--create-issues",
        action="store_true",
        help="Create sample issues in the demo repository",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Check if demo is enabled
    demo_config = config.get("demo", {})
    if demo_config.get("enabled") is False:
        print("Demo creation disabled in config ([demo] enabled = false)")
        return

    # Get admin password from environment
    admin_password = os.environ.get("GITEA_ADMIN_PASSWORD")
    if not admin_password:
        print("Error: GITEA_ADMIN_PASSWORD environment variable required")
        sys.exit(1)

    # Get Gitea URL and admin from config
    gitea_url = config.get("gitea", {}).get("url", "http://gitea.localhost")
    admin_username = config.get("admin", {}).get("username", "admin")

    # Create API client
    client = GiteaClient(
        base_url=gitea_url,
        username=admin_username,
        password=admin_password,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("=== DRY RUN MODE - No changes will be made ===\n")

    # Test connection
    print("Connecting to Gitea...")
    try:
        resp = client.get("/version")
        if resp.status_code != 200:
            print(f"Error: Could not connect to Gitea at {gitea_url}")
            sys.exit(1)
        version = resp.json().get("version", "unknown")
        print(f"  Connected to Gitea v{version}\n")
    except httpx.RequestError as e:
        print(f"Error: Could not connect to Gitea: {e}")
        sys.exit(1)

    # Determine repository owner (org or user)
    org_config = config.get("organization")
    repo_name = demo_config.get("repo_name", "demo-app")
    repo_description = demo_config.get(
        "repo_description", "Demo Python application for CI testing"
    )

    if org_config and org_exists(client, org_config["name"]):
        owner = org_config["name"]
        is_org = True
        print(f"Using organization: {owner}")
    else:
        owner = admin_username
        is_org = False
        print(f"No organization configured, using user: {owner}")

    # Create repository
    print(f"\nCreating repository '{repo_name}'...")
    if not create_repository(
        client, owner, repo_name, repo_description, is_org, dry_run=args.dry_run
    ):
        print("Failed to create repository, aborting")
        sys.exit(1)

    # Upload demo files
    print("\nUploading demo files...")
    for filepath, content in DEMO_FILES.items():
        create_or_update_file(
            client,
            owner,
            repo_name,
            filepath,
            content,
            "Initial commit: Add demo application",
            dry_run=args.dry_run,
        )

    # Create issues if requested
    if args.create_issues or demo_config.get("create_issues", False):
        print("\nCreating sample issues...")

        # Use custom issues from config if provided
        issues = demo_config.get("issues", SAMPLE_ISSUES)
        for issue in issues:
            create_issue(
                client,
                owner,
                repo_name,
                issue["title"],
                issue.get("body", ""),
                dry_run=args.dry_run,
            )

    print("\nDone!")
    print(f"\nRepository URL: {gitea_url}/{owner}/{repo_name}")
    print("\nNext steps:")
    print("  1. Go to Woodpecker CI (http://ci.localhost)")
    print("  2. Click 'Add repository' and activate the demo-app")
    print("  3. Push a commit or trigger a build to see the pipeline run")

    if args.dry_run:
        print("\n=== DRY RUN COMPLETE - Run without --dry-run to apply changes ===")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""
Harbor Setup Script - Configure Harbor projects and robot accounts from TOML config.

Usage:
    uv run scripts/harbor_setup.py                    # Apply config
    uv run scripts/harbor_setup.py --dry-run          # Preview changes
    uv run scripts/harbor_setup.py --config path.toml # Custom config file

Environment Variables:
    HARBOR_ADMIN_PASSWORD - Harbor admin password (default: Harbor12345)
"""

from __future__ import annotations

import argparse
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

# Default paths
DEFAULT_CONFIG = Path("config/setup.toml")


@dataclass
class HarborClient:
    """Simple Harbor API client with basic auth."""

    base_url: str
    username: str
    password: str
    dry_run: bool = False

    def _auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(self.username, self.password)

    def _api(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/api/v2.0{path}"

    def get(self, path: str) -> httpx.Response:
        """GET request to Harbor API."""
        return httpx.get(self._api(path), auth=self._auth(), timeout=30)

    def post(self, path: str, json: dict[str, Any] | None = None) -> httpx.Response:
        """POST request to Harbor API."""
        if self.dry_run:
            return httpx.Response(201)
        return httpx.post(self._api(path), auth=self._auth(), json=json, timeout=30)

    def delete(self, path: str) -> httpx.Response:
        """DELETE request to Harbor API."""
        if self.dry_run:
            return httpx.Response(200)
        return httpx.delete(self._api(path), auth=self._auth(), timeout=30)


def project_exists(client: HarborClient, name: str) -> bool:
    """Check if a Harbor project exists."""
    resp = client.get(f"/projects?name={name}")
    if resp.status_code == 200:
        projects = resp.json()
        return any(p.get("name") == name for p in projects)
    return False


def create_project(
    client: HarborClient,
    name: str,
    public: bool = True,
    dry_run: bool = False,
) -> bool:
    """Create a Harbor project."""
    if project_exists(client, name):
        print(f"  Project '{name}' already exists, skipping")
        return True

    if dry_run:
        visibility = "public" if public else "private"
        print(f"  [DRY-RUN] Would create project '{name}' ({visibility})")
        return True

    payload = {
        "project_name": name,
        "metadata": {
            "public": "true" if public else "false",
        },
    }

    resp = client.post("/projects", payload)

    if resp.status_code in (200, 201):
        print(f"  Created project '{name}'")
        return True
    elif resp.status_code == 409:
        print(f"  Project '{name}' already exists")
        return True
    else:
        print(f"  Failed to create project '{name}': {resp.status_code}")
        try:
            print(f"    {resp.json()}")
        except Exception:
            pass
        return False


def get_robot_account(client: HarborClient, name: str) -> dict[str, Any] | None:
    """Get robot account by name."""
    # Robot accounts are named robot$<name> in Harbor
    resp = client.get(f"/robots?q=name%3D~robot%24{name}")
    if resp.status_code == 200:
        robots = resp.json()
        for robot in robots:
            if robot.get("name") == f"robot${name}":
                return robot
    return None


def create_robot_account(
    client: HarborClient,
    name: str,
    projects: list[str],
    permissions: list[str],
    dry_run: bool = False,
) -> tuple[bool, str | None]:
    """Create a Harbor robot account. Returns (success, token)."""
    existing = get_robot_account(client, name)
    if existing:
        print(f"  Robot account 'robot${name}' already exists (id={existing.get('id')})")
        print("    Note: Token was only shown at creation time")
        return True, None

    if dry_run:
        print(f"  [DRY-RUN] Would create robot account 'robot${name}'")
        print(f"    Projects: {', '.join(projects)}")
        print(f"    Permissions: {', '.join(permissions)}")
        return True, "dry-run-token-placeholder"

    # Build permissions for each project
    access = []
    for project in projects:
        for perm in permissions:
            if perm == "push":
                access.append({
                    "resource": f"/project/{project}/repository",
                    "action": "push",
                })
                access.append({
                    "resource": f"/project/{project}/repository",
                    "action": "pull",
                })
            elif perm == "pull":
                access.append({
                    "resource": f"/project/{project}/repository",
                    "action": "pull",
                })

    payload = {
        "name": name,
        "duration": -1,  # Never expires
        "description": "Robot account for CI pipelines",
        "disable": False,
        "level": "system",
        "permissions": [
            {
                "kind": "project",
                "namespace": project,
                "access": [
                    {"resource": "repository", "action": "push"},
                    {"resource": "repository", "action": "pull"},
                ],
            }
            for project in projects
        ],
    }

    resp = client.post("/robots", payload)

    if resp.status_code in (200, 201):
        data = resp.json()
        token = data.get("secret", "")
        robot_name = data.get("name", f"robot${name}")
        print(f"  Created robot account '{robot_name}'")
        print(f"    Token: {token}")
        print("    (Save this token - it won't be shown again!)")
        return True, token
    else:
        print(f"  Failed to create robot account '{name}': {resp.status_code}")
        try:
            print(f"    {resp.json()}")
        except Exception:
            pass
        return False, None


def print_woodpecker_secret_instructions(
    registry_url: str,
    robot_name: str,
    token: str | None,
) -> None:
    """Print instructions for configuring Woodpecker secrets."""
    print("\n=== Woodpecker Secret Configuration ===")
    print("\nTo push images to Harbor from Woodpecker CI pipelines:")
    print("\n1. Go to http://ci.localhost")
    print("2. Navigate to your repository settings")
    print("3. Add the following secrets:")
    print(f"\n   registry_url = {registry_url}")
    print(f"   registry_username = robot${robot_name}")
    if token:
        print(f"   registry_password = {token}")
    else:
        print("   registry_password = (use token from robot account creation)")
    print("\n4. The demo pipeline will automatically use these secrets")


def load_config(config_path: Path) -> dict[str, Any]:
    """Load and validate TOML configuration."""
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        print(f"Create {config_path} with a [registry.harbor] section.")
        sys.exit(1)

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    return config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Configure Harbor projects and robot accounts from TOML config"
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
        "--url",
        default="http://registry.localhost",
        help="Harbor URL (default: http://registry.localhost)",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Get Harbor config section
    registry_config = config.get("registry", {})
    harbor_config = registry_config.get("harbor", {})

    if not harbor_config:
        print("No [registry.harbor] section found in config.")
        print("Using defaults: create 'library' project and 'ci' robot account.")
        harbor_config = {
            "projects": [{"name": "library", "public": True}],
            "robot_accounts": [
                {"name": "ci", "projects": ["library"], "permissions": ["push", "pull"]}
            ],
        }

    # Get Harbor URL from config or CLI
    harbor_url = harbor_config.get("url", args.url)

    # Get admin password from environment
    admin_password = os.environ.get("HARBOR_ADMIN_PASSWORD", "Harbor12345")

    # Create API client
    client = HarborClient(
        base_url=harbor_url,
        username="admin",
        password=admin_password,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("=== DRY RUN MODE - No changes will be made ===\n")

    # Test connection
    print(f"Connecting to Harbor at {harbor_url}...")
    try:
        resp = client.get("/systeminfo")
        if resp.status_code != 200:
            print(f"Error: Could not connect to Harbor at {harbor_url}")
            print(f"  Status: {resp.status_code}")
            print("  Make sure Harbor is running: just harbor-up")
            sys.exit(1)
        info = resp.json()
        version = info.get("harbor_version", "unknown")
        print(f"  Connected to Harbor v{version}\n")
    except httpx.RequestError as e:
        print(f"Error: Could not connect to Harbor: {e}")
        print("  Make sure Harbor is running: just harbor-up")
        sys.exit(1)

    # Create projects
    projects = harbor_config.get("projects", [])
    if projects:
        print("Creating projects...")
        for project in projects:
            create_project(
                client,
                project["name"],
                public=project.get("public", True),
                dry_run=args.dry_run,
            )
        print()

    # Create robot accounts
    robot_accounts = harbor_config.get("robot_accounts", [])
    created_tokens: dict[str, str] = {}
    if robot_accounts:
        print("Creating robot accounts...")
        for robot in robot_accounts:
            success, token = create_robot_account(
                client,
                robot["name"],
                robot.get("projects", ["library"]),
                robot.get("permissions", ["push", "pull"]),
                dry_run=args.dry_run,
            )
            if success and token:
                created_tokens[robot["name"]] = token
        print()

    # Print Woodpecker secret instructions if we created tokens
    if created_tokens:
        first_robot = list(created_tokens.keys())[0]
        first_token = created_tokens[first_robot]
        print_woodpecker_secret_instructions(harbor_url, first_robot, first_token)

    print("\nDone!")
    if args.dry_run:
        print("\n=== DRY RUN COMPLETE - Run without --dry-run to apply changes ===")


if __name__ == "__main__":
    main()

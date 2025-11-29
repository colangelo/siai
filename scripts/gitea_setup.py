#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""
Gitea Setup Script - Provision users, organizations, and teams from TOML config.

Usage:
    uv run scripts/gitea_setup.py                    # Apply config
    uv run scripts/gitea_setup.py --dry-run          # Preview changes
    uv run scripts/gitea_setup.py --config path.toml # Custom config file
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

# Default paths
DEFAULT_CONFIG = Path("config/setup.toml")
EXAMPLE_CONFIG = Path("config/setup.toml.example")


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

    def put(self, path: str) -> httpx.Response:
        """PUT request to Gitea API."""
        if self.dry_run:
            return httpx.Response(200)
        return httpx.put(self._api(path), auth=self._auth(), timeout=30)


def generate_password(length: int = 16) -> str:
    """Generate a random password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def user_exists(client: GiteaClient, username: str) -> bool:
    """Check if a user exists."""
    resp = client.get(f"/users/{username}")
    return resp.status_code == 200


def create_user(
    client: GiteaClient, username: str, email: str, dry_run: bool = False
) -> str | None:
    """Create a Gitea user. Returns password if created, None if exists."""
    if user_exists(client, username):
        print(f"  User '{username}' already exists, skipping")
        return None

    # Get password from env or generate
    env_key = f"{username.upper()}_PASSWORD"
    password = os.environ.get(env_key)
    generated = False
    if not password:
        password = generate_password()
        generated = True

    if dry_run:
        print(f"  [DRY-RUN] Would create user '{username}' ({email})")
        return password if generated else None

    resp = client.post(
        "/admin/users",
        {
            "username": username,
            "email": email,
            "password": password,
            "must_change_password": False,
        },
    )

    if resp.status_code in (200, 201):
        print(f"  Created user '{username}'")
        if generated:
            print(f"    Generated password: {password}")
            print(f"    (Set {env_key} to use a custom password)")
        return password if generated else None
    else:
        print(f"  Failed to create user '{username}': {resp.status_code}")
        try:
            print(f"    {resp.json()}")
        except Exception:
            pass
        return None


def org_exists(client: GiteaClient, org_name: str) -> bool:
    """Check if an organization exists."""
    resp = client.get(f"/orgs/{org_name}")
    return resp.status_code == 200


def create_organization(
    client: GiteaClient,
    name: str,
    description: str,
    visibility: str,
    dry_run: bool = False,
) -> bool:
    """Create a Gitea organization."""
    if org_exists(client, name):
        print(f"  Organization '{name}' already exists, skipping")
        return True

    if dry_run:
        print(f"  [DRY-RUN] Would create organization '{name}' ({visibility})")
        return True

    resp = client.post(
        "/orgs",
        {
            "username": name,
            "description": description,
            "visibility": visibility,
        },
    )

    if resp.status_code in (200, 201):
        print(f"  Created organization '{name}'")
        return True
    else:
        print(f"  Failed to create organization '{name}': {resp.status_code}")
        try:
            print(f"    {resp.json()}")
        except Exception:
            pass
        return False


def get_team_id(client: GiteaClient, org_name: str, team_name: str) -> int | None:
    """Get team ID by name, or None if not found."""
    resp = client.get(f"/orgs/{org_name}/teams")
    if resp.status_code != 200:
        return None
    teams = resp.json()
    for team in teams:
        if team.get("name") == team_name:
            return team.get("id")
    return None


def create_team(
    client: GiteaClient,
    org_name: str,
    team_name: str,
    permission: str,
    dry_run: bool = False,
) -> int | None:
    """Create a team in an organization. Returns team ID."""
    existing_id = get_team_id(client, org_name, team_name)
    if existing_id:
        print(f"  Team '{team_name}' already exists (id={existing_id}), skipping")
        return existing_id

    if dry_run:
        print(f"  [DRY-RUN] Would create team '{team_name}' ({permission})")
        return -1  # Placeholder ID for dry run

    # Map permission to Gitea's expected values
    perm_map = {"read": "read", "write": "write", "admin": "admin"}
    gitea_perm = perm_map.get(permission, "read")

    resp = client.post(
        f"/orgs/{org_name}/teams",
        {
            "name": team_name,
            "permission": gitea_perm,
            "units": [
                "repo.code",
                "repo.issues",
                "repo.pulls",
                "repo.releases",
                "repo.wiki",
            ],
        },
    )

    if resp.status_code in (200, 201):
        team_id = resp.json().get("id")
        print(f"  Created team '{team_name}' (id={team_id})")
        return team_id
    else:
        print(f"  Failed to create team '{team_name}': {resp.status_code}")
        try:
            print(f"    {resp.json()}")
        except Exception:
            pass
        return None


def add_team_member(
    client: GiteaClient, team_id: int, username: str, dry_run: bool = False
) -> bool:
    """Add a user to a team."""
    if dry_run:
        print(f"    [DRY-RUN] Would add '{username}' to team")
        return True

    # Check if user exists first
    if not user_exists(client, username):
        print(f"    User '{username}' not found, skipping team assignment")
        return False

    resp = client.put(f"/teams/{team_id}/members/{username}")

    if resp.status_code in (200, 204):
        print(f"    Added '{username}' to team")
        return True
    else:
        print(f"    Failed to add '{username}' to team: {resp.status_code}")
        return False


def load_config(config_path: Path) -> dict[str, Any]:
    """Load and validate TOML configuration."""
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        print(f"Copy {EXAMPLE_CONFIG} to {config_path} and customize it.")
        sys.exit(1)

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    # Validate required sections
    if "gitea" not in config:
        print("Error: [gitea] section required in config")
        sys.exit(1)
    if "admin" not in config:
        print("Error: [admin] section required in config")
        sys.exit(1)

    return config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision Gitea users, organizations, and teams from TOML config"
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
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Get admin password from environment
    admin_password = os.environ.get("GITEA_ADMIN_PASSWORD")
    if not admin_password:
        print("Error: GITEA_ADMIN_PASSWORD environment variable required")
        sys.exit(1)

    # Create API client
    client = GiteaClient(
        base_url=config["gitea"]["url"],
        username=config["admin"]["username"],
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
            print(f"Error: Could not connect to Gitea at {config['gitea']['url']}")
            sys.exit(1)
        version = resp.json().get("version", "unknown")
        print(f"  Connected to Gitea v{version}\n")
    except httpx.RequestError as e:
        print(f"Error: Could not connect to Gitea: {e}")
        sys.exit(1)

    # Create users
    users = config.get("users", [])
    if users:
        print("Creating users...")
        for user in users:
            create_user(
                client,
                user["username"],
                user["email"],
                dry_run=args.dry_run,
            )
        print()

    # Create organization
    org_config = config.get("organization")
    if org_config:
        print("Creating organization...")
        org_created = create_organization(
            client,
            org_config["name"],
            org_config.get("description", ""),
            org_config.get("visibility", "public"),
            dry_run=args.dry_run,
        )

        # Create teams
        teams = org_config.get("teams", [])
        if org_created and teams:
            print("\nCreating teams...")
            for team in teams:
                team_id = create_team(
                    client,
                    org_config["name"],
                    team["name"],
                    team.get("permission", "read"),
                    dry_run=args.dry_run,
                )

                # Add members to team
                if team_id:
                    members = team.get("members", [])
                    for member in members:
                        add_team_member(client, team_id, member, dry_run=args.dry_run)

    print("\nDone!")
    if args.dry_run:
        print("\n=== DRY RUN COMPLETE - Run without --dry-run to apply changes ===")


if __name__ == "__main__":
    main()

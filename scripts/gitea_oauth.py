#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""
Gitea OAuth Script - Create OAuth2 applications for CI integration.

Usage:
    uv run scripts/gitea_oauth.py                           # Create and save to .env
    uv run scripts/gitea_oauth.py --name "App" --redirect "http://..."
    uv run scripts/gitea_oauth.py --format json             # JSON output (no .env write)
    uv run scripts/gitea_oauth.py --config config/setup.toml  # From config
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any

import httpx

# Defaults
DEFAULT_CONFIG = Path("config/setup.toml")
DEFAULT_NAME = "Woodpecker CI"
DEFAULT_REDIRECT = "http://ci.localhost/authorize"
ENV_FILE = Path(".env")


def update_env_file(client_id: str, client_secret: str, prefix: str = "WOODPECKER_GITEA") -> bool:
    """Update or append OAuth credentials in .env file."""
    if not ENV_FILE.exists():
        return False

    content = ENV_FILE.read_text()
    lines = content.splitlines()
    new_lines = []
    client_key = f"{prefix}_CLIENT"
    secret_key = f"{prefix}_SECRET"
    client_found = False
    secret_found = False

    for line in lines:
        if line.startswith(f"{client_key}="):
            new_lines.append(f"{client_key}={client_id}")
            client_found = True
        elif line.startswith(f"{secret_key}="):
            new_lines.append(f"{secret_key}={client_secret}")
            secret_found = True
        else:
            new_lines.append(line)

    if not client_found:
        new_lines.append(f"{client_key}={client_id}")
    if not secret_found:
        new_lines.append(f"{secret_key}={client_secret}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n")
    return True


def get_oauth_apps(
    base_url: str, username: str, password: str
) -> list[dict[str, Any]]:
    """Get list of existing OAuth2 applications."""
    auth = httpx.BasicAuth(username, password)
    resp = httpx.get(
        f"{base_url}/api/v1/user/applications/oauth2",
        auth=auth,
        timeout=30,
    )
    if resp.status_code == 200:
        return resp.json()
    return []


def find_app_by_name(
    apps: list[dict[str, Any]], name: str
) -> dict[str, Any] | None:
    """Find OAuth app by name."""
    for app in apps:
        if app.get("name") == name:
            return app
    return None


def create_oauth_app(
    base_url: str,
    username: str,
    password: str,
    name: str,
    redirect_uri: str,
    confidential: bool = True,
) -> dict[str, Any] | None:
    """Create OAuth2 application. Returns app data with client_id and client_secret."""
    auth = httpx.BasicAuth(username, password)
    resp = httpx.post(
        f"{base_url}/api/v1/user/applications/oauth2",
        auth=auth,
        json={
            "name": name,
            "redirect_uris": [redirect_uri],
            "confidential_client": confidential,
        },
        timeout=30,
    )

    if resp.status_code in (200, 201):
        return resp.json()
    else:
        print(f"Error creating OAuth app: {resp.status_code}", file=sys.stderr)
        try:
            print(resp.json(), file=sys.stderr)
        except Exception:
            pass
        return None


def format_output(
    app_data: dict[str, Any], format_type: str, prefix: str = "WOODPECKER_GITEA"
) -> str:
    """Format OAuth credentials for output."""
    client_id = app_data.get("client_id", "")
    client_secret = app_data.get("client_secret", "")

    if format_type == "json":
        return json.dumps(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "name": app_data.get("name", ""),
            },
            indent=2,
        )
    elif format_type == "env":
        return f"{prefix}_CLIENT={client_id}\n{prefix}_SECRET={client_secret}"
    else:  # human-readable
        return (
            f"✓ OAuth2 app '{app_data.get('name', '')}' created\n"
            f"  Client ID:     {client_id}\n"
            f"  Client Secret: {client_secret}"
        )


def load_oauth_config(config_path: Path) -> list[dict[str, Any]]:
    """Load OAuth app config from TOML file."""
    if not config_path.exists():
        return []

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    return config.get("oauth_apps", [])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Gitea OAuth2 applications for CI integration"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help=f"Path to TOML config file with [[oauth_apps]] section",
    )
    parser.add_argument(
        "--name",
        "-n",
        default=DEFAULT_NAME,
        help=f"OAuth application name (default: {DEFAULT_NAME})",
    )
    parser.add_argument(
        "--redirect",
        "-r",
        default=DEFAULT_REDIRECT,
        help=f"OAuth redirect URI (default: {DEFAULT_REDIRECT})",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["human", "json", "env"],
        default="human",
        help="Output format (default: human, writes to .env)",
    )
    parser.add_argument(
        "--no-env",
        action="store_true",
        help="Don't update .env file (just print credentials)",
    )
    parser.add_argument(
        "--url",
        default="http://gitea.localhost",
        help="Gitea server URL (default: http://gitea.localhost)",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Create public client (no secret, PKCE required)",
    )
    args = parser.parse_args()

    # Get admin credentials from environment
    admin_user = os.environ.get("GITEA_ADMIN", "admin")
    admin_pass = os.environ.get("GITEA_ADMIN_PASSWORD")

    if not admin_pass:
        print("Error: GITEA_ADMIN_PASSWORD environment variable required", file=sys.stderr)
        sys.exit(1)

    # Load URL from config if available
    gitea_url = args.url
    if args.config and args.config.exists():
        with open(args.config, "rb") as f:
            config = tomllib.load(f)
        gitea_url = config.get("gitea", {}).get("url", gitea_url)
        admin_user = config.get("admin", {}).get("username", admin_user)

    # Check for existing apps
    existing_apps = get_oauth_apps(gitea_url, admin_user, admin_pass)

    # Process apps from config or command line
    apps_to_create: list[dict[str, Any]] = []

    if args.config:
        oauth_configs = load_oauth_config(args.config)
        for oauth_config in oauth_configs:
            apps_to_create.append({
                "name": oauth_config.get("name", DEFAULT_NAME),
                "redirect_uri": oauth_config.get("redirect_uri", DEFAULT_REDIRECT),
                "confidential": oauth_config.get("confidential", True),
            })
    else:
        apps_to_create.append({
            "name": args.name,
            "redirect_uri": args.redirect,
            "confidential": not args.public,
        })

    # Create each app
    for app_config in apps_to_create:
        name = app_config["name"]
        redirect_uri = app_config["redirect_uri"]
        confidential = app_config["confidential"]

        # Check if app already exists
        existing = find_app_by_name(existing_apps, name)
        if existing:
            if args.format == "human":
                print(f"OAuth app '{name}' already exists (id={existing.get('id')})")
                print("Note: Cannot retrieve existing secret. Delete and recreate if needed.")
                print(f"  Client ID: {existing.get('client_id', 'N/A')}")
            else:
                # For non-human formats, output existing client_id (no secret available)
                print(format_output({"client_id": existing.get("client_id"), "client_secret": "[EXISTING - NOT AVAILABLE]", "name": name}, args.format))
            continue

        # Create new app
        app_data = create_oauth_app(
            gitea_url, admin_user, admin_pass, name, redirect_uri, confidential
        )

        if app_data:
            print(format_output(app_data, args.format))

            # Write to .env unless --no-env or non-human format
            if args.format == "human" and not args.no_env:
                client_id = app_data.get("client_id", "")
                client_secret = app_data.get("client_secret", "")
                if update_env_file(client_id, client_secret):
                    print("✓ Updated .env with OAuth credentials")
                else:
                    print("⚠ Could not update .env (file not found)")

    # Show next steps for human format
    if args.format == "human":
        print()
        print("Next steps:")
        print("  1. just restart    # Apply OAuth config")
        print("  2. just wizard     # Configure users/orgs (optional)")
        print("  3. just setup      # Apply provisioning (optional)")
        print()
        print("Then visit:")
        print("  http://gitea.localhost   - Git server")
        print("  http://ci.localhost      - CI (login via Gitea)")


if __name__ == "__main__":
    main()

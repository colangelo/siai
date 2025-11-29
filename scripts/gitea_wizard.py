#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich", "tomli-w"]
# ///
"""
Gitea Setup Wizard - Interactive configuration generator with Rich UI.

Usage:
    uv run scripts/gitea_wizard.py
    just wizard
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import tomli_w
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

CONFIG_PATH = Path("config/setup.toml")


def welcome() -> None:
    """Display welcome screen."""
    console.print()
    console.print(
        Panel.fit(
            "[bold blue]Gitea Setup Wizard[/bold blue]\n\n"
            "This wizard will help you create [cyan]config/setup.toml[/cyan]\n"
            "for provisioning users, organizations, and teams in Gitea.\n\n"
            "[dim]Press Enter to accept default values shown in brackets.[/dim]",
            title="Welcome",
            border_style="blue",
        )
    )
    console.print()


def prompt_gitea_config() -> dict[str, str]:
    """Prompt for Gitea server configuration."""
    console.print("[bold]1. Gitea Server Configuration[/bold]", style="cyan")
    console.print()

    url = Prompt.ask(
        "  Gitea URL",
        default="http://gitea.localhost",
    )

    return {"url": url}


def prompt_admin_config() -> dict[str, str]:
    """Prompt for admin credentials."""
    console.print()
    console.print("[bold]2. Admin Credentials[/bold]", style="cyan")
    console.print("  [dim]Used for API authentication. Password is read from GITEA_ADMIN_PASSWORD env var.[/dim]")
    console.print()

    username = Prompt.ask("  Admin username", default="admin")
    email = Prompt.ask("  Admin email", default="admin@localhost")

    return {"username": username, "email": email}


def prompt_organization() -> dict[str, Any] | None:
    """Prompt for organization setup."""
    console.print()
    console.print("[bold]3. Organization Setup[/bold]", style="cyan")
    console.print()

    if not Confirm.ask("  Do you want to create an organization?", default=True):
        return None

    console.print()
    name = Prompt.ask("  Organization name", default="myorg")
    description = Prompt.ask(
        "  Description",
        default="Main development organization",
    )
    visibility = Prompt.ask(
        "  Visibility",
        choices=["public", "private"],
        default="public",
    )

    org: dict[str, Any] = {
        "name": name,
        "description": description,
        "visibility": visibility,
        "teams": [],
    }

    # Team creation loop
    console.print()
    console.print("  [bold]Teams[/bold]")
    console.print("  [dim]Teams help organize repository access within the organization.[/dim]")
    console.print()

    while True:
        if not Confirm.ask("  Add a team?", default=len(org["teams"]) < 2):
            break

        team_name = Prompt.ask("    Team name", default="developers" if not org["teams"] else "")
        permission = Prompt.ask(
            "    Permission level",
            choices=["read", "write", "admin"],
            default="write",
        )

        org["teams"].append({
            "name": team_name,
            "permission": permission,
            "members": [],  # Will be populated from users
        })
        console.print(f"    [green]✓[/green] Added team '{team_name}' with {permission} access")
        console.print()

    return org


def prompt_users(org: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Prompt for user creation."""
    console.print()
    console.print("[bold]4. User Creation[/bold]", style="cyan")
    console.print("  [dim]Passwords are read from {USERNAME}_PASSWORD env vars or auto-generated.[/dim]")
    console.print()

    users: list[dict[str, Any]] = []
    team_names = [t["name"] for t in org.get("teams", [])] if org else []

    while True:
        if not Confirm.ask("  Add a user?", default=len(users) < 2):
            break

        username = Prompt.ask("    Username")
        email = Prompt.ask("    Email", default=f"{username}@example.com")

        user: dict[str, Any] = {"username": username, "email": email}

        # Team assignment
        if team_names:
            console.print(f"    [dim]Available teams: {', '.join(team_names)}[/dim]")
            if Confirm.ask("    Assign to teams?", default=True):
                for team in org["teams"]:  # type: ignore
                    if Confirm.ask(f"      Add to '{team['name']}'?", default=True):
                        if username not in team["members"]:
                            team["members"].append(username)

        users.append(user)
        console.print(f"    [green]✓[/green] Added user '{username}'")
        console.print()

    return users


def prompt_oauth_apps() -> list[dict[str, Any]]:
    """Prompt for OAuth app configuration."""
    console.print()
    console.print("[bold]5. OAuth Applications[/bold]", style="cyan")
    console.print("  [dim]OAuth apps allow external services to authenticate via Gitea.[/dim]")
    console.print()

    apps: list[dict[str, Any]] = []

    # Default Woodpecker app
    if Confirm.ask("  Add Woodpecker CI OAuth app?", default=True):
        redirect = Prompt.ask(
            "    Redirect URI",
            default="http://ci.localhost/authorize",
        )
        apps.append({
            "name": "Woodpecker CI",
            "redirect_uri": redirect,
            "confidential": True,
        })
        console.print("    [green]✓[/green] Added Woodpecker CI OAuth app")

    # Additional apps
    console.print()
    while Confirm.ask("  Add another OAuth app?", default=False):
        name = Prompt.ask("    App name")
        redirect = Prompt.ask("    Redirect URI")
        confidential = Confirm.ask("    Confidential client?", default=True)

        apps.append({
            "name": name,
            "redirect_uri": redirect,
            "confidential": confidential,
        })
        console.print(f"    [green]✓[/green] Added '{name}' OAuth app")
        console.print()

    return apps


def show_summary(config: dict[str, Any]) -> None:
    """Display configuration summary."""
    console.print()
    console.print(Panel("[bold]Configuration Summary[/bold]", style="cyan"))
    console.print()

    # Gitea & Admin
    table = Table(title="Server & Admin", show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")
    table.add_row("Gitea URL", config["gitea"]["url"])
    table.add_row("Admin User", config["admin"]["username"])
    table.add_row("Admin Email", config["admin"]["email"])
    console.print(table)
    console.print()

    # Organization
    if config.get("organization"):
        org = config["organization"]
        table = Table(title="Organization", show_header=False, box=None)
        table.add_column("Key", style="dim")
        table.add_column("Value")
        table.add_row("Name", org["name"])
        table.add_row("Visibility", org["visibility"])
        table.add_row("Description", org.get("description", ""))
        console.print(table)
        console.print()

        # Teams
        if org.get("teams"):
            table = Table(title="Teams")
            table.add_column("Name")
            table.add_column("Permission")
            table.add_column("Members")
            for team in org["teams"]:
                members = ", ".join(team.get("members", [])) or "[dim]none[/dim]"
                table.add_row(team["name"], team["permission"], members)
            console.print(table)
            console.print()

    # Users
    if config.get("users"):
        table = Table(title="Users")
        table.add_column("Username")
        table.add_column("Email")
        for user in config["users"]:
            table.add_row(user["username"], user["email"])
        console.print(table)
        console.print()

    # OAuth Apps
    if config.get("oauth_apps"):
        table = Table(title="OAuth Applications")
        table.add_column("Name")
        table.add_column("Redirect URI")
        table.add_column("Type")
        for app in config["oauth_apps"]:
            app_type = "Confidential" if app.get("confidential", True) else "Public"
            table.add_row(app["name"], app["redirect_uri"], app_type)
        console.print(table)
        console.print()


def build_toml_config(config: dict[str, Any]) -> dict[str, Any]:
    """Build TOML-compatible config structure."""
    toml_config: dict[str, Any] = {
        "gitea": config["gitea"],
        "admin": config["admin"],
    }

    if config.get("organization"):
        org = config["organization"]
        toml_config["organization"] = {
            "name": org["name"],
            "description": org.get("description", ""),
            "visibility": org["visibility"],
        }
        if org.get("teams"):
            # Teams go as array of tables
            toml_config["organization"]["teams"] = org["teams"]

    if config.get("users"):
        toml_config["users"] = config["users"]

    if config.get("oauth_apps"):
        toml_config["oauth_apps"] = config["oauth_apps"]

    return toml_config


def write_config(config: dict[str, Any]) -> bool:
    """Write configuration to file."""
    # Check for existing file
    if CONFIG_PATH.exists():
        console.print(f"[yellow]Warning:[/yellow] {CONFIG_PATH} already exists.")
        if not Confirm.ask("Overwrite existing file?", default=False):
            console.print("[dim]Cancelled. Existing file preserved.[/dim]")
            return False

    # Ensure directory exists
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Build TOML structure
    toml_config = build_toml_config(config)

    # Write file
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(toml_config, f)

    return True


def main() -> None:
    welcome()

    # Gather configuration
    config: dict[str, Any] = {}

    config["gitea"] = prompt_gitea_config()
    config["admin"] = prompt_admin_config()
    config["organization"] = prompt_organization()
    config["users"] = prompt_users(config.get("organization"))
    config["oauth_apps"] = prompt_oauth_apps()

    # Show summary
    show_summary(config)

    # Confirm and write
    console.print()
    if not Confirm.ask("Write configuration to config/setup.toml?", default=True):
        console.print("[dim]Cancelled. No files written.[/dim]")
        sys.exit(0)

    if write_config(config):
        console.print()
        console.print(
            Panel.fit(
                f"[green]✓[/green] Configuration written to [cyan]{CONFIG_PATH}[/cyan]\n\n"
                "Next steps:\n"
                "  1. Ensure [cyan]GITEA_ADMIN_PASSWORD[/cyan] is set in .env\n"
                "     [dim](default: admin123, set by 'just init')[/dim]\n"
                "  2. Run [cyan]just setup-dry-run[/cyan] to preview\n"
                "  3. Run [cyan]just setup[/cyan] to apply",
                title="Done",
                border_style="green",
            )
        )


if __name__ == "__main__":
    main()

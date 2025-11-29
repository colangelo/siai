#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich", "tomli-w"]
# ///
"""
Gitea Setup Wizard - Interactive configuration generator with Rich UI.

Usage (interactive):
    uv run scripts/gitea_wizard.py
    just wizard

Usage (non-interactive):
    uv run scripts/gitea_wizard.py --non-interactive \\
        --gitea-url http://gitea.localhost \\
        --admin-username admin \\
        --admin-email admin@localhost \\
        --new-admin-username ac \\
        --new-admin-email ac@example.com \\
        --new-admin-password  \\
        --org-name myorg \\
        --org-description "Development org" \\
        --org-visibility public \\
        --team developers:write:alice,bob \\
        --team maintainers:admin:alice \\
        --user alice:alice@example.com \\
        --user bob:bob@example.com \\
        --oauth "Woodpecker CI:http://ci.localhost/authorize:confidential"

    # Minimal non-interactive (just OAuth for Woodpecker):
    uv run scripts/gitea_wizard.py --non-interactive --oauth-woodpecker

    # From backup file:
    uv run scripts/gitea_wizard.py --from-toml config/setup.toml.backup.20251129-133054
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
import tomllib
from pathlib import Path
from typing import Any

import tomli_w


from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table


def generate_safe_password(length: int = 24) -> str:
    """Generate a safe password with only alphanumeric characters."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

console = Console()

CONFIG_PATH = Path("config/setup.toml")
ENV_PATH = Path(".env")


def load_env_defaults() -> dict[str, str]:
    """Load defaults from .env file if it exists."""
    defaults = {
        "GITEA_ADMIN": "admin",
        "GITEA_ADMIN_EMAIL": "admin@localhost",
        "GITEA_EXTERNAL_URL": "http://gitea.localhost",
    }

    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if key in defaults:
                        defaults[key] = value

    return defaults


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


def prompt_gitea_config(env_defaults: dict[str, str]) -> dict[str, str]:
    """Prompt for Gitea server configuration."""
    console.print("[bold]1. Gitea Server Configuration[/bold]", style="cyan")
    console.print()

    url = Prompt.ask(
        "  Gitea URL",
        default=env_defaults.get("GITEA_EXTERNAL_URL", "http://gitea.localhost"),
    )

    return {"url": url}


def prompt_current_admin(env_defaults: dict[str, str]) -> dict[str, str]:
    """Prompt for current admin credentials (for API authentication)."""
    console.print()
    console.print("[bold]2. Current Admin (for API authentication)[/bold]", style="cyan")
    console.print("  [dim]These credentials are used to connect to Gitea API.[/dim]")
    console.print("  [dim]Values loaded from .env file.[/dim]")
    console.print()

    username = Prompt.ask(
        "  Current admin username",
        default=env_defaults.get("GITEA_ADMIN", "admin"),
    )
    email = Prompt.ask(
        "  Current admin email",
        default=env_defaults.get("GITEA_ADMIN_EMAIL", "admin@localhost"),
    )

    return {"username": username, "email": email}


def prompt_admin_update(current_admin: dict[str, str]) -> dict[str, Any] | None:
    """Prompt for admin profile update (rename, change email/password)."""
    console.print()
    console.print("[bold]3. Update Admin Profile (optional)[/bold]", style="cyan")
    console.print("  [dim]Optionally rename the admin user or change email/password.[/dim]")
    console.print()

    if not Confirm.ask("  Do you want to update the admin profile?", default=False):
        return None

    console.print()
    update: dict[str, Any] = {}

    new_username = Prompt.ask(
        "    New username",
        default=current_admin["username"],
    )
    if new_username != current_admin["username"]:
        update["new_username"] = new_username
        console.print(f"    [yellow]→[/yellow] Will rename '{current_admin['username']}' to '{new_username}'")

    new_email = Prompt.ask(
        "    New email",
        default=current_admin["email"],
    )
    if new_email != current_admin["email"]:
        update["new_email"] = new_email
        console.print(f"    [yellow]→[/yellow] Will change email to '{new_email}'")

    if Confirm.ask("    Change password?", default=False):
        update["change_password"] = True
        new_password = generate_safe_password(24)
        update["generated_password"] = new_password
        console.print(f"    [yellow]→[/yellow] Generated new password: [cyan]{new_password}[/cyan]")
        console.print("    [dim]    (Will be saved to .env as NEW_GITEA_ADMIN_PASSWORD)[/dim]")

    if not update:
        console.print("    [dim]No changes to admin profile.[/dim]")
        return None

    return update


def prompt_organization(step_num: int) -> dict[str, Any] | None:
    """Prompt for organization setup."""
    console.print()
    console.print(f"[bold]{step_num}. Organization Setup[/bold]", style="cyan")
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


def prompt_users(org: dict[str, Any] | None, step_num: int) -> list[dict[str, Any]]:
    """Prompt for user creation."""
    console.print()
    console.print(f"[bold]{step_num}. User Creation[/bold]", style="cyan")
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


def prompt_oauth_apps(step_num: int) -> list[dict[str, Any]]:
    """Prompt for OAuth app configuration."""
    console.print()
    console.print(f"[bold]{step_num}. OAuth Applications[/bold]", style="cyan")
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
    table = Table(title="Server & Current Admin", show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")
    table.add_row("Gitea URL", config["gitea"]["url"])
    table.add_row("Admin User", config["admin"]["username"])
    table.add_row("Admin Email", config["admin"]["email"])
    console.print(table)
    console.print()

    # Admin Update
    if config.get("admin_update"):
        table = Table(title="Admin Profile Updates", show_header=False, box=None)
        table.add_column("Change", style="dim")
        table.add_column("Value")
        update = config["admin_update"]
        if update.get("new_username"):
            table.add_row("Rename to", update["new_username"])
        if update.get("new_email"):
            table.add_row("New email", update["new_email"])
        if update.get("change_password"):
            table.add_row("Password", "[yellow]Will be changed[/yellow]")
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

    if config.get("admin_update"):
        # Don't include generated_password in TOML (it goes to .env)
        admin_update = {k: v for k, v in config["admin_update"].items() if k != "generated_password"}
        if admin_update:
            toml_config["admin_update"] = admin_update

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


def update_env_file(key: str, value: str) -> bool:
    """Update or append a key in .env file."""
    if not ENV_PATH.exists():
        return False

    content = ENV_PATH.read_text()
    lines = content.splitlines()
    new_lines = []
    found = False

    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n")
    return True


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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Gitea Setup Wizard - Generate config/setup.toml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  %(prog)s

  # Non-interactive with admin rename and Woodpecker OAuth
  %(prog)s --non-interactive --new-admin-username ac --new-admin-password --oauth-woodpecker

  # From existing TOML backup
  %(prog)s --from-toml config/setup.toml.backup.20251129-133054

  # Full configuration
  %(prog)s --non-interactive \\
    --admin-username admin --admin-email admin@localhost \\
    --new-admin-username ac --new-admin-email ac@example.com --new-admin-password \\
    --org-name myorg --org-visibility public \\
    --team developers:write:alice,bob --team maintainers:admin:alice \\
    --user alice:alice@example.com --user bob:bob@example.com \\
    --oauth-woodpecker
""",
    )

    # Mode selection
    parser.add_argument(
        "--non-interactive", "-n",
        action="store_true",
        help="Run in non-interactive mode (requires other arguments)",
    )
    parser.add_argument(
        "--from-toml",
        type=Path,
        metavar="FILE",
        help="Load configuration from existing TOML file (e.g., backup)",
    )
    parser.add_argument(
        "--overwrite", "-y",
        action="store_true",
        help="Overwrite existing config/setup.toml without prompting",
    )

    # Gitea server
    parser.add_argument(
        "--gitea-url",
        default="http://gitea.localhost",
        help="Gitea server URL (default: http://gitea.localhost)",
    )

    # Current admin (for API auth)
    parser.add_argument(
        "--admin-username",
        default="admin",
        help="Current admin username for API auth (default: admin)",
    )
    parser.add_argument(
        "--admin-email",
        default="admin@localhost",
        help="Current admin email (default: admin@localhost)",
    )

    # Admin update
    parser.add_argument(
        "--new-admin-username",
        metavar="NAME",
        help="Rename admin to this username",
    )
    parser.add_argument(
        "--new-admin-email",
        metavar="EMAIL",
        help="Change admin email to this",
    )
    parser.add_argument(
        "--new-admin-password",
        action="store_true",
        help="Generate and set new admin password (saved to .env)",
    )

    # Organization
    parser.add_argument(
        "--org-name",
        metavar="NAME",
        help="Organization name (omit to skip org creation)",
    )
    parser.add_argument(
        "--org-description",
        default="",
        help="Organization description",
    )
    parser.add_argument(
        "--org-visibility",
        choices=["public", "private"],
        default="public",
        help="Organization visibility (default: public)",
    )

    # Teams (can be specified multiple times)
    parser.add_argument(
        "--team",
        action="append",
        metavar="NAME:PERM:MEMBERS",
        help="Add team as 'name:permission:member1,member2' (e.g., 'developers:write:alice,bob')",
    )

    # Users (can be specified multiple times)
    parser.add_argument(
        "--user",
        action="append",
        metavar="NAME:EMAIL",
        help="Add user as 'username:email' (e.g., 'alice:alice@example.com')",
    )

    # OAuth apps
    parser.add_argument(
        "--oauth-woodpecker",
        action="store_true",
        help="Add default Woodpecker CI OAuth app",
    )
    parser.add_argument(
        "--oauth",
        action="append",
        metavar="NAME:REDIRECT:TYPE",
        help="Add OAuth app as 'name:redirect_uri:confidential|public'",
    )

    return parser.parse_args()


def load_from_toml(path: Path) -> dict[str, Any]:
    """Load configuration from existing TOML file."""
    with open(path, "rb") as f:
        toml_data = tomllib.load(f)

    config: dict[str, Any] = {
        "gitea": toml_data.get("gitea", {"url": "http://gitea.localhost"}),
        "admin": toml_data.get("admin", {"username": "admin", "email": "admin@localhost"}),
    }

    # Admin update
    if "admin_update" in toml_data:
        config["admin_update"] = toml_data["admin_update"]
        # If change_password is set, generate a new password
        if toml_data["admin_update"].get("change_password"):
            config["admin_update"]["generated_password"] = generate_safe_password(24)

    # Organization with teams
    if "organization" in toml_data:
        org = toml_data["organization"]
        config["organization"] = {
            "name": org.get("name", ""),
            "description": org.get("description", ""),
            "visibility": org.get("visibility", "public"),
            "teams": org.get("teams", []),
        }

    # Users
    if "users" in toml_data:
        config["users"] = toml_data["users"]

    # OAuth apps
    if "oauth_apps" in toml_data:
        config["oauth_apps"] = toml_data["oauth_apps"]

    return config


def build_config_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """Build configuration from command line arguments."""
    config: dict[str, Any] = {
        "gitea": {"url": args.gitea_url},
        "admin": {"username": args.admin_username, "email": args.admin_email},
    }

    # Admin update
    admin_update: dict[str, Any] = {}
    if args.new_admin_username:
        admin_update["new_username"] = args.new_admin_username
    if args.new_admin_email:
        admin_update["new_email"] = args.new_admin_email
    if args.new_admin_password:
        admin_update["change_password"] = True
        admin_update["generated_password"] = generate_safe_password(24)
    if admin_update:
        config["admin_update"] = admin_update

    # Organization
    if args.org_name:
        config["organization"] = {
            "name": args.org_name,
            "description": args.org_description,
            "visibility": args.org_visibility,
            "teams": [],
        }

        # Parse teams
        if args.team:
            for team_str in args.team:
                parts = team_str.split(":")
                if len(parts) >= 2:
                    name = parts[0]
                    permission = parts[1] if parts[1] in ("read", "write", "admin") else "write"
                    members = parts[2].split(",") if len(parts) > 2 and parts[2] else []
                    config["organization"]["teams"].append({
                        "name": name,
                        "permission": permission,
                        "members": members,
                    })

    # Users
    if args.user:
        config["users"] = []
        for user_str in args.user:
            parts = user_str.split(":")
            username = parts[0]
            email = parts[1] if len(parts) > 1 else f"{username}@example.com"
            config["users"].append({"username": username, "email": email})

    # OAuth apps
    oauth_apps: list[dict[str, Any]] = []
    if args.oauth_woodpecker:
        oauth_apps.append({
            "name": "Woodpecker CI",
            "redirect_uri": "http://ci.localhost/authorize",
            "confidential": True,
        })
    if args.oauth:
        for oauth_str in args.oauth:
            parts = oauth_str.split(":")
            if len(parts) >= 2:
                name = parts[0]
                redirect_uri = parts[1]
                # Handle redirect URIs with colons (http://...)
                if len(parts) > 3:
                    redirect_uri = ":".join(parts[1:-1])
                    confidential = parts[-1].lower() != "public"
                elif len(parts) == 3:
                    confidential = parts[2].lower() != "public"
                else:
                    confidential = True
                oauth_apps.append({
                    "name": name,
                    "redirect_uri": redirect_uri,
                    "confidential": confidential,
                })
    if oauth_apps:
        config["oauth_apps"] = oauth_apps

    return config


def run_non_interactive(args: argparse.Namespace) -> None:
    """Run wizard in non-interactive mode."""
    # Load config from TOML or args
    if args.from_toml:
        if not args.from_toml.exists():
            console.print(f"[red]Error:[/red] File not found: {args.from_toml}")
            sys.exit(1)
        console.print(f"Loading configuration from [cyan]{args.from_toml}[/cyan]")
        config = load_from_toml(args.from_toml)
    else:
        config = build_config_from_args(args)

    # Show summary
    show_summary(config)

    # Check for existing file
    if CONFIG_PATH.exists() and not args.overwrite:
        console.print(f"\n[yellow]Warning:[/yellow] {CONFIG_PATH} already exists.")
        console.print("Use --overwrite (-y) to replace it.")
        sys.exit(1)

    # Write config
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    toml_config = build_toml_config(config)
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(toml_config, f)

    console.print(f"\n[green]✓[/green] Configuration written to [cyan]{CONFIG_PATH}[/cyan]")

    # Save generated password to .env if present
    admin_update = config.get("admin_update", {})
    generated_password = admin_update.get("generated_password")
    if generated_password:
        if update_env_file("NEW_GITEA_ADMIN_PASSWORD", generated_password):
            console.print(f"[green]✓[/green] Saved NEW_GITEA_ADMIN_PASSWORD to .env: [cyan]{generated_password}[/cyan]")
        else:
            console.print("[yellow]⚠[/yellow] Could not save password to .env")
            console.print(f"  Generated password: [cyan]{generated_password}[/cyan]")

    console.print("\nNext steps:")
    console.print("  1. Run [cyan]just setup-dry-run[/cyan] to preview")
    console.print("  2. Run [cyan]just setup[/cyan] to apply")


def main() -> None:
    args = parse_args()

    # Non-interactive mode
    if args.non_interactive or args.from_toml:
        run_non_interactive(args)
        return

    welcome()

    # Load defaults from .env
    env_defaults = load_env_defaults()

    # Gather configuration
    config: dict[str, Any] = {}

    # Step 1: Gitea URL
    config["gitea"] = prompt_gitea_config(env_defaults)

    # Step 2: Current admin (for API auth)
    config["admin"] = prompt_current_admin(env_defaults)

    # Step 3: Optional admin update
    config["admin_update"] = prompt_admin_update(config["admin"])

    # Dynamic step numbering based on whether admin update was shown
    next_step = 4

    # Step 4: Organization
    config["organization"] = prompt_organization(next_step)
    next_step += 1

    # Step 5: Users
    config["users"] = prompt_users(config.get("organization"), next_step)
    next_step += 1

    # Step 6: OAuth apps
    config["oauth_apps"] = prompt_oauth_apps(next_step)

    # Show summary
    show_summary(config)

    # Confirm and write
    console.print()
    if not Confirm.ask("Write configuration to config/setup.toml?", default=True):
        console.print("[dim]Cancelled. No files written.[/dim]")
        sys.exit(0)

    if write_config(config):
        console.print()

        # Save generated password to .env if present
        admin_update = config.get("admin_update", {})
        generated_password = admin_update.get("generated_password")
        if generated_password:
            if update_env_file("NEW_GITEA_ADMIN_PASSWORD", generated_password):
                console.print("[green]✓[/green] Saved NEW_GITEA_ADMIN_PASSWORD to .env")
            else:
                console.print("[yellow]⚠[/yellow] Could not save password to .env")

        # Build next steps based on config
        next_steps = "Next steps:\n"
        next_steps += "  1. Ensure [cyan]GITEA_ADMIN_PASSWORD[/cyan] is set in .env\n"
        next_steps += "     [dim](default: admin123, set by 'just init')[/dim]\n"
        next_steps += "  2. Run [cyan]just setup-dry-run[/cyan] to preview\n"
        next_steps += "  3. Run [cyan]just setup[/cyan] to apply"

        console.print(
            Panel.fit(
                f"[green]✓[/green] Configuration written to [cyan]{CONFIG_PATH}[/cyan]\n\n"
                + next_steps,
                title="Done",
                border_style="green",
            )
        )


if __name__ == "__main__":
    main()

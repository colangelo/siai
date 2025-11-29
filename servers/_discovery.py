#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

"""
Server and tool discovery for progressive disclosure.

This module allows agents to explore available servers and tools
without loading all definitions upfront.

Usage:
    # List all servers
    uv run servers/_discovery.py servers

    # List tools in a server
    uv run servers/_discovery.py tools playwright

    # Search for tools by keyword
    uv run servers/_discovery.py search "screenshot"

    # Get tool details
    uv run servers/_discovery.py detail playwright screenshot
"""

import ast
import json
import sys
from pathlib import Path

SERVERS_DIR = Path(__file__).parent


def list_servers() -> list[dict]:
    """List all available MCP servers."""
    servers = []
    for path in SERVERS_DIR.iterdir():
        if path.is_dir() and not path.name.startswith("_"):
            readme = path / "README.md"
            description = ""
            if readme.exists():
                # Get first non-empty line after title
                lines = readme.read_text().split("\n")
                for i, line in enumerate(lines):
                    if line.startswith("#") and i + 1 < len(lines):
                        for next_line in lines[i + 1 :]:
                            if next_line.strip() and not next_line.startswith("#"):
                                description = next_line.strip().rstrip(".")
                                break
                        break

            servers.append(
                {
                    "name": path.name,
                    "description": description or f"{path.name} server",
                    "path": f"servers/{path.name}/",
                }
            )
    return servers


def list_tools(server_name: str, detail_level: str = "name") -> list[dict]:
    """
    List tools in a server.

    detail_level:
        - "name": Just tool names
        - "description": Names and descriptions
        - "full": Full signature and docstring
    """
    server_path = SERVERS_DIR / server_name
    if not server_path.exists():
        return [{"error": f"Server '{server_name}' not found"}]

    tools = []
    for py_file in server_path.glob("*.py"):
        if py_file.name.startswith("_") or py_file.name in ("models.py", "types.py"):
            continue

        tool_name = py_file.stem
        tool_info = {"name": tool_name}

        if detail_level in ("description", "full"):
            # Parse the file to get docstring
            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                # Get module docstring
                module_doc = ast.get_docstring(tree)
                if module_doc:
                    # First line is description
                    tool_info["description"] = module_doc.split("\n")[0]

                if detail_level == "full":
                    tool_info["docstring"] = module_doc
                    # Find async function signatures
                    for node in ast.walk(tree):
                        if isinstance(node, ast.AsyncFunctionDef):
                            if not node.name.startswith("_"):
                                tool_info["function"] = node.name
                                tool_info["file"] = f"servers/{server_name}/{py_file.name}"
                                break
            except Exception as e:
                tool_info["error"] = str(e)

        tools.append(tool_info)

    return sorted(tools, key=lambda x: x["name"])


def search_tools(query: str) -> list[dict]:
    """Search for tools across all servers by keyword."""
    query_lower = query.lower()
    results = []

    for server in list_servers():
        server_name = server["name"]
        tools = list_tools(server_name, detail_level="description")

        for tool in tools:
            if "error" in tool:
                continue

            # Search in name and description
            name_match = query_lower in tool["name"].lower()
            desc_match = query_lower in tool.get("description", "").lower()

            if name_match or desc_match:
                results.append(
                    {
                        "server": server_name,
                        "tool": tool["name"],
                        "description": tool.get("description", ""),
                        "path": f"servers/{server_name}/{tool['name']}.py",
                    }
                )

    return results


def get_tool_detail(server_name: str, tool_name: str) -> dict:
    """Get full details for a specific tool."""
    tool_path = SERVERS_DIR / server_name / f"{tool_name}.py"
    if not tool_path.exists():
        return {"error": f"Tool '{tool_name}' not found in server '{server_name}'"}

    content = tool_path.read_text()

    try:
        tree = ast.parse(content)
        module_doc = ast.get_docstring(tree)

        # Find the main function
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
                func_doc = ast.get_docstring(node)
                return {
                    "server": server_name,
                    "tool": tool_name,
                    "function": node.name,
                    "module_doc": module_doc,
                    "function_doc": func_doc,
                    "file": f"servers/{server_name}/{tool_name}.py",
                    "usage": f"uv run servers/playwright/run.py {tool_name.replace('_', '-')} <args>",
                }
    except Exception as e:
        return {"error": str(e)}

    return {"error": "No async function found"}


def main():
    if len(sys.argv) < 2:
        print("Server Discovery Tool")
        print()
        print("Commands:")
        print("  servers              - List all available servers")
        print("  tools <server>       - List tools in a server")
        print("  search <query>       - Search for tools by keyword")
        print("  detail <server> <tool> - Get full tool details")
        print()
        print("Examples:")
        print("  uv run servers/_discovery.py servers")
        print("  uv run servers/_discovery.py tools playwright")
        print('  uv run servers/_discovery.py search "screenshot"')
        print("  uv run servers/_discovery.py detail playwright screenshot")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "servers":
        result = list_servers()
    elif cmd == "tools":
        if len(sys.argv) < 3:
            print("Usage: tools <server_name>")
            sys.exit(1)
        detail = "description" if "--full" not in sys.argv else "full"
        result = list_tools(sys.argv[2], detail_level=detail)
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: search <query>")
            sys.exit(1)
        result = search_tools(sys.argv[2])
    elif cmd == "detail":
        if len(sys.argv) < 4:
            print("Usage: detail <server> <tool>")
            sys.exit(1)
        result = get_tool_detail(sys.argv[2], sys.argv[3])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

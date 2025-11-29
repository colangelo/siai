# Playwright Code Execution API

Browser automation through code execution, using Playwright directly (NOT via MCP).

> **Key Insight**: Claude executes Python code via Bash using the underlying Playwright library directly. The MCP server is NOT required.

## Quick Start

```bash
# Navigate to a page
uv run servers/playwright/run.py navigate "https://example.com"

# Get accessibility snapshot
uv run servers/playwright/run.py snapshot

# Take screenshot
uv run servers/playwright/run.py screenshot /tmp/test.png

# Get page text content
uv run servers/playwright/run.py content

# Click an element
uv run servers/playwright/run.py click "button.submit"

# Type into a field
uv run servers/playwright/run.py type "input[name='email']" "user@example.com"

# Evaluate JavaScript
uv run servers/playwright/run.py eval "document.title"

# Wait for element
uv run servers/playwright/run.py wait ".loading-complete"
```

## Tool Discovery

Progressive discovery reduces token usage from ~15,000 to ~500:

```bash
# List all servers
uv run servers/_discovery.py servers

# List tools in this server
uv run servers/_discovery.py tools playwright

# Search for tools by keyword
uv run servers/_discovery.py search "screenshot"

# Get full tool details
uv run servers/_discovery.py detail playwright screenshot
```

## Available Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `navigate <url>` | `nav` | Navigate to URL |
| `snapshot` | `snap` | Get accessibility tree |
| `screenshot [file]` | `ss` | Take screenshot |
| `content` | `text` | Get page text content |
| `click <selector>` | - | Click element by CSS selector |
| `type <selector> <text>` | `fill` | Type into element |
| `eval <expression>` | - | Evaluate JavaScript |
| `wait [selector]` | - | Wait for element or timeout |

## Examples

### Form Submission

```bash
# Navigate to login page
uv run servers/playwright/run.py navigate "https://example.com/login"

# Fill in credentials
uv run servers/playwright/run.py type "input[name='email']" "user@example.com"
uv run servers/playwright/run.py type "input[name='password']" "secret123"

# Submit form
uv run servers/playwright/run.py click "button[type='submit']"

# Verify success
uv run servers/playwright/run.py content
```

### Screenshot Workflow

```bash
# Navigate to target
uv run servers/playwright/run.py navigate "http://localhost:8500"

# Take viewport screenshot
uv run servers/playwright/run.py screenshot /tmp/viewport.png

# Get accessibility snapshot (better for automation)
uv run servers/playwright/run.py snapshot
```

### JavaScript Evaluation

```bash
# Get page title
uv run servers/playwright/run.py eval "document.title"

# Get element count
uv run servers/playwright/run.py eval "document.querySelectorAll('a').length"

# Check if element exists
uv run servers/playwright/run.py eval "!!document.querySelector('.success-message')"
```

### Multi-Step Workflow

```bash
# State is persisted between calls via /tmp/playwright_state.json
uv run servers/playwright/run.py navigate "http://localhost:8500/admin"
uv run servers/playwright/run.py snapshot  # Restores previous URL automatically
uv run servers/playwright/run.py click "button.refresh"
uv run servers/playwright/run.py screenshot /tmp/result.png
```

## State Persistence

Browser state (current URL) is saved between commands:

```
/tmp/playwright_state.json
```

This allows multi-command workflows where each command restores the previous page before executing.

## How It Works

1. **No MCP tool definitions loaded** - Claude discovers tools on-demand
2. **Direct library usage** - `run.py` uses `playwright.async_api` directly
3. **Bash execution** - Claude runs `uv run servers/playwright/run.py <cmd>`
4. **JSON output** - All results are JSON for easy parsing
5. **State persistence** - URL saved between commands for multi-step workflows

## Installation

```bash
# Install browser (first time only)
uv run --with playwright python -c "from playwright.__main__ import main; main()" install chromium
```

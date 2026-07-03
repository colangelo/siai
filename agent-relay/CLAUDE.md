# Agent relay — Claude Code

Protocol + schema: @AGENTS.md (this folder).

**On session start**, check `inbox/` for messages addressed to this repo and handle
them before other work:

```bash
find agent-relay/inbox -type f -name '*.md' -exec grep -l 'status: new' {} + 2>/dev/null || true
```

To message another repo's agent, drop a file in **that repo's** `agent-relay/inbox/`
per the schema in `AGENTS.md`, then commit & push.

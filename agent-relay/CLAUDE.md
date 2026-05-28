# Agent relay — Claude Code

Protocol + schema: @AGENTS.md (this folder).

**On session start**, check `inbox/` for messages addressed to this repo and handle
them before other work:

```bash
grep -l 'status: new' agent-relay/inbox/*.md 2>/dev/null
```

To message another repo's agent, drop a file in **that repo's** `agent-relay/inbox/`
per the schema in `AGENTS.md`, then commit & push.

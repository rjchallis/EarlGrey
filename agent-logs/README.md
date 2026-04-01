# Agent logs

Agent logs record significant automated edits made by AI agents. See `AGENTS.md` for the policy that requires these entries.

Naming

```
agent-logs/YYYY-MM-DD_NNN_short-description.md
```

Minimum fields

- `date` — ISO 8601 date
- `branch` — repository branch the agent was working on
- `summary` — short description of what changed and why
- `files_changed` — list of modified/added files
- `commands_run` — key commands executed to verify changes
- `acceptance_criteria` — how we decided the change is complete
- `next_steps` — recommended follow-ups

Use this file as the authoritative place other developers can read what the agent changed.

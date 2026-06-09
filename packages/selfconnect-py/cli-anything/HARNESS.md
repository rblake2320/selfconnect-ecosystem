# selfconnect CLI Harness

## Installation

```bash
pip install selfconnect
```

Verify:
```bash
selfconnect version
```

## Authentication Setup

```bash
# Option 1: Interactive login (prompts for key)
selfconnect login

# Option 2: Non-interactive (for CI/CD)
selfconnect login --key sc-tsk-YOUR-KEY

# Option 3: Environment variable (no config file needed)
export SELFCONNECT_TSK_KEY=sc-tsk-YOUR-KEY
```

## Command Reference

### Status & Budget

```
selfconnect status [--key KEY] [--json]
```

Returns: key info, budget total, tokens used, tokens remaining, % used

### Recent Usage

```
selfconnect usage [--limit N] [--key KEY] [--json]
```

Returns: table of recent events with timestamps, session IDs, event types, token counts

### Audit Trail

```
selfconnect audit SESSION_ID [--output FILE] [--key KEY]
```

Returns: full chain-of-custody JSON for the session

### Session Management

```
selfconnect session start AGENT_ID [--key KEY] [--json]
selfconnect session end SESSION_ID [--summary TEXT] [--key KEY] [--json]
```

### Key Management

```
selfconnect keys info [--key KEY] [--json]
selfconnect keys revoke TSK_KEY_TO_REVOKE [--key ADMIN_KEY]
```

## Agent Usage Patterns

### Pattern 1: Check budget before running

```bash
# Get remaining tokens as JSON, parse with jq
REMAINING=$(selfconnect status --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['remaining'])")
if [ "$REMAINING" -gt 10000 ]; then
    echo "Budget OK, proceeding"
fi
```

### Pattern 2: Governed session in a shell script

```bash
SESSION=$(selfconnect session start "my-pipeline-agent")
echo "Session: $SESSION"

# ... run agent work here ...

selfconnect session end "$SESSION" --summary "Task complete"
selfconnect audit "$SESSION" --output "audit-$(date +%Y%m%d-%H%M%S).json"
```

### Pattern 3: JSON output for programmatic use

```bash
# Get budget as JSON
selfconnect status --json

# Get events as JSON array
selfconnect usage --limit 100 --json

# Get audit trail
selfconnect audit SESSION_ID
```

## Error Handling

All commands exit with code 0 on success, 1 on error. Error messages go to stderr.

```bash
selfconnect status 2>/dev/null || echo "Not logged in"
```

## Notes for Agents

- Always run `selfconnect status` before starting long agent tasks to verify budget
- Session IDs are UUIDs — capture them from `selfconnect session start` stdout
- Audit exports are JSON — parse with `python3 -c "import json,sys; ..."` or `jq`
- The `--json` flag on any command produces machine-readable output safe for parsing
- Keys starting with `sc-tsk-` are required; the CLI validates format before API calls

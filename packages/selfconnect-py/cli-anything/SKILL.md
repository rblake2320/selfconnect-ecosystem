# selfconnect CLI Skill

## Overview

The `selfconnect` CLI is a client for SelfConnect session, event, budget-status,
and server-reported workflow APIs. Server policy determines whether a request
is accepted; the CLI does not itself create a non-bypassable enforcement or
authorization boundary.

Install: `pip install selfconnect`

## Authentication

Before using any command, save your TSK key:

```bash
selfconnect login --key sc-tsk-YOUR-KEY
```

Or set the environment variable:

```bash
export SELFCONNECT_TSK_KEY=sc-tsk-YOUR-KEY
```

## Commands

### selfconnect login

Save TSK key credentials to `~/.selfconnect/config.json`.

```bash
selfconnect login --key sc-tsk-YOUR-KEY
selfconnect login --key sc-tsk-YOUR-KEY --url https://api.selfconnect.ai
```

### selfconnect logout

Remove saved credentials.

```bash
selfconnect logout
```

### selfconnect status

Show TSK key info and current budget usage.

```bash
selfconnect status
selfconnect status --json           # machine-readable JSON
selfconnect status --key sc-tsk-X   # override key
```

**Output fields:** key, registered, revoked, created, budget, used, remaining, pct_used

### selfconnect usage

Show recent events and token usage for this TSK key.

```bash
selfconnect usage
selfconnect usage --limit 50        # show last 50 events
selfconnect usage --json            # raw JSON
```

**Output columns:** Time, Session ID, Event Type, Tokens In, Tokens Out

### selfconnect audit SESSION_ID

Export the configured server's workflow and retained event hash-chain data for
a session.

```bash
selfconnect audit 3f2a1b4c-...
selfconnect audit 3f2a1b4c-... --output audit.json
```

**Output:** Server-reported JSON. Hash chaining can support tamper detection for
retained entries, but the CLI does not prove completeness, immutable custody,
signer identity, legal admissibility, or regulatory compliance.

### selfconnect keys info

Show detailed info for a TSK key.

```bash
selfconnect keys info
selfconnect keys info --key sc-tsk-X
selfconnect keys info --json
```

### selfconnect keys revoke TSK_KEY

Permanently revoke a TSK key.

```bash
selfconnect keys revoke sc-tsk-XXXX-YYYY
```

### selfconnect session start AGENT_ID

Start a new governed session. Prints session ID to stdout.

```bash
selfconnect session start my-agent
SESSION=$(selfconnect session start my-agent)   # capture in scripts
selfconnect session start my-agent --json       # JSON output
```

### selfconnect session end SESSION_ID

End an active session.

```bash
selfconnect session end 3f2a1b4c-...
selfconnect session end 3f2a1b4c-... --summary "Completed research task"
```

### selfconnect version

Print SDK version.

```bash
selfconnect version
```

## Common Workflows

### Check budget before running an agent

```bash
selfconnect status
# If remaining tokens > 0, proceed
```

### Script-based session governance

```bash
SESSION=$(selfconnect session start my-pipeline-agent)
# ... run your agent ...
selfconnect session end "$SESSION" --summary "Pipeline completed"
selfconnect audit "$SESSION" --output "audit-$(date +%Y%m%d).json"
```

### Export workflow evidence input

```bash
selfconnect audit SESSION_ID --output workflow-evidence.json
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (authentication, API, invalid input) |

## Global Options

All commands support:
- `--key / -k TEXT` — Override the configured TSK key for this invocation
- `--json` — Output machine-readable JSON instead of formatted text

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SELFCONNECT_TSK_KEY` | TSK key (overrides config file) |
| `SELFCONNECT_BASE_URL` | API base URL (default: https://api.selfconnect.ai) |

## Links

- Docs: https://selfconnect.ai/docs/cli
- PyPI: https://pypi.org/project/selfconnect/
- GitHub: https://github.com/rblake2320/selfconnect-ecosystem
- Issues: https://github.com/rblake2320/selfconnect-ecosystem/issues

# SelfConnect Ecosystem — Claude Code Instructions

## What This Repo Is

This is the **meta/umbrella repository** for the SelfConnect project. Most
product folders are git submodules pointing to separate repositories. The
versioned Python SDK under `packages/selfconnect-py/` is an exception and is
maintained directly in this repository.

**Edit source in its owning repository.** For submodule products, work in the
submodule repository. For the Python SDK, work in `packages/selfconnect-py/`.

## Repo Map

| Folder | What it is | When to touch it |
|--------|------------|-----------------|
| `core/` | Win32 injection SDK — PostMessage WM_CHAR | Any agent communication, window targeting, mesh injection |
| `enterprise/` | Governance layer — policy and audit mechanisms | Enterprise deployment and regulated-environment evaluation |
| `federal/` | Restricted-environment identity + orchestration research | Government/defense deployment evaluation |
| `accord/` | Cryptographic evidence packaging | Producing integrity-verifiable evidence inputs |
| `alt/` | Deep Win32 optimization — ConPTY, SharedMemIPC, DXGI | Performance-critical injection, screen capture, low-latency |
| `mac/` | macOS port | Any Mac-side agent communication |
| `audio/` | Audio/voice channel | Voice-to-agent, speech injection |
| `plugins/` | Extension/plugin layer | Adding new capabilities to the SDK |
| `log/` | Audit logging | Tracing agent actions |
| `provenance/` | Cryptographic provenance tracking | Chain-of-custody for agent actions |
| `agent-wire/` | Dispatch gateway — deny-by-default policy, hash-chained ledger | All inter-agent message routing |
| `agent-status/` | Token burn daemon — JSONL tailing, USD limits, PreToolUse hook | Budget enforcement, combined cross-session ceiling, fleet monitoring |
| `selfconnect-store/` | SQLite event store — session/workflow queries and evidence bundle inputs | Operational queries, evidence review, cross-session analytics |
| `bpc/` | Bound Pair Credentials — registered pair-key auth with configurable replay controls | Agent authentication in higher-assurance tiers |
| `tsk/` | Tumbler-Style Rotating Segment Keys — structural key secrecy | Key rotation in federal/enterprise tiers |
| `demo/` | Demo kit | Demos and examples |

## Critical Rules

1. **Use `core/` for injection** — `enterprise/` has diverged and will fail for direct injection tasks
2. **Re-enumerate HWNDs each session** — Windows terminal handles (HWNDs) change on every reboot
3. **`agent-wire` is the policy gate** — all inter-agent messages must pass through it; do not bypass
4. **Win32 injection requires `char_delay=0.02`** — too fast causes dropped characters
5. **Mesh replies travel over SelfConnect** — when Codex, Gemini, or another agent asks you to reply, send the answer into that agent's registered terminal. Do not narrate the answer in your own pane. Local output after sending should be only `SENT`, `ACK`, or a one-line blocker.

Read `docs/agent-mesh-coordination.md` before multi-agent work.

## Key API (core)

```python
import sys
sys.path.insert(0, 'core/')
from self_connect import list_windows, send_string

# Find target window
win = next(w for w in list_windows() if w.hwnd == TARGET_HWND)
send_string(win, "Your message here\r", char_delay=0.02)
```

## Three-Node Mesh Architecture

```
Windows PC (AXIOM) ←──→ Spark-1 ←──→ Spark-2
    RTX 5090               GB10          GB10

Pipe 1 — Discovery:
  spark2_client.py → Hub:8765 → hub_relay.py (Windows) → HWND list

Pipe 2 — I/O:
  windows_agent_client.py → SSH :9877 → windows_agent.py → Win32
```

Both pipes must be live for full mesh capability. Run `hub_relay.py` and `windows_agent.py` on Windows.

## Policy (agent-wire / mesh_wire.py)

| Action | Policy |
|--------|--------|
| `terminal.inject.chat` | allow (logged, hash-chained) |
| `terminal.inject.shell` | require_operator_approval |
| `terminal.inject.approval_response` | deny |
| Unknown target_id | deny — raw HWNDs forbidden at boundary |

## Working with Submodules

```bash
# Update a specific submodule to latest
cd core && git pull origin main && cd ..
git add core && git commit -m "chore: update core"

# Update all submodules at once
git submodule update --remote --merge

# Check submodule status
git submodule status
```

## Docs

- `docs/architecture.md` — full system design
- `docs/mesh-setup.md` — step-by-step mesh bring-up
- `docs/security-model.md` — threat model and policy design
- `docs/agent-mesh-coordination.md` — token-disciplined agent-to-agent transport rules

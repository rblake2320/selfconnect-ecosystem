# SelfConnect — System Architecture

## Core Concept

SelfConnect replaces the assumption that AI agents need an external API or network service to communicate. Instead it uses the OS's native window messaging system to inject text directly into a target process.

On Windows: `PostMessage(hwnd, WM_CHAR, char, 0)` — the same mechanism the OS uses to deliver keyboard input.

This means:
- Works entirely offline
- No server to stand up
- Works across any process boundary (not just terminals)
- Survives network partitions

---

## Component Dependency Graph

```
                    ┌──────────────┐
                    │    federal   │
                    │ (restricted) │
                    └──────┬───────┘
                           │ extends
                    ┌──────▼───────┐
                    │  enterprise  │◄── accord (signed evidence inputs)
                    │ (governance) │
                    └──────┬───────┘
                           │ governs
                    ┌──────▼───────┐
                    │  agent-wire  │
                    │   (gateway)  │
                    └──────┬───────┘
                           │ dispatches to
         ┌─────────────────┼─────────────────┐
    ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
    │  core   │       │   alt   │       │   mac   │
    │ (Win32) │       │(Win32+) │       │ (macOS) │
    └────┬────┘       └─────────┘       └─────────┘
         │
    ┌────┴──────────────────────────────────────────┐
    │  audio  │  plugins  │  log  │  provenance     │
    └─────────────────────────────────────────────── ┘
```

---

## core — The Injection Engine

**File:** `core/self_connect.py`

### How It Works

1. Enumerate all top-level windows via `EnumWindows`
2. For each window, fetch title and class name via `GetWindowText` / `GetClassName`
3. For a Claude Code terminal: class = `CASCADIA_HOSTING_WINDOW_CLASS`
4. Inject characters one-by-one via `PostMessage(hwnd, WM_CHAR, ord(char), 0)`
5. `send_string()` adds `char_delay=0.02` between chars — the minimum safe rate

### PrintWindow Capture

`core` also wraps `PrintWindow()` + `BitBlt` for screen capture of any window without focus.

### What `alt` Adds

`alt/` layers on top:
- CacheRequest for UIA accessibility tree (faster than repeated Win32 calls)
- `WriteConsoleInput` for direct console injection (bypasses WM_CHAR)
- ConPTY own-pipe (own the pseudo-terminal)
- dxcam DXGI capture (GPU-accelerated screen grab)
- SharedMemIPC (zero-copy shared memory channel)
- SendInput batching (bulk key events)

---

## agent-wire — The Policy Gateway

All inter-agent messages route through `agent-wire` before reaching an injection endpoint. This enforces the policy table:

| Action | Verdict | Logged |
|--------|---------|--------|
| `terminal.inject.chat` | allow | yes, hash-chained |
| `terminal.inject.shell` | deny (configurable) | yes |
| `terminal.inject.approval_response` | deny always | yes |
| Unknown `target_id` | deny | yes |

The ledger is a JSONL file where each entry carries a SHA-256 chain hash of the previous entry — tamper-evident.

`target_id` is a logical name from `TARGET_REGISTRY` (e.g., `axiom-windows-claude`) — raw HWNDs are rejected at the boundary to prevent TOCTOU attacks.

---

## enterprise — Governance Layer

Adds on top of `core`:
- Policy definition language (YAML-based rules)
- Operator approval workflow
- Audit ledger (beyond agent-wire's gateway log)
- 528 tests
- 15 modules

**Critical rule:** enterprise has diverged from core's injection path. Use core for injection. Use enterprise for governance, policy checks, and audit — not for sending messages.

---

## federal — Restricted-Environment Deployment Research

Extends enterprise with:
- Agent identity mechanisms that may combine device and operator credentials
- Configurable classification gating intended for deployment-specific assessment
- Audit events that can be mapped during a deployment-specific control assessment
- Integration research for deployment-provided PKI

---

## accord — Evidence Packaging

Adds detached signatures to hash-chained JSONL ledger exports. The resulting
files provide integrity and signer-attribution inputs; they do not by themselves
establish completeness, legal admissibility, regulatory compliance, or an
authorization decision.

---

## Three-Node Mesh

The ecosystem scales to a cross-OS cluster via two independent communication pipes:

```
Windows PC (192.168.12.198)
  RTX 5090 — runs AXIOM (Windows Claude Code terminal)
  Runs: hub_relay.py, windows_agent.py:9877

Spark-1 (192.168.12.132)
  GB10 — relay node
  Runs: Hub:8765

Spark-2 (10.0.0.2)
  GB10 — remote node
  Runs: spark2_client.py, governed_inject.py
```

### Pipe 1 — Discovery (Hub)

```
Spark-2: spark2_client.py
  → POST hub.windows:8765  (CMD: LIST_WINDOWS)
  → hub_relay.py (Windows)
  → calls list_windows()
  → returns HWND table to Spark-2
```

Used for: discovering what terminals are available before injecting.

### Pipe 2 — I/O (SSH Tunnel)

```
Spark-2: windows_agent_client.py
  → SSH tunnel → windows_agent.py:9877 (Windows)
  → send_string() / read_text() / capture()
```

Used for: actual injection and screen reading.

Both pipes must be live for full capability.

---

## Security Model

See [security-model.md](security-model.md).

---

## Mesh Bring-Up

See [mesh-setup.md](mesh-setup.md).

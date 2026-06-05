# SelfConnect Ecosystem — Agent Guide

This file tells AI coding agents (Claude Code, Codex, Cursor, Copilot, Gemini Code, etc.) how to understand and work within this repository.

---

## What SelfConnect Is

SelfConnect is an **OS-native AI-to-AI communication protocol**. It lets AI agents talk to each other by injecting text directly into terminal windows — no external API, no browser, no middleware. It works at the Win32 layer (PostMessage WM_CHAR) on Windows and has a macOS port.

**In plain terms:** One AI agent can send a message to another AI agent running in a different terminal, just by knowing its window handle — entirely local, entirely offline-capable.

---

## Repository Structure

This is a **meta/umbrella repository**. Every subfolder is a git submodule — a separate GitHub repo that happens to be nested here. You can work in any folder independently.

```
selfconnect-ecosystem/
├── core/           → selfconnect           (the Win32 injection SDK — start here)
├── enterprise/     → selfconnect-enterprise (governance + policy enforcement)
├── federal/        → selfconnect-federal    (IL6/IL7 government tier)
├── accord/         → selfconnect-accord     (cryptographic compliance evidence)
├── alt/            → selfconnect-alt        (optimized Win32 fork)
├── mac/            → SelfConnect-Mac        (macOS port)
├── audio/          → selfconnect-audio      (voice/audio channel)
├── plugins/        → selfconnect-plugins    (extension layer)
├── log/            → selfconnect-log        (audit logging)
├── provenance/     → selfconnect-provenance (chain-of-custody)
├── agent-wire/     → agent-wire             (inter-agent dispatch gateway)
├── agent-status/   → agent-status           (token burn monitor + budget enforcement)
├── bpc/            → bpc-protocol           (hardware-bound credential protocol)
├── tsk/            → tsk-protocol           (rotating segment key protocol)
├── demo/           → SelfConnect-Demo-kit-  (examples and demos)
└── docs/                                    (cross-repo design documents)
```

---

## Layer Model (bottom to top)

```
┌──────────────────────────────────────────┐
│  federal / accord                        │  Compliance & evidence
├──────────────────────────────────────────┤
│  enterprise                              │  Governance, policy, audit
├──────────────────────────────────────────┤
│  agent-wire                              │  Message routing (deny-by-default)
├──────────────────────────────────────────┤
│  core / alt / mac                        │  OS-level injection
├──────────────────────────────────────────┤
│  audio / plugins / log / provenance      │  Channel extensions
└──────────────────────────────────────────┘
```

---

## Where to Start

**If you want to understand the protocol:** read `core/` first — specifically `self_connect.py`.

**If you want to send a message between agents:**

```python
from self_connect import list_windows, send_string

# List all terminal windows
windows = list_windows()

# Send to a specific HWND
send_string(win, "Hello from another agent\r", char_delay=0.02)
```

**If you want to enforce policy on agent messages:** look at `agent-wire/`.

**If you're deploying in an enterprise or government context:** start in `enterprise/` or `federal/`.

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| Win32 PostMessage instead of pipes or sockets | Works across process boundaries with no prior setup; no server needed |
| `char_delay=0.02` minimum | Windows message queue drops characters at higher speed |
| HWNDs re-enumerated each session | Windows reassigns handles on every reboot — never hardcode |
| `agent-wire` as policy gate | Central deny-by-default prevents unauthorized injection |
| Two-pipe mesh (Hub + SSH) | Hub for discovery, SSH for I/O — each pipe has a distinct failure mode |
| Enterprise diverged from core | Enterprise added governance that broke the injection path — keep them separate |

---

## Three-Node Mesh (Windows ↔ Spark-1 ↔ Spark-2)

The protocol scales to a cross-OS cluster:

```
Windows PC (Win32 injection)
    ↕  Hub :8765  (discovery pipe)
Spark-1 GB10
    ↕  xdotool    (Linux injection)
Spark-2 GB10
    ↕  SSH :9877  (I/O pipe back to Windows)
```

The round-trip has been confirmed live: Spark-2 can inject text into a Windows terminal and receive a reply with zero human relay.

---

## Agent Policy (mesh_wire.py)

| Action | Policy |
|--------|--------|
| `terminal.inject.chat` | ALLOW — logged + hash-chained |
| `terminal.inject.shell` | DENY by default (require operator approval) |
| `terminal.inject.approval_response` | DENY always |
| Raw HWND as target_id | DENY — must use logical name from TARGET_REGISTRY |

---

## Common Tasks

**Enumerate windows (find a target):**
```python
from self_connect import list_windows
for w in list_windows():
    if w.class_name == 'CASCADIA_HOSTING_WINDOW_CLASS':
        print(f"0x{w.hwnd:08X}  {w.title[:60]}")
```

**Update all submodules to latest:**
```bash
git submodule update --remote --merge
```

**Work on one module:**
```bash
cd core
git checkout main
# edit, commit, push — changes go to rblake2320/selfconnect
```

---

## Related Projects

- **GUMBO** (`rblake2320/gumbo`) — Fusion orchestrator built on top of SelfConnect Enterprise + BPC + TSK
- **PKA Team** (`rblake2320/pka-team`) — 15-agent workspace that uses SelfConnect for inter-agent communication
- **TSK Protocol** (`rblake2320/tsk-protocol`) — Tumbler-Style Rotating Segment Keys, used in federal/enterprise tiers for structural key secrecy (`tsk/` submodule)

---

## Docs

| File | Contents |
|------|----------|
| `docs/architecture.md` | Full system design with diagrams |
| `docs/mesh-setup.md` | Step-by-step: bring up the three-node mesh |
| `docs/security-model.md` | Threat model, policy design, audit chain |

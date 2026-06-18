# SelfConnect Ecosystem

> **OS-native AI-to-AI communication — no API, no browser, no middleware.**
> Win32 PostMessage injection, cross-node mesh, enterprise governance, and federal-tier compliance — all from a single protocol.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      SelfConnect Ecosystem                       │
│                                                                  │
│  ┌──────────┐   ┌────────────┐   ┌──────────┐  ┌───────────┐  │
│  │   core   │──▶│ enterprise │──▶│ federal  │  │   accord  │  │
│  │ (Win32   │   │(governance │   │(IL6/IL7  │  │(crypto    │  │
│  │  SDK)    │   │ + policy)  │   │ tier)    │  │ evidence) │  │
│  └──────────┘   └────────────┘   └──────────┘  └───────────┘  │
│       │                                                          │
│       ├──▶ alt        (deep Win32 optimization fork)            │
│       ├──▶ mac        (macOS port)                              │
│       ├──▶ audio      (audio/voice channel)                     │
│       ├──▶ plugins    (extension layer)                         │
│       ├──▶ log        (audit + logging)                         │
│       ├──▶ provenance (cryptographic provenance)                │
│       ├──▶ agent-wire   (policy dispatch gateway)               │
│       ├──▶ agent-status (token burn monitor + budget enforcement)│
│       ├──▶ bpc          (hardware-bound credential protocol)    │
│       ├──▶ tsk          (rotating segment key protocol)         │
│       └──▶ demo         (demo kit)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repos in This Ecosystem

Note: this table reflects the historical submodule layout. For the current owner-declared product boundary and the adjacent/non-core repo list, use [Ecosystem Scope And Workspaces](docs/ecosystem-scope-and-workspaces.md) as the source of truth.

| Folder | Repo | Description |
|--------|------|-------------|
| `core/` | [selfconnect](https://github.com/rblake2320/selfconnect) | Core Win32 SDK — PostMessage + PrintWindow injection, zero API between agents |
| `enterprise/` | [selfconnect-enterprise](https://github.com/rblake2320/selfconnect-enterprise) | Enterprise AI agent infrastructure — Win32-native mesh for government and regulated enterprise |
| `federal/` | [selfconnect-federal](https://github.com/rblake2320/selfconnect-federal) | IL6/IL7 aligned agentic identity and orchestration |
| `accord/` | [selfconnect-accord](https://github.com/rblake2320/selfconnect-accord) | Cryptographically enforced agent compliance evidence platform |
| `alt/` | [selfconnect-alt](https://github.com/rblake2320/selfconnect-alt) | Deep Win32 optimization fork — CacheRequest UIA, WriteConsoleInput, ConPTY, dxcam DXGI, SharedMemIPC |
| `mac/` | [SelfConnect-Mac](https://github.com/rblake2320/SelfConnect-Mac) | macOS port |
| `audio/` | [selfconnect-audio](https://github.com/rblake2320/selfconnect-audio) | Audio/voice communication channel |
| `plugins/` | [selfconnect-plugins](https://github.com/rblake2320/selfconnect-plugins) | Plugin and extension layer |
| `log/` | [selfconnect-log](https://github.com/rblake2320/selfconnect-log) | Audit logging |
| `provenance/` | [selfconnect-provenance](https://github.com/rblake2320/selfconnect-provenance) | Cryptographic provenance tracking |
| `agent-wire/` | [agent-wire](https://github.com/rblake2320/agent-wire) | Policy-as-code dispatch gateway with deny-by-default, cryptographic ledger, and classification gating |
| `agent-status/` | [agent-status](https://github.com/rblake2320/agent-status) | Real-time token burn monitor — JSONL tailing, combined cross-session ceiling, USD limits, PreToolUse enforcement hook |
| `bpc/` | [bpc-protocol](https://github.com/rblake2320/bpc-protocol) | Bound Pair Credentials — hardware-bound, pair-verified, replay-proof credential protocol used in enterprise/federal tiers |
| `tsk/` | [tsk-protocol](https://github.com/rblake2320/tsk-protocol) | Tumbler-Style Rotating Segment Keys — structural key secrecy, used in federal/enterprise tiers |
| `demo/` | [SelfConnect-Demo-kit-](https://github.com/rblake2320/SelfConnect-Demo-kit-) | Demo kit |

---

## Quick Start

Clone everything at once (all submodules included):

```bash
git clone --recurse-submodules https://github.com/rblake2320/selfconnect-ecosystem
```

Or if you already cloned without submodules:

```bash
git submodule update --init --recursive
```

---

## Layer Model

```
┌─────────────────────────────────────┐
│  federal/accord                     │  ← Compliance & evidence layer
├─────────────────────────────────────┤
│  enterprise                         │  ← Governance, policy, audit ledger
├─────────────────────────────────────┤
│  agent-wire                         │  ← Dispatch gateway (deny-by-default)
├─────────────────────────────────────┤
│  core  /  alt  /  mac               │  ← OS-level injection (Win32 / macOS)
├─────────────────────────────────────┤
│  audio / plugins / log / provenance │  ← Channel extensions
└─────────────────────────────────────┘
```

**Rule:** Always use `core` for injection. `enterprise` handles governance — it has diverged from the injection path.

---

## Key Concepts

**Win32 PostMessage injection** — `core` uses `WM_CHAR` PostMessage to inject keystrokes into any process window by HWND. No focus required. No API. No browser.

**Two-pipe mesh architecture** (three-node: Windows ↔ Spark-1 ↔ Spark-2):
- Pipe 1 — Discovery: `spark2_client.py → Hub:8765 → hub_relay.py → HWND list`
- Pipe 2 — I/O: `windows_agent_client.py → SSH tunnel → windows_agent.py:9877 → Win32`

**Policy gate** (`agent-wire` / `mesh_wire.py`):
- `terminal.inject.chat` → allow (logged, hash-chained)
- `terminal.inject.shell` → require operator approval
- Unknown target → deny

---

## Contributing / Updating Submodules

Each folder is a live git submodule pointing to its own repo. To update all to latest:

```bash
git submodule update --remote --merge
```

To work on a specific module:

```bash
cd core
git checkout main
# make changes, commit, push — goes to rblake2320/selfconnect
```

The ecosystem repo tracks the commit SHA of each submodule. After updating, commit the pointer change here:

```bash
cd ..
git add core  # or whichever changed
git commit -m "chore: update core to latest"
```

---

## Docs

See `docs/` for cross-repo design documents:
- [Architecture](docs/architecture.md)
- [Mesh Setup](docs/mesh-setup.md)
- [Security Model](docs/security-model.md)
- [Agent Mesh Coordination](docs/agent-mesh-coordination.md)
- [Ecosystem Scope And Workspaces](docs/ecosystem-scope-and-workspaces.md)
- [Competitive And Patent Watch](docs/competitive-patent-watch.md)

---

## Repository Visibility

All repositories in this ecosystem are **private**. Access is by invitation only.

| Repo | Role |
|------|------|
| `selfconnect-ecosystem` | This umbrella meta-repo |
| `selfconnect` | Core Win32 SDK |
| `selfconnect-enterprise` | Enterprise governance layer |
| `selfconnect-federal` | Federal/IL6-IL7 tier |
| `selfconnect-accord` | Compliance evidence platform |
| `selfconnect-alt` | Deep Win32 optimization fork |
| `SelfConnect-Mac` | macOS port |
| `selfconnect-audio` | Audio/voice channel |
| `selfconnect-plugins` | Plugin extension layer |
| `selfconnect-log` | Audit logging |
| `selfconnect-provenance` | Cryptographic provenance |
| `agent-wire` | Policy dispatch gateway |
| `agent-status` | Token burn / budget monitor |
| `bpc-protocol` | Bound Pair Credentials |
| `tsk-protocol` | Tumbler-Style Rotating Segment Keys |
| `SelfConnect-Demo-kit-` | Demo kit |

To request access contact the maintainer: **github.com/rblake2320**

---

## License

Each repository carries its own license. See individual repo READMEs.

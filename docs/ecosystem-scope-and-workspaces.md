# SelfConnect Ecosystem Scope And Workspaces

Last updated: 2026-06-18 07:28:24 -05:00

This is the command-center map for SelfConnect. It exists so agents do not have to infer the ecosystem from whatever happens to be open in `PKA testing`.

## Workspace Rule

`C:\Users\techai\PKA testing` is the active workbench. It contains current experiments, unrelated repos, temporary clones, owner inboxes, generated artifacts, and scratch work. Do not treat every folder there as part of SelfConnect.

`C:\Users\techai\PKA testing\pka clone` is the cleaner PKA reference workspace. Use it for PKA governance, team process, watch reports, and owner-inbox context. It is not the SelfConnect product boundary.

`selfconnect-ecosystem` is the SelfConnect big-view repo. It should hold maps, cross-repo strategy, watch procedures, and high-level evidence indexes. Source changes still belong in their owning repos.

## SelfConnect Ecosystem Repos

These are the repos currently treated as part of the SelfConnect ecosystem:

| Repo | Role |
| --- | --- |
| `selfconnect-ecosystem` | Umbrella command-center repo and cross-repo map. |
| `selfconnect` | Normal/core SelfConnect SDK: fast local AI-to-AI transport, Win32 terminal channel, packaging, MCP adapter, readback helpers. |
| `selfconnect-enterprise` | Enterprise governance: service mode, leases, WORM wiring, TPM adapter, MCP runtime dispatch, ATO docs. |
| `selfconnect-federal` | Government/federal tier with IL6/IL7-minded process and evidence goals. |
| `selfconnect-provenance` | Provenance and chain-of-custody layer. |
| `selfconnect-terminal` | Terminal experience and terminal-specific mesh workflows. |
| `selfconnect-plugins` | Plugin and extension surface. |
| `selfconnect-audio` | Audio/voice channel work. |
| `SelfConnect-Mac` | macOS SelfConnect path. |
| `SelfConnect-Demo-kit-` | Demo and reproducible proof kit. |
| `selfconnect-frontier-harness` | Frontier model and agent test harness work. |
| `selfconnect-accord` | Compliance/evidence agreement layer. |
| `selfconnect-linux` | Linux SelfConnect path. |
| `selfconnect-alt` | Alternative and optimized SelfConnect path. |
| `bpc-protocol` | Bound Pair Credentials, hardware-bound credential work used by higher assurance tiers. |
| `tsk-protocol` | Rotating segment key protocol used by enterprise/federal support paths. |
| `patent-portfolio` | Patent and claim evidence workspace. |
| `ultra-computer` | Only the parts directly supporting SelfConnect should be considered ecosystem-adjacent. |

## Adjacent But Not Core Ecosystem

These can inform SelfConnect, but agents should not classify them as SelfConnect product repos without an explicit task:

| Repo or project | Why it is adjacent |
| --- | --- |
| `ultra-protocol` | Protocol research, not current SelfConnect ecosystem scope. |
| `ultra-rag` | RAG support work, not SelfConnect itself. |
| `mcp-router` | MCP routing research/tooling. SelfConnect can expose MCP, but does not depend on MCP for OS-native actions. |
| `mcp-server-builder` | MCP tooling. |
| `agent-brain` | Agent logic research. |
| `agent-status` | Agent status/budgeting context, not current ecosystem scope. |
| `ai-army-core` | Multi-agent workspace context. |
| `nexus-agi-army` | Multi-agent workspace context. |
| `verified-agent-ops` | Agent operations/evidence ideas, not current SelfConnect product boundary. |
| `gumbo` | Orchestration concept, not current SelfConnect product boundary. |
| `agent-wire` | Policy-as-code work that can inform enterprise design, but should not be assumed to be current SelfConnect core. |

## Three Product Tracks

SelfConnect should stay usable at three distinct levels. Do not let government controls make normal SelfConnect hard to use.

| Track | Goal | Defaults |
| --- | --- | --- |
| Normal | Fast personal AI-to-AI work: bidirectional, tridirectional, and N-agent mesh testing. | Keep gates open. Keep target guard, birth ID, mesh registry, compact handoff, and echo-filtered readback because they are correctness, not governance friction. |
| Enterprise | Governance, controls, audit, service mode, WORM, leases, MCP dispatch, admin visibility. | Policy-enabled by explicit profile. Fail closed where enterprise customers expect it. |
| Government | IL6/IL7-minded process, provenance, TPM/WORM evidence, ATO package, strict records. | Full governance and evidence mode. This should not be the default personal developer path. |

## Cross-Repo Agent Rule

Before changing code, identify the owning repo. If the work is:

- raw OS-native send/read/package behavior, use `selfconnect`;
- enterprise controls or service behavior, use `selfconnect-enterprise`;
- federal/IL6/IL7 evidence, use `selfconnect-federal`;
- patent claim/evidence records, use `patent-portfolio` or this repo's watch docs;
- broad map, competitive watch, or cross-repo strategy, use `selfconnect-ecosystem`.

When unsure, add a short note here or in `docs/competitive-patent-watch.md` instead of moving source code.

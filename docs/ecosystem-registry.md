# SelfConnect Ecosystem Registry

> **Purpose:** This registry is the single navigation point for SelfConnect-related repositories. It records how each repository connects to the ecosystem without moving source code out of its owning repository.

The [SelfConnect Ecosystem Scope And Workspaces](ecosystem-scope-and-workspaces.md) document remains the source of truth for product-boundary decisions. This registry provides the operational lookup layer: it shows which components are checked out as submodules, which are catalog-only, and which require an explicit decision before work begins.

## How to Use This Registry

Clone the command-center repository and its checked-out components with:

```bash
git clone --recurse-submodules https://github.com/rblake2320/selfconnect-ecosystem
```

The umbrella repository contains maps, cross-repository strategy, security guidance, and evidence indexes. Each component repository remains the source of truth for its implementation, release history, and repository-local documentation. A catalog entry creates a discoverable connection; it does **not** imply that the component is part of the product boundary or that a user has permission to access a private repository.

| Connection type | Meaning |
|---|---|
| **Umbrella** | The command-center repository that owns cross-repository maps and strategy. |
| **Submodule** | A first-class checked-out component tracked by a commit pointer in this repository. |
| **Catalog-only** | A linked repository that is discoverable here but deliberately is not initialized by a recursive clone. |
| **Adjacent** | A related project that may inform SelfConnect but is not a current product component unless an explicit task says otherwise. |
| **Legacy / duplicate** | A historical or duplicate repository retained for traceability; do not treat it as an active module without review. |

## Product-Boundary Components

| Connection | Path | Repository | Role |
|---|---|---|---|
| Umbrella | `/` | [selfconnect-ecosystem](https://github.com/rblake2320/selfconnect-ecosystem) | Command-center map, cross-repository strategy, security guidance, and evidence indexes. |
| Submodule | `core/` | [selfconnect](https://github.com/rblake2320/selfconnect) | Normal/core SDK for OS-native AI-to-AI transport and Win32 terminal workflows. |
| Submodule | `terminal/` | [selfconnect-terminal](https://github.com/rblake2320/selfconnect-terminal) | Governed terminal experience and terminal-specific mesh workflows. |
| Submodule | `enterprise/` | [selfconnect-enterprise](https://github.com/rblake2320/selfconnect-enterprise) | Enterprise governance, service mode, policy, audit, and administrative controls. |
| Submodule | `federal/` | [selfconnect-federal](https://github.com/rblake2320/selfconnect-federal) | Restricted-environment process and evidence goals; deployment authorization remains environment-specific. |
| Submodule | `accord/` | [selfconnect-accord](https://github.com/rblake2320/selfconnect-accord) | Signed evidence packaging and verification layer. |
| Submodule | `provenance/` | [selfconnect-provenance](https://github.com/rblake2320/selfconnect-provenance) | Provenance and chain-of-custody layer. |
| Submodule | `plugins/` | [selfconnect-plugins](https://github.com/rblake2320/selfconnect-plugins) | Plugin and extension surface. |
| Submodule | `audio/` | [selfconnect-audio](https://github.com/rblake2320/selfconnect-audio) | Audio and voice-channel work. |
| Submodule | `linux/` | [selfconnect-linux](https://github.com/rblake2320/selfconnect-linux) | Linux-native SelfConnect path. |
| Submodule | `mac/` | [SelfConnect-Mac](https://github.com/rblake2320/SelfConnect-Mac) | macOS SelfConnect path. |
| Submodule | `alt/` | [selfconnect-alt](https://github.com/rblake2320/selfconnect-alt) | Alternative and optimized SelfConnect path. |
| Submodule | `harness/` | [selfconnect-frontier-harness](https://github.com/rblake2320/selfconnect-frontier-harness) | Frontier model and agent execution harness. |
| Submodule | `bpc/` | [bpc-protocol](https://github.com/rblake2320/bpc-protocol) | Bound Pair Credentials protocol used by supported identity paths. |
| Submodule | `tsk/` | [tsk-protocol](https://github.com/rblake2320/tsk-protocol) | Rotating segment-key protocol used by enterprise and federal support paths. |
| Submodule | `demo/` | [SelfConnect-Demo-kit-](https://github.com/rblake2320/SelfConnect-Demo-kit-) | Demonstration and reproducible proof kit. |
| Catalog-only | — | [patent-portfolio](https://github.com/rblake2320/patent-portfolio) | Confidential patent and claim-evidence workspace. It is intentionally not initialized through submodules. |

## Supporting Components Already Checked Out

These repositories are already connected as submodules because they provide cross-cutting transport, policy, observability, or storage capabilities. Their current product-boundary classification is governed by the scope document.

| Connection | Path | Repository | Role |
|---|---|---|---|
| Submodule | `agent-wire/` | [agent-wire](https://github.com/rblake2320/agent-wire) | Policy-as-code dispatch gateway and deny-by-default control point. |
| Submodule | `agent-status/` | [agent-status](https://github.com/rblake2320/agent-status) | Agent status and budget-monitoring context. |
| Submodule | `log/` | [selfconnect-log](https://github.com/rblake2320/selfconnect-log) | Audit-log support. |
| Submodule | `selfconnect-store/` | [selfconnect-store](https://github.com/rblake2320/selfconnect-store) | SQLite-backed event-store support. |

## Connected Catalog: Adjacent, View, and Legacy Repositories

These repositories are linked from this registry so they can be found from one place. They are not submodules because doing so would either blur the declared product boundary, duplicate a working tree, or pull in a repository intended only for review.

| Connection | Repository | Classification | Registry treatment |
|---|---|---|---|
| Catalog-only | [blake-memory-os](https://github.com/rblake2320/blake-memory-os) | Ecosystem memory and visualization view | Linked as a discoverability and navigation layer; it is not a source-code dependency of the runtime. |
| Adjacent | [gumbo](https://github.com/rblake2320/gumbo) | Multi-agent orchestration concept | Linked for coordination context. Do not treat it as a SelfConnect product component without an explicit task. |
| Legacy / duplicate | [selfconnect-terminal-](https://github.com/rblake2320/selfconnect-terminal-) | Older terminal repository | Retained as a direct link only. The canonical terminal component is `terminal/` → `selfconnect-terminal`. |
| Legacy / duplicate | [selfconnect-terminal-1](https://github.com/rblake2320/selfconnect-terminal-1) | Minimal or historical terminal repository | Retained as a direct link only; it is not initialized as a working module. |

## Ownership and Change Rules

| Change type | Owning location |
|---|---|
| OS-native send/read/package behavior | [`core/`](../core/) → `selfconnect` |
| Terminal experience and terminal-specific mesh workflows | [`terminal/`](../terminal/) → `selfconnect-terminal` |
| Enterprise controls or service behavior | [`enterprise/`](../enterprise/) → `selfconnect-enterprise` |
| Restricted-environment process and authorization-package evidence | [`federal/`](../federal/) → `selfconnect-federal` |
| Signed evidence packaging | [`accord/`](../accord/) → `selfconnect-accord` |
| Broad maps, cross-repository strategy, registry, and watch procedures | This repository |

When a submodule changes, update its owning repository first. Then update this repository’s submodule pointer in a separate, reviewable commit. Catalog-only records should be updated whenever a repository is renamed, archived, replaced, or formally reclassified.

## Maintainer Checklist

1. Add a new repository to this registry when it has a genuine SelfConnect relationship.
2. Use a **submodule** only when the repository is a first-class checkout that belongs in the recursive-clone workspace.
3. Use a **catalog-only** entry for traceability, confidential repositories, review-only tools, and intentionally separate workspaces.
4. Mark duplicates and historical snapshots explicitly; do not make them appear to be canonical implementation paths.
5. Keep [Ecosystem Scope And Workspaces](ecosystem-scope-and-workspaces.md) synchronized whenever the formal product boundary changes.

## Related Documents

| Document | Purpose |
|---|---|
| [Architecture](architecture.md) | System-level design and mesh relationships. |
| [Security Model](security-model.md) | Security boundaries and operational controls. |
| [Ecosystem Scope And Workspaces](ecosystem-scope-and-workspaces.md) | Declared product boundary and workspace rules. |
| [README](../README.md) | Top-level orientation and recursive-clone instructions. |

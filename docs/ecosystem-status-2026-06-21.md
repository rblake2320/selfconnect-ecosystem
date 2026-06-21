# SelfConnect Ecosystem Status - 2026-06-21

This is the current big-view status for the SelfConnect ecosystem. It is meant
to keep repo state, proof state, and remaining blockers visible without hunting
through multiple terminals or session transcripts.

## Primary Repos

| Repo | Local path | Branch | Head | State | Remote |
|---|---|---:|---:|---|---|
| selfconnect | `C:\Users\techai\PKA testing\selfconnect` | `test/win32-hardening-v1` | `ec44a0f` | clean | `https://github.com/rblake2320/selfconnect.git` |
| selfconnect-enterprise | `C:\Users\techai\PKA testing\selfconnect-enterprise` | `master` | `4287eb5` | clean, CI PASS | `https://github.com/rblake2320/selfconnect-enterprise.git` |
| selfconnect-ecosystem | `C:\Users\techai\PKA testing\selfconnect-ecosystem` | `main` | `695cf8a` | clean before this doc | `https://github.com/rblake2320/selfconnect-ecosystem.git` |
| selfconnect-terminal | `C:\Users\techai\PKA testing\selfconnect-terminal` | `main` | `bcf86ca` | clean | `https://github.com/rblake2320/selfconnect-terminal.git` |
| selfconnect-linux | `C:\Users\techai\PKA testing\selfconnect-linux` | `main` | `b2c1723` | clean | `https://github.com/rblake2320/selfconnect-linux.git` |
| patent-portfolio | `C:\Users\techai\PKA testing\patent-portfolio` | `master` | `1687559` | clean | `https://github.com/rblake2320/patent-portfolio.git` |

## Repos Present But Dirty

These were not modified as part of this status pass. They need separate cleanup
before relying on them as source-of-truth.

| Repo/path | Branch | Head | Dirty count | Remote |
|---|---:|---:|---:|---|
| `selfconnect_plugins` | `feature/browser-agent-hire` | `3c8ec183` | 64 | `https://github.com/rblake2320/pka-workspace.git` |
| `selfconnect_audio` | `feature/browser-agent-hire` | `3c8ec183` | 64 | `https://github.com/rblake2320/pka-workspace.git` |
| `selfconnect-alt` | `master` | `a0961b3` | 27 | `https://github.com/rblake2320/selfconnect-alt.git` |
| `bpc-protocol` | `master` | `7eb2769` | 5 | `https://github.com/rblake2320/bpc-protocol.git` |
| `tsk-protocol` | `master` | `35edeb4` | 27 | `https://github.com/rblake2320/tsk-protocol.git` |

## Expected But Not Found Locally

| Repo | Expected remote |
|---|---|
| SelfConnect-Mac | `https://github.com/rblake2320/SelfConnect-Mac` |
| selfconnect-federal | `https://github.com/rblake2320/selfconnect-federal` |
| selfconnect-provenance | `https://github.com/rblake2320/selfconnect-provenance` |

## Current Proof State

### Core SelfConnect

Current branch: `test/win32-hardening-v1` at `ec44a0f`.

Validated on this node:

- Full pytest: `434 passed, 28 skipped`
- Scoped package ruff gate: PASS
- `py_compile` for package entry modules: PASS
- Targeted Win32 package tests: `35 passed`
- Python package build: `selfconnect-0.10.4` sdist/wheel PASS

Real-agent proof already recorded in core docs:

- 20 real Codex terminals: PASS
- 20 real mixed Codex/Claude terminals: PASS
- Exact-line ACK hardening: PASS
- Logical/adversarial Fabric suites: PASS

Boundary:

- Broad `ruff check .` in core is not a valid release gate today because the
  repo includes legacy scratch scripts and vision-server experiments with
  pre-existing lint debt. Use the scoped package gate until those folders are
  either excluded or cleaned.

### SelfConnect Enterprise

Current branch: `master` at `4287eb5`.

Validated on this node and GitHub:

- GitHub CI run `27896478148`: PASS
- Local pytest: `1307 passed, 21 skipped`
- Ruff: PASS
- Python package build: PASS
- MSI build: PASS
- Live AWS S3 Object Lock WORM proof: PASS
- TPM platform attestation ABI: fixed and tested

Evidence added in enterprise:

- `docs/ato/WORM_LIVE_AWS_PROOF_2026-06-21.md`
- `docs/ato/WORM_LIVE_AWS_PROOF_2026-06-21.json`
- `docs/ato/MSI_BUILD_PROOF_2026-06-21.md`
- `docs/ato/TPM_LIVE_PROBE_2026-06-21.md`
- `docs/ato/TPM_LIVE_PROBE_2026-06-21.json`
- `docs/ato/GEMINI_REAL_AGENT_AUTH_BLOCKER_2026-06-21.md`

Boundary:

- TPM returns clean NA on this machine with `NCryptCreateClaim -> 0x80090026`.
  This is not a fake PASS. A separate TPM-provisioned machine is still needed
  for a hardware claim PASS artifact.
- Gemini real-agent tests remain blocked by provider authentication, not by
  SelfConnect transport.
- MSI is built locally and hash-recorded. Release automation still needs signing
  and published release artifacts.

## Remaining Gates

1. Gemini real-agent participation:
   - Required evidence: Gemini CLI starts non-interactively and returns a known
     nonce through SelfConnect.
   - Current blocker: Gemini CLI requires interactive login, `GEMINI_API_KEY`,
     or Google Application Default Credentials.

2. TPM PASS artifact:
   - Required evidence: `enterprise.tpm_attestation.tpm_probe()` returns
     `supported=true`, nonzero claim blob, and verification succeeds.
   - Current blocker: this host returns `0x80090026`.

3. Release installer automation:
   - Required evidence: CI/release runner builds, signs, and publishes the MSI.
   - Current state: local WiX v4 MSI build passes and SHA-256 is recorded.

4. Dirty repo cleanup:
   - Required evidence: each repo listed under "Repos Present But Dirty" has a
     clean or intentionally committed status.
   - Current state: not addressed in this pass to avoid mixing cleanup with
     proof work.

5. Ecosystem submodule/source-of-truth cleanup:
   - Required evidence: `selfconnect-ecosystem` accurately points to the current
     intended repos/commits and does not track build dependencies such as
     `node_modules`.
   - Current state: status map added; broad restructuring deferred.

## Ecosystem Validation Notes

Validation performed while adding this snapshot:

- `git diff --check`: PASS, with only Git line-ending conversion warnings.
- `packages/selfconnect-py` unit tests: PASS with repo-local temp directory,
  `57 passed, 7 deselected`.

Known ecosystem test-runner cleanup:

- `pnpm -r run test` is not clean on this Windows node. `tsk-client` passes
  after a fresh pnpm install, but the existing workspace dependency layout for
  `tsk-mcp` cannot resolve sibling package `@selfconnect/tsk-client` without a
  separate package-link/build cleanup.
- The ecosystem repo currently tracks package `node_modules` content. That is a
  source-of-truth problem and should be cleaned in a dedicated repo hygiene
  branch, not mixed into this status snapshot.

## Version-Control Repair Note

On 2026-06-21 this repo had staged deletions for the full tree while matching
files still existed as untracked working-tree files. The staged deletions were
unstaged without modifying file contents. A snapshot of the staged-deletion list
was written under `.git/` for local forensic reference and is intentionally not
tracked.

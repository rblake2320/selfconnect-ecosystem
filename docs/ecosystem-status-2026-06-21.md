# SelfConnect Ecosystem Status - 2026-06-21

This is the current big-view status for the SelfConnect ecosystem. It is meant
to keep repo state, proof state, and remaining blockers visible without hunting
through multiple terminals or session transcripts.

## Primary Repos

| Repo | Local path | Branch | Head | State | Remote |
|---|---|---:|---:|---|---|
| selfconnect | `C:\Users\techai\PKA testing\selfconnect` | `test/win32-hardening-v1` | `01b241b` | clean, Gemini 5 PASS, 10 blocked by quota, Fabric V2 frame/mailbox PASS | `https://github.com/rblake2320/selfconnect.git` |
| selfconnect-enterprise | `C:\Users\techai\PKA testing\selfconnect-enterprise` | `master` | `9d3f98d` | clean, CI PASS | `https://github.com/rblake2320/selfconnect-enterprise.git` |
| selfconnect-ecosystem | `C:\Users\techai\PKA testing\selfconnect-ecosystem` | `main` | `81ebcad` | clean, readiness checker added | `https://github.com/rblake2320/selfconnect-ecosystem.git` |
| selfconnect-terminal | `C:\Users\techai\PKA testing\selfconnect-terminal` | `main` | `bcf86ca` | clean | `https://github.com/rblake2320/selfconnect-terminal.git` |
| selfconnect-linux | `C:\Users\techai\PKA testing\selfconnect-linux` | `main` | `b2c1723` | clean | `https://github.com/rblake2320/selfconnect-linux.git` |
| selfconnect-alt | `C:\Users\techai\PKA testing\selfconnect-alt` | `master` | `8a6a2c4` | clean, local evidence manifest pushed | `https://github.com/rblake2320/selfconnect-alt.git` |
| bpc-protocol | `C:\Users\techai\PKA testing\bpc-protocol` | `master` | `63e8493` | clean, tests/build PASS | `https://github.com/rblake2320/bpc-protocol.git` |
| tsk-protocol | `C:\Users\techai\PKA testing\tsk-protocol` | `master` | `3eecf2a` | clean, tests/build/typecheck PASS | `https://github.com/rblake2320/tsk-protocol.git` |
| patent-portfolio | `C:\Users\techai\PKA testing\patent-portfolio` | `master` | `1687559` | clean | `https://github.com/rblake2320/patent-portfolio.git` |

## Repos Present But Dirty

These were not modified as part of this status pass. They need separate cleanup
before relying on them as source-of-truth.

| Repo/path | Branch | Head | Dirty count | Remote |
|---|---:|---:|---:|---|
| `selfconnect_plugins` | `feature/browser-agent-hire` | `3c8ec183` | 64 | `https://github.com/rblake2320/pka-workspace.git` |
| `selfconnect_audio` | `feature/browser-agent-hire` | `3c8ec183` | 64 | `https://github.com/rblake2320/pka-workspace.git` |

## Expected But Not Found Locally

| Repo | Expected remote |
|---|---|
| SelfConnect-Mac | `https://github.com/rblake2320/SelfConnect-Mac` |
| selfconnect-federal | `https://github.com/rblake2320/selfconnect-federal` |
| selfconnect-provenance | `https://github.com/rblake2320/selfconnect-provenance` |

## Current Proof State

### Core SelfConnect

Current branch: `test/win32-hardening-v1` at `01b241b`.

Validated on this node:

- Full pytest: `470 passed, 9 skipped`
- Scoped package ruff gate: PASS
- `py_compile` for package entry modules: PASS
- Fabric V2 focused tests: `19 passed`
- Targeted Win32 package tests: `35 passed`
- Python package build: `selfconnect-0.10.4` sdist/wheel PASS

Real-agent proof already recorded in core docs:

- 20 real Codex terminals: PASS
- 20 real mixed Codex/Claude terminals: PASS
- Gemini API-key mode preflight: PASS, `SC_PROVIDER_PREFLIGHT_20260621_062323`
- 1 real visible Gemini terminal: PASS, `SC_REAL5_20260621_062543`
- 3-provider real visible mixed run: PASS, `SC_REAL5_20260621_062940`
- 5 real visible Gemini terminals: PASS, `SC_REAL5_20260621_064240`
- 10 real visible Gemini terminals: BLOCKED by provider quota,
  `SC_REAL5_20260621_073044`
- Exact-line ACK hardening: PASS
- Logical/adversarial Fabric suites: PASS
- Fabric V2 frame/mailbox slice: PASS
  - `sc_fabric_v2.py`
  - `selfconnect-fabric selftest`
  - real Windows named-pipe ACK selftest: `0.797 ms`
  - `selfconnect-bench --transport fabric_v2_frame_mailbox --agents 5`
  - V2 transport/governance p99: `0.152 ms`
  - model calls per known task: `0.0`

Boundary:

- Broad `ruff check .` in core is not a valid release gate today because the
  repo includes legacy scratch scripts and vision-server experiments with
  pre-existing lint debt. Use the scoped package gate until those folders are
  either excluded or cleaned.
- Fabric V2 now proves frame/mailbox/security semantics and a real Windows
  named-pipe transport species. Production IOCP host service is still the next
  controllable build target, not yet complete. Tracker:
  https://github.com/rblake2320/selfconnect/issues/7

### SelfConnect Enterprise

Current branch: `master` at `9d3f98d`.

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
- Core Gemini real-agent tests pass when an API key is supplied in the process
  environment and Gemini CLI is temporarily switched to `gemini-api-key` mode.
  Persistent enterprise readiness still requires installing key/ADC
  configuration outside the repository.
- MSI is built locally and hash-recorded. Release automation still needs signing
  and published release artifacts.

## Remaining Gates

1. Gemini persistent workstation readiness:
   - Required evidence: readiness checker sees a persistent User/Machine
     environment key or Google ADC outside the repository.
   - Current state: ephemeral process-scoped key tests passed in core, including
     one real Gemini visible-window ACK and one Codex+Claude+Gemini real mixed
     ACK run. The readiness checker should still report blocked if no persistent
     key/ADC is installed.
   - Tracker: https://github.com/rblake2320/selfconnect-ecosystem/issues/2

2. TPM PASS artifact:
   - Required evidence: `enterprise.tpm_attestation.tpm_probe()` returns
     `supported=true`, nonzero claim blob, and verification succeeds.
   - Current blocker: this host returns `0x80090026`.
   - Tracker: https://github.com/rblake2320/selfconnect-ecosystem/issues/3

3. Gemini 10/15/20 provider quota:
   - Required evidence: 10/15/20 Gemini-included real-agent rungs complete with
     exact ACKs and no provider quota errors.
   - Current blocker: supplied Gemini API key hit
     `generate_content_free_tier_requests` quota, limit `20`, at the 10-agent
     rung.
   - Tracker: https://github.com/rblake2320/selfconnect-ecosystem/issues/5

4. Release installer automation:
   - Required evidence: CI/release runner builds, signs, and publishes the MSI.
   - Current state: local WiX v4 MSI build passes and SHA-256 is recorded.
   - Tracker: https://github.com/rblake2320/selfconnect-ecosystem/issues/4

5. Dirty repo cleanup:
   - Required evidence: each repo listed under "Repos Present But Dirty" has a
     clean or intentionally committed status.
   - Current state: `bpc-protocol`, `tsk-protocol`, and `selfconnect-alt` are
     now clean and pushed. `selfconnect_plugins` and `selfconnect_audio` are
     still broad `pka-workspace` views and require a dedicated cleanup pass.

6. Ecosystem submodule/source-of-truth cleanup:
   - Required evidence: `selfconnect-ecosystem` accurately points to the current
     intended repos/commits and does not track build dependencies such as
     `node_modules`.
   - Current state: status map added; broad restructuring deferred.

## Ecosystem Validation Notes

Additional validation completed after the initial snapshot:

- `selfconnect-ecosystem` at `81ebcad`: added
  `scripts/readiness.py`, `docs/external-gate-readiness.md`, and
  `npm run readiness` as the single big-view readiness gate. Current readiness
  output is `ATTENTION`, not because local repo work is dirty, but because
  external gates remain unresolved:
  - repo hygiene: PASS, `9/9` tracked primary repos clean and synced
  - Gemini non-interactive auth: BLOCKED, Gemini CLI `0.46.0` present but no
    `GEMINI_API_KEY`, no Google ADC, no `gcloud`, and no default ADC file
  - TPM platform attestation: NA on this host, `NCryptCreateClaim -> 0x80090026`
  - MSI release workflow: PASS, run `27897466199`
  - MSI code-signing secrets: BLOCKED, missing
    `WINDOWS_SIGNING_CERT_BASE64` and `WINDOWS_SIGNING_CERT_PASSWORD`
- `selfconnect` at `01b241b`: freeze-check PASS, adversarial suite PASS
  (`adversarial_20260621_023543`), mesh event chain PASS at head
  `66a303516a8bf39576ffe679ed6747e8b8802ab99a240cdc2e8f8d88cbb36bd1`,
  scoped Win32/package tests `35 passed`, scoped ruff PASS, py_compile PASS.
  Fresh Gemini ADC checks are recorded: no API key, no gcloud, no default ADC.
  Gemini recheck `SC_PROVIDER_PREFLIGHT_20260621_061132` still failed as
  `provider_auth_required` because the key was not visible to the test process.
  Runner hardening now pulls Gemini auth variables from Process, User, or
  Machine env at runtime without printing secrets. The user-supplied ephemeral
  key proved the remaining CLI selector issue: env-only still failed under
  `oauth-personal` (`SC_PROVIDER_PREFLIGHT_20260621_061757`), while temporary
  `gemini-api-key` mode passed in preflight
  (`SC_PROVIDER_PREFLIGHT_20260621_062323`), passed one real visible Gemini ACK
  (`SC_REAL5_20260621_062543`), and passed one real mixed Codex+Claude+Gemini
  ACK run (`SC_REAL5_20260621_062940`). The 5-Gemini rung passed
  (`SC_REAL5_20260621_064240`). The 10-Gemini rung is blocked by provider quota
  (`SC_REAL5_20260621_073044`), tracked in issue #5. No secret values are
  tracked.
- `selfconnect` Fabric V2 slice at `01b241b`: `sc_fabric_v2.py` added with
  session-derived HMAC frames, receiver binding, payload hashes, replay
  rejection, deadline rejection, bounded mailbox backpressure, and
  `selfconnect-fabric` CLI. Redacted artifacts are tracked in core:
  `fabric_v2_selftest_20260621_073951_redacted.json`,
  `fabric_v2_5agent_baseline_redacted.json`, and
  `baseline_5agent_fabric_v2_frame_mailbox.json`. The wheel includes the new
  module, CLI entry point, and these artifacts.
- `selfconnect-enterprise` at `9d3f98d`: GitHub Actions MSI release workflow
  run `27897466199` PASS; artifact bundle `selfconnect-enterprise-msi`
  contains `selfconnect-enterprise-1.2.3.msi`, `msi-evidence.json`, and
  `msi-sha256.txt`. Artifact SHA-256:
  `9A1CD2F56B6A4CE3AEFC6CC8CF4C5FE09B07F406F6D0E3ED8E62D9591749CF4D`.
  Signing remains `false` until certificate secrets are configured. GitHub CI
  run `27897628104` PASS for the evidence commit.
- `bpc-protocol` at `63e8493`: `npm test` PASS and `npm run build` PASS.
- `tsk-protocol` at `3eecf2a`: `npm test` PASS, `npm run build` PASS,
  `npm run typecheck` PASS, `demo/e2e_browser_test.py` py_compile PASS, and
  `demo/report.ts --format json` smoke PASS.
- `selfconnect-alt` at `8a6a2c4`: raw root screenshot evidence was not pushed;
  `docs/LOCAL_EVIDENCE_MANIFEST_2026-05-13.md` records filename, byte size,
  and SHA-256 for local verification without public screenshot disclosure.

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

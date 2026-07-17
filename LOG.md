# Change Log

## 2026-07-17

- Added an executable reviewed-squash gate after BPC PR #19 and TSK PR #11
  retained superseded intermediate statements in GitHub-generated squash
  messages. PR commits now reject evidence-like results; the merge helper
  supplies an explicit final subject/body, binds it to the exact head and a
  retained evidence digest, and never requests admin bypass.
- Added first-parent detection after pinned baseline
  `d25b8a1372a15e2332c5b0551c28332dda5f4820`. An unmanaged owner merge is
  detectable and fails the gate; it is not claimed impossible.
- Pinned that baseline as a workflow literal. Reading it from the candidate
  tree would let an unmanaged commit advance the baseline to itself and evade
  the scan.

## 2026-07-16 (fail-closed readiness and security boundary)

- Reproduced hosted run `29509501237` succeeding while its own report said
  `Overall: ATTENTION` and multiple required checks were blocked or
  unavailable.
- Made the readiness CLI fail nonzero by default. Added only an explicit
  `--report-only` diagnostic path, whose output states that it is not readiness
  evidence.
- Split hosted contract validation from live readiness evidence. The hosted
  status is now `readiness-contract`; the manual live gate requires a
  provisioned self-hosted runner and protected cross-repository token.
- Replaced cached repository-ref comparison with live remote-head comparison.
- Replaced provider configuration presence with a real non-interactive exact
  nonce response.
- Bound MSI readiness to a fresh successful run on the current default-branch
  head and to a downloaded, signed, size/hash-consistent artifact evidence set.
- Added adversarial coverage for unavailable checks, truthy non-boolean
  results, stale remote refs, failed provider probes, empty ADC material,
  stale/wrong-head runs, unavailable artifacts, unsigned artifacts, and
  tampered checksums.
- Rewrote `SECURITY.md` to describe the code actually present in this
  repository, bind claims to existing tests, correct cross-repository default
  branch links, and provide a private vulnerability-reporting process without
  publishing exploit details.

## 2026-07-16 (required Python artifact gate)

- Removed pull-request path filtering from the Python SDK workflow so its
  artifact job always reports a status on protected-branch pull requests.
- This permits branch protection to require
  `Claims, build, wheel smoke, audit`; a package change cannot satisfy the
  merge rule while its build or artifact validation is red or absent.

## 2026-07-16 (PyPI environment configuration)

- Created the GitHub `pypi` environment and restricted deployments to
  `selfconnect-py-v*` tags.
- Left `PYPI_TRUSTED_PUBLISHING_ENABLED` absent, so the release workflow remains
  fail-closed until the matching publisher is registered in PyPI.
- GitHub returned HTTP 422 when required-reviewer and wait-timer rules were
  requested because the current plan does not support those environment
  controls. Corrected the runbook rather than claiming they are active.

## 2026-07-16 (Python SDK 1.1.1 claim and release hardening)

- Corrected ecosystem and Python SDK public language so local Win32 transport,
  API-client behavior, callback coverage, server-side rejection, retained
  hash-chain data, hardware backing, and deployment authorization have separate
  bounded claims.
- Removed the invalid impact-level reference and unsupported compliance,
  completeness, immutability, enforcement, hardware-binding, and replay
  absolutes from current umbrella/package documentation.
- Invalidated the prior `docs/WATCH_LEDGER_IBCT_AIP.md` mapping after checking
  the cited primary source: NIST SP 800-204C is a DevSecOps/service-mesh
  publication and does not define the attributed IBCT/AIP concepts.
- Single-sourced Python package version 1.1.1 through
  `selfconnect/_version.py`; runtime export, User-Agent, handler metadata, and
  build metadata now share that source.
- Removed committed wheel/sdist files and Python bytecode/cache artifacts; CI
  rebuilds distributions from reviewed source.
- Added `scripts/package_release_gate.py`: source claims/version/tracked-file
  checks plus static wheel RECORD coverage, exact payload, metadata,
  archive-path/link, and annotated-tag binding verification. Artifact code is
  never imported by the gate.
- Added version, fail-open callback, claim-gate, wheel-tamper, and explicit
  disposable-live-identity tests.
- Added Python 3.9-3.13 unit CI and a 3.12 artifact lane with Ruff, build,
  Twine metadata validation, clean-wheel smoke testing, and a resolved-
  dependency audit that excludes only the unpublished local package.
- Hosted 3.9/3.10 CI exposed a test-only dotted-import ambiguity caused by the
  `selfconnect.cli` package exporting a function named `main`. CLI tests now
  patch the explicitly imported module object, so the same assertion runs
  consistently across supported Python versions.
- Added a disabled-until-owner-configured Trusted Publishing workflow. It
  requires the protected `pypi` environment activation variable and matching
  PyPI OIDC publisher, then verifies published hashes and attestations.

## 2026-07-16 (incident record — hosted hash mismatch)

- Root cause: Windows cp1252 locale decoding of gh's UTF-8 stdout mangled
  em dashes (3 bytes -> 3 mojibake chars each) before hashing, so locally
  generated allowlist hashes disagreed with the correctly-decoded hosted
  runner. NOT a newline issue: CRLF->LF normalization (bf23347) is retained
  as defensive cross-platform canonicalization only, and the earlier CRLF
  attribution in that commit message is superseded by this record.
- Fix: fetch_releases pins encoding=utf-8 errors=strict (fail-closed on
  undecodable bytes); allowlist regenerated from correctly decoded bodies
  (BPC 06c4595c..., len 5092; Enterprise 5ef3287d..., len 6246 — verified
  byte-identical to hosted actuals by both agents independently).
- Regression: non-ASCII subprocess decode round-trip test; mangled-variant
  hash must not match; production fetch_releases call params asserted via
  mock (deleting encoding/errors from production fails the suite).

## 2026-07-16

- Replaced the hosted readiness smoke report with a required, hosted
  `readiness` contract job. It runs only deterministic checker/security-policy
  tests and commit-pinned reference resolution; it does not claim to evaluate
  local hardware, provider credentials, or sibling repository state.
- Added a separate manual `live-readiness` workflow for a protected self-hosted
  Windows runner. It requires the canonical PKA repository root, a bounded
  cross-repository token, an expected signer-certificate fingerprint, live
  Gemini response, TPM probe, current repository heads, and current MSI
  evidence.
- Hardened repository evidence against fork and non-default-branch
  substitution. Hardened result composition so `ok: true` cannot override an
  unexpected status. Evidence age may be tightened but never expanded beyond
  seven days.
- Replaced MSI manifest self-attestation with Windows Authenticode validation:
  `Valid` status, pinned signer SHA-256 fingerprint, and timestamp presence are
  required in addition to workflow/head/hash binding.
- Replaced ecosystem-wide security guarantees with client/component boundaries,
  commit-pinned component policy links, executable local evidence paths, and a
  private-repository disclosure boundary.

## 2026-07-16

- Repointed the `provenance` submodule to rewritten commit
  `dda8d3511713503e51e486004e57563775df4410` after the provenance signing-key
  incident response. The rewrite removed the three revoked private-key paths
  from every commit reachable from `selfconnect-provenance/master`; the
  repository's protected branch and required `test` check were restored after
  the bounded force update.
- The rewritten provenance tree is content-equivalent to the already reviewed
  hardened tree. This change updates only the gitlink so fresh ecosystem
  clones no longer request the superseded key-bearing history.

## 2026-07-16

- Added `scripts/release_claim_scan.py`: executable portfolio gate that scans
  public GitHub release titles and bodies (BPC, TSK, Enterprise) for
  compliance/authorization claims a repository cannot self-establish (FIPS
  validation, DoD Impact Level authorization, ATO, production-readiness).
  Titles must always be clean; body hits pass only under a dated bounded
  correction notice that links the maintained SECURITY/PARKED boundary.
  Motivated by the 2026-07-16 release-claim audit: masters were cleaned but
  the pinned releases (BPC v0.2.0, Enterprise v1.0.0) still carried the
  claims — releases are where stale claims survive.
- Added `tests/test_release_claim_scan.py` (23 tests final): clean pass, title
  overclaim always fails even with notice, body overclaim without notice
  fails, bounded correction passes, Production Release label detection,
  notice marker requirements, case insensitivity, offline CLI mode, error
  exit on no input, undated-notice rejection, notice-after-claim bypass,
  split-marker/date-after-claim bypass, leading-block validation, allowlist
  requirement, sha256-mismatch (post-review edit) rejection, expired
  exception rejection, verdict date boundaries.
- Bounded status is an exact expiring exception (codex-1 reviews 2-3):
  `scripts/claim_scan_allowlist.json` pins repo@tag + body_sha256 +
  review_by. Any body edit after review voids the exception (kills the
  future-claims-under-old-notice blind spot); expiry forces re-review via
  the daily CI run.
- fetch paginates ALL releases (gh api --paginate --slurp, per_page=100,
  pages flattened after strict shape check, malformed page = fail closed):
  the plain endpoint returns only 30, so older releases could evade the
  gate. Two-page + malformed-page regressions.
- Pinned pytest==9.1.1 in release-claim-gate.yml (hosted-proven version):
  the daily cron runs unattended, so a floating pytest could change gate
  behavior with zero commits — same supply-chain rule as the action SHAs.
- Pinned checkout/setup-python to core's immutable SHAs in BOTH workflows
  (release-claim-gate.yml and readiness.yml — the readiness contract's
  floating tags were part of the same gate).
- Added package.json `readiness` + `test:readiness` scripts (readiness CI
  contract from origin/main 9718541).
- Amended Enterprise v1.0.0 release notice: explicitly retracts the
  retained v0.6 statement that denied actions were never exposed to
  observers (v1.0.0 shipped unfiltered context_before, GAPS OBS-1; master
  2026-07-14 filters primary+context under named tests).

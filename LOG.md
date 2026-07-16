# Change Log

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

- Added `scripts/release_claim_scan.py`: executable portfolio gate that scans
  public GitHub release titles and bodies (BPC, TSK, Enterprise) for
  compliance/authorization claims a repository cannot self-establish (FIPS
  validation, DoD Impact Level authorization, ATO, production-readiness).
  Titles must always be clean; body hits pass only under a dated bounded
  correction notice that links the maintained SECURITY/PARKED boundary.
  Motivated by the 2026-07-16 release-claim audit: masters were cleaned but
  the pinned releases (BPC v0.2.0, Enterprise v1.0.0) still carried the
  claims — releases are where stale claims survive.
- Added `tests/test_release_claim_scan.py` (21 tests final): clean pass, title
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

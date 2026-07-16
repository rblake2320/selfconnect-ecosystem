# Change Log

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
- Added `tests/test_release_claim_scan.py` (9 tests): clean pass, title
  overclaim always fails even with notice, body overclaim without notice
  fails, bounded correction passes, Production Release label detection,
  notice marker requirements, case insensitivity, offline CLI mode, error
  exit on no input.

# PyPI Release Procedure

The repository contains a Trusted Publishing workflow, but repository code
cannot authorize itself to publish. The GitHub environment and tag policy are
configured; the owner must complete the PyPI-side trust registration before
the `publish` job can pass.

## One-Time Owner Setup

1. The GitHub environment `pypi` exists.
2. Its deployment policy permits only `selfconnect-py-v*` tags.
3. Required-reviewer and wait-timer environment rules are unavailable on the
   repository's current GitHub plan. Do not claim those controls are active.
4. Add the environment variable
   `PYPI_TRUSTED_PUBLISHING_ENABLED=true` only after the remaining steps are
   complete.
5. In the PyPI `selfconnect` project, add a GitHub Trusted Publisher:
   - owner: `rblake2320`
   - repository: `selfconnect-ecosystem`
   - workflow: `release.yml`
   - environment: `pypi`
6. Protect `main` and require the Python SDK and claim-gate checks before
   merge. Protect changes to `.github/workflows/release.yml`.

No PyPI password or long-lived API token belongs in GitHub.

## Release

1. Merge a reviewed commit whose package version is correct.
2. Create the annotated tag `selfconnect-py-vX.Y.Z` on that commit.
3. Publish a GitHub release for the exact tag.
4. Confirm the `pypi` environment activation variable is set.

The workflow verifies that the tag matches the package version, that the tagged
commit is in `origin/main`, that tests and static gates pass, and that the wheel
and source distribution match their metadata. It then publishes the exact
stored artifacts through short-lived OIDC credentials.

The final job compares PyPI file hashes with the artifacts built earlier in the
workflow and cryptographically verifies the PyPI Trusted Publisher
attestations against this repository.

## Current Block

Until the owner registers the matching PyPI Trusted Publisher and then sets the
environment activation variable, the workflow exits before the publish action.
This is intentional. The activation variable is currently absent.

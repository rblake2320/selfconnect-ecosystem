# PyPI Release Procedure

The repository contains a Trusted Publishing workflow, but repository code
cannot authorize itself to publish. The owner must complete both external
controls before the `publish` job can pass.

## One-Time Owner Setup

1. In GitHub, create an environment named `pypi`.
2. Require an owner-approved reviewer for that environment.
3. Restrict deployment tags to `selfconnect-py-v*`.
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
4. Approve the `pypi` environment deployment.

The workflow verifies that the tag matches the package version, that the tagged
commit is in `origin/main`, that tests and static gates pass, and that the wheel
and source distribution match their metadata. It then publishes the exact
stored artifacts through short-lived OIDC credentials.

The final job compares PyPI file hashes with the artifacts built earlier in the
workflow and cryptographically verifies the PyPI Trusted Publisher
attestations against this repository.

## Current Block

Until the owner creates and approves the `pypi` environment, sets its activation
variable, and registers the matching PyPI Trusted Publisher, the workflow exits
before the publish action. This is intentional.

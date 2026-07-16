# Why

## Release claim scan (2026-07-16)

Test count is not claim governance. The 2026-07-16 audit showed all three
protocol masters green and their READMEs correctly disclaiming FIPS/IL/ATO —
while the *releases* still told the public "IL4-7 Hardening", "production-
ready", "comply with IL4/5/6/7". Source-tree hygiene never reaches pinned
release pages, so claim rot concentrates exactly where consumers look first.

The gate is executable, not editorial: run it in CI or before any release
publish; exit 1 blocks. Bounded correction notices are accepted so that
implementation history can be preserved instead of rewritten — retraction
with provenance beats deletion.

Scope choice: title violations are unconditional failures because titles are
rendered in listings, feeds, and embeds where no notice can travel with them.

## Python package release gate (2026-07-16)

The PyPI 1.1.0 audit found a second claim surface that the GitHub release gate
could not see: wheel metadata, source-distribution documentation, and runtime
version strings. The files were internally hash-consistent, but the public
description overstated callback completeness, storage properties, enforcement,
and authorization support. Metadata said 1.1.0 while runtime and User-Agent
strings said 1.0.0, and the upload had no PyPI provenance.

The correction uses one runtime version file and an executable source/artifact
gate. Built wheels and source distributions are inputs to the check, not trusted
outputs: the gate verifies full wheel RECORD coverage, exact wheel payload,
archive paths and links, metadata/runtime version agreement, prohibited claims,
and annotated release-tag binding without importing artifact code.

Publishing is separate from building. The release workflow uses a manually
approved `pypi` environment, an explicit activation variable, and PyPI Trusted
Publishing. Repository code cannot configure those owner-side controls or
authorize its own publication.

The same review checked cited standards instead of only softening their
language. `docs/WATCH_LEDGER_IBCT_AIP.md` was invalidated because the cited
NIST SP 800-204C covers DevSecOps for microservices and service meshes; it does
not define the IBCT/AIP terms previously attributed to it. Preserving a dated
correction is more defensible than substituting a different unsupported
mapping.

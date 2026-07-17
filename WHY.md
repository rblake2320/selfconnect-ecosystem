# Why

## Readiness status and readiness evidence must be different checks

The old hosted workflow always returned success because it ran the report
without the opt-in failure flag. The hosted runner also lacked the sibling
repositories, private cross-repository permissions, provider credentials, and
TPM capability that the report expected. A green status therefore meant only
that the script printed output, even when the output said the system was not
ready.

The correct composition is:

- hosted CI verifies the checker contract and adversarial behavior;
- a separately named live gate evaluates real evidence on a provisioned host;
- the live checker fails by default;
- diagnostic output can exit zero only when explicitly marked report-only; and
- configuration presence is never substituted for a live response or signed
  artifact.

This prevents a workflow badge or required status from being cited as runtime
readiness evidence.

The hosted job keeps the required check name `readiness` so existing branch
protection continues to enforce the contract without administrative bypass.
The separate live job is named `live-readiness`; its result is evidence only
for the provisioned runner and the exact evaluation timestamp.

Repository and artifact identity are verified independently of self-reported
metadata. Repository checks bind canonical remote URL plus default branch to a
live remote SHA. MSI checks bind current workflow head and artifact hashes,
then verify Authenticode status, the expected signer certificate fingerprint,
and timestamp presence. A manifest cannot declare itself signed into a PASS.

## Security claims belong to the component and named proposition

This umbrella repository contains clients and adapters, not the TSK or BPC
protocol verifier implementations. Client tests can establish request shape,
response mapping, and adapter behavior. They cannot establish key entropy,
replay resistance, HMAC secrecy, immutable evidence, deployment authorization,
or absence of vulnerabilities.

`SECURITY.md` therefore binds each maintained proposition to an executable file
in the current tree and links protocol claims to their owning repositories.
Historical analysis remains non-authoritative until independently rebound to
current code and tests.

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

## Scale readiness is evidence, not issue state (2026-07-17)

The base live-readiness workflow deliberately tests bounded platform and
artifact gates. Ecosystem issue #5, however, requires three costly real-agent
runs with exact provider mixes. Listing that issue in documentation did not
make it executable, and checking whether the issue was open or closed would
let repository metadata substitute for runtime evidence.

The scale gate is therefore separate. A protected Windows runner executes the
real 10/15/20 ladder and a strict collector validates the runner's existing v3
result schema. Evidence is current-head bound, content hashed, time bounded,
and reduced before upload. Hosted CI tests the validator contract but cannot
claim the live agents ran. This separation keeps ordinary pull requests fast
without allowing a green base-readiness check to imply scale proof.

The evidence bundle is a closed, reduced projection rather than a copy of raw
provider output. That preserves the exact proposition needed for review while
excluding paths, process/window identifiers, and provider logs that could
contain unrelated machine context. Per-file hashes detect changes after
collection; exact source/result schemas and cross-rung uniqueness checks stop
shape-compatible substituted results from passing.

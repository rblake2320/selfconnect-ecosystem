# Why

## Working commit messages are not final evidence

Adversarial development deliberately records failed approaches and provisional
counts. GitHub's default squash body can preserve all of them even when the
final code and PR body are corrected. The reviewed merge message is therefore
an explicit artifact, not a concatenation. It binds the final text, the exact
PR head, and a retained evidence file by digest.

This is a detection and provenance control. A repository administrator can
bypass any in-repository helper, so post-merge first-parent scanning remains
mandatory and the boundary is stated rather than hidden.

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

The scale gate is therefore separate and split across repositories. A
restricted, disposable Windows producer belongs in canonical `selfconnect`,
where the Win32 guard and provider-launch implementation can be reviewed with
the code it exercises. The ecosystem workflow does not launch providers. It
accepts only an attested v2 archive signed by the exact core producer workflow
on current `master`, then independently validates and attests the reduced
contract. Hosted CI tests the consumer but cannot claim the live agents ran.
This separation prevents ecosystem secrets or synthetic fixtures from being
mistaken for execution evidence.

The evidence bundle is a closed, reduced projection rather than raw provider
output. GitHub artifact attestation provides the external integrity and signer
boundary; in-bundle hashes alone are not treated as authenticity. The consumer
parses the verified certificate, timestamps, SLSA subject digest, source ref,
source digest, signer workflow, and producer run URI rather than trusting a
caller-supplied identity. Each agent retains a cryptorandom nonce, recomputed
expected-ACK hash, one provider-stdout observation, and a later terminal copy
that is explicitly bound as a derivative of that stdout event. A terminal that
renders captured stdout is not independent UIA evidence and is not counted as
corroboration. Static required-
policy hashes remain distinct from observed CLI version/help/entrypoint data.
The consumer recomputes the bounded process-tree projection and checks its
window-root-to-provider relationship. This remains a producer assertion covered
by the workflow's GitHub artifact attestation, not a separately observed or
signed guard receipt. Exact schemas and
cross-rung uniqueness checks prevent substituted
shape-compatible evidence and unsupported claims from passing.

Provider safety claims stay narrow. Requested flags and credential allowlists
are rejected as runtime evidence. The producer must record the actual provider
argv projection and constructed initial environment-variable names passed at
child creation; the
consumer compares those to the exact bounded contract. This remains an attested
producer observation, not a provider receipt or proof that a model made exactly
one API call. Gemini's
noninteractive Plan mode can transition toward YOLO; the contract therefore
also pins a deny-all admin policy and sandbox request, while still describing
the result only as requested restricted controls plus an observed exact ACK.
The protected runner group and isolated provider environment remain mandatory
defense-in-depth boundaries. The consumer independently binds GitHub's job and
runner-group metadata, but neither that metadata nor workflow inputs prove an
ephemeral image, disk cleanliness, or absence of sensitive repositories.

The retained consumer report records its own GitHub Actions run ID, attempt,
actor, workflow, repository, source SHA, and main-branch context. The verifier
requires those values to match the live Actions environment before the report
can say `ready`; the report is then separately provenance-attested.

The checked-in producer compatibility vector binds two independent locations
inside the generated fixture: the vector's generator-source digest and the
manifest's producer-code digest must be identical. File hashes alone would
detect edited bundle bytes but would not prove that the advertised generator
identity matched the identity consumed by the normal manifest validator.
Producer source hashing decodes strict UTF-8 and canonicalizes CRLF/CR to LF so
the cross-repository identity is stable across supported checkout newline
conventions without accepting invalid source bytes.

The fixture validator preflights the exact directory entries before parsing:
the root must be a real directory, and every manifest, rung, and vector must be
a bounded, singly linked regular file. Symlinks, Windows junctions, any Windows
reparse point, and hardlinks are rejected. This prevents an otherwise identical
external `vector.json` or directory from satisfying a closed-fixture check
through path redirection or inode aliasing. The vector still establishes
only internal compatibility-fixture consistency. It is not a signature and
does not authenticate the producer or replace the attested live artifact path.

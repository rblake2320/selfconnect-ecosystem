# Security Policy and Evidence Boundary

This file is the maintained security boundary for `selfconnect-ecosystem`.
It describes what the current repository establishes, what remains dependent
on another repository or deployment, and how to report a suspected
vulnerability privately.

The repository is an umbrella workspace. Its directly maintained executable
code is primarily:

- the Python API client, CLI, framework adapters, and MCP adapter under
  `packages/selfconnect-py`;
- the TypeScript HTTP client under `packages/tsk-client`; and
- the TypeScript MCP adapter under `packages/tsk-mcp`.

The TSK protocol verifier, BPC verifier, enterprise policy engine, operating
system transport, deployed API, and evidence store are separate components.
Their properties cannot be inferred from a green ecosystem client test.

Component policies are pinned to the exact commits recorded by this umbrella
repository. They are not statements about newer component revisions:

- [TSK protocol at `abbcb210`](https://github.com/rblake2320/tsk-protocol/blob/abbcb210fe77fc9ec00763138caa007be57ef5d3/SECURITY.md)
- [BPC protocol at `2a23fcfb`](https://github.com/rblake2320/bpc-protocol/blob/2a23fcfb5f17d95e84c4de21363fda9ca141a225/SECURITY.md)
- [Enterprise engine at `57d020ca`](https://github.com/rblake2320/selfconnect-enterprise/blob/57d020caf28a0489c08c2cfc316ab392cef1a62b/SECURITY.md)

The pinned core transport commit does not contain a `SECURITY.md`; this
composition therefore does not cite one as component evidence.

## Executable Evidence in This Repository

The current unit tests narrowly establish these propositions:

| Proposition | Evidence |
|---|---|
| The Python client places its configured bearer credential in the expected request header and maps selected HTTP responses to typed client exceptions. | `packages/selfconnect-py/tests/test_client.py` |
| The Python LangChain adapter can be configured either to continue after an event-delivery error or to propagate it. The default is fail-open telemetry. | `packages/selfconnect-py/tests/test_langchain_handler.py` |
| The Python CLI and MCP handlers expose the currently documented command/tool surface under mocked client responses. | `packages/selfconnect-py/tests/test_cli.py`, `packages/selfconnect-py/tests/test_mcp.py` |
| The TypeScript client validates required configuration shape and exposes its current error types under unit tests. | `packages/tsk-client/tests/tsk-client.test.ts` |
| The TypeScript MCP adapter exports the tested tool definitions and rejects missing local credential configuration. | `packages/tsk-mcp/tests/tsk-mcp.test.ts` |
| The readiness contract rejects mocked unavailable, stale, wrong-head, wrong-repository, wrong-branch, contradictory, or invalid-signature conditions and requires the live Authenticode verifier boundary. | `tests/test_readiness.py` |
| Local evidence paths and commit-pinned component-policy reference structure are checked, and the hosted contract resolves those external references through the GitHub contents API. | `tests/test_security_policy.py`, `tests/test_security_reference_check.py`, `scripts/security_reference_check.py` |

These tests do not prove the absence of vulnerabilities. Mocked client tests do
not establish live server enforcement. Test counts are intentionally not
copied into this policy because counts change and do not describe assurance.
Use the test report for the commit being evaluated.

## Bounded Security Properties

### Client credential handling

The clients present a configured TSK value to a server. Local constructor
checks establish only the accepted client-side format; they do not establish
entropy, issuer authenticity, hardware binding, revocation, or resistance to
credential theft. A TSK used by these clients is a bearer credential unless
the deployed server and gateway add separately verified protections.

### Server-reported decisions and evidence

The clients can surface server responses for authorization, policy, budget,
session, and retained event data. The client code does not independently prove
that the server:

- observed every relevant action;
- rejected every unauthorized action;
- generated or protected a credential correctly;
- prevented replay;
- preserved an append-only or externally anchored history; or
- produced evidence acceptable to an assessor, court, regulator, or
  authorizing official.

Those propositions require evidence from the owning server/protocol repository
and the actual deployment boundary.

### Transport and endpoint security

TLS verification is enabled by default in the TypeScript client, but transport
security depends on the runtime, certificate validation, proxy path, and
deployment configuration. Development options that disable certificate
verification must not be used as production evidence.

Endpoint compromise, operating-system security, secret custody, database
access, denial-of-service capacity, disaster recovery, and key lifecycle are
outside the assurance provided by this client repository.

### Compliance and government use

Nothing in this repository grants or proves an ATO, FedRAMP authorization, DoD
Impact Level authorization, FIPS validation, legal admissibility, ISO 42001
conformity, EU AI Act conformity, or readiness for classified operation.
Repository tests can support a broader evidence package only for the exact
proposition each test exercises.

## Readiness Evidence

`scripts/readiness.py` is fail-closed by default. A required check that is
blocked, unavailable, malformed, stale, attached to the wrong source revision,
or missing its required artifact makes the command exit nonzero.

The live MSI gate does not trust an artifact manifest's `signed` field. On the
provisioned Windows runner it invokes `Get-AuthenticodeSignature`, requires
status `Valid`, requires a timestamp signer, and compares the signer
certificate's SHA-256 fingerprint with the separately configured
`READINESS_WINDOWS_SIGNER_SHA256` policy value.

`--report-only` is a diagnostic escape hatch. Its output is explicitly marked
as not readiness evidence and must not be used for a status badge, release
decision, procurement statement, or authorization claim.

The hosted `Readiness Gate Contract` workflow verifies the gate implementation;
it is not a live-environment readiness result. An actual readiness result must
come from the separate `Live Readiness Evidence Gate` on a provisioned runner
that can perform every required check.

## Known Limitations and Historical Material

Open limitations and external dependencies are recorded in `PARKED.md` and the
linked issue tracker. A missing entry is not evidence that a risk does not
exist.

Research notes and historical analysis files, including
`SECURITY-ANALYSIS.md`, are not the maintained security boundary and must not
be cited as current implementation evidence unless their propositions are
independently rebound to current code and executable tests.

## Supported Security-Fix Scope

Security fixes are made against the current `main` branch. Historical commits,
downloaded archives, cached artifacts, forks, and separately deployed services
may require independent remediation. A repository merge does not activate a
deployment or rotate a credential.

## Reporting a Vulnerability

Do not open a public issue, discussion, pull request, or chat message containing
security-sensitive reproduction details, credentials, customer data, or an
unpatched exploit.

This repository is private, so GitHub Private Vulnerability Reporting is not
available as a public intake channel. Authorized collaborators with repository
security-advisory access should create a private draft under GitHub
**Security** / **Advisories**. Everyone else must first ask the repository
owner through an already established private channel to designate a secure
reporting path; do not include technical details in that request.

Include:

- affected repository, commit, package, and version;
- the narrow impact and required preconditions;
- a minimal reproduction using synthetic data;
- whether the issue is already public or actively exploited;
- suggested mitigation, if known; and
- a private contact method for coordinated follow-up.

Do not test against systems, accounts, devices, or data you are not authorized
to use. This repository does not promise a bounty, response deadline, or legal
safe harbor. The owner will triage reports based on reproducibility, impact,
affected boundary, and available remediation evidence, and will coordinate any
public disclosure after a fix or bounded mitigation is available.

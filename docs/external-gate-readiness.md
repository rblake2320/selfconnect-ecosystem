# External Gate Readiness

`scripts/readiness.py` evaluates external conditions that ordinary unit tests
cannot establish. It is fail-closed by default:

```powershell
python scripts\readiness.py --markdown
```

The command exits nonzero if any required check is blocked, unavailable,
malformed, stale, attached to the wrong source revision, or missing its
required artifact. JSON output has the same exit behavior:

```powershell
python scripts\readiness.py --json
```

For diagnostics only:

```powershell
python scripts\readiness.py --markdown --report-only
```

Report-only output is marked as not readiness evidence. Do not use it for a
badge, release decision, procurement claim, or authorization statement.

## Hosted Contract Versus Live Evidence

`.github/workflows/readiness.yml` is named **Readiness Gate Contract**. It
compiles the checker and runs adversarial tests. A green contract job proves
only that the gate implementation behaved as tested.

`.github/workflows/live-readiness.yml` is the separate **Live Readiness
Evidence Gate**. It is manual and requires:

- a protected self-hosted Windows runner labeled `selfconnect-readiness`;
- a protected GitHub environment named `live-readiness`, restricted to the
  default branch and holding the live token/variables;
- repository variable `READINESS_PKA_ROOT`, set to an absolute path containing
  every required repository;
- a protected `READINESS_GH_TOKEN` with the minimum private cross-repository
  access needed for current workflow, artifact, commit, and secret-name
  queries;
- repository variable `READINESS_WINDOWS_SIGNER_SHA256`, pinned to the
  expected Windows signing certificate's SHA-256 fingerprint; and
- the actual provider, TPM, signing, and repository conditions being tested.

The live workflow invokes the default fail-closed command. Missing runner,
token, repository, permission, provider response, platform capability, or
artifact evidence is a failure, not `NA`.

The base live gate does not establish the separate 10/15/20-agent scale
ladder. `.github/workflows/scale-readiness.yml` is a manual hosted **consumer**
for restricted scale evidence. It does not launch providers, hold provider
credentials, or run the ladder. The canonical `selfconnect` producer tracked
by selfconnect issue #21 must run these exact visible-agent mixes on a
dedicated disposable Windows runner:

- 10 Gemini agents;
- 15 agents split 5 Codex, 5 Claude, and 5 Gemini; and
- 20 agents split 7 Codex, 7 Claude, and 6 Gemini.

The producer requires protected provider capacity and exact, isolated
provider-process environments. Those credentials belong only in the core
producer environment; none is configured in the ecosystem consumer. Requested
environment and runner-group values are retained as configuration, not proof
that the host was disposable, dedicated, clean, or built from a particular
image. The consumer separately fetches the GitHub Actions jobs result and binds
the successful producer job, runner, runner group, labels, run, and source
commit into its report. GitHub job metadata still does not prove runner-image
contents or absence of sensitive data.

The producer pins the required policy projections and Gemini deny-all policy
separately from observed CLI versions, canonical help-output hashes, direct
package entrypoint hashes, and provider executable names used for the run. Each
invocation records `actual_argv_projection` and
`constructed_initial_environment_names`; the latter describes the environment
constructed for child creation, not an externally read post-launch process
environment. The consumer requires the exact bounded values
and rejects the former requested-policy/credential-allowlist schema.

Every agent must provide one reduced observation of the standalone ACK captured
from provider stdout. A later terminal rendering may be retained only as an
explicit derivative of that stdout event. It is not independent UIA evidence
and does not add a second source of truth. Both hashes must equal the recomputed
expected ACK, the derivative must name the stdout event, timestamps must be
ordered inside the agent interval, and exit status must be zero. This is
producer-attested reduced evidence, not a provider-signed API receipt, an
independent terminal observation, or proof of an absolute no-write property.

The bundle deliberately retains the numeric process-tree root, provider,
window, and session identifiers plus a bounded PID/parent/executable projection
needed to check the producer's process-tree/window guard assertion. The consumer
recomputes that projection digest and requires the provider process to descend
from the Windows Terminal root with the pinned provider executable and
entrypoint. It excludes raw provider output, window-title text, local paths,
and credential values. The guard assertion is integrity-bound by the GitHub-
attested archive but is not represented as an independently signed guard
receipt. Exact schemas reject extra fields and files.

The checked-in producer compatibility fixture has a narrower boundary than the
live attested artifact path. Under a trusted checkout, its supplied root and
direct entries are preflighted to reject direct symlinks, a direct junction
root, reparse-point entries, and hardlinks. The helper does not prove ancestor
path containment and does not hold no-follow handles across subsequent reads;
ancestor reparse indirection and lstat-to-open replacement are explicit
residuals. Fixture hash agreement establishes internal test consistency only,
not producer authenticity or live evidence.

Before parsing, the ecosystem workflow verifies GitHub artifact provenance
against the exact core signer workflow, `master` source ref, and producer run
commit. The consumer then parses the verified certificate, timestamps, SLSA
predicate and exact archive subject digest instead of accepting an opaque
verification blob. Verification binds the archive SHA-256, producer run ID,
attempt, actor, source commit, current core head, ecosystem contract commit, and
consumer run ID/attempt/actor into an attested consumer report. A separately
downloaded, paginated GitHub jobs result binds the successful producer job and
runner-group identity rather than accepting runner facts from the artifact.
Missing/modified files, a wrong role-provider map,
reused nonce or run ID, stale/overlapping rungs, policy drift, quota/auth
failure, or legacy v3 evidence fails closed. Closing or editing issue #5 cannot
cause this gate to pass.

The enterprise TPM module is not imported or executed until the complete
canonical repository precondition passes. A dirty, forked, wrong-branch, or
stale local checkout therefore cannot supply executable probe code.

## Required Checks

### Repository state

Every listed repository must exist locally, be clean, be on its declared
default branch, use the canonical `rblake2320` repository as its upstream, and
match that default branch head returned by a live `git ls-remote` query.
Forks, feature branches, alternate upstream branches, and cached
remote-tracking refs are not accepted as proof of synchronization.

### Gemini non-interactive access

The checker requires:

- the Gemini CLI and a successful version command;
- configured non-interactive credential material; and
- a live `gemini -p` request that returns a generated nonce exactly.

Environment-variable or ADC-file presence alone does not pass. The probe uses
Gemini CLI's documented non-interactive prompt mode. It establishes only that
the selected host completed that bounded provider request, not a full
SelfConnect multi-agent run.

### TPM platform attestation

The enterprise TPM probe must execute on the evaluated host and return the
strict boolean `supported: true`. Missing repositories, probe errors, malformed
output, unsupported hardware, and string-like truthy values fail.

### Signed MSI evidence

The latest enterprise MSI workflow on the current default-branch head must:

- be completed successfully;
- fall within the configured evidence-age limit;
- expose the named artifact;
- include parseable `msi-evidence.json`, `msi-sha256.txt`, and exactly one MSI;
- bind the evidence to the workflow, run ID, branch, and current commit;
- match the MSI byte length and SHA-256 digest;
- pass Windows `Get-AuthenticodeSignature` with status `Valid`;
- be signed by the certificate whose SHA-256 fingerprint is independently
  configured in `READINESS_WINDOWS_SIGNER_SHA256`; and
- include a timestamp signer.

A historical successful run, a success on an older commit, secret-name
presence, an expired artifact, manifest-only `signed: true`, a signer mismatch,
a missing timestamp, or an invalid Authenticode signature does not pass.

### Signing secret configuration

The required secret names must be present in the enterprise repository.
This is configuration evidence only. It is never substituted for the signed
MSI artifact check.

## Evidence Freshness

The default and hard maximum age is 168 hours:

```powershell
python scripts\readiness.py --markdown --max-evidence-age-hours 168
```

The caller may tighten this age but cannot expand it beyond 168 hours. The
report records its evaluation timestamp and evidence-age policy. Future,
missing, malformed, or expired timestamps fail.

## Current Expected Result

Until the tracked external gates are closed, a real live readiness evaluation
is expected to fail. That is the correct result. In particular, the historical
enterprise MSI run from June 21, 2026 is not current-head evidence and its
recorded artifact is unsigned.

Open trackers:

| Gate | Issue |
|---|---|
| Gemini non-interactive auth | https://github.com/rblake2320/selfconnect-ecosystem/issues/2 |
| Gemini 10/15/20 scale quota | https://github.com/rblake2320/selfconnect-ecosystem/issues/5 |
| TPM platform attestation PASS artifact | https://github.com/rblake2320/selfconnect-ecosystem/issues/3 |
| Windows MSI signing and signed artifact | https://github.com/rblake2320/selfconnect-ecosystem/issues/4 |

Until the restricted core producer completes and the hosted consumer accepts
all three rungs, issue #5 remains open and no 10/15/20 scale-readiness claim is
established. A green hosted `readiness` job proves only the validator contract
and adversarial tests; it is not live scale evidence.

## Primary References

- Gemini CLI non-interactive options:
  https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/cli-reference.md
- Gemini CLI authentication:
  https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/authentication.mdx
- GitHub Actions workflow-run evidence fields:
  https://docs.github.com/en/rest/actions/workflow-runs
- GitHub artifact attestations:
  https://docs.github.com/en/actions/concepts/security/artifact-attestations
- GitHub workflow badges:
  https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge

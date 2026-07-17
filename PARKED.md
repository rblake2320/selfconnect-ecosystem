# Parked

Deliberately out of scope for the release claim scan, recorded so absence is
not mistaken for oversight:

- **Live readiness runner and token activation**: the fail-closed manual
  workflow is defined, but this change does not register a self-hosted runner
  or create `READINESS_GH_TOKEN`, `READINESS_PKA_ROOT`, or
  `READINESS_WINDOWS_SIGNER_SHA256`. Closure requires least-privilege
  cross-repository access, protected runner custody, a canonical repository
  root, an independently obtained signer fingerprint, one full run, and
  retained non-secret output. Until then, no green live-readiness result
  exists.
- **Restricted real-agent 10/15/20 producer activation**: this repository now
  contains only the fail-closed v2 evidence consumer. The canonical core
  producer, disposable runner group, protected environment, provider capacity,
  and successful attested run are prerequisites outside this change. Issue #5
  remains open until the core workflow executes all three exact provider rungs,
  emits producer guard assertions and dual ACK observations under pinned
  CLI/tool/entrypoint policies, the ecosystem
  consumer accepts the current-head attestation, and retained non-secret
  evidence survives independent review. Legacy v3 output, unit fixtures,
  workflow existence, and issue state cannot close it. The paid ladder remains
  manually dispatched; hosted pull-request CI cannot access a protected Windows
  UI session or establish visible-agent execution.
- **Current signed MSI evidence**: the available June 21, 2026 workflow run is
  stale relative to current enterprise `master`, and its evidence records
  `signed: false`. Secret-name presence cannot close this. Issue #4 remains the
  owner-visible closure path.
- **Historical `SECURITY-ANALYSIS.md` revalidation**: the maintained
  `SECURITY.md` now marks that research note non-authoritative. Retiring or
  rewriting it requires a separate cross-repository protocol-evidence review;
  it is not silently treated as current proof.
- **Dedicated external vulnerability intake**: GitHub Private Vulnerability
  Reporting is not available for this private repository. The policy defines
  Security Advisories for authorized collaborators and an
  established-private-channel bootstrap for others. A monitored security alias
  remains an owner decision and is not claimed active.
- **GitHub hidden pull-request ref purge**: the public provenance `master`
  history and ecosystem gitlink have been rewritten, but GitHub keeps
  `refs/pull/2/head` read-only. GitHub Support must purge the hidden ref and
  cached object after confirming the branch rewrite. This is not treated as
  closed merely because normal clones no longer reach the old object.
- **Existing PyPI 1.1.0 replacement/yank**: source and artifact gates now cover
  future Python package claims, but repository code cannot publish or yank a
  public package. The GitHub `pypi` environment and `selfconnect-py-v*` tag
  policy are configured. Owner action remains: register the matching PyPI
  Trusted Publisher, set the intentionally absent activation variable, publish
  verified 1.1.1, then yank 1.1.0 with a bounded reason. The current GitHub
  plan does not support required-reviewer or wait-timer environment rules. Do
  not delete the historical release.
- **README/tag-message scanning**: READMEs are already governed by the
  Enterprise control catalog; duplicating here would create two sources of
  truth. Tag messages are low-visibility; revisit if audits find rot there.
- **Automatic remediation** (auto-editing releases): the gate detects and
  blocks; editing public artifacts stays a human/owner-approved action.
- **Deployment/authorization evidence** (ATO, WORM custody, assessor
  opinions): external by nature; no repository tool can create it. Tracked in
  the Enterprise control catalog as explicitly incomplete.
- **Live API integration lane**: unit and artifact validation are automatic.
  Live API tests require a disposable restricted identity and endpoint supplied
  through a protected environment. No permanent test credential is stored in
  the repository.

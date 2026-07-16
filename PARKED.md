# Parked

Deliberately out of scope for the release claim scan, recorded so absence is
not mistaken for oversight:

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

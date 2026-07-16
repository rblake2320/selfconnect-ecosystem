# Parked

Deliberately out of scope for the release claim scan, recorded so absence is
not mistaken for oversight:

- **Package registry claims** (npm/PyPI descriptions, classifiers such as
  `Development Status :: 5 - Production/Stable`): same failure mode, different
  surface. Needs registry API adapters; park until the release gate has run
  in CI for one cycle.
- **README/tag-message scanning**: READMEs are already governed by the
  Enterprise control catalog; duplicating here would create two sources of
  truth. Tag messages are low-visibility; revisit if audits find rot there.
- **Automatic remediation** (auto-editing releases): the gate detects and
  blocks; editing public artifacts stays a human/owner-approved action.
- **Deployment/authorization evidence** (ATO, WORM custody, assessor
  opinions): external by nature; no repository tool can create it. Tracked in
  the Enterprise control catalog as explicitly incomplete.

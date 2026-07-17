# Reviewed squash merge procedure

GitHub's default squash message can concatenate intermediate commit messages.
Those messages are working notes and may contain superseded counts or rejected
designs. They are not evidence.

Use the gate helper for an intentionally reviewed squash merge:

```powershell
python scripts/merge_message_gate.py merge-pr `
  --repo rblake2320/REPOSITORY `
  --pr 123 `
  --subject "fix: reviewed final subject" `
  --body-file .review/final-pr-body.md `
  --evidence-file .review/final-evidence.json `
  --delete-branch
```

The body and evidence inputs must be retained in the PR or a durable workflow
artifact. Evidence is strict JSON using schema
`selfconnect.reviewed_merge_evidence.v1`; it binds the exact head to a named,
successful GitHub Actions pull-request run URL. The merge helper fetches that
run and checks repository, head, workflow, event, status, and conclusion before
merging. Empty or descriptive-only evidence is rejected.

The helper refuses draft/closed PRs, scans every PR commit page, binds the
reviewed body and evidence digests to the exact PR head, supplies explicit
`gh pr merge --subject/--body-file` values, and uses `--match-head-commit`
without `--admin` or automatic merge. Final merge text cannot carry test-count,
green-suite, approval, zero-failure, or unsupported capability assertions;
those belong in the retained evidence artifact, not permanent commit prose.

On a pull request, `merge-message-gate` scans `base..head`. On a push to main,
it checks every first-parent commit after the pinned adoption baseline for the
reviewed trailers. The latter is detection: an administrator can bypass the
helper, but the unmanaged result turns the gate red and cannot be cited as
governed evidence.

The adoption baseline is an immutable literal in the workflow, not a file read
from the commit being evaluated. This prevents a bypassing commit from moving
the baseline to itself and producing an empty scan. A later baseline change
requires a separately reviewed workflow change and dated incident/boundary
record; it must never be used to hide an unmanaged commit.

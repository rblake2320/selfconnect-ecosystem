# Merge-message baseline adoption - 2026-07-19

## Incident

SelfConnect ecosystem pull request `#23` was squash-merged at
`a64a10ee6e30482f889c2c68d29792b10c25f0b9` with an explicit subject and body,
but the repository's `scripts/merge_message_gate.py merge-pr` helper was not
used. The resulting commit therefore lacks the reviewed content, evidence, and
head trailers required by the main-branch detective control. Exact-main run
`29695857039` correctly failed with `reviewed content trailer is absent`.

The failure was operator process error. It was not a product-test failure and
must not be hidden or relabelled as governed merge evidence.

## Bounded Adoption

Pull request `#23` changed one documentation file. Its exact head and all
hosted pull-request checks were reviewed before merge, and an independent peer
review found no blocker. The resulting main commit contains the same reviewed
file content. This follow-up pull request openly advances the workflow's
literal adoption baseline to that commit so later first-parent commits remain
subject to the trailer gate.

This adoption does not add missing trailers to `a64a10e`, make that commit a
helper-governed merge, or turn its failed merge-message run into evidence. The
core baseline manifest continues to rely on the three exact repository commits
and their linked exact-master runs.

## Prevention

All later ecosystem squash merges must use the documented
`merge_message_gate.py merge-pr` flow with strict structured evidence bound to
the exact pull-request head. Do not use a direct `gh pr merge` command for this
repository.

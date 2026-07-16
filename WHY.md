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

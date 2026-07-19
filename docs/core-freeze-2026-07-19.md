# SelfConnect Core Baseline - 2026-07-19

This document freezes the reviewed SelfConnect core runtime baseline. It is an
engineering acceptance record, not a package release, certification, ATO, or
claim that every optional deployment tier is complete.

## Pinned Baseline

| Repository | Commit | Tag | Exact-master evidence |
|---|---|---|---|
| `rblake2320/selfconnect` | `569f456a81b22905c0f96827471cb2cdcb65bf01` | `core-freeze-2026-07-19` | [CI 29665329542](https://github.com/rblake2320/selfconnect/actions/runs/29665329542) |
| `rblake2320/bpc-protocol` | `aedf67b89574066e1df0575e68fdb58ea0dc9297` | `core-freeze-2026-07-19` | [CI 29695233967](https://github.com/rblake2320/bpc-protocol/actions/runs/29695233967) |
| `rblake2320/tsk-protocol` | `00e7457f4ca19435794b3e876a37bd7f90b99317` | `core-freeze-2026-07-19` | [CI 29695231735](https://github.com/rblake2320/tsk-protocol/actions/runs/29695231735) |

All three evidence runs completed successfully on the exact commits above.
BPC issue `#16` and TSK issue `#10` closed through reviewed squash merges.
SelfConnect had no open pull requests when this baseline was recorded.

The annotated tags are unsigned discovery labels. The full commit identifiers
in this reviewed manifest are the authoritative baseline identities; the tags
do not provide signer authenticity.

## Accepted Boundary

The baseline is the SelfConnect core runtime candidate with its reviewed BPC
and TSK security and HA mechanisms. Future fixes and features build after this
point. They do not retroactively change the evidence or claims attached to this
baseline.

## Explicitly Outside This Baseline

- The protected 10/15/20 real-agent evidence run, artifact attestation,
  ecosystem consumer acceptance, and independent evidence review tracked by
  `selfconnect#21`.
- Signed Windows release artifacts and managed-policy deployment evidence
  tracked by `selfconnect#3` and the ecosystem signing gate.
- Independent-state and multi-site Ultra HA tracked by
  `selfconnect-enterprise#28`.
- TPM PASS evidence, provider credentials or quota, HSM/TPM production key
  custody, government authorization, certification, and patent filing.
- Separate SelfConnect-branded projects unless the owner explicitly adds them
  to this release boundary.
- Any Brain or Mission Control capability. Those projects remain separate and
  are not dependencies of SelfConnect correctness.

## Change Rule

Do not move or recreate the baseline tag. Correct this record with a new dated
baseline and new evidence. Do not broaden public claims from this document;
use the maintained readiness and claim gates for any release statement.

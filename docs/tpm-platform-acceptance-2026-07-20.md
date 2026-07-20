# TPM Platform-Attestation Consumer Acceptance

## Result

The hardened ecosystem consumer returned `ok: true` and `status: ready` on
2026-07-20 at 20:32:39 UTC against the exact merged Enterprise commit
`9e69c6eaff0b7ca522a808075daea6bf41b592ad` and the pinned SelfConnect commit
`787a6b88d9ff4a79917ebba94bffc7fe38d700d2`.

The consumer independently pinned TPM public-key digest
`e5954da7514dcc6574cd9d429d7cf36fa3fa0ca8a57da348fb6e99d48402ba96`
and required strict verified, platform-key-bound, and replay-checked results.
The signed claim was 1,187 bytes; its SHA-256 was
`a9f81fc40a129684c2990c800f55883e253dde102743a07743bc772772319754`.
PCR algorithm 11 and mask `0x00FFFFFF` were verified, with PCR-value digest
`cfa6d2a34942a42a3e96ce4ed26037f138d6695ad8d127824a13ccba6d22540d`.

The complete redacted machine-readable result is retained in
`docs/tpm-platform-acceptance-2026-07-20.json`. The evaluated consumer script
SHA-256 was
`f9ae2e163641b9497105da39e45860675e79cc795a81e603d3093584cf07895e`.
Enterprise exact-master CI run `29776283750` passed on the evaluated commit.

## Verification

- Readiness contract: 43 tests passed.
- Scale-readiness contract: 47 tests passed.
- Security policy contract: 9 tests passed.
- Live consumer execution: `ok: true`, `status: ready`.
- Producer exact-master CI: all four jobs passed, including the Windows live
  contract and PostgreSQL/Redis durability jobs.

## Boundary

This accepts the bounded local platform-attestation mechanism. It does not
claim manufacturer/EK certificate-chain trust, remote enrollment or revocation,
binding of the separate agent-signing identity, independent assessment, or an
authorization to operate.

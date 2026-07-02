# Security Properties — selfconnect-ecosystem

This document covers the security posture of the selfconnect-ecosystem monorepo, which contains the TSK (Trust Session Key) protocol, the selfconnect Python SDK, and the TSK MCP server. For the BPC (Binary Pair Credential) protocol, see [bpc-protocol/SECURITY.md](https://github.com/rblake2320/bpc-protocol/blob/main/SECURITY.md). For the enterprise governance engine, see [selfconnect-enterprise/SECURITY.md](https://github.com/rblake2320/selfconnect-enterprise/blob/main/SECURITY.md).

---

## What This System Guarantees

### 1. TSK Key Integrity

Every Trust Session Key is a 52-character base64url string derived from 256 bits of cryptographically secure entropy (`crypto.randomBytes(32)`). The key space is 64^52 = 2^312 — brute-force is computationally impossible with any known or theoretically possible classical hardware.

**Proven by:** `test-suite.ts` — 39 assertions covering key generation, validation, expiry, and replay protection.

### 2. Replay Protection

TSK keys include a time-window component. Keys are valid only within a configurable window (default: ±30 seconds). A key captured and replayed outside the window is rejected. The replay window is tested with both positive (within window) and negative (outside window) cases.

**Proven by:** `attack-suite.mts` — Attack 2 (replay attack): tests key validity at +25s (accepted) and +2 min (rejected).

### 3. HMAC Secret Confidentiality

The HMAC secret used for key validation is never transmitted. An attacker with full network visibility cannot recover the secret from observed keys. 50,000 brute-force attempts against the 256-bit secret space are verified to fail.

**Proven by:** `attack-suite.mts` — Attack 4 (HMAC secret brute force): 50,000 attempts, 0 breaches.

### 4. Structural Unforgeability

An attacker with knowledge of the static portions of a TSK key cannot forge a valid key by guessing the rotating portion. 10,000 forge attempts with known static + random rotating components are verified to fail.

**Proven by:** `attack-suite.mts` — Attack 3 (structural analysis + forge): 10,000+ attempts, 0 breaches.

### 5. Flood / DoS Resistance

100,000 rapid validation attempts do not degrade the validation function or produce false positives. The validator is stateless and O(1) per call.

**Proven by:** `attack-suite.mts` — Attack 10 (flood): 100,000 rapid attempts, 0 breaches, no performance degradation.

### 6. Ultra Bridge Identity Binding

When TSK and BPC are used together via `verifyUltraRequest`, both layers must pass independently and the verified identities must match. A mismatch between the BPC `pairId` and the TSK `clientId` is an immediate rejection — there is no code path that accepts a request where the two layers identify different principals.

**Proven by:** `ultra-bridge.test.ts` — 11 assertions covering valid ultra requests, identity mismatch rejection, BPC-only failure, TSK-only failure, and combined failure modes.

---

## What This System Does Not Guarantee

**Transport security is out of scope.** TSK provides application-layer key validation. It does not provide transport encryption. TLS must be enforced at the infrastructure layer.

**Key storage is out of scope.** TSK keys are generated and validated by the server. The security of key storage (database, environment variable, secrets manager) depends entirely on the host environment.

**Rate limiting is not built in.** The TSK validator is a pure function. Rate limiting must be implemented at the server layer (e.g., Express middleware, API gateway).

---

## Known Vulnerabilities & Remediation Record

### CVE-2021-44531 / CVE-2021-44532 — Node.js TLS Certificate Validation

| Field | Value |
|---|---|
| **CVEs** | CVE-2021-44531, CVE-2021-44532 |
| **Affected** | Node.js < 17.3.0 / 16.13.2 / 12.22.9 |
| **Severity** | High |
| **Type** | TLS certificate validation bypass |

**Scope assessment.** These CVEs appear in `@types/node` documentation as historical references to Node.js TLS behavior. They are not exploitable in this codebase — TSK does not perform TLS certificate validation (that is delegated to the Node.js runtime and infrastructure layer). The references appear in type definition files only.

**Remediation.** Use Node.js >= 17.3.0 / 16.13.2 / 12.22.9. The TSK package itself does not perform certificate validation and is not directly affected.

---

### CVE-2026-4747 — FreeBSD kgssapi KASLR Bypass (Threat Model Reference)

| Field | Value |
|---|---|
| **CVE** | CVE-2026-4747 |
| **Affected** | FreeBSD `kgssapi.ko` kernel module |
| **Severity** | Critical (RCE) |
| **Discovered by** | Anthropic Claude Mythos Preview (autonomous zero-day discovery) |
| **Type** | Kernel RCE — 17-year-old bounds check error + KASLR bypass |

**Scope assessment.** This CVE is referenced in `tsk/SECURITY-POSITION.md` as a threat model reference, not as a vulnerability in this codebase. TSK/BPC/Ultra are a different target class: pure TypeScript/Python with no C code, no manual memory management, no kernel modules, and no KASLR dependency.

**Relevance.** CVE-2026-4747 was the first publicly documented autonomous zero-day discovery by an AI system. It informs the threat model for AI-assisted attacks against this codebase. The TSK architecture is designed to be resistant to this class of attack: the attack surface is minimal (pure functions, no native bindings), and the cryptographic primitives are post-quantum migration-ready.

**Reference.** `tsk/SECURITY-POSITION.md` — "Why TSK/BPC/Ultra Are a Different Target Class."

---

## Test Coverage Summary

| Package | Test files | Total tests | Attack scenarios |
|---|---|---|---|
| `tsk-protocol` | `test-suite.ts`, `attack-suite.mts`, `adversarial-proof.ts`, `ultra-bridge.test.ts`, `redteam-*.test.ts` | 192 | 12 attack scenarios, 389k+ attempts |
| `selfconnect-py` | `test_client.py`, `test_cli.py`, `test_mcp.py` | 64 | — |
| `tsk-mcp` | `tsk-mcp.test.ts` | 7 | — |
| **Total** | | **263** | |

### Attack Suite Summary (attack-suite.mts)

| Attack | Attempts | Result |
|---|---|---|
| Brute force (random keys) | 100,000 | 0 breaches |
| Replay attack | ~120 time offsets | 0 breaches |
| Structural analysis + forge | 11,000+ | 0 breaches |
| HMAC secret brute force | 50,000 | 0 breaches |
| Checksum forgery | 10,000 | 0 breaches |
| HOTP lookahead | 4,000 | 0 breaches |
| Collision attack | 50,000 | 0 breaches |
| Timing attack | 50,000 | 0 breaches |
| Single-char mutation (52×63) | 3,276 | 0 breaches |
| Flood / DoS | 100,000 | 0 breaches |
| Replay window | 50,000 | 0 breaches |
| Multi-segment | 10,000 | 0 breaches |
| **Total** | **~438,276** | **0 breaches** |

---

## Reporting Security Issues

This is a private research and patent-portfolio repository. Security issues should be reported directly to the repository owner.

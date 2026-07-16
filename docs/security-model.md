# SelfConnect — Security Model

---

## Threat Model

SelfConnect gives agents the ability to inject arbitrary text into terminal windows. This is powerful and must be constrained. The threat model covers:

| Threat | Description |
|--------|-------------|
| **Unauthorized injection** | An agent injects into a terminal it shouldn't access |
| **Shell command injection** | An agent uses the chat channel to inject shell commands |
| **TOCTOU on HWND** | An attacker substitutes a different window after the HWND is resolved |
| **Replay attack** | A captured message is resent to inject again |
| **Ledger tampering** | Audit trail is altered to hide injection events |
| **Runaway agent** | An agent loops and floods a terminal with messages |

---

## Defense Layers

### Layer 1 — Logical Target Registry

Raw HWNDs are rejected at the `agent-wire` boundary. Agents must use logical names (`axiom-windows-claude`, `cc-spark1-claude`) which are resolved to HWNDs at dispatch time in `windows_agent.py`.

This prevents TOCTOU: the registry is the authoritative mapping, re-enumerated each session.

### Layer 2 — Action Classification (agent-wire)

Every message carries an `action` field. The policy table maps actions to verdicts:

```
terminal.inject.chat             → allow
terminal.inject.shell            → deny (require_operator_approval)
terminal.inject.approval_response → deny (always)
*                                → deny (default deny)
```

Shell injection requires out-of-band operator approval before `agent-wire` will allow it.

### Layer 3 — Hash-Chained Audit Ledger

Every dispatched message is written to `mesh_wire_ledger.jsonl` with:
- `timestamp`
- `agent_id`
- `target_id`
- `action`
- `verdict`
- `prev_hash` — SHA-256 of the previous entry

Any modification of a past entry breaks the chain. Validators check the full chain on startup.

### Layer 4 — WIRE_ENABLED Kill Switch

The env var `WIRE_ENABLED=0` causes `mesh_wire.py` to deny all dispatches immediately — no code change required. For emergency lockdown.

### Layer 5 — Accord Signatures (selfconnect-accord)

`selfconnect-accord` adds detached cryptographic signatures to ledger exports.
Those signatures can support integrity and attribution review, but suitability
for an audit or legal proceeding depends on the complete collection, custody,
retention, assessment, and deployment process.

---

## Rate Limiting

`windows_agent.py` enforces a per-agent rate limit (default: 60 messages/minute). Exceeding it triggers a `rate_limit_exceeded` denial in the ledger and a warning to the operator.

---

## Authentication (enterprise / federal)

The enterprise and federal tiers add agent identity:
- **enterprise**: operator-issued agent tokens, revocable
- **federal**: registered BPC pair-key identity with configured replay controls;
  device or hardware binding depends on the deployed key store and attestation path

An agent must present a valid identity before `agent-wire` will dispatch its messages.

---

## What Is Intentionally Out of Scope

| Out of scope | Reason |
|-------------|--------|
| Encrypting the injected text | Text appears in a terminal — the terminal operator can see it |
| Hiding the fact injection happened | The ledger is append-only; hiding injection is a policy violation |
| Cross-user injection | OS-level access controls prevent injection across Windows user sessions |

---

## Recommended Deployment Posture

1. Run `windows_agent.py` as a non-admin user — it only needs `PostMessage` access to windows in its own session
2. Bind SSH to loopback (`127.0.0.1:9877`) and tunnel through known SSH keys only
3. Set `WIRE_ENABLED=1` only when the mesh is actively needed; default to `0`
4. Review `mesh_wire_ledger.jsonl` daily in production environments
5. Use `selfconnect-accord` to sign daily ledger snapshots

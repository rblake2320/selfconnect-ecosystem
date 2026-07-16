# Watch Ledger Entry: IBCT/AIP Alignment for SelfConnect

## Innovation Record

| Field | Value |
|-------|-------|
| **ID** | INNO:selfconnect/ibct-aip-alignment |
| **Found** | 2026-07-02 |
| **Description** | SelfConnect's BPC (Bonded Pair Channel) and TSK (Task Signing Key) mechanisms map directly to NIST SP 800-204C IBCT (Identity-Based Communication Tokens) and AIP (Agent Identity Proofs). BPC = mutual attestation between two agents (IBCT bilateral binding). TSK = delegated authority with budget ceiling (AIP scoped capability). The provenance ledger's precommit/postcommit hash pair implements the IBCT "evidence of intent" requirement. |
| **Disposition** | ADOPT — document alignment, no code change needed |
| **Why** | SelfConnect already implements the functional equivalent of IBCT/AIP through BPC+TSK. Documenting this alignment strengthens patent claims (prior art defense), simplifies FedRAMP/IL4+ compliance narratives, and provides a standards-based vocabulary for enterprise sales conversations. No new code is required — this is a documentation and positioning exercise. |
| **Platforms** | all |
| **Revisit when** | NIST SP 800-204C finalizes (currently draft); if the final standard diverges from the current draft, re-evaluate whether BPC/TSK need structural changes or just terminology updates. |
| **Owner** | AXIOM |
| **Source** | Cross-project analysis (GUMBO/PKA/ultra-computer session, 2026-07-02) |

## Alignment Mapping

| NIST Concept | SelfConnect Equivalent | Implementation Location |
|---|---|---|
| IBCT (Identity-Based Communication Token) | BPC (Bonded Pair Channel) | `selfconnect/self_connect.py` Layer 3 |
| AIP (Agent Identity Proof) | TSK (Task Signing Key) | `selfconnect-store/api.py` TSK table |
| Bilateral binding | BPC handshake via PostMessage ACK | `selfconnect/self_connect.py` send_frame/verify_delivery |
| Scoped capability | TSK budget_tokens + is_active | `selfconnect-store/api.py` _validate_tsk() |
| Evidence of intent | Provenance precommit_hash → postcommit_hash | `provenance/schemas/ledger_entry.schema.json` |
| Revocation | TSK revoke (is_active=0, revoked_at) | `selfconnect-store/api.py` POST /tsk/revoke |
| Audit trail | Hash-chained JSONL ledger + EventStore | `agent-wire/wire-dispatch.jsonl` + `selfconnect-store/store.db` |

## Compliance Narrative (for enterprise/government sales)

> SelfConnect implements the functional equivalent of NIST SP 800-204C's
> Identity-Based Communication Tokens (IBCTs) through its Bonded Pair Channel
> (BPC) mechanism, and Agent Identity Proofs (AIPs) through its Task Signing
> Key (TSK) system. Every agent-to-agent communication is mutually attested
> via BPC handshake, budget-bounded via TSK enforcement, and recorded in a
> hash-chained provenance ledger with precommit/postcommit evidence pairs.
> This architecture satisfies the intent-attestation, scoped-delegation, and
> non-repudiation requirements of IBCT/AIP without requiring external PKI
> infrastructure — all cryptographic material is generated and stored locally
> via Windows DPAPI, enabling air-gapped IL4-IL7 deployment.

## Action Items

1. **Add this mapping to the main SelfConnect README** under a "Standards Alignment" section (5 min)
2. **Reference in patent filing** as evidence of standards compliance (strengthens non-obviousness argument)
3. **Update the compliance bundle** (`GET /compliance/bundle`) to include IBCT/AIP mapping in the output JSON
4. **Revisit** when NIST SP 800-204C moves from draft to final publication

## CLI command to record in PKA watch ledger

```bash
python scripts/pka_watch_ledger.py decide "INNO:selfconnect/ibct-aip-alignment" \
  --status ADOPTED \
  --decision "ADOPT" \
  --description "BPC+TSK maps to NIST SP 800-204C IBCT/AIP — document alignment, no code change" \
  --reason "Strengthens patent claims, simplifies FedRAMP narrative, standards vocabulary for enterprise" \
  --platforms "all" \
  --revisit-when "NIST SP 800-204C finalizes" \
  --owner AXIOM
```

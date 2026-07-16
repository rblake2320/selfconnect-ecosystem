# Watch Ledger Correction: IBCT/AIP Attribution

## Correction Record

| Field | Value |
|-------|-------|
| **ID** | INNO:selfconnect/ibct-aip-alignment |
| **Original record** | 2026-07-02 |
| **Reviewed** | 2026-07-16 |
| **Disposition** | INVALIDATED |
| **Original claim** | NIST SP 800-204C defines Identity-Based Communication Tokens (IBCTs) and Agent Identity Proofs (AIPs), and SelfConnect BPC/TSK maps directly to them. |
| **Finding** | The cited NIST publication does not define IBCTs, AIPs, bilateral agent binding, or an "evidence of intent" requirement. |
| **Authoritative source** | [NIST SP 800-204C, Implementation of DevSecOps for a Microservices-based Application with Service Mesh](https://doi.org/10.6028/NIST.SP.800-204C), final March 2022 |
| **Owner** | AXIOM |

## Why The Prior Mapping Is Invalid

NIST SP 800-204C addresses DevSecOps practices for cloud-native,
microservices-based applications and service-mesh environments. Its subject
matter includes application code, application-services code, infrastructure as
code, policy as code, observability as code, CI/CD, and continuous
authorization considerations.

The publication is not an AI-agent identity protocol specification. The
original record attributed terminology and requirements to the document that
are not present in the cited source. The related statements about mutual
attestation, scoped delegation, non-repudiation, external PKI, FedRAMP, and DoD
deployment therefore cannot be supported by NIST SP 800-204C.

## What Remains Available For Separate Evaluation

SelfConnect repositories contain independently testable mechanisms involving:

- registered pair-key authentication in BPC;
- rotating credential segments in TSK;
- configured request-freshness and replay controls;
- server-side budget fields and revocation state;
- retained hash-chain and provenance data.

Those mechanisms must be described from their implementation, named tests, and
deployment configuration. They are not NIST SP 800-204C conformance evidence,
and this correction does not assign them to any replacement standard.

## Required Handling

1. Do not cite this record as standards alignment, compliance evidence, prior
   art, or patent evidence.
2. Remove or correct any downstream statement that repeats the invalid
   SP 800-204C/IBCT/AIP attribution.
3. If an authoritative publication defining IBCT or AIP terminology is later
   identified, create a new dated comparison that quotes the actual
   definitions, names the implementation evidence, and records the mapping as
   preliminary pending qualified review.
4. Preserve this correction so the reason for removing the earlier mapping is
   auditable rather than silently rewriting history.

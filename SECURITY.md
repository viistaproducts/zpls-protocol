# Security Policy

ZPL-S currently provides integrity, not confidentiality.

## What Is Implemented

- HMAC-SHA256 frame sealing.
- Deterministic canonical material before signing.
- Constant-time MAC comparison via Python `hmac.compare_digest`.
- Fabric envelope checks for destination, TTL and frame hash.
- In-process Fabric replay cache keyed by source, trace id and frame hash.
- Closed failure for malformed frames and invalid seals.

For the full pre-1.0 threat model, see [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## What Is Not Yet Audited

This project has not received an external security audit. Do not describe it as
audited until an independent review has happened.

Not yet implemented:

- Public-key signatures.
- Key rotation.
- Revocation.
- Distributed replay cache for multi-node clusters.
- Rate limiting.
- Authentication for HTTP endpoints beyond frame seals.
- Confidential encryption.

## Allowed Security Claim

Allowed:

> ZPL-S provides deterministic canonicalization, semantic hashing, HMAC-based
> frame integrity, TTL validation and replay detection in the reference Fabric
> gateway.

Not allowed yet:

> ZPL-S is audited or secure for arbitrary public internet agent communication.

## Responsible Disclosure

For private deployments, treat mesh keys like production secrets. Rotate them if
they are logged, shared or committed.

For public release, publish security issues privately first and include:

- affected version,
- minimal reproduction,
- expected impact,
- proposed mitigation if known.

# ZPL-S Threat Model

Status: normative security guidance for pre-1.0 implementations.

ZPL-S provides deterministic frame semantics and integrity checks for sealed
frames. It does not provide confidentiality, endpoint authentication,
authorization, rate limiting or a complete public-internet trust model by
itself.

## Security Goals

ZPL-S aims to protect:

- frame integrity for sealed frames,
- canonical replayability,
- replay detection inside a single gateway process during the TTL window,
- auditability through source, destination, trace ID, route and frame hash,
- closed failure for malformed frames, invalid hashes, expired TTLs, wrong
  destinations and invalid seals.

## Non-Goals Today

ZPL-S does not yet provide:

- encryption,
- public-key identity,
- authorization policy,
- protection against compromised shared HMAC keys,
- distributed replay protection across a cluster,
- denial-of-service protection,
- sandboxing for actions triggered by received frames,
- external security audit.

## Trust Boundaries

### Local Mesh

Agents inside a local mesh may share state refs, keys and routing semantics.
Keep mesh secrets out of logs, avoid direct high-risk side effects and re-seal
frames after deterministic observation if secure delivery is required.

### Fabric Gateway

The Fabric gateway accepts frames from other nodes. It must validate content
type, destination, TTL, frame hash, seal when required, replay cache, body size
and accepted/rejected receipts.

### Public Internet

The public internet is untrusted. Production deployments need HTTPS, endpoint
authentication, authorization, rate limiting, key rotation, revocation and a
distributed replay cache.

## Common Attacks

- **Tampered frame:** semantic hash or seal must fail.
- **Replay attack:** cache `source + trace_id + frame_hash` until expiration.
- **Stale command:** reject expired TTL and use short TTLs for side effects.
- **Confused deputy:** enforce authorization outside the parser by source,
  role, operation, risk and target.
- **Sensitive delta leak:** send state refs or redacted views, not secrets.
- **Compromised key:** rotate key ID and reject old keys.
- **Denial of service:** add rate limits, parse timeouts and body limits.

## Allowed Security Claim

Allowed:

> ZPL-S provides deterministic canonicalization, semantic hashing, HMAC-based
> frame integrity, TTL validation and replay detection in the reference Fabric
> gateway.

Not allowed yet:

> ZPL-S is audited or secure for arbitrary public internet agent communication.

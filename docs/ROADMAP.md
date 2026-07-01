# ZPL-S Roadmap

This roadmap separates implemented behavior from future production hardening.

## v0.3.x — Usable Protocol Kernel

Implemented:

- S1 text frames.
- Canonical serialization and semantic hashing.
- Binary MVP encoding.
- Q-state and Q-field tensor logic.
- Deterministic observation.
- HMAC frame sealing.
- In-process Fabric replay protection.
- Minimal mesh kernel.
- Minimal HTTP Fabric.
- S1.1 Delta Algebra as an experimental apply/canonicalization layer.
- Killer demo and machine-readable delta conformance.

Known limitations:

- Security is not audited.
- HMAC is shared-secret integrity, not public identity.
- S1.1 Delta Algebra is experimental.
- CI workflow publishing still requires a GitHub token with `workflow` scope.
- TypeScript interop needs a parser that matches the Python top-level grammar.
- No production authorization or rate-limit layer.

## v0.4.0 — Interop Proof

- TypeScript implementation with robust delta and frame parsing.
- Shared JSON conformance vectors for Python and TypeScript.
- Cross-implementation conformance table.
- CI for Python and TypeScript once workflow scope is available.

## v0.5.0 — Security Hardening

- Ed25519/JWS signatures.
- Key discovery, rotation hooks and revocation.
- Distributed replay cache interface.
- HTTP auth and rate-limit middleware.
- Stable error codes.

## v1.0.0 — Stable Protocol

- Frozen S1 core.
- Frozen S1.1 delta algebra.
- Stable conformance suite.
- At least two independent implementations.
- External security review.
- SemVer policy.

# ZPL-S FAQ

## Is ZPL-S AGI?

No. ZPL-S is protocol infrastructure. It does not create intelligence by
itself. It gives agents and machines a deterministic way to exchange state.

## Is This Real Quantum Computing?

No. The Q-Matrix is quantum-inspired protocol logic. It uses state vectors,
phase, interference and observation as useful abstractions for unresolved
machine state. It does not claim physical quantum computation.

## Why Not Just JSON?

ZPL-S can be transported inside JSON envelopes, but the core frame is compact,
canonical and designed for machine-state deltas. JSON alone does not define:

- canonical semantic hashing,
- Q-state weights and phases,
- deterministic observation,
- protocol-level risk/confidence semantics,
- HMAC seal material,
- conformance vectors.

## Is It Secure?

It has integrity primitives: HMAC-SHA256 seals, frame hashes, TTL checks and
closed validation failures. It is not yet independently security-audited and
does not yet provide encryption, public-key identity, replay cache or key
rotation.

## Who Is It For?

- multi-agent systems,
- AI workflow engines,
- robotics/IoT coordination,
- internal AI infrastructure,
- research prototypes,
- gateway layers between AI systems.

## What Is The Smallest Useful Demo?

```bash
zpls conformance
zpls fabric-demo
zpls serve --node-id worker.local --endpoint http://127.0.0.1:8787/.well-known/zpls.json --key mesh-secret
```

## What Would Make It Production-Grade?

- public-key signatures,
- key rotation,
- replay cache,
- HTTP authentication/rate limits,
- CBOR/CDDL final binary spec,
- fuzzing,
- external security review,
- independent implementations.

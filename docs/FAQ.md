# ZPL-S FAQ

## Is ZPL-S AGI?

No. ZPL-S is protocol infrastructure. It does not create intelligence by
itself. It gives agents and machines a deterministic way to exchange state.

## Is This Real Quantum Computing?

No. The Q-Matrix is quantum-inspired protocol logic. It uses state vectors,
layer vectors, phase, interference and observation as useful abstractions for
unresolved machine state. It does not claim physical quantum computation.

## Why Not Just JSON?

ZPL-S can be transported inside JSON envelopes, but the core frame is compact,
canonical and designed for machine-state deltas. JSON alone does not define:

- canonical semantic hashing,
- Q-state weights and phases,
- layer/state tensor fields,
- deterministic observation,
- protocol-level risk/confidence semantics,
- HMAC seal material,
- conformance vectors.

Use ZPL-S if your agents already coordinate work and you need the handoff to be
deterministic, hashable, signable, replayable and auditable. Stay with ordinary
JSON if you only need a private app payload and do not need canonical replay or
protocol conformance.

## Is It Secure?

It has integrity primitives: HMAC-SHA256 seals, frame hashes, TTL checks and
closed validation failures. It is not yet independently security-audited and
does not yet provide encryption, public-key identity, key rotation or a
distributed replay cache for multi-node clusters.

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
- distributed replay cache,
- HTTP authentication/rate limits,
- CBOR/CDDL final binary spec,
- fuzzing,
- external security review,
- independent implementations.

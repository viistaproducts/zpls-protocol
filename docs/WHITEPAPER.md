# ZPL-S: A Canonical State Protocol for AI-Machine Coordination

## Abstract

ZPL-S is a protocol kernel for compact AI-to-AI and machine-to-machine
coordination. Instead of exchanging natural-language
instructions as the primary machine interface, systems exchange canonical state
frames with operation, target, confidence, risk and delta semantics. The
protocol adds a quantum-inspired Q-Matrix/Q-Field overlay for representing
multiple candidate machine states across layer superpositions, a deterministic
observation function, HMAC-based integrity seals, and an HTTP-compatible
Internet-Fabric envelope.

## Problem

Multi-agent systems often communicate through verbose natural language. This is
useful for humans but problematic for machines:

- ambiguous semantics,
- poor replayability,
- weak integrity guarantees,
- high token cost,
- difficult conformance testing,
- no compact representation of unresolved parallel state.

## Core Model

A ZPL-S frame is:

```text
F = (version, agent, state_hash, op, target, confidence, risk, delta)
```

The canonical frame is the normative object. Text and binary forms are
serializations of the same semantic value.

## Q-Matrix Overlay

The Q-Matrix overlay represents a sparse state vector:

```text
q = [(ref_i, weight_i, phase_i)]
```

A Q-Field can additionally carry a sparse layer vector:

```text
ql = [(layer_k, weight_k, phase_k)]
```

Weights are normalized on a fixed Q4 scale:

```text
Q = 10000
sum(weight_i) = Q
```

Sparse gates project one layer into another:

```text
src=dst@gain[/phase_shift]
```

Contributions to the same destination interfere through phase coherence and are
renormalized. A state vector and layer vector can also be expanded as a tensor
field:

```text
layer/state @ round(layer_weight * state_weight / Q)
```

Observation is deterministic:

```text
bucket = floor(first64bits(sha256(canonical_frame + observer)) * Q / 2^64)
```

This is protocol logic, not a physical quantum-computing claim.

## Integrity

Sealed frames use:

```text
seal:hmac-sha256.<key_id>.<mac>
```

The MAC is computed over the canonical frame with the `seal` field removed.
Any semantic mutation invalidates the seal.

## Internet-Fabric

ZPL-S Fabric defines:

- node descriptors,
- capability negotiation,
- signed JSON envelopes,
- TTL validation,
- frame hash verification,
- receipts,
- local mesh routing.

## Current Reference Implementation

The Python implementation includes:

- strict parser,
- canonical serializer,
- binary codec,
- semantic hash,
- Q-Matrix and Q-Field tensor logic,
- HMAC seal,
- Mesh kernel,
- HTTP server,
- Internet-Fabric gateway,
- CLI,
- conformance vectors,
- 108 automated tests.

The exact number may change as the test suite grows; `zpls conformance` is the
stable compatibility signal.

## Limitations

ZPL-S is not yet a standard and has not received an independent security audit.
It does not implement public-key identity, encryption, key rotation,
cluster-wide replay persistence or global network governance yet.

## Vision

The long-term vision is an AI-machine internet where systems do not need to
share prompts, vendors or programming languages. They need only exchange:

```text
state, operation, confidence, risk, delta, possible futures and proof.
```

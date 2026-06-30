# ZPL-S Launch Brief

## One-Line Pitch

ZPL-S is a compact state protocol for AI-to-AI and machine-to-machine
coordination: canonical frames, quantum-inspired state vectors, signed Internet
envelopes and a runnable HTTP fabric.

## Deutsch

ZPL-S ist kein weiterer Chatbot-Wrapper. Es ist ein Zustandsprotokoll fuer eine
Welt, in der AIs, Agenten, Roboter, Sensoren, Cloud-Dienste und Maschinen nicht
mehr lange Prosa austauschen, sondern kurze, pruefbare, mathematisch stabile
Frames.

Ein ZPL-S Frame sagt:

```text
Wer spricht?
Worauf bezieht sich der Zustand?
Was ist die Operation?
Wie sicher ist das System?
Wie hoch ist das Risiko?
Welche Zustandsaenderung wird vorgeschlagen?
Welche moeglichen Zukuenfte existieren noch unbeobachtet?
```

## Scientific Angle

ZPL-S separates language from machine state.

Natural language is high bandwidth for humans but ambiguous for machines.
ZPL-S makes the machine layer explicit:

- canonical semantic representation,
- stable semantic hashing,
- deterministic binary representation,
- sparse Q-state vectors,
- phase-based interference,
- deterministic observation,
- HMAC-sealed frames,
- Internet-Fabric envelopes with TTL, route and receipt.

The Q-Matrix layer is quantum-inspired protocol logic, not a claim of physical
quantum computation. It borrows the useful abstraction: multiple possible states
can remain encoded until an explicit observation event materializes one path.

## Why It Matters

Current agent systems often communicate by copying text. That is expensive,
ambiguous and difficult to verify.

ZPL-S makes inter-agent communication:

- smaller,
- deterministic,
- hashable,
- signable,
- testable,
- bridgeable across HTTP gateways.

## Demo Commands

```bash
zpls conformance
zpls mesh-demo
zpls fabric-demo
zpls serve --node-id worker.local --endpoint http://127.0.0.1:8787/.well-known/zpls.json --key mesh-secret
```

## Public Positioning

Use this phrase:

```text
ZPL-S is an experimental protocol kernel for the AI-machine internet.
```

Do not claim:

- audited security,
- real quantum computation,
- AGI,
- standard-body approval,
- production safety without review.

## Viral Short Copy

```text
What if AI agents stopped chatting and started exchanging verifiable state?

ZPL-S is a compact protocol for the AI-machine internet:
canonical frames, Q-state vectors, deterministic observation, HMAC seals,
HTTP fabric envelopes and conformance tests.

Not AGI. Not quantum hype. A real protocol kernel you can run today.
```

## Suggested GitHub Description

```text
Experimental AI-machine internet protocol: canonical state frames, Q-matrix logic, HMAC seals, HTTP fabric and conformance tests.
```

## Suggested Topics

```text
ai-agents
agent-protocol
machine-to-machine
multi-agent-systems
protocol
state-machine
semantic-hashing
quantum-inspired
ai-infrastructure
http-fabric
```

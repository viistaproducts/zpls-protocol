# Killer Demo: Planner / Coder / Critic

This demo shows the practical point of ZPL-S in one command: agents can exchange
compact, deterministic, auditable state transitions instead of copying long
chat context.

## Run

```bash
python examples/killer_demo.py
```

## Scenario

- `planner` wants to ship.
- `coder` has prepared the release.
- `critic` detects stale pricing.
- A risk gate blocks `ship` and routes back to `planner`.

## What It Shows

- compact ZPL-S frame size versus equivalent chat JSON size,
- deterministic frame hash,
- canonical S1.1 delta operations,
- replay equality,
- risk gate decision,
- audit events for why routing changed.

## Expected Shape

```text
zpls_frame_bytes: 90
chat_json_bytes: 317
replay_equal: true
risk_gate: ship blocked -> revise_pricing
receiver: planner
```

Use this when explaining ZPL-S quickly:

> What if AI agents stopped chatting and started exchanging verifiable state?

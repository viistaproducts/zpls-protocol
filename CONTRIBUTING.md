# Contributing

ZPL-S is experimental protocol infrastructure. Contributions should keep the
protocol deterministic, compact and testable.

## Ground Rules

- Do not introduce nondeterministic wire semantics.
- Add or update conformance vectors for protocol-visible changes.
- Keep security claims precise.
- Do not describe the project as audited, AGI, or real quantum computing.
- Prefer small, reviewable protocol changes.

## Development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
zpls conformance
```

## Protocol Changes

Protocol-visible changes need:

- implementation,
- tests,
- docs,
- conformance vector when deterministic output changes,
- migration note if existing frames are affected.

## Security Changes

Security changes need tests for:

- valid path,
- invalid key,
- tampered data,
- malformed input,
- replay or expiry behavior if relevant.

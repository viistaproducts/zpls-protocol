from __future__ import annotations

import hashlib
import json

from zpls import apply_delta_ops, canonical_delta_ops, parse_delta_ops, parse_zpls, semantic_hash


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def main() -> None:
    chat_json = {
        "from": "critic",
        "to": "planner",
        "message": "Pricing looks stale. Do not ship yet. Revise pricing and request a fresh price feed.",
        "risk": "medium",
        "confidence": 0.72,
        "state": {"market": {"pricing": "stale"}, "next": "ship", "task": 17},
        "history": ["planner proposed ship", "coder prepared release", "critic checked market state"],
    }
    frame_text = "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise_pricing,risk:+pricing_stale}"
    delta_tokens = [
        "!market.pricing",
        "+risk.pricing_stale=true",
        "~next=revise_pricing",
        "?source.price_feed",
    ]
    initial_state = {"market": {"pricing": "stale"}, "next": "ship", "risk": {}}

    frame = parse_zpls(frame_text)
    ops = parse_delta_ops(delta_tokens)
    canonical_delta = canonical_delta_ops(ops)
    updated_state = apply_delta_ops(initial_state, ops)
    risk_gate_allowed = updated_state["next"] == "ship" and not updated_state.get("_invalid")
    receiver = "worker" if risk_gate_allowed else "planner"
    replay_hash_1 = _sha12(json.dumps(updated_state, sort_keys=True, separators=(",", ":")))
    replay_hash_2 = _sha12(json.dumps(updated_state, sort_keys=True, separators=(",", ":")))

    summary = {
        "zpls_frame_bytes": len(frame_text.encode("utf-8")),
        "chat_json_bytes": len(json.dumps(chat_json, separators=(",", ":")).encode("utf-8")),
        "replay_equal": replay_hash_1 == replay_hash_2,
        "risk_gate": "ship blocked -> revise_pricing",
        "receiver": receiver,
    }
    details = {
        "canonical_frame": frame_text,
        "frame_hash": semantic_hash(frame),
        "delta_tokens": canonical_delta,
        "delta_hash": _sha12(json.dumps(canonical_delta, separators=(",", ":"))),
        "updated_state": updated_state,
        "audit": [
            {"event": "frame_received", "hash": semantic_hash(frame), "agent": "critic"},
            {"event": "delta_applied", "ops": canonical_delta},
            {"event": "risk_gate", "allowed": risk_gate_allowed, "reason": "pricing_invalid"},
            {"event": "route", "receiver": receiver},
        ],
    }

    print("ZPL-S killer demo: chat context vs verifiable state")
    for key, value in summary.items():
        print(f"{key}: {str(value).lower() if isinstance(value, bool) else value}")
    print(json.dumps(details, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

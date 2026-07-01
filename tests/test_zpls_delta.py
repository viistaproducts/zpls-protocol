from __future__ import annotations

import pytest

from zpls import (
    DeltaError,
    DeltaOp,
    apply_delta_ops,
    canonical_delta_ops,
    delta_material,
    parse_delta_op,
    parse_delta_ops,
    split_delta_ops,
)


def test_parse_add_replace_remove_invalidate_need():
    assert parse_delta_op("+risk.pricing_stale=true") == DeltaOp("+", "risk.pricing_stale", True)
    assert parse_delta_op("~next=revise_pricing") == DeltaOp("~", "next", "revise_pricing")
    assert parse_delta_op("-draft.old") == DeltaOp("-", "draft.old")
    assert parse_delta_op("!market.pricing") == DeltaOp("!", "market.pricing")
    assert parse_delta_op("?source.price_feed") == DeltaOp("?", "source.price_feed")


def test_canonical_delta_ops_sorted_by_path_then_op():
    ops = parse_delta_ops(["?source.price_feed", "~next=revise_pricing", "!market.pricing", "+risk.pricing_stale=true"])

    assert canonical_delta_ops(ops) == [
        "!market.pricing",
        "~next=revise_pricing",
        "+risk.pricing_stale=true",
        "?source.price_feed",
    ]
    assert delta_material(ops) == '["!market.pricing","~next=revise_pricing","+risk.pricing_stale=true","?source.price_feed"]'


def test_split_delta_ops_accepts_commas_and_token_lists():
    assert split_delta_ops(["!market.pricing,+risk.pricing_stale=true", "?source.price_feed"]) == [
        "!market.pricing",
        "+risk.pricing_stale=true",
        "?source.price_feed",
    ]


def test_delta_float_values_roundtrip_compact_form():
    assert parse_delta_op("+score=.5") == DeltaOp("+", "score", 0.5)
    assert parse_delta_op("~score=-.25") == DeltaOp("~", "score", -0.25)
    assert canonical_delta_ops([DeltaOp("+", "score", 0.5)]) == ["+score=.5"]


def test_apply_delta_ops_without_mutating_input():
    state = {
        "market": {"pricing": "stale"},
        "next": "ship",
        "draft": {"old": "remove me"},
        "risk": {},
    }
    ops = parse_delta_ops(
        [
            "!market.pricing",
            "+risk.pricing_stale=true",
            "~next=revise_pricing",
            "-draft.old",
            "?source.price_feed",
        ]
    )

    out = apply_delta_ops(state, ops)

    assert state["next"] == "ship"
    assert out == {
        "market": {"pricing": "stale"},
        "next": "revise_pricing",
        "draft": {},
        "risk": {"pricing_stale": True},
        "_invalid": {"market.pricing": True},
        "_needs": {"source.price_feed": True},
    }


@pytest.mark.parametrize(
    ("state", "op", "message"),
    [
        ({"a": 1}, DeltaOp("+", "a", 2), "already exists"),
        ({}, DeltaOp("~", "a", 2), "missing"),
        ({}, DeltaOp("-", "a"), "missing"),
    ],
)
def test_apply_delta_ops_fail_closed(state, op, message):
    with pytest.raises(DeltaError, match=message):
        apply_delta_ops(state, [op])


@pytest.mark.parametrize("token", ["", "x", "+bad-path=true", "+risk=", "-a=1", "?bad.path-"])
def test_invalid_delta_tokens_fail_closed(token):
    with pytest.raises(DeltaError):
        parse_delta_op(token)

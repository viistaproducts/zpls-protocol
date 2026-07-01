from __future__ import annotations

import json

from zpls.cli import main


def test_cli_conformance_reports_ok(capsys):
    assert main(["conformance"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert all(out["checks"].values())


def test_cli_qmake_qgate_observe_flow(capsys):
    assert (
        main(
            [
                "qmake",
                "--agent",
                "planner",
                "--state",
                "8f3c",
                "--op",
                "plan",
                "--target",
                "17",
                "--confidence",
                ".81",
                "--risk",
                "med",
                "--branches",
                "u0/a@.5,u0/b@.5/.5",
            ]
        )
        == 0
    )
    qframe = capsys.readouterr().out.strip()
    assert qframe == "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med Δ{q:[u0/a@.5,u0/b@.5/.5]}"

    assert (
        main(
            [
                "qgate",
                "--frame",
                qframe,
                "--edges",
                "u0/a=u1/x@.8,u0/b=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/y@.2/-.5",
                "--keep-gate",
            ]
        )
        == 0
    )
    projected = capsys.readouterr().out.strip()
    assert projected == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{gate:[u0/a=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/x@.8,u0/b=u1/y@.2/-.5],"
        "q:[u1/x@.6667/.25,u1/y@.3333]}"
    )

    assert main(["observe", "--observer", "human", "--json", projected]) == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["bucket"] == 6824
    assert observed["observed"] == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{gate:[u0/a=u1/x@.8,u0/a=u1/y@.2,u0/b=u1/x@.8,u0/b=u1/y@.2/-.5],"
        "qobs:human,qpick:u1/y}"
    )


def test_cli_qfield_flow(capsys):
    assert (
        main(
            [
                "qmake",
                "--agent",
                "planner",
                "--state",
                "8f3c",
                "--op",
                "plan",
                "--target",
                "17",
                "--confidence",
                ".81",
                "--risk",
                "med",
                "--branches",
                "revise@.4/-.25,ship@.6",
                "--layers",
                "sim@.55/.25,prod@.45/-.25",
            ]
        )
        == 0
    )
    qfield = capsys.readouterr().out.strip()
    assert qfield == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{q:[revise@.4/-.25,ship@.6],ql:[prod@.45/-.25,sim@.55/.25]}"
    )

    assert main(["qfield", "--frame", qfield]) == 0
    tensor = json.loads(capsys.readouterr().out)
    assert tensor["coherence"] == 0.1644
    assert tensor["tensor"] == [
        "prod/revise@.18/-.5",
        "prod/ship@.27/-.25",
        "sim/revise@.22",
        "sim/ship@.33/.25",
    ]

    assert main(["qfield", "--frame", qfield, "--as-frame"]) == 0
    tensor_frame = capsys.readouterr().out.strip()
    assert tensor_frame == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{q:[prod/revise@.18/-.5,prod/ship@.27/-.25,sim/revise@.22,sim/ship@.33/.25],qcoh:.1644}"
    )

    assert main(["observe", "--observer", "human", "--json", qfield]) == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["bucket"] == 9949
    assert observed["layer_bucket"] == 4301
    assert observed["observed"] == (
        "§S1 a:planner sh:8f3c op:plan t:17 c:.81 r:med "
        "Δ{qlphase:-.25,qlpick:prod,qobs:human,qpick:ship}"
    )


def test_cli_delta_canon_and_apply_flow(capsys):
    assert (
        main(
            [
                "delta-canon",
                "?source.price_feed",
                "~next=revise_pricing",
                "!market.pricing",
                "+risk.pricing_stale=true",
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.strip() == (
        "!market.pricing,~next=revise_pricing,+risk.pricing_stale=true,?source.price_feed"
    )

    assert (
        main(
            [
                "delta-apply",
                "--state",
                '{"market":{"pricing":"stale"},"next":"ship","risk":{}}',
                "!market.pricing,+risk.pricing_stale=true,~next=revise_pricing,?source.price_feed",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {
        "_invalid": {"market.pricing": True},
        "_needs": {"source.price_feed": True},
        "market": {"pricing": "stale"},
        "next": "revise_pricing",
        "risk": {"pricing_stale": True},
    }


def test_cli_validate_failure_returns_nonzero(capsys):
    assert main(["validate", "not-a-frame"]) == 1

    err = capsys.readouterr().err
    assert "zpls error" in err


def test_cli_seal_and_verify_flow(capsys):
    frame = "§S1 a:critic sh:8f3c op:eval t:17 c:.72 r:med Δ{next:revise}"

    assert main(["seal", "--key", "mesh-secret", "--key-id", "mesh", frame]) == 0
    sealed = capsys.readouterr().out.strip()
    assert "seal:hmac-sha256.mesh." in sealed

    assert main(["verify", "--key", "mesh-secret", "--json", sealed]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["seal"]["key_id"] == "mesh"

    assert main(["verify", "--key", "wrong-secret", sealed]) == 1
    assert capsys.readouterr().out.strip() == "fail"


def test_cli_mesh_demo_is_executable(capsys):
    assert main(["mesh-demo"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["accepted"] is True
    assert out["receiver"] == "worker"
    assert out["worker_inbox"] == [out["frame"]]
    assert "qobs:human" in out["frame"]
    assert "qpick:" in out["frame"]


def test_cli_fabric_demo_is_executable(capsys):
    assert main(["fabric-demo"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["agreement"]["protocol_version"] == "S1"
    assert out["receipt"]["accepted"] is True
    assert out["receipt"]["receiver"] == "worker"


def test_cli_fabric_pack_receive_flow(capsys):
    frame = "§S1 a:planner sh:8f3c op:plan t:17 c:.91 r:low Δ{next:worker}"

    assert (
        main(
            [
                "fabric-pack",
                "--source",
                "planner.example",
                "--endpoint",
                "https://planner.example/zpls",
                "--destination",
                "worker.example",
                "--trace",
                "trace.demo",
                "--created-at",
                "1",
                "--key",
                "mesh-secret",
                frame,
            ]
        )
        == 0
    )
    envelope = capsys.readouterr().out.strip()
    assert "hmac-sha256.mesh" in envelope

    assert (
        main(
            [
                "fabric-receive",
                "--node-id",
                "worker.example",
                "--endpoint",
                "https://worker.example/zpls",
                "--roles",
                "worker",
                "--key",
                "mesh-secret",
                "--now",
                "2",
                envelope,
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["accepted"] is True
    assert receipt["receiver"] == "worker"

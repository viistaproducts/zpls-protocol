from __future__ import annotations

from zpls import QBranch, explain_qstate, make_qframe, observe_qstate, serialize_zpls


frame = make_qframe(
    agent="planner",
    state_hash="8f3c",
    op="plan",
    target="17",
    confidence=0.81,
    risk="med",
    branches=[
        QBranch("revise", 0.37, -0.5),
        QBranch("ship", 0.63),
    ],
    entangled=["critic.17", "coder.17"],
)

observed = observe_qstate(frame, "human")

print(serialize_zpls(frame))
print(explain_qstate(frame))
print(serialize_zpls(observed))
print(explain_qstate(observed))

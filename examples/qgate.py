from __future__ import annotations

from zpls import QBranch, QEdge, apply_qgate, format_qbranches


branches = [
    QBranch("u0/a", 0.5),
    QBranch("u0/b", 0.5, 0.5),
]

gate = [
    QEdge("u0/a", "u1/x", 0.8),
    QEdge("u0/b", "u1/x", 0.8),
    QEdge("u0/a", "u1/y", 0.2),
    QEdge("u0/b", "u1/y", 0.2, -0.5),
]

projected = apply_qgate(branches, gate)

print(format_qbranches(branches))
print([edge.canonical() for edge in gate])
print(format_qbranches(projected))

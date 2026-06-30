from zpls import QBranch, ZplsMesh, make_qframe, serialize_zpls


mesh = ZplsMesh()
mesh.register("planner")
mesh.register("worker")

state_ref = mesh.put_state("plan.17", {"status": "open", "task": "price_check"})
frame = make_qframe(
    agent="planner",
    state_hash=state_ref,
    op="plan",
    target="17",
    confidence=0.81,
    risk="med",
    branches=[QBranch("revise", 0.37, -0.5), QBranch("ship", 0.63)],
)

event = mesh.route(frame, sender="planner", observer="human")

print(event)
print(serialize_zpls(mesh.inbox("worker")[0]))

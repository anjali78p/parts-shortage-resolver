"""Bina API key ke test. FakeLLM script ke hisaab se tool calls karta hai aur kuch galat jawab bhi deta hai."""
import uuid

from langgraph.types import Command

from data import repair_orders, reset_demo_data
from fake_llm import FakeLLM
from graph import build_graph
from resequence import Move, ResequencePlan, verify_plan


def cfg():
    return {"configurable": {"thread_id": uuid.uuid4().hex}}


app = build_graph(FakeLLM())
reset_demo_data()
c1 = cfg()
out = app.invoke({"ro_id": "RO-1042", "log": []}, c1)
for line in out["log"]:
    print(" ", line)

plan = out["plan"]
ids = [m["ro_id"] for m in plan["moves"]]
assert ids == ["RO-1070", "RO-1055"], ids
assert plan["idle_hours_saved"] == 2.0 and plan["stalled_ro_resumes_at"] == "12:00"
assert sum("Guardrail" in l for l in out["log"] if "hataya" in l) == 2

# overlap guardrail alag se
state = {"ro_id": "RO-1042", "ranked_options": [{"eta_hours": 3}]}
p, notes = verify_plan(ResequencePlan(moves=[Move(ro_id="RO-1070", new_start="10:00", reasoning=""),
                                             Move(ro_id="RO-1055", new_start="10:30", reasoning="")],
                                      summary=""), state)
assert [m["ro_id"] for m in p["moves"]] == ["RO-1070"] and "overlap" in notes[0]

assert app.invoke({"ro_id": "RO-1060", "log": []}, cfg()).get("plan") is None
assert app.invoke({"ro_id": "RO-1055", "log": []}, cfg()).get("plan") is None

# ---------- Step 4: approval flow ----------
assert "__interrupt__" in out, "graph approval pe rukna chahiye"
assert app.get_state(c1).next == ("human_approval",)       # checkpointer ne paused state save ki
assert repair_orders["RO-1070"]["bay"] == 4                  # abhi kuch badla nahi

res = app.invoke(Command(resume={"approved": True}), c1)     # manager: approve
assert repair_orders["RO-1070"]["bay"] == 3 and repair_orders["RO-1070"]["start"] == "10:00"
assert repair_orders["RO-1055"]["start"] == "11:00"
assert repair_orders["RO-1042"]["status"] == "Part Ordered" and repair_orders["RO-1042"]["start"] == "12:00"
assert res["approved"] is True and res["applied_changes"]
print("  approve flow OK")

reset_demo_data()
c2 = cfg()
app.invoke({"ro_id": "RO-1042", "log": []}, c2)
res = app.invoke(Command(resume={"approved": False, "note": "tech busy"}), c2)   # manager: reject
assert res["approved"] is False and not res.get("applied_changes")
assert repair_orders["RO-1070"]["bay"] == 4 and repair_orders["RO-1042"]["status"] == "Waiting on Part"
print("  reject flow OK")

# stream mode mein interrupt update ke roop mein aata hai (main.py yahi use karta hai)
reset_demo_data()
seen = [k for u in app.stream({"ro_id": "RO-1042", "log": []}, cfg(), stream_mode="updates") for k in u]
assert seen[-1] == "__interrupt__", seen
reset_demo_data()
print("OK: Step 4 approval flow + guardrails kaam kar rahe hain")

"""Step 4: Human-in-the-loop. interrupt() graph ko rok deta hai; checkpointer state yaad rakhta hai."""
from langgraph.types import interrupt

from data import repair_orders


def human_approval(state: dict) -> dict:
    plan = state["plan"]
    best = state["ranked_options"][0]

    # interrupt(): yahan graph RUK jata hai. Jo value bheji (dict), wo UI/CLI ko milti hai.
    # Resume par yahi call manager ka jawab return karti hai.
    # DHYAN: resume par ye POORA node dobara chalta hai, isliye interrupt se pehle koi side-effect mat rakho.
    decision = interrupt({
        "question": "Kya ye schedule change approve karna hai?",
        "part_order": f"{best['name']} se part mangwana ({best['eta_hours']}h, Rs {best['total_cost_inr']})",
        "plan": plan,
    })

    approved = bool(decision.get("approved"))
    note = decision.get("note", "")
    msg = "Manager ne APPROVE kiya" if approved else "Manager ne REJECT kiya"
    return {"approved": approved, "log": [msg + (f": {note}" if note else "")]}


def apply_plan_to(ros: dict, plan: dict) -> list[str]:
    """Plan ko kisi bhi RO-dict pe lagata hai. Asli data pe (apply_schedule) aur copy pe (UI preview) dono."""
    changes = []
    for m in plan["moves"]:
        ro = ros[m["ro_id"]]
        ro["bay"], ro["tech"], ro["start"] = m["bay"], m["tech"], m["new_start"]
        changes.append(f"{m['ro_id']} -> bay {m['bay']}, {m['new_start']}-{m['new_end']}")
    stalled = ros[plan["stalled_ro"]]
    stalled["start"], stalled["status"] = plan["stalled_ro_resumes_at"], "Part Ordered"
    changes.append(f"{plan['stalled_ro']} -> {plan['stalled_ro_resumes_at']} pe resume, status 'Part Ordered'")
    return changes


def apply_schedule(state: dict) -> dict:
    """Sirf approve hone par chalta hai. Real system mein yahan API call hoti; hum mock data badalte hain."""
    plan, best = state["plan"], state["ranked_options"][0]
    changes = [f"Part order: {best['name']} se {best['eta_hours']}h mein aayega"]
    changes += apply_plan_to(repair_orders, plan)
    return {"applied_changes": changes, "log": ["Schedule update ho gaya"] + changes}


def route_after_plan(state: dict) -> str:
    return "human_approval" if state.get("plan", {}).get("moves") else "__end__"


def route_after_approval(state: dict) -> str:
    return "apply_schedule" if state["approved"] else "__end__"

import os
import sys
import uuid

from dotenv import load_dotenv
from langgraph.types import Command

from graph import build_graph
from ranking import get_llm

load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    sys.exit("GOOGLE_API_KEY not found. Create a .env file (see .env.example).")

ro_id = next((a for a in sys.argv[1:] if a.startswith("RO-")), "RO-1042")
auto = "--approve" if "--approve" in sys.argv else "--reject" if "--reject" in sys.argv else None

app = build_graph(get_llm())
# thread_id = ek "conversation/run" ki pehchaan. Checkpointer isi se paused state dhoondhta hai.
config = {"configurable": {"thread_id": f"{ro_id}-{uuid.uuid4().hex[:6]}"}}
next_input = {"ro_id": ro_id, "log": []}


def ask_manager(request: dict) -> dict:
    plan = request["plan"]
    print("\n" + "=" * 50)
    print("MANAGER APPROVAL NEEDED")
    print("=" * 50)
    print("Part:", request["part_order"])
    for m in plan["moves"]:
        print(f"  {m['ro_id']} ({m['job']}): {m['original_start']} -> {m['new_start']}-{m['new_end']}, bay {m['bay']}")
    print(f"Idle time recovered: {plan['idle_hours_saved']}h of {plan['idle_hours_total']}h")
    if auto:
        print(f"(auto: {auto})")
        return {"approved": auto == "--approve"}
    answer = input("\nApprove? (y/n): ").strip().lower()
    note = input("Note (optional): ").strip() if answer != "y" else ""
    return {"approved": answer == "y", "note": note}


while True:
    pending = None
    for update in app.stream(next_input, config, stream_mode="updates"):
        for node_name, changes in update.items():
            if node_name == "__interrupt__":      # graph ruka: manager ka jawab chahiye
                pending = changes[0].value
                continue
            print(f"[{node_name}]")
            for line in changes.get("log", []):
                print("   ", line)
    if pending is None:
        break
    next_input = Command(resume=ask_manager(pending))   # jawab ke saath wahin se aage badho

# Checkpointer se final state wapas lo (manual merge ki zaroorat nahi)
final = app.get_state(config).values

if final.get("ranked_options"):
    print("\n=== RANKED OPTIONS ===")
    for o in final["ranked_options"]:
        print(f"#{o['rank']} {o['name']} | {o['eta_hours']}h | Rs {o['total_cost_inr']} "
              f"| promise ok: {o['meets_promise']}\n    {o['reasoning']}")

plan = final.get("plan")
if plan:
    w = plan["idle_window"]
    print("\n=== RESEQUENCE PLAN ===")
    print(f"Bay {w['bay']} idle: {w['idle_start']} - {w['idle_end']} ({plan['idle_hours_total']}h)")
    for m in plan["moves"]:
        print(f"  {m['ro_id']}: {m['original_start']} -> {m['new_start']}-{m['new_end']} (bay {m['bay']})")
    print(f"Idle time recovered: {plan['idle_hours_saved']}h | Summary: {plan['summary']}")

print("\n=== RESULT ===")
if final.get("applied_changes"):
    print("APPROVED. Schedule updated:")
    for c in final["applied_changes"]:
        print("  -", c)
elif plan and plan.get("moves"):
    print("REJECTED. No changes were made to the schedule.")

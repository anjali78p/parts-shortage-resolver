import os
import sys

from dotenv import load_dotenv

from graph import build_graph
from ranking import get_llm

load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    sys.exit("GOOGLE_API_KEY nahi mili. .env file banao (.env.example dekho).")

app = build_graph(get_llm())
ro_id = sys.argv[1] if len(sys.argv) > 1 else "RO-1042"

# .stream() se live steps dikhte hain AUR final state bhi yahin jama karte hain.
# (Pehle alag se .invoke() karte the: isse har LLM call do baar lagti thi, free limit jaldi khatam.)
final = {"ro_id": ro_id}
for update in app.stream({"ro_id": ro_id, "log": []}, stream_mode="updates"):
    for node_name, changes in update.items():
        print(f"[{node_name}]")
        for line in changes.get("log", []):
            print("   ", line)
        final.update({k: v for k, v in changes.items() if k not in ("log", "messages")})

if final.get("ranked_options"):
    print("\n=== RANKED OPTIONS ===")
    for o in final["ranked_options"]:
        print(f"#{o['rank']} {o['name']} | {o['eta_hours']}h | Rs {o['total_cost_inr']} "
              f"| promise ok: {o['meets_promise']}\n    {o['reasoning']}")
    print("\nSummary:", final["summary"])

plan = final.get("plan")
if plan:
    w = plan["idle_window"]
    print(f"\n=== RESEQUENCE PLAN ===")
    print(f"Bay {w['bay']} idle: {w['idle_start']} - {w['idle_end']} ({plan['idle_hours_total']}h), "
          f"tech {w['tech']}")
    for m in plan["moves"]:
        print(f"  {m['ro_id']} ({m['vehicle']}, {m['job']}): {m['original_start']} -> "
              f"{m['new_start']}-{m['new_end']} in bay {m['bay']}\n      {m['reasoning']}")
    print(f"Idle time bacha: {plan['idle_hours_saved']}h of {plan['idle_hours_total']}h")
    print(f"{plan['stalled_ro_resumes_at']} pe {plan['stalled_ro']} wapas bay mein shuru hoga")
    print("Summary:", plan["summary"])

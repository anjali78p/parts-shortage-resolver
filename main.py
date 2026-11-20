import os
import sys

from dotenv import load_dotenv

from graph import build_graph
from ranking import get_llm

load_dotenv()  # .env se GOOGLE_API_KEY padhta hai
if not os.getenv("GOOGLE_API_KEY"):
    sys.exit("GOOGLE_API_KEY nahi mili. .env file banao (.env.example dekho).")

app = build_graph(get_llm())
ro_id = sys.argv[1] if len(sys.argv) > 1 else "RO-1042"
initial = {"ro_id": ro_id, "log": []}

for update in app.stream(initial, stream_mode="updates"):
    for node_name, changes in update.items():
        print(f"[{node_name}]")
        for line in changes.get("log", []):
            print("   ", line)

final = app.invoke(initial)
if final.get("ranked_options"):
    print("\n=== RANKED OPTIONS ===")
    for o in final["ranked_options"]:
        print(f"#{o['rank']} {o['name']} | {o['eta_hours']}h | Rs {o['total_cost_inr']} "
              f"| promise ok: {o['meets_promise']}\n    {o['reasoning']}")
    print("\nSummary:", final["summary"])

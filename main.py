import sys

from graph import build_graph

app = build_graph()
ro_id = sys.argv[1] if len(sys.argv) > 1 else "RO-1042"

initial = {"ro_id": ro_id, "log": []}

# .stream() har node ke baad state update deta hai. UI pe live steps isi se dikhenge.
for update in app.stream(initial, stream_mode="updates"):
    for node_name, changes in update.items():
        print(f"[{node_name}]")
        for line in changes.get("log", []):
            print("   ", line)

final = app.invoke(initial)
print("\nSister options:", final.get("sister_options"))
print("Vendor options:", final.get("vendor_options"))

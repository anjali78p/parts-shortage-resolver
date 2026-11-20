"""Bina API key ke test. FakeLLM jaan-boojh ke GALAT jawab deta hai, guardrail ko test karne ke liye."""
from graph import build_graph
from ranking import RankedOption, RankingResult


class BadFakeLLM:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return RankingResult(
            ranked=[
                RankedOption(rank=1, source="vendor", name="QuickSpares", eta_hours=6,
                             total_cost_inr=2100, meets_promise=True, reasoning="x"),
                RankedOption(rank=2, source="sister_store", name="Store B - Malviya Nagar", eta_hours=3,
                             total_cost_inr=2400, meets_promise=True, reasoning="y"),   # galat cost
                RankedOption(rank=3, source="vendor", name="Ghost Vendor", eta_hours=1,
                             total_cost_inr=1, meets_promise=True, reasoning="z"),      # nakli
            ],
            summary="test")


app = build_graph(BadFakeLLM())
out = app.invoke({"ro_id": "RO-1042", "log": []})
for line in out["log"]:
    print(" ", line)
names = [o["name"] for o in out["ranked_options"]]
assert "Ghost Vendor" not in names
store_b = next(o for o in out["ranked_options"] if o["name"].startswith("Store B"))
assert store_b["total_cost_inr"] == 2000, store_b
assert any("rule order" in l for l in out["log"])
assert app.invoke({"ro_id": "RO-1060", "log": []}).get("ranked_options") is None
assert app.invoke({"ro_id": "RO-1055", "log": []}).get("ranked_options") is None
print("OK: guardrails kaam kar rahe hain")

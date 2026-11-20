"""Bina API key ke LLM ki nakal. Sirf testing ke liye (jaan-boojh ke kuch galtiyan karta hai taaki guardrails test hon)."""
from langchain_core.messages import AIMessage, ToolMessage

from ranking import RankedOption, RankingResult
from resequence import Move, ResequencePlan


class FakeLLM:
    def with_structured_output(self, schema):
        outer = self

        class S:
            def invoke(self, messages):
                return outer.rank() if schema is RankingResult else outer.plan()
        return S()

    def bind_tools(self, tools):
        outer = self

        class T:
            def invoke(self, messages):
                return outer.agent_step(sum(isinstance(m, ToolMessage) for m in messages))
        return T()

    def rank(self):
        return RankingResult(ranked=[RankedOption(rank=1, source="sister_store", name="Store B - Malviya Nagar",
                             eta_hours=3, total_cost_inr=2400, meets_promise=True, reasoning="x")], summary="s")

    def agent_step(self, n_tool_msgs):
        calls = {
            0: [("get_idle_window", {"ro_id": "RO-1042", "part_arrival_hours": 3})],
            1: [("find_candidate_ros", {"idle_start": "10:00", "idle_end": "12:00"})],
            2: [("check_technician_skill", {"tech_id": "T-07", "job_type": "wipers"}),
                ("check_technician_skill", {"tech_id": "T-07", "job_type": "oil_service"})],
        }.get(n_tool_msgs)
        if calls is None:
            return AIMessage(content="Research done.")
        return AIMessage(content="", tool_calls=[{"name": n, "args": a, "id": f"call_{n_tool_msgs}_{i}"}
                                                 for i, (n, a) in enumerate(calls)])

    def plan(self):
        return ResequencePlan(moves=[
            Move(ro_id="RO-1090", new_start="10:00", reasoning="tech qualified nahi (trap)"),
            Move(ro_id="RO-1070", new_start="10:00", reasoning="wipers fit"),
            Move(ro_id="RO-1080", new_start="11:00", reasoning="part local nahi (trap)"),
            Move(ro_id="RO-1055", new_start="11:00", reasoning="oil service fit"),
        ], summary="Fill bay 3 with two quick jobs.")

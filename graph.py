"""LangGraph wiring. Step 1: nodes/edges. Step 2: LLM rank. Step 3: ReAct loop with tools."""
import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition

from approval import apply_schedule, human_approval, route_after_approval, route_after_plan
from data import repair_orders
from ranking import make_rank_options
from resequence import (make_finalize_plan, make_resequence_agent, make_run_tools,
                        prepare_resequence)
from tools import check_local_inventory, check_sister_stores, check_vendor_stock


class StallState(TypedDict):
    ro_id: str
    part_no: str
    is_stalled: bool
    local_qty: int
    sister_options: list[dict]
    vendor_options: list[dict]
    promise_by_hours: float
    ranked_options: list[dict]
    summary: str
    # Step 3
    messages: Annotated[list, add_messages]   # LLM <-> tools ki baatcheet; add_messages = special reducer
    plan: dict
    # Step 4
    approved: bool
    applied_changes: list[str]
    log: Annotated[list[str], operator.add]


def detect_stall(state: StallState) -> dict:
    ro = repair_orders[state["ro_id"]]
    stalled = ro["status"] == "Waiting on Part"
    msg = (f"{state['ro_id']} ({ro['vehicle']} - {ro['job']}) STALLED, part {ro['part_no']} chahiye"
           if stalled else f"{state['ro_id']} stalled nahi hai")
    return {"part_no": ro["part_no"], "is_stalled": stalled,
            "promise_by_hours": ro.get("promise_by_hours", 24), "log": [msg]}


def check_local(state: StallState) -> dict:
    qty = check_local_inventory(state["part_no"])
    return {"local_qty": qty, "log": [f"Local stock: {qty} -> " + ("mil gaya" if qty > 0 else "nahi hai")]}


def check_sister(state: StallState) -> dict:
    options = check_sister_stores(state["part_no"])
    return {"sister_options": options, "log": [f"Sister stores: {len(options)} option(s) mile"]}


def check_vendor(state: StallState) -> dict:
    options = check_vendor_stock(state["part_no"])
    return {"vendor_options": options, "log": [f"Vendors: {len(options)} option(s) mile"]}


def route_after_detect(state: StallState) -> str:
    return "check_local" if state["is_stalled"] else END


def route_after_local(state: StallState) -> str:
    return END if state["local_qty"] > 0 else "check_sister"


def route_after_rank(state: StallState) -> str:
    return "prepare_resequence" if state.get("ranked_options") else END


def build_graph(llm, checkpointer=None):
    g = StateGraph(StallState)

    g.add_node("detect_stall", detect_stall)
    g.add_node("check_local", check_local)
    g.add_node("check_sister", check_sister)
    g.add_node("check_vendor", check_vendor)
    g.add_node("rank_options", make_rank_options(llm))
    g.add_node("prepare_resequence", prepare_resequence)
    g.add_node("resequence_agent", make_resequence_agent(llm))
    g.add_node("tools", make_run_tools())
    g.add_node("finalize_plan", make_finalize_plan(llm))
    g.add_node("human_approval", human_approval)
    g.add_node("apply_schedule", apply_schedule)

    g.add_edge(START, "detect_stall")
    g.add_conditional_edges("detect_stall", route_after_detect)
    g.add_conditional_edges("check_local", route_after_local)
    g.add_edge("check_sister", "check_vendor")
    g.add_edge("check_vendor", "rank_options")
    g.add_conditional_edges("rank_options", route_after_rank)

    # ReAct loop: agent -> (tool call hai?) -> tools -> agent -> ... -> finalize_plan
    g.add_edge("prepare_resequence", "resequence_agent")
    g.add_conditional_edges("resequence_agent", tools_condition, {"tools": "tools", END: "finalize_plan"})
    g.add_edge("tools", "resequence_agent")
    g.add_conditional_edges("finalize_plan", route_after_plan, {"human_approval": "human_approval", END: END})

    # Step 4: manager approve kare tabhi apply_schedule
    g.add_conditional_edges("human_approval", route_after_approval, {"apply_schedule": "apply_schedule", END: END})
    g.add_edge("apply_schedule", END)

    # interrupt() ke liye checkpointer zaroori hai (paused state yahin save hoti hai)
    return g.compile(checkpointer=checkpointer or MemorySaver())

"""Step 1: LLM ke bina LangGraph. Focus: State, Nodes, Edges, Conditional edges."""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from data import repair_orders
from tools import check_local_inventory, check_sister_stores, check_vendor_stock


# 1) STATE: graph ki shared memory. Har node isme se padhta hai aur isme likhta hai.
class StallState(TypedDict):
    ro_id: str
    part_no: str
    is_stalled: bool
    local_qty: int
    sister_options: list[dict]
    vendor_options: list[dict]
    # Annotated + operator.add = "reducer": nodes ki list append hoti hai, overwrite nahi.
    log: Annotated[list[str], operator.add]


# 2) NODES: har node state leta hai aur state ka *sirf badla hua hissa* return karta hai.
def detect_stall(state: StallState) -> dict:
    ro = repair_orders[state["ro_id"]]
    stalled = ro["status"] == "Waiting on Part"
    msg = (f"{state['ro_id']} ({ro['vehicle']} - {ro['job']}) STALLED, part {ro['part_no']} chahiye"
           if stalled else f"{state['ro_id']} stalled nahi hai")
    return {"part_no": ro["part_no"], "is_stalled": stalled, "log": [msg]}


def check_local(state: StallState) -> dict:
    qty = check_local_inventory(state["part_no"])
    msg = f"Local stock: {qty} -> " + ("mil gaya" if qty > 0 else "nahi hai")
    return {"local_qty": qty, "log": [msg]}


def check_sister(state: StallState) -> dict:
    options = check_sister_stores(state["part_no"])
    msg = f"Sister stores: {len(options)} option(s) mile"
    return {"sister_options": options, "log": [msg]}


def check_vendor(state: StallState) -> dict:
    options = check_vendor_stock(state["part_no"])
    msg = f"Vendors: {len(options)} option(s) mile"
    return {"vendor_options": options, "log": [msg]}


# 3) CONDITIONAL EDGES: function ek string return karta hai, jo batati hai agla node kaunsa.
def route_after_detect(state: StallState) -> str:
    return "check_local" if state["is_stalled"] else END


def route_after_local(state: StallState) -> str:
    return END if state["local_qty"] > 0 else "check_sister"


# 4) GRAPH BUILD
def build_graph():
    g = StateGraph(StallState)

    g.add_node("detect_stall", detect_stall)
    g.add_node("check_local", check_local)
    g.add_node("check_sister", check_sister)
    g.add_node("check_vendor", check_vendor)

    g.add_edge(START, "detect_stall")
    g.add_conditional_edges("detect_stall", route_after_detect)
    g.add_conditional_edges("check_local", route_after_local)
    g.add_edge("check_sister", "check_vendor")
    g.add_edge("check_vendor", END)  # Step 2 mein yahan rank_options aayega

    return g.compile()

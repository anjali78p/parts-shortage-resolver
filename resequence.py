"""Step 3: ReAct loop (agent <-> tools) + final plan + Python guardrail."""
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from data import NOW, repair_orders
from schedule_tools import (TOOLS, candidate_ros, compute_idle_window, tech_qualified,
                            to_hhmm, to_hours)


class Move(BaseModel):
    ro_id: str
    new_start: str = Field(description="HH:MM, 24-hour, start time in the idle bay")
    reasoning: str = Field(description="One short sentence")


class ResequencePlan(BaseModel):
    moves: list[Move]
    summary: str = Field(description="2-line summary for the service manager")


SYSTEM_PROMPT = """You are a service-department scheduler at a car dealership.
A repair order is stalled waiting for a part, so its bay and technician would sit idle.
Fill the idle time by pulling forward other scheduled repair orders.

Steps (use the tools, do not guess):
1. Call get_idle_window for the stalled RO.
2. Call find_candidate_ros with the idle window.
3. For each candidate you want to move, call check_technician_skill using the IDLE technician's id.
Only move jobs that are candidates AND whose technician check says qualified=true.
Fit as many jobs as possible without overlapping; try longer jobs first. Times are HH:MM."""


# ---------- NODE 1: conversation shuru karo ----------
def prepare_resequence(state: dict) -> dict:
    best = state["ranked_options"][0]
    task = (f"Stalled RO: {state['ro_id']}. Best part option: {best['name']}, arriving in "
            f"{best['eta_hours']} hours from now (current time {NOW}). Plan how to use the idle bay time.")
    return {"messages": [SystemMessage(SYSTEM_PROMPT), HumanMessage(task)],
            "log": [f"Resequence shuru: part {best['eta_hours']}h mein aayega ({best['name']})"]}


# ---------- NODE 2: LLM (tools ke saath). Tool call kare ya final jawab de ----------
def make_resequence_agent(llm):
    llm_with_tools = llm.bind_tools(TOOLS)

    def resequence_agent(state: dict) -> dict:
        response = llm_with_tools.invoke(state["messages"])
        calls = [f"Agent tool call: {c['name']}({c['args']})" for c in response.tool_calls]
        return {"messages": [response], "log": calls or ["Agent ne research poori ki"]}

    return resequence_agent


# ---------- NODE 3: tools chalao (ToolNode) ----------
def make_run_tools():
    tool_node = ToolNode(TOOLS)

    def run_tools(state: dict) -> dict:
        out = tool_node.invoke(state)
        log = [f"Tool result [{m.name}]: {str(m.content)[:140]}" for m in out["messages"]]
        return {"messages": out["messages"], "log": log}

    return run_tools


# ---------- Guardrail: LLM ka plan Python se verify ----------
def verify_plan(result: ResequencePlan, state: dict) -> tuple[dict, list[str]]:
    ro = repair_orders[state["ro_id"]]
    eta = state["ranked_options"][0]["eta_hours"]
    window = compute_idle_window(state["ro_id"], eta)
    w_start, w_end = to_hours(window["idle_start"]), to_hours(window["idle_end"])
    valid = {c["ro_id"]: c for c in candidate_ros(window["idle_start"], window["idle_end"])["candidates"]}

    accepted, notes = [], []
    for m in result.moves:
        c = valid.get(m.ro_id)
        if c is None:
            notes.append(f"{m.ro_id}: valid candidate nahi hai, hataya")
            continue
        if not tech_qualified(window["tech"], c["job_type"]):
            notes.append(f"{m.ro_id}: tech {window['tech']} {c['job_type']} ke liye qualified nahi, hataya")
            continue
        try:
            start = to_hours(m.new_start)
        except ValueError:
            notes.append(f"{m.ro_id}: time '{m.new_start}' samajh nahi aaya, hataya")
            continue
        end = start + c["duration_hrs"]
        if start < w_start or end > w_end:
            notes.append(f"{m.ro_id}: idle window ke bahar ({m.new_start}), hataya")
            continue
        if any(start < a["_end"] and end > a["_start"] for a in accepted):
            notes.append(f"{m.ro_id}: doosre move se overlap, hataya")
            continue
        accepted.append({"ro_id": m.ro_id, "vehicle": c["vehicle"], "job": c["job"],
                         "bay": window["bay"], "tech": window["tech"],
                         "new_start": to_hhmm(start), "new_end": to_hhmm(end),
                         "original_start": c["original_start"], "reasoning": m.reasoning,
                         "_start": start, "_end": end})
    saved = sum(a["_end"] - a["_start"] for a in accepted)
    for a in accepted:
        a.pop("_start"), a.pop("_end")
    plan = {"stalled_ro": state["ro_id"], "idle_window": window, "moves": accepted,
            "idle_hours_total": window["idle_hours"], "idle_hours_saved": round(saved, 2),
            "stalled_ro_resumes_at": to_hhmm(to_hours(NOW) + eta), "summary": result.summary}
    return plan, notes


# ---------- NODE 4: final structured plan ----------
def make_finalize_plan(llm):
    structured = llm.with_structured_output(ResequencePlan)

    def finalize_plan(state: dict) -> dict:
        result = structured.invoke(state["messages"] + [HumanMessage(
            "Now give the final plan. Include only moves that passed all tool checks.")])
        plan, notes = verify_plan(result, state)
        log = [f"Plan: {len(plan['moves'])} job(s) move honge, {plan['idle_hours_saved']}h idle bachega"]
        log += [f"Guardrail: {n}" for n in notes]
        return {"plan": plan, "log": log}

    return finalize_plan

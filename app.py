"""Streamlit UI. Run with:  streamlit run app.py"""
import copy
import os
import uuid

import streamlit as st
from dotenv import load_dotenv
from langgraph.types import Command

from approval import apply_plan_to
from data import NOW, repair_orders, reset_demo_data
from graph import build_graph
from ranking import get_llm
from ui_components import (AMBER, BLUE, CSS, GREEN, RED, banner_html, board_html, decision_html, esc,
                           header_html, inr, kpi_html, legend_html, log_html, options_html, pill_html,
                           pipeline_html)

load_dotenv()
st.set_page_config(page_title="Parts Shortage Resolver", page_icon="🛠️", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

SCENARIOS = {
    "RO-1042": ("RO-1042 · Honda City brake job",
                "Part missing locally. Full flow: sourcing, ranking, re-planning, approval."),
    "RO-1060": ("RO-1060 · Maruti Swift oil service", "Part is on the shelf. The agent stops early."),
    "RO-1055": ("RO-1055 · Hyundai i20 oil service", "Not stalled. The agent has nothing to do."),
}

# Streamlit reruns this whole script on every click, so anything that must survive lives in session_state.
for key, default in {"status": "idle", "log": [], "visited": [], "before": None, "pending": None,
                     "graph": None, "cfg": None, "final": None, "ro_id": None}.items():
    st.session_state.setdefault(key, default)
ss = st.session_state

# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("### 🛠️ Scenario")
    ro_choice = st.radio("Repair order", list(SCENARIOS), format_func=lambda r: SCENARIOS[r][0],
                         label_visibility="collapsed")
    st.caption(SCENARIOS[ro_choice][1])
    with st.expander("Assumptions"):
        labor_rate = st.number_input("Value of one bay-hour (₹)", min_value=0, value=1500, step=100,
                                     help="Used only for the revenue estimate. A real deployment would use the dealership's labour rate.")
    run_clicked = st.button("Run agent", type="primary", key="run", use_container_width=True)
    st.divider()
    key_ok = bool(os.getenv("GOOGLE_API_KEY"))
    st.markdown(pill_html("API key found" if key_ok else "API key missing", GREEN if key_ok else RED),
                unsafe_allow_html=True)
    st.caption(f"Model: {os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')}  \nOne run makes about 5 LLM calls.")

# ---------------- header + live pipeline strip ----------------
st.markdown(header_html(NOW), unsafe_allow_html=True)
pipe_ph = st.empty()


def draw_pipe():
    pipe_ph.markdown(pipeline_html(set(ss.visited), ss.status), unsafe_allow_html=True)


def run_stream(graph_input):
    """Streams the graph, updates the pipeline strip live, and stores everything in session_state."""
    ss.status = "running"
    draw_pipe()
    with st.status("Agent is working…", expanded=True) as status:
        for update in ss.graph.stream(graph_input, ss.cfg, stream_mode="updates"):
            for node, changes in update.items():
                if node == "__interrupt__":          # graph paused: waiting for the manager
                    ss.pending = changes[0].value
                    continue
                ss.visited.append(node)
                draw_pipe()
                for line in changes.get("log", []):
                    st.write(f"`{node}` {line}")
                    ss.log.append((node, line))
        state = ss.graph.get_state(ss.cfg)
        ss.final = state.values
        waiting = bool(state.next)
        ss.status = "awaiting" if waiting else "done"
        if not waiting:
            ss.pending = None
        status.update(label="Waiting for manager approval" if waiting else "Agent finished",
                      state="running" if waiting else "complete")
    st.rerun()


draw_pipe()

if run_clicked:
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("GOOGLE_API_KEY not found. Add it to your .env file (see .env.example).")
        st.stop()
    reset_demo_data()
    ss.update(status="running", log=[], visited=[], pending=None, final=None, ro_id=ro_choice,
              before=copy.deepcopy(repair_orders), graph=build_graph(get_llm()),
              cfg={"configurable": {"thread_id": f"{ro_choice}-{uuid.uuid4().hex[:6]}"}})
    run_stream({"ro_id": ro_choice, "log": []})

# ---------------- idle state ----------------
if ss.status == "idle":
    reset_demo_data()
    st.markdown(banner_html("info", "Ready when you are",
                            "Choose a scenario on the left and press <b>Run agent</b>. "
                            "The agent finds the part, plans the bay schedule and asks you to approve."),
                unsafe_allow_html=True)
    st.markdown(board_html("Today's bay schedule", f"Live view · demo clock {NOW}", repair_orders, NOW,
                           focus_ro=ro_choice) + legend_html(), unsafe_allow_html=True)
    st.stop()

# ---------------- results ----------------
final, before = ss.final or {}, ss.before
plan = final.get("plan") or {}
ranked = final.get("ranked_options") or []
has_plan = bool(plan.get("moves"))
approved = final.get("approved")
w = plan.get("idle_window", {})

if ss.status == "done" and not has_plan:
    if not final.get("is_stalled"):
        banner = banner_html("info", "Nothing to do",
                             f"{esc(ss.ro_id)} is not waiting on a part, so the agent stopped after the first check.")
    elif final.get("local_qty", 0) > 0:
        banner = banner_html("success", "No shortage",
                             f"{final['local_qty']} unit(s) of {esc(final['part_no'])} are on the local shelf. "
                             "The agent stopped after the local stock check.")
    elif not ranked:
        banner = banner_html("warn", "No sourcing options found",
                             "Neither sister stores nor vendors have the part. Escalate to the service manager.")
    else:
        banner = banner_html("warn", "No job fits the idle window",
                             "The part can still be ordered, but no other job could be pulled forward.")
    st.markdown(banner, unsafe_allow_html=True)
    st.markdown(board_html("Current schedule", "No changes proposed", before, NOW, focus_ro=ss.ro_id)
                + legend_html(), unsafe_allow_html=True)
    if ranked:
        st.markdown("**Part sourcing**")
        st.markdown(options_html(ranked), unsafe_allow_html=True)
else:
    best = ranked[0]
    saved, total = plan["idle_hours_saved"], plan["idle_hours_total"]
    promise_ok = best["meets_promise"]
    st.markdown(kpi_html([
        ("Idle time recovered" if approved else "Recoverable idle time", f"{saved:.1f} h",
         f"of {total:.1f} h idle · Bay {w['bay']}, {w['idle_start']}–{w['idle_end']}", GREEN),
        ("Revenue protected (est.)", inr(saved * labor_rate), f"at {inr(labor_rate)} per bay-hour · assumption", BLUE),
        ("Part arrives in", f"{best['eta_hours']:g} h", f"{best['name']} · {inr(best['total_cost_inr'])}", AMBER),
        ("Customer promise", "On track" if promise_ok else "At risk",
         f"deadline {final['promise_by_hours']:g} h from now", GREEN if promise_ok else RED),
    ]), unsafe_allow_html=True)

    # Decision first (what the manager must do), evidence (boards) below it.
    decision_col, options_col = st.columns(2, gap="large")
    with decision_col:
        if ss.status == "awaiting":
            with st.container(border=True):
                st.markdown(decision_html(final["part_no"], best, plan, before), unsafe_allow_html=True)
                note = st.text_input("Note (optional)", key="note", placeholder="e.g. Technician T-07 confirmed")
                a, r = st.columns(2)
                if a.button("Approve", key="approve", use_container_width=True):
                    run_stream(Command(resume={"approved": True, "note": note}))
                if r.button("Reject", key="reject", use_container_width=True):
                    run_stream(Command(resume={"approved": False, "note": note}))
        elif approved:
            st.markdown(banner_html("success", "Schedule updated",
                                    "<br>".join(esc(c) for c in final["applied_changes"])), unsafe_allow_html=True)
        else:
            st.markdown(banner_html("warn", "Rejected, no changes made",
                                    "The schedule stays as it is. The bay will remain idle until the part arrives."),
                        unsafe_allow_html=True)
    with options_col:
        st.markdown("**Part sourcing**")
        st.markdown(options_html(ranked), unsafe_allow_html=True)

    st.markdown(board_html("Current schedule",
                           f"Bay {w['bay']} sits idle {w['idle_start']}–{w['idle_end']} while {plan['stalled_ro']} waits for its part",
                           before, NOW, focus_ro=ss.ro_id), unsafe_allow_html=True)
    after = copy.deepcopy(before)
    apply_plan_to(after, plan)
    moved = {m["ro_id"]: (before[m["ro_id"]]["bay"], before[m["ro_id"]]["start"]) for m in plan["moves"]}
    if approved:
        title, badge = "Updated schedule", pill_html("Approved", GREEN)
    elif ss.status == "awaiting":
        title, badge = "Proposed schedule", pill_html("Awaiting approval", AMBER)
    else:
        title, badge = "Proposed schedule", pill_html("Rejected · not applied", RED)
    st.markdown(board_html(title,
                           f"{len(moved)} job(s) pulled into Bay {w['bay']} · {saved:.1f} h recovered · "
                           f"{plan['stalled_ro']} resumes at {plan['stalled_ro_resumes_at']}",
                           after, NOW, focus_ro=ss.ro_id, moved=moved, badge=badge) + legend_html(),
                unsafe_allow_html=True)

with st.expander(f"Agent activity · {len(ss.log)} steps"):
    st.markdown(log_html(ss.log), unsafe_allow_html=True)

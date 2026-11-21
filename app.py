"""Step 5: Streamlit UI. Chalane ke liye:  streamlit run app.py"""
import copy
import html
import os
import uuid

import streamlit as st
from dotenv import load_dotenv
from langgraph.types import Command

from approval import apply_plan_to
from data import NOW, repair_orders, reset_demo_data
from graph import build_graph
from ranking import get_llm
from schedule_tools import to_hours

load_dotenv()
st.set_page_config(page_title="Parts Shortage Resolver", page_icon="🛠️", layout="wide")

SCENARIOS = {
    "RO-1042": "Brake job, part nahi hai. Full demo: sister store, vendor, rank, resequence, approval.",
    "RO-1060": "Oil service, part local stock mein hai. Agent turant ruk jata hai.",
    "RO-1055": "Oil service, stalled hi nahi hai. Agent kuch nahi karta.",
}
START_H, END_H, BAYS = 9, 18, (1, 2, 3, 4)

# ---------------- session state (Streamlit har click pe script dobara chalata hai, isliye yahan yaad rakhte hain) ----
for key, default in {"status": "idle", "log": [], "before": None, "pending": None,
                     "graph": None, "cfg": None, "final": None, "ro_id": None}.items():
    st.session_state.setdefault(key, default)
ss = st.session_state


# ---------------- bay board ----------------
def render_board(ros: dict, moved: frozenset = frozenset(), focus_ro: str | None = None) -> str:
    """focus_ro: sirf wahi RO laal 'STALLED' dikhega jo agent abhi handle kar raha hai."""
    colors = {"stalled": ("#f8d7da", "#842029"), "moved": ("#d1e7dd", "#0f5132"),
              "ordered": ("#fff3cd", "#664d03"), "scheduled": ("#cfe2ff", "#084298")}
    th = "".join(f"<th style='font-size:11px;padding:2px'>{h:02d}:00</th>" for h in range(START_H, END_H))
    rows = []
    for bay in BAYS:
        items = sorted((to_hours(r["start"]), rid, r) for rid, r in ros.items() if r["bay"] == bay)
        cells, cursor = [], float(START_H)
        for start, rid, r in items:
            end = min(start + r["duration_hrs"], END_H)
            if start < cursor or start >= END_H:
                continue
            if start > cursor:
                cells.append(f"<td colspan='{round(start - cursor)}' style='border:1px solid rgba(128,128,128,.25)'></td>")
            if rid in moved:
                kind, tag = "moved", "MOVED HERE"
            elif r["status"] == "Waiting on Part" and (focus_ro is None or rid == focus_ro):
                kind, tag = "stalled", "STALLED, bay idle"
            elif r["status"] == "Waiting on Part":
                kind, tag = "scheduled", "(waiting)"
            elif r["status"] == "Part Ordered":
                kind, tag = "ordered", "part ordered"
            else:
                kind, tag = "scheduled", ""
            bg, fg = colors[kind]
            label = (f"<b>{html.escape(rid)}</b> {html.escape(tag)}<br>"
                     f"{html.escape(r['vehicle'])} · {html.escape(r['job'])}")
            cells.append(f"<td colspan='{round(end - start)}' style='background:{bg};color:{fg};padding:4px;"
                         f"border:1px solid rgba(128,128,128,.4);font-size:11px;vertical-align:top'>{label}</td>")
            cursor = end
        if cursor < END_H:
            cells.append(f"<td colspan='{round(END_H - cursor)}' style='border:1px solid rgba(128,128,128,.25)'></td>")
        rows.append(f"<tr><td style='padding:4px;font-weight:600'>Bay {bay}</td>{''.join(cells)}</tr>")
    return (f"<table style='width:100%;border-collapse:collapse;table-layout:fixed'>"
            f"<tr><th style='width:56px'></th>{th}</tr>{''.join(rows)}</table>")


# ---------------- graph streaming ----------------
def run_stream(graph_input):
    """Graph ko stream karta hai, live steps dikhata hai, aur log ko session_state mein jama karta hai."""
    with st.status("Agent kaam kar raha hai...", expanded=True) as status:
        for update in ss.graph.stream(graph_input, ss.cfg, stream_mode="updates"):
            for node, changes in update.items():
                if node == "__interrupt__":
                    ss.pending = changes[0].value
                    continue
                st.markdown(f"**{node}**")
                for line in changes.get("log", []):
                    st.write("• " + line)
                    ss.log.append((node, line))
        ss.final = ss.graph.get_state(ss.cfg).values
        waiting = bool(ss.graph.get_state(ss.cfg).next)
        ss.status = "awaiting" if waiting else "done"
        if not waiting:
            ss.pending = None
        status.update(label="Manager approval ka intezaar..." if waiting else "Agent ka kaam poora",
                      state="running" if waiting else "complete")
    st.rerun()


# ---------------- sidebar ----------------
st.sidebar.header("Demo scenario")
ro_choice = st.sidebar.radio("Repair Order", list(SCENARIOS), format_func=lambda r: r)
st.sidebar.caption(SCENARIOS[ro_choice])
labor_rate = st.sidebar.number_input("Assumption: bay-hour ki value (Rs)", min_value=0, value=1500, step=100,
                                     help="Revenue protected ka estimate nikalne ke liye. Real number dealership se aayega.")
run_clicked = st.sidebar.button("▶ Run agent", type="primary", key="run", use_container_width=True)
st.sidebar.caption("Har run pe demo data reset hota hai. Free-tier API ek run mein ~5 LLM calls leti hai.")

st.title("🛠️ Service Parts Shortage Resolver")
st.caption(f"LangGraph agent: part atakne par sister store/vendor check karta hai aur bay idle na rahe iske liye "
           f"schedule resequence karta hai. Demo time: {NOW}")

if run_clicked:
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("GOOGLE_API_KEY nahi mili. .env file mein daalo (.env.example dekho).")
        st.stop()
    reset_demo_data()
    ss.update(status="running", log=[], pending=None, final=None, ro_id=ro_choice,
              before=copy.deepcopy(repair_orders), graph=build_graph(get_llm()),
              cfg={"configurable": {"thread_id": f"{ro_choice}-{uuid.uuid4().hex[:6]}"}})
    run_stream({"ro_id": ro_choice, "log": []})

# ---------------- main area ----------------
if ss.status == "idle":
    st.info("Left se scenario chuno aur **Run agent** dabao.")
    st.markdown("**Abhi ka bay schedule**")
    st.markdown(render_board(repair_orders), unsafe_allow_html=True)
    st.stop()

final = ss.final or {}
plan = final.get("plan") or {}

# metrics
if plan.get("moves"):
    best = final["ranked_options"][0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bay idle hoti (bina agent)", f"{plan['idle_hours_total']} h")
    c2.metric("Idle time bacha", f"{plan['idle_hours_saved']} h")
    c3.metric("Revenue protected (est.)", f"Rs {plan['idle_hours_saved'] * labor_rate:,.0f}")
    c4.metric("Part", f"{best['eta_hours']} h", f"Rs {best['total_cost_inr']:,.0f} · {best['name']}", delta_color="off")

# boards
moved = frozenset(m["ro_id"] for m in plan.get("moves", []))
left, right = st.columns(2)
with left:
    st.markdown("**Pehle (agent se pehle)**")
    st.markdown(render_board(ss.before, focus_ro=ss.ro_id), unsafe_allow_html=True)
with right:
    if ss.status == "awaiting" and plan.get("moves"):
        preview = copy.deepcopy(ss.before)
        apply_plan_to(preview, plan)
        st.markdown("**Proposed (approve hone par)**")
        st.markdown(render_board(preview, moved, ss.ro_id), unsafe_allow_html=True)
    elif final.get("approved"):
        st.markdown("**Baad mein (approved)**")
        st.markdown(render_board(repair_orders, moved, ss.ro_id), unsafe_allow_html=True)
    else:
        st.markdown("**Baad mein**")
        st.caption("Koi schedule change nahi hua.")

# agent steps
with st.expander("Agent ke steps", expanded=(ss.status != "awaiting")):
    for node, line in ss.log:
        st.write(f"`{node}` {line}")

# ranked options
if final.get("ranked_options"):
    with st.expander("Part options (ranked)", expanded=True):
        for o in final["ranked_options"]:
            ok = "✅" if o["meets_promise"] else "❌"
            st.write(f"**#{o['rank']} {o['name']}** · {o['eta_hours']} h · Rs {o['total_cost_inr']:,.0f} · "
                     f"customer promise {ok}  \n{o['reasoning']}")

# approval
if ss.status == "awaiting":
    st.divider()
    st.subheader("Manager approval chahiye")
    st.write(f"**Part:** {ss.pending['part_order']}")
    for m in plan["moves"]:
        st.write(f"- **{m['ro_id']}** ({m['job']}): {m['original_start']} → {m['new_start']}-{m['new_end']}, "
                 f"bay {m['bay']}  \n  _{m['reasoning']}_")
    note = st.text_input("Note (optional)", key="note")
    a, r, _ = st.columns([1, 1, 4])
    if a.button("✅ Approve", type="primary", key="approve"):
        run_stream(Command(resume={"approved": True, "note": note}))
    if r.button("❌ Reject", key="reject"):
        run_stream(Command(resume={"approved": False, "note": note}))

# result
if ss.status == "done":
    st.divider()
    if not final.get("is_stalled"):
        st.info(f"{ss.ro_id} stalled nahi hai, agent ko kuch karna nahi tha.")
    elif final.get("local_qty", 0) > 0:
        st.success(f"Part local stock mein hai ({final['local_qty']} pcs). Koi shortage nahi, graph yahin ruk gaya.")
    elif not final.get("ranked_options"):
        st.warning("Koi sister store ya vendor option nahi mila. Manager ko escalate karo.")
    elif not plan.get("moves"):
        st.warning("Idle bay mein fit hone wala koi job nahi mila.")
    elif final.get("approved"):
        st.success("APPROVED. Schedule update ho gaya:")
        for c in final["applied_changes"]:
            st.write("- " + c)
    else:
        st.warning("REJECTED. Schedule mein koi badlav nahi hua.")

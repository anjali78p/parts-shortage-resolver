Service Parts Shortage Resolver Agent

Tek Qubit Hackathon · Theme 1: AI & Automation (Intelligent Solutions for Operations)

An agentic AI system that detects a repair order stalled on a missing part, finds the fastest way to get that part, and re-sequences the schedule so the service bay never sits idle. A service manager approves every change before it is applied.

Bay board: before vs proposed

The problem

When a repair order (RO) is waiting on a part, its bay and technician sit idle while the service advisor makes phone calls: check the local shelf, ask sister stores, ring vendors, then manually shuffle other jobs. This takes time, depends on who is on shift, and idle bay-hours are lost revenue.

What the agent does
Detects the stalled RO and the part it needs.
Checks sources in order: local stock, sister stores, vendors.
Ranks the options against the customer's promise deadline, then cost, then speed.
Finds the idle window (from now until the part arrives) and fills it with other scheduled jobs whose parts are already in stock and whose technician is qualified.
Asks the manager to approve the part order and the new schedule. Only after approval does anything change.
Demo scenario (RO-1042)
	
Stalled job	Honda City, brake job, part BP-221, bay 3 at 10:00
Local stock	0
Best option	Store B: 3 h, Rs 2,000, meets the 8 h customer promise
Idle window	Bay 3, 10:00 to 12:00 (2 bay-hours)
Agent's plan	Pull forward RO-1055 (oil service) and RO-1070 (wipers) into bay 3
Rejected by the agent	RO-1080 (part not in local stock) and RO-1090 (technician T-07 not qualified for coolant flush)
Result	2.0 of 2.0 idle bay-hours reclaimed; RO-1042 resumes at 12:00
How it works

Built with LangGraph. The graph has conditional edges (it stops early when there is nothing to solve), a tool-calling loop, and a human approval gate.

not stalled
stalled
part in local stock
not in stock
no options
tool call
research done
no job fits
approve
reject
START
detect_stall
END
check_local
check_sister
check_vendor
rank_options (LLM +guardrail)
prepare_resequence
resequence_agent (LLM +tools)
tools
finalize_plan (LLM +guardrail)
human_approval (interrupt)
apply_schedule
Node	Type	Role
detect_stall, check_local, check_sister, check_vendor	Plain code	Deterministic lookups
rank_options	LLM, structured output	Ranks part options and explains why
resequence_agent + tools	LLM with tools (ReAct loop)	Calls get_idle_window, find_candidate_ros, check_technician_skill
finalize_plan	LLM, structured output	Produces the final move list
human_approval	interrupt() + checkpointer	Pauses the graph until the manager decides
apply_schedule	Plain code	Runs only after approval
Design decisions

The LLM judges, code verifies. Numbers, deadlines and constraints are computed in Python. The LLM only decides and explains. After every LLM step, a guardrail re-checks the output against the source of truth:

rank_options: costs, ETAs and the deadline flag are overwritten from real data, invented options are dropped, and the LLM's order is compared with a rule-based order.
finalize_plan: every proposed move must be a valid candidate, the technician must be qualified, it must fit inside the idle window, and it must not overlap another move.

This came from a real bug found during development: the LLM added a transfer fee twice and quoted Store B at Rs 2,400 instead of Rs 2,000, which flipped the ranking. Guardrails now catch this class of error.

Human in the loop. The agent proposes, a manager decides. The graph is paused with LangGraph's interrupt(), and its state is held by a checkpointer until the manager approves or rejects. Nothing touches the schedule before that.

Testable without an API key. A scripted FakeLLM (which deliberately makes mistakes) lets the whole graph, the guardrails, the approval flow and the Streamlit UI be tested offline.

Business impact

The metric the app reports is idle bay-hours reclaimed. In the demo scenario that is 2.0 hours that would otherwise have been lost.

The UI also shows an estimated revenue protected figure: reclaimed hours multiplied by a bay-hour value. The default (Rs 1,500) is an illustrative assumption, adjustable in the sidebar. A real deployment would use the dealership's own labour rate. We make no claim about industry-wide savings.

Other expected benefits: faster response than manual phone calls, a consistent decision that does not depend on who is on shift, and an audit trail of every step the agent took.

Tech stack

Python · LangGraph · LangChain · Google Gemini (via langchain-google-genai) · Pydantic · Streamlit

Quick start
bash
git clone <this-repo>
cd parts-shortage-resolver
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # add your GOOGLE_API_KEY (free key from Google AI Studio)

streamlit run app.py             # UI
python main.py RO-1042           # terminal version (add --approve or --reject to skip the prompt)

The model name is read from GEMINI_MODEL in .env, because model names change over time.

Try three scenarios in the UI sidebar:

RO-1042: full flow, ends with the approval step.
RO-1060: part is in local stock, so the graph stops early.
RO-1055: RO is not stalled, so the agent does nothing.
Tests (no API key needed)
bash
python test_graph_offline.py     # graph wiring, guardrails, approve/reject flow
python test_ui_offline.py        # Streamlit UI flows
Project structure
app.py                Streamlit UI (bay board, live agent steps, approval buttons)
main.py               Terminal runner
graph.py              LangGraph state and wiring
ranking.py            Part-option ranking node + guardrail
resequence.py         Tool-calling agent, plan node, plan guardrail
approval.py           Human approval (interrupt) and applying the schedule
schedule_tools.py     Tools the agent can call
tools.py              Inventory and vendor lookups
data.py               Mock data (ROs, stores, vendors, technicians)
fake_llm.py           Scripted LLM for offline tests
Limitations and next steps
Mock data. Inventory, schedules and vendors are simulated. A real version needs integration with the dealership management system (DMS) and vendor APIs.
In-memory state. The checkpointer is MemorySaver; a production version would use a persistent store such as SQLite or Postgres.
One stalled RO at a time. Handling several at once would need coordination so they do not compete for the same idle bay or the same parts.
No stock reservation. Parts used in a plan are not reserved against other jobs.
Fixed schedule rules. Technician skill and bay fit are modelled simply; real shops also have breaks, shifts and bay equipment limits.
Next: trigger the agent automatically when an RO changes to "Waiting on Part", and notify the customer of the new timeline (links naturally to Theme 3: Proactive Service Status Companion).